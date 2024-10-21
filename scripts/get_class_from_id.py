import os
import logging
import sys
from pathlib import Path
from collections import OrderedDict

sys.path.append(str(Path(__file__).parent.parent))

from app import config as config
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

# sis_url = "/sis/classes/"
# class_id = "338892b9-de8a-46a5-9327-c44893d65fdc"
# url = url = app_vars.base_url + sis_url + class_id
# headers = config.set_headers()
# response = classes.get_class_info(url, headers)

# # Process the response data (e.g., convert to JSON if applicable)
# if response.ok:
#   data = response.json()
#   # Do something with the class data
#   print(data["Item"]["LocationName"])

# Get info about a specific class by ID via function - Works
# class_id = "338892b9-de8a-46a5-9327-c44893d65fdc"
# response = iiq.get_class_info(class_id)
# print(response)

# Get all classes for a userID - Works
# user_id = "991f5394-035e-4e8d-8099-dd41b6bf57dc"
# classes = iiq.get_classes_for_user(user_id)
# print(classes)

all_users = iiq.get_all_users()
all_classes = iiq.get_all_classes()
all_roles = iiq.get_role_ids()
all_locations = iiq.get_all_locations()
faculty_id = all_roles["Faculty"]
staff_id = all_roles["Staff"]
user_list = []
rooms_list = []

# Process all rooms at each location, get locationID, room ID and Room Name (Room Number)
logging.debug("=============all_locations===============")
logging.debug(all_locations)
for location in all_locations:
    location_id = location["LocationId"]
    all_rooms = iiq.get_rooms_at_location(location_id)
    if all_rooms:
        for class_room_number in all_rooms:
            room_dict = {}
            room_dict["RoomNumber"] = class_room_number["Name"]
            room_dict["RoomId"] = class_room_number["LocationRoomId"]
            room_dict["LocationId"] = location_id
            rooms_list.append(room_dict)
    else:
        continue

# Drop duplicates
unique_room_list = list(
    OrderedDict(
        (frozenset(item.items()), item) for item in rooms_list
    ).values()
)
logging.debug("=============unique_room_list===============")
logging.debug(unique_room_list)
# for class_room_number in unique_room_list:
#     logging.debug(class_room_number)

# Process all class data. Get classroom number and locationId
class_list = []
for data in all_classes:
    class_dict = {}
    try:
        class_dict["RoomNumber"] = data["LocationDetails"]
        class_dict["LocationId"] = data["LocationId"]
        class_dict["ClassId"] = data["SisClassId"]
        class_list.append(class_dict)
    except KeyError:
        continue

# Drop duplicates
unique_class_list = list(
    OrderedDict(
        (frozenset(item.items()), item) for item in class_list
    ).values()
)
logging.debug("==============unique_class_list==============")
logging.debug(unique_class_list)

combined_classrooms_list = [
    {**dict1, **dict2}
    for dict1 in unique_class_list
    for dict2 in unique_room_list
    if dict1["RoomNumber"] == dict2["RoomNumber"]
    and dict1["LocationId"] == dict2["LocationId"]
]

logging.debug("==============combined_classrooms_list==============")
logging.debug(combined_classrooms_list)

for cr in combined_classrooms_list:
    logging.debug(cr)
logging.debug(len(combined_classrooms_list))

# Parse through all users for faculty / staff. Find any courses they're tied to. Parse through the combined class list to match SisClassId. Add RoomId to a list
# Grab the user's existing assigned rooms, append the UserIds to the list and dedupe. If new list == old list, do nothing, otherwise update user with
# new assigned rooms.


# for user in all_users:
#     # logging.debug(users["UserId"])
#     user_id = user["UserId"]
#     role_id = user["RoleId"]
#     if role_id == faculty_id or role_id == staff_id:
#         classes = iiq.get_classes_for_user(user_id)
#         # logging.debug(f"Classes Type: {type(classes)}")
#         # logging.debug(classes)
#         if classes is None:
#             continue
#         else:
#             for c in classes:
#                 # logging.debug(c)
#                 class_dict = {}
#                 class_location_id = c["LocationId"]
#                 # class_site_name = c["LocationName"]
#                 class_room_number = c["LocationDetails"]
#                 class_dict["UserId"] = user_id
#                 class_dict["RoomNumber"] = class_room_number
#                 class_dict["LocationId"] = class_location_id
#                 user_list.append(class_dict)

# unique_user_list = list(OrderedDict((frozenset(item.items()), item) for item in user_list).values())
# for u in unique_user_list:
#     logging.debug(u)

# logging.debug(unique_room_list[0])
# logging.debug(unique_user_list[0])
# combined_list = [{**dict1, **dict2} for dict1 in unique_user_list for dict2 in unique_room_list if dict1['LocationId'] == dict2['LocationId']]
# unique_combined_list = list(OrderedDict((frozenset(item.items()), item) for item in combined_list).values())
# for l in combined_list:
#     for k,v in l:
#         logging.debug(k,v)
