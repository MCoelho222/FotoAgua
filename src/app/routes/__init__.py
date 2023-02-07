from flask import Flask
from src.app.controllers.ctd import ctd

def routes(app: Flask):
    app.register_blueprint(ctd)