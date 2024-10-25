# import csv
# import json
import logging
import os
import sys
from pathlib import Path
import datetime

sys.path.append(str(Path(__file__).parent.parent))

# from app import config
# from app import variables as vars
from app import helper
from api import google_api as elgoog
from api import iiq

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

data = [
    {"Header1": "Row 1", "Header2": "Row 1"},
    {"Header1": "Row2", "Haeder2": "Row2"},
]
svc_creds = elgoog.load_google_credentials()
today = datetime.date.today()
date_string = today.strftime("%Y-%m-%d")
file_name = date_string + " Frequent Fliers"
folder_id = "0AMCxmb-RqkwpUk9PVA"

# sheet_id = elgoog.create_sheet(folder_id, file_name, svc_creds)
sheet_id = "1UX0I2iCCzDpBMsKEOOpB-iUjI0HAx_BT438HFLPpbqg"
sheet = elgoog.get_spreadsheet(sheet_id, svc_creds)
# logging.info(sheet)
# values = helper.convert_to_sheets(data)
# result = elgoog.update_values(
#     sheet_id, "A:I", "USER_ENTERED", values, svc_creds
# )
# print(result)

locations = iiq.get_all_locations()

data_tab_name = "Data"
rename_first_sheet = {
    "requests": [
        {
            "updateSheetProperties": {
                "properties": {"sheetId": 0, "title": data_tab_name},
                "fields": "title",
            }
        },
    ]
}
hide_first_sheet = {
    "requests": [
        {
            "updateSheetProperties": {
                "properties": {"sheetId": 0, "hidden": True},
                "fields": "hidden",
            }
        },
    ]
}
update_tab = elgoog.update_sheet(sheet_id, svc_creds, body=rename_first_sheet)


def create_subsheets(sheet_id):
    for loc in locations:
        if not loc["Abbreviation"]:
            continue
        if loc["Abbreviation"] in ["MOT", "M&O", "WCR"]:
            continue
        requests = [
            {"addSheet": {"properties": {"title": loc["Abbreviation"]}}}
        ]
        body = {"requests": requests}
        resp = elgoog.update_sheet(sheet_id, svc_creds, body)
        logging.info(resp)
        # tab_id = resp["replies"][0]["addSheet"]["properties"]["sheetId"]
        query = [
            [
                f"=query('{data_tab_name}'!1:1000,\"select * where C='{loc["Name"]}' order by C,B,F\",1)"
            ]
        ]
        range = f"'{loc["Abbreviation"]}'!A1"

        update_resp = elgoog.update_values(
            spreadsheet_id=sheet_id,
            range_name=range,
            value_input_option="USER_ENTERED",
            values=query,
            creds=svc_creds,
        )
        logging.info(update_resp)


create_subsheets(sheet_id)
elgoog.update_sheet(sheet_id, svc_creds, body=hide_first_sheet)
# requests = [
#     {
#         "updateSheetProperties": {
#             "properties": {"sheetId": 0, "hidden": True},
#             "fields": "hidden",
#         }
#     }
# ]
