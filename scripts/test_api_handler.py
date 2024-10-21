import json
import logging
import os
import sys
from pathlib import Path

import app.variables as vars
from api import iiq as iiq

sys.path.append(str(Path(__file__).parent.parent))


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

# Get all locations - Works
# data = iiq.get_all_locations()
# print(data)

# Get all rooms at a location_id - Works
# location_id = "f12ca8b4-190e-ef11-96f5-000d3a0e23bd"
# room_data = iiq.get_rooms_at_location(location_id)
# print(room_data)

# Get Room info by Room ID - Works
# room_id = "aa21012b-9b90-4b5e-a48c-5040437bdaa0"
# room_data = iiq.get_room_by_id(room_id)
# print(room_data)

# Assign user to room with raw post - Works
# user_id = "297614d1-58ba-49ca-82f1-16fdeb9faff3"
# room_id = "56f2bc93-059c-4ca2-9165-94d3379c38e9"
# url = vars.users_url + "/" + user_id + "/rooms"
# payload = json.dumps([room_id])
# iiq.call_api(url, method="POST", iiq_payload=payload)

# email = "lcampbell@wusd.org"
# user_data = iiq.get_user_id_by_email(email) # Works
# print(user_data)

# Get all users from IIQ via function - Works
# user_data = iiq.get_all_users()
# print(user_data)

# Get all assigned rooms for a user - Works
# user_id = "297614d1-58ba-49ca-82f1-16fdeb9faff3"
# user_data = iiq.get_assigned_rooms_for_user_id(user_id)
# assigned_rooms = []
# for i in user_data:
#     room_dict = {
#     'LocationName': i['LocationName'],
#     'LocationId': i['LocationId'],
#     'LocationRoomName': i['Name'],
#     'LocationRoomId': i['LocationRoomId']
#     }
#     assigned_rooms.append(room_dict)
# print(assigned_rooms)

# Modify a user's assigned rooms with function - Works
# user_id = "297614d1-58ba-49ca-82f1-16fdeb9faff3"
# # room_id = "56f2bc93-059c-4ca2-9165-94d3379c38e9" # Add Room ID
# # room_id = "" # Remove Room ID
# # room_id = ["56f2bc93-059c-4ca2-9165-94d3379c38e9", "f33554a5-4ef2-48f8-a021-289ce0159f10"] # Multiple Rooms
# iiq.modify_assigned_rooms(user_id, room_id)

# Get all classes with a function - Works
# response = iiq.get_all_classes()
# print(response)

# Get info about a specific class by ID via function - Works
# class_id = "338892b9-de8a-46a5-9327-c44893d65fdc"
# response = iiq.get_class_info(class_id)
# print(response)

# Get all classes for a userID - Works
# user_id = "991f5394-035e-4e8d-8099-dd41b6bf57dc"
# classes = iiq.get_classes_for_user(user_id)
# print(classes)

# Get all assets - Works
# assets = iiq.get_assets()
# print(assets[0]["AssetId"]) # Print the first asset ID from the results

# Get Asset by ID - Works
# asset_id = "1b56d2eb-9bbc-42ff-a183-a8d6e3ecdcea"
# asset = iiq.get_asset_by_id(asset_id)
# print(asset)

# Get Asset by Serial Number - Works
# serial_number = "YX0BP6NA"
# asset = iiq.get_asset_by_serial(serial_number)
# print(asset)

# Get Asset status Types - Works
# asset_types = iiq.get_asset_status_types()
# print(asset_types)

# Get Assets with Filter. WIP, not real ID or asset type ID. Need to figure out how to get those
# filter = {"Filters":[{"Facet":"location","Id":"ca6ffef3-cb32-40cb-a62c-7b1068b5cc21","Negative":false},{"Facet":"AssetType","Id":"2a1561e5-34ff-4fcf-87de-2a146f0e1c01"}]}
# assets = iiq.get_assets(filter=filter)
# print(assets[0]["AssetId"])

# Get status type based on name of status - Works
# status = "Broken"
# asset_types = iiq.get_asset_status_types()
# for i in asset_types:
#     # Get the AssetStatusTypeId based on the Name value
#     asset_status_type_id = i.get('AssetStatusTypeId', None) if i.get('Name') == 'Broken' else None
#     if not asset_status_type_id:
#         pass
#     else:
#         print(asset_status_type_id)

