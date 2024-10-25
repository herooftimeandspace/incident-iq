import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from api import iiq
from app import helper as helper

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
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

frequent_flyer_field_id = "cbe10bf8-7be2-421c-a1ea-f66100d74093"
student_role_id = "6d5fee76-e05e-43c0-b8e9-b8447746e501"
student_site_id = "ef2ca8b4-190e-ef11-96f5-000d3a0e23bd"  # Brooks
all_users = iiq.get_all_users()
location_ids = iiq.get_all_locations_ids()

# frequent_flier_events = []
combined_data = []
toggle = 0

#################################################
# Old Way
#################################################

for user in all_users:
    logging.info(f"================= {user["Email"]} =================")
    frequent_flier_activity = []
    user_activity = None
    if user["RoleId"] != student_role_id:
        logging.debug(f"User {user["Email"]} is not a student.")
        continue
    elif user["LocationId"] != student_site_id:
        logging.debug(
            f"User {user["Email"]} is not at BES."
        )  # For testing purposes. Remove
        continue
    else:
        logging.debug(
            f"User {user["Email"]} meets the criteria for evaluation"
        )

    if (
        toggle == 0
    ):  # Remove this after testing. Gets all activity for every student
        logging.info(
            "You've reached the logic where we check all students. There is no logic here."
        )
        user_activity = iiq.get_user_activity(user["UserId"])
    elif toggle == 1:  # get only frequent fliers
        logging.info(
            "You've reached the logic where we check for frequent fliers."
        )
        for fields in user["CustomFieldValues"]:
            if not fields["CustomFieldTypeId"]:
                continue
            else:
                if not fields["Value"] == "yes":
                    continue
                elif fields["Value"] == "yes":
                    logging.info(
                        f"Getting user activity history for {user["Email"]}"
                    )
                    user_activity = iiq.get_user_activity(user["UserId"])
                else:
                    continue
    else:
        logging.warning(
            f"Toggle value set incorrectly. Type: {type(toggle)} | Value: {toggle}"
        )

    # logging.info(
    #     f"User Activty. Type {type(user_activity)} | Value {user_activity}"
    # )
    if not user_activity:
        logging.info(
            f"User activity for {user["Email"]} is empty. Continuing to next user."
        )
        continue
    else:
        logging.info(
            f"User activity for {user["Email"]} has {len(user_activity)} records. Continuing to process."
        )

    for act in user_activity:
        logging.debug(
            f"You've reached an activity record! Here's the value: {act}"
        )
        event = {}
        event["Email"] = user["Email"]
        event["Site"] = user["LocationName"]
        if act["UserDetails"] == "AppId: googleSso":
            logging.info(
                f"Activity value: {act["UserDetails"]}. Skipping activity."
            )
            continue
        elif act["UserDetails"] == "AppId: aeriesSis":
            logging.info(
                f"Activity value: {act["UserDetails"]}. Skipping activity."
            )
            continue
        elif (
            isinstance(act["UserDetails"], str) and len(act["UserDetails"]) > 0
        ):
            logging.info(
                f"Activity is a string, and has a length greater than 0. UserDetails: {act["UserDetails"]}"
            )
            logging.debug(
                f"Details List len {len(act["UserDetails"])} | type: {type(act["UserDetails"])} | value: {act["UserDetails"]}"
            )
            continue  # skip
        elif len(act["UserDetails"]) == 0:
            logging.debug(
                f"Activty len is {len(act["UserDetails"])}. We might need a better way to check this."
            )
            event["Date"] = act["ActivityDate"]
            # Parse Activity string
            details_list = json.loads(act["Details"])
            logging.debug(
                f"Details List len {len(details_list)} | type: {type(details_list)} | value: {details_list}"
            )
            if len(details_list) == 1:
                logging.debug(
                    "This logic is for when there's only a single item in the details_list"
                )
                # details_dict = {item["p"]: item["o"] for item in details_list}
                details_dict = details_list[0]
                if details_dict["p"] == "Unassigned Asset":
                    event["Activity"] = details_dict["p"]
                    event["Serial Number"] = details_dict["o"].split("#")[1]
                    frequent_flier_activity.append(event)
            elif len(details_list) > 1:
                logging.debug(
                    "This logic is for when there's multiple items in the details_list"
                )
                for item in details_list:
                    logging.info(f"item: {item} | type: {type(item)}")
                    if isinstance(item, dict):
                        i = item
                        logging.info(f"Item is a {type(item)}. Assigned to i")
                    else:
                        i = json.loads(item)
                        logging.info(
                            f"Item is a {type(item)}. Converted to {type(i)}"
                        )

                    if i["p"].split(" #")[0] == "Asset":
                        event["Activity"] = "Assigned Asset"
                        event["Serial Number"] = i["p"].split(" #")[1]
                        frequent_flier_activity.append(event)
                        logging.info(f"Event data: {event}")
                    else:
                        logging.warning(f"i['p'] is {i["p"]} not 'Asset'")
            else:
                logging.warning(
                    f"Unexpected list length for UserDetails: {len(details_list)}"
                )
        else:
            logging.warning(
                f"User Details is not an expected type or value: {act["UserDetails"]}"
            )

    # combined_data = []
    assigned_assets = {}

    logging.info("Now we combine events.")
    for event in frequent_flier_activity:
        # ƒlogging.debug(f"event: {event}")
        if event["Activity"] == "Assigned Asset":
            assigned_assets[event["Serial Number"]] = event
        elif event["Activity"] == "Unassigned Asset":
            assigned_event = assigned_assets.get(event["Serial Number"])
            if assigned_event:
                combined_event = {
                    "User": event["Email"],
                    "Site": event["Site"],
                    "Serial Number": event["Serial Number"],
                    "Assigned Date": assigned_event["Date"],
                    "Unassigned Date": event["Date"],
                }
                combined_data.append(combined_event)
                del assigned_assets[event["Serial Number"]]

    # Add any remaining unassigned assets
    for serial_number, assigned_event in assigned_assets.items():
        combined_data.append(
            {
                "User": event["Email"],
                "Site": event["Site"],
                "Serial Number": serial_number,
                "Assigned Date": assigned_event["Date"],
                "Unassigned Date": None,
            }
        )
    # frequent_flier_events.append(frequent_flier_activity)

