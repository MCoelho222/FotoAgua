from flask import Blueprint
from flask.wrappers import Response
from src.app import mongo_client
from bson import json_util
from flask import request, jsonify

ctd = Blueprint("ctd", __name__, url_prefix="/ctd")

@ctd.route("/", methods=['GET'])
def get_data():
    return "Hello, world!"