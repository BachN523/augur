
import os
from sqlalchemy.dialects.postgresql import insert
import sqlalchemy as s
import pandas as pd
import json

# from db_models import *
from config import AugurConfig

from random_key_auth import RandomKeyAuth


#TODO: setup github headers in a method here.
#Encapsulate data for celery task worker api


#TODO: Test all methods
class TaskSession(s.orm.Session):

    ROOT_AUGUR_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    def __init__(self,logger,config={},platform='github'):
        self.logger = logger
        
        self.root_augur_dir = TaskSession.ROOT_AUGUR_DIR
        self.__init_config(self.root_augur_dir)
        
        DB_STR = f'postgresql://{self.config["user_database"]}:{self.config["password_database"]}@{self.config["host_database"]}:{self.config["port_database"]}/{self.config["name_database"]}'

        self.config.update(config)
        self.platform = platform
        
        #print(f"path = {str(ROOT_AUGUR_DIR) + "augur.config.json"}")
        
        self.__engine = s.create_engine(DB_STR)

        keys = self.get_list_of_oauth_keys()

        self.oauths = RandomKeyAuth(keys)

        super().__init__(self.__engine)

    def __init_config(self, root_augur_dir):
        #Load config.
        self.augur_config = AugurConfig(self.root_augur_dir)
        self.config = {
            'host': self.augur_config.get_value('Server', 'host')
        }
        self.config.update(self.augur_config.get_section("Logging"))

        self.config.update({
            'capture_output': False,
            'host_database': self.augur_config.get_value('Database', 'host'),
            'port_database': self.augur_config.get_value('Database', 'port'),
            'user_database': self.augur_config.get_value('Database', 'user'),
            'name_database': self.augur_config.get_value('Database', 'name'),
            'password_database': self.augur_config.get_value('Database', 'password'),
            'key_database' : self.augur_config.get_value('Database', 'key')
        })

        print(self.config)

    
    @property
    def access_token(self):
        try:
            return self.__oauths.get_key()
        except:
            self.logger.error("No access token in queue!")
            return None

    
    def execute_sql(self, sql_text):
        connection = self.__engine.connect()

        return connection.execute(sql_text)
    
    def insert_data(self, data, table, natural_keys):

        self.logger.info(f"Length of data to insert: {len(data)}")
        self.logger.info(type(data))

        if type(data) != list:
            self.logger.info("Data must be a list")
            return

        if type(data[0]) != dict:
            self.logger.info("Must be list of dicts")
            return

        table_stmt = insert(table)
        for value in data:
            insert_stmt = table_stmt.values(value)
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=natural_keys, set_=dict(value))
            result = self.execute_sql(insert_stmt)


def get_list_of_oauth_keys(self, db_engine, config_key):

    oauthSQL = s.sql.text(f"""
            SELECT access_token FROM augur_operations.worker_oauth WHERE access_token <> '{config_key}' and platform = 'github'
            """)

    oauth_keys_list = [{'access_token': config_key}] + json.loads(
        pd.read_sql(oauthSQL, db_engine, params={}).to_json(orient="records"))

    return oauth_keys_list

    