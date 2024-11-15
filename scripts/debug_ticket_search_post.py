# import csv
import json
import logging
import os
import sys
from pathlib import Path
import requests

sys.path.append(str(Path(__file__).parent.parent))

# from app import config
from app import variables as vars
from api import iiq
from app import config

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s"
)

# Create a logs subdirectory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(logs_dir, exist_ok=True)

# Create a file handler for each log level
debug_handler = logging.FileHandler(
    os.path.join(logs_dir, "debug.log"), mode="a"
)
debug_handler.setLevel(logging.DEBUG)
info_handler = logging.FileHandler(
    os.path.join(logs_dir, "info.log"), mode="a"
)
info_handler.setLevel(logging.INFO)
warning_handler = logging.FileHandler(
    os.path.join(logs_dir, "warning.log"), mode="a"
)
warning_handler.setLevel(logging.WARNING)
error_handler = logging.FileHandler(
    os.path.join(logs_dir, "error.log"), mode="a"
)
error_handler.setLevel(logging.ERROR)

# Add the handlers to the root logger
logging.getLogger().addHandler(debug_handler)
logging.getLogger().addHandler(info_handler)
logging.getLogger().addHandler(warning_handler)
logging.getLogger().addHandler(error_handler)


payload_str = "{'Filters': [{'Facet': 'asset','Id': '3899fb02-14d9-4b8d-a89b-18136e05db01'},{'Facet': 'user','Id': '4227b755-0c8c-4507-ad2b-2ac0216da8ce'},]}"
payload_dict = {
    "Filters": [
        {"Facet": "asset", "Id": "3899fb02-14d9-4b8d-a89b-18136e05db01"},
        {"Facet": "user", "Id": "4227b755-0c8c-4507-ad2b-2ac0216da8ce"},
    ]
}

func_response = iiq.call_api(
    vars.tickets_url,
    method="POST",
    iiq_payload=payload_str,
)
logging.info(f"Function response as STR {func_response}")
func_response2 = iiq.call_api(
    vars.tickets_url, method="POST", iiq_payload=payload_dict
)
logging.info(f"Function response as DICT {func_response2}")

raw_response = requests.post(
    vars.tickets_url, data=payload_str, headers=config.set_headers()
)
raw_response_json = raw_response.json()
logging.info(f"Raw response as STR {raw_response_json}")

raw_response2 = requests.post(
    vars.tickets_url, data=payload_dict, headers=config.set_headers()
)
raw_response_json = raw_response2.json()
logging.info(f"Raw response as DICT {raw_response_json}")

payload_json = json.dumps(payload_dict)
raw_response3 = requests.post(
    vars.tickets_url, json=payload_json, headers=config.set_headers()
)
raw_response_json = raw_response3.json()
logging.info(f"Raw response as JSON {raw_response_json}")


payload_json = json.dumps(payload_dict)
raw_response3 = requests.post(
    vars.tickets_url, data=payload_json, headers=config.set_headers()
)
raw_response_json = raw_response3.json()
logging.info(f"Raw response as DICT → data {raw_response_json}")
