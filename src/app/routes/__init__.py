from flask import Flask
from src.app.controllers.ctd import ctd
from src.app.controllers.minidot import minidot

def routes(app: Flask):
    app.register_blueprint(ctd)
    app.register_blueprint(minidot)