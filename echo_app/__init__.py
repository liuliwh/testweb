import logging

from flask import Flask
from flask_cors import CORS
import os


logging.basicConfig(
    format="[%(asctime)s] %(levelname)s in %(lineno)d : %(module)s: %(message)s",
    level=logging.INFO,
)


app = Flask(__name__)


CORS(
    app,
    origins=os.environ.get("CORS_ORIGIN", "http://localhost:8080").split(','),
    allow_headers=["x-is-ajax", "X-Is-Ajax"],
    supports_credentials=True,
)
