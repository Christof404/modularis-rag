from dotenv import load_dotenv
import os


class Config:
    def __init__(self, env_path='.env', reload=True):
        if reload:
            load_dotenv(dotenv_path=env_path)
        # otherwise the env variables are already set

    @staticmethod
    def get_db_dsn():
        return os.getenv("DB_DSN")