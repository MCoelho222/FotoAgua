import os
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())

class Development(object):
    TESTING = True
    FLASK_DEBUG = os.getenv("FLASK_DEBUG")
    MONGO_URI = os.getenv("MONGO_URI")
    SECRET_KEY = os.getenv("SECRET_KEY")

class Production(object):
    TESTING = False 
    FLASK_DEBUG = os.getenv("FLASK_DEBUG")
    MONGO_URI = os.getenv("MONGO_URI")
    SECRET_KEY = os.getenv("SECRET_KEY")

app_config = {
    "development": Development,
    "production": Production
}
