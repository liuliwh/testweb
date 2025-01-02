import logging

from flask import Flask
from flask_cors import CORS

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s in %(lineno)d : %(module)s: %(message)s",
    level=logging.INFO,
)

app = Flask(__name__)
CORS(
    app,
    origins=[
        "https://masterapp3.riversecurity.com.cn",
        "https://workerapp3.riversecurity.com.cn",
        "https://plugin.riversecurity.com.cn",
        "http://plugin.riversecurity.com.cn",
    ],
    allow_headers=["x-is-ajax", "X-Is-Ajax"],
    supports_credentials=True,
)