# Get all corporate Intune devices
# Need to string together 2 searches. 1 where "App Link(s) = Microsoft Intune"
# Step 1 validate Intune device by checking asset["Items"]["Data Mappings"]["Model"]["AppId"] = "microsoftIntune"
# Step 2 for each asset["Items"]["Data Mappings"]["Lookups"] check if Key = ExternalId. If yes, pull "Value"
# Step 3 POST to "https://wusd-org.incidentiq.com/apps/microsoftIntune/api/microsoftIntune/data/assets/search" with this JSON: "{
#     "AssetId": "af081be8-1055-4715-927a-e6fd8d662691",
#     "AssetTag": "G3H5H02",
#     "SerialNumber": "G3H5H02",
#     "Skip": 0,
#     "Limit": 1
# }"
# response JSON should have asset["ExternalId"] == asset["Items"]["Data Mappings"]["Lookups"][1]["Value"] and asset["CustomFields"]["ManagedDeviceOwnerType"] == "Company"
assets = iiq.get_assets()
intune_assets = []
company_assets = []
personal_assets = []
for i in assets:
    try:
        if i["DataMappings"]["Model"]["AppId"] == "microsoftIntune":
            intune_assets.append(i)
    except KeyError:
        continue

for i in intune_assets:
    try:
        for id in i["DataMappings"]["Lookups"]:
            try:
                if id["Key"] == "ExternalId":
                    external_id = id["Value"]
            except KeyError as e:
                logging.debug(f"No such key: {e}")
                continue
        asset_id = i["AssetId"]
        asset_tag = i["AssetTag"]
        serial_number = i["SerialNumber"]
    except KeyError as e:
        logging.debug(f"No such key: {e}")
        continue

    asset = {
        "AssetId": asset_id,
        "AssetTag": asset_tag,
        "SerialNumber": serial_number,
        "Skip": 0,
        "Limit": 1,
    }
    asset_payload = json.dumps(asset.copy())
    asset_query = iiq.call_intune_api(
        vars.ms_api_search, "POST", iiq_payload=asset_payload
    )
    if asset_query:
        logging.debug(f"Type: {type(asset_query)} | Len: {
                      len(asset_query)} | Values: {asset_query}")

    try:
        if (
            asset_query["ExternalId"] == external_id
            and asset_query["CustomFields"]["ManagedDeviceOwnerType"]
            == "Company"
        ):
            # asset["ExternalId"] = external_id
            asset["CompanyDevice"] = True
            asset.pop("Skip", None)
            asset.pop("Limit", None)
            company_assets.append(asset)
        elif (
            asset_query["ExternalId"] == external_id
            and asset_query["CustomFields"]["ManagedDeviceOwnerType"]
            == "Personal"
        ):
            # asset["ExternalId"] = external_id
            asset["CompanyDevice"] = False
            asset.pop("Skip", None)
            asset.pop("Limit", None)
            personal_assets.append(asset)
    except KeyError as e:
        logging.debug(f"No such key: {e}")
        continue

logging.debug(f"Company Assets: {company_assets}")
logging.debug(f"Personal Assets: {personal_assets}")

# Unassign personal Intune devices
# for asset in personal_assets:
#     #Step 1, query asset for owner
#     owner = iiq.get_asset_by_id(asset["AssetId"])
#     if owner["OwnerId"] is not None:
#         #Step 2, if not blank, clear owner
#         iiq.update_owner(asset_id, owner_id)
#     else:
#         continue

# Assign Zoom devices to IIQ Owners

# Payload format for POST search queries as JSON /assets endpoint
# {
#     "Filters":
#     [
#         {
#             "Facet":"location", #JSON attribute (location, assetType, AssutStatusTypeId)
#             "Id":"ca6ffef3-cb32-40cb-a62c-7b1068b5cc21", # Value to filter by
#             "Negative":false
#         },
#         {
#             "Facet":"AssetType",
#             "Id":"2a1561e5-34ff-4fcf-87de-2a146f0e1c01"
#         }
#     ]
# }
