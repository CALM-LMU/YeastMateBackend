import os

from flask import Flask
from flask_cors import CORS
from huey import  SqliteHuey

DEBUG = True

app = Flask(__name__)
app.config.from_object(__name__)

CORS(app)

huey =  SqliteHuey()