logging.info("Trimming to events in the last 30 days")
curated_events = []
for event in combined_data:
    if helper.is_within_last_30_days(
        event["Assigned Date"]
    ) or helper.is_within_last_30_days(event["Unassigned Date"]):
        # print(event)
        curated_events.append(event)

logging.info(f"Curated events: {curated_events}")
# frequent_fliers = []
user_counts = Counter(item["User"] for item in curated_events)
frequent_fliers = [
    item for item in curated_events if user_counts[item["User"]] > 2
]

for event in frequent_fliers:
    # print(event)
    logging.info(event)
#################################################
# Old Way
#################################################

# [
#     {"User": "bsisko-test"},
#     {"User": "bsisko-test"},
#     {"User": "bsisko-test"},
#     {"User": "bsisko-test"},
#     {"User": "nkira"},
#     {"User": "jsisko"},
#     {"User": "jsisko"},
#     {"User": "quark"},
#     {"User": "rom"},
#     {"User": "nog"},
#     {"User": "jbashir"},
#     {"User": "jbashir"},
#     {"User": "jbashir"},
# ]


# [
#     {
#         "Activity": "Assigned Asset",
#         "Serial Number": "PF3RAZX5",
#         "Date": "2024-10-10T08:43:50.8816187",
#     },
#     {
#         "Activity": "Unassigned Asset",
#         "Serial Number": "PF3RAZX5",
#         "Date": "2024-10-21T08:43:50.8816187",
#     },
#     {
#         "Activity": "Assigned Asset",
#         "Serial Number": "PF3RAZX6",
#         "Date": "2024-11-10T08:43:50.8816187",
#     },
#     {
#         "Activity": "Unassigned Asset",
#         "Serial Number": "PF3RAZX6",
#         "Date": "2024-11-21T08:43:50.8816187",
#     },
#     {
#         "Activity": "Assigned Asset",
#         "Serial Number": "PF3RAZX7",
#         "Date": "2024-12-10T08:43:50.8816187",
#     },
#     {
#         "Activity": "Unassigned Asset",
#         "Serial Number": "PF3RAZX7",
#         "Date": "2024-12-21T08:43:50.8816187",
#     },
#     {
#         "Activity": "Assigned Asset",
#         "Serial Number": "PF3RAZX8",
#         "Date": "2025-01-01T08:43:50.8816187",
#     }
# ]
