import os
import certifi
from flask import Flask
from flask_cors import CORS
from pymongo import MongoClient
from src.app.config import app_config


app = Flask(__name__)
app.config.from_object(app_config[os.getenv("FLASK_ENV")])
mongo = client = MongoClient(os.getenv("MONGO_URI"), tls=True, tlsCAFile=certifi.where())
mongo_client = mongo["fotoagua"]
CORS(app)
