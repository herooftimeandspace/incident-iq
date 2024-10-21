import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path
from types import NoneType
import time

sys.path.append(str(Path(__file__).parent.parent))

from api import iiq as iiq
from app import helper as helper
from app import variables as vars

start = time.time()

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

# frequent_flyer_field_id = "cbe10bf8-7be2-421c-a1ea-f66100d74093"
student_role_id = "6d5fee76-e05e-43c0-b8e9-b8447746e501"
# student_site_id = "ef2ca8b4-190e-ef11-96f5-000d3a0e23bd"  # Brooks
all_users = iiq.get_all_users()
location_ids = iiq.get_all_locations_ids()

# frequent_flier_events = []
combined_data = []
toggle = 0


# New Way
def combine_event_data(frequent_flier_activity):
    """Combines check in and check out events into a single dict.
        Merge is based on asset serial number.
        Sets 'Unassigned Asset' to None if it is still checked out to the student.

    Args:
        frequent_flier_activity (list): A list of dicts with discrete assigned
        or unassigned asset entries

    Raises:
        TypeError: Parameter must be a list.
        ValueError: Parameter must not be empty.

    Returns:
        list: A list of dicts. Each dict represents a combined check-in/check-out
        activity per device serial number
    """
    start = time.time()
    if not isinstance(frequent_flier_activity, list):
        raise TypeError(
            f"Required parameter '{repr(frequent_flier_activity)}' is type {type(frequent_flier_activity)}, not list."
        )
    if not frequent_flier_activity:
        raise ValueError(
            f"Required parameter '{repr(frequent_flier_activity)}' is empty."
        )
    combined_data = []
    assigned_assets = {}
    for event in frequent_flier_activity:
        logging.debug(f"Single event data: {event}")
        if event["Activity"] == "Assigned Asset":
            assigned_assets[event["Serial Number"]] = event
        elif event["Activity"] == "Unassigned Asset":
            assigned_event = assigned_assets.get(event["Serial Number"])
            if assigned_event:
                combined_event = {
                    "UserId": event["UserId"],
                    "Email": event["Email"],
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
                "UserId": event["UserId"],
                "Email": event["Email"],
                "Site": event["Site"],
                "Serial Number": serial_number,
                "Assigned Date": assigned_event["Date"],
                "Unassigned Date": None,
            }
        )
    end = time.time()
    elapsed = end - start
    elapsed = helper.truncate(elapsed, 3)
    logging.debug(f"combine_event_data() took {elapsed} seconds.")
    return combined_data


def trim_events(combined_data, threshold=2, days=45):
    """Trims the device assigned or unassigned events based on the threshold and days criteria.

    Args:
        combined_data (list): A list of events to parse
        threshold (int, optional): The number of times a user must appear in the list before they are considered a frequent_flier. Defaults to 2.
        days (int, optional): Events older than this value are discarded. Defaults to 45.

    Raises:
        TypeError: Parameter must be a list
        ValueError: Parameter must not be empty
        TypeError: Parameter must be an int
        ValueError: Parameter must be >= 2
        TypeError: Parameter must be an int
        ValueError: Parameter must be < 0 or > 0, but != 0

    Returns:
        list: A list of dicts representing users who have had multiple check-in and check-out events within the last N days
    """
    start = time.time()
    if not isinstance(combined_data, list):
        raise TypeError(
            f"Required parameter '{repr(combined_data)}' is type {type(combined_data)}, not list."
        )
    if not combined_data:
        logging.warning(
            f"Required parameter '{repr(combined_data)}' is empty."
        )
        return []
    if not isinstance(threshold, int):
        raise TypeError(
            f"Optional parameter '{repr(threshold)}' is type {type(threshold)}, not int."
        )
    if threshold < 2:
        raise ValueError(
            f"Optional parameter '{repr(threshold)}' must be at least 2."
        )
    if not isinstance(days, int):
        raise TypeError(
            f"Optional parameter '{repr(days)}' is type {type(days)}, not int."
        )
    if days == 0:
        raise ValueError(
            f"Optional parameter '{repr(days)}' must be a positive or negative int, not {days}"
        )
    logging.debug(f"Trimming to events in the last {days} days")
    curated_events = []
    frequent_fliers = []
    for event in combined_data:
        if helper.is_within_last_N_days(
            event["Assigned Date"], days
        ) or helper.is_within_last_N_days(event["Unassigned Date"], days):
            # print(event)
            curated_events.append(event)
    logging.debug(
        f"List of events after removing events with invalid dates: {curated_events}"
    )

    user_counts = Counter(item["Email"] for item in curated_events)
    frequent_fliers = [
        item
        for item in curated_events
        if user_counts[item["Email"]] > threshold
    ]
    logging.debug(
        f"List of events after removing entries below the threshold: {frequent_fliers}"
    )
    end = time.time()
    elapsed = end - start
    elapsed = helper.truncate(elapsed, 3)
    logging.debug(f"trim_events() took {elapsed} seconds.")
    return frequent_fliers


def get_frequent_flier_activity(
    all_users, ff_toggle=toggle, site_id=None, days=vars.days
):
    start = time.time()
    if not isinstance(all_users, list):
        raise TypeError(
            f"Required parameter {repr(all_users)} is type {type(all_users)}, not list."
        )
    if not all_users:
        raise ValueError("Required parameter 'all_users' is empty.")
    if not isinstance(ff_toggle, int):
        raise TypeError(
            f"Optional parameter {repr(ff_toggle)} is type {type(ff_toggle)}, not int."
        )
    if ff_toggle < 0 or ff_toggle >= 2:
        raise ValueError(
            f"Optional parameter {repr(ff_toggle)} value is {ff_toggle}. Value must be 0 or 1"
        )
    if not isinstance(site_id, (str, NoneType)):
        raise TypeError(
            f"Optional parameter {repr(site_id)} is type {type(ff_toggle)}, not str or None."
        )
    if site_id not in location_ids and site_id is not None:
        logging.warning(
            f"Optional parameter {repr(site_id)} is set to {site_id}. That value is not in the list of valid location IDs. Setting to None"
        )
        site_id = None
    all_activity = []
    for user in all_users:
        logging.debug(f"================= {user["Email"]} =================")
        frequent_flier_activity = []
        user_activity = None
        if user["RoleId"] != student_role_id:
            logging.debug(f"User {user["Email"]} is not a student.")
            continue
        elif user["LocationId"] != site_id and site_id is not None:
            logging.debug(
                f"User {user["Email"]} is not at {site_id}."
            )  # For testing purposes. Remove
            continue
        elif user["LocationId"] != site_id and site_id is None:
            logging.debug(
                f"User {user["Email"]} is in scope because {repr(site_id)} == {site_id}"
            )
        elif not helper.is_within_last_N_days(user["ModifiedDate"], days):
            logging.debug(
                f"User {user["Email"]} hasn't been modified in the last {days} days."
            )
            continue
        else:
            logging.debug(
                f"User {user["Email"]} meets the criteria for evaluation"
            )

        if ff_toggle == 0:  # Gets all activity for every student
            logging.debug(
                "You've reached the logic where we check all students. There is no logic here."
            )
            user_activity = iiq.get_user_activity(user["UserId"])
        # elif ff_toggle == 1:  # get only frequent fliers
        #     logging.debug(
        #         "You've reached the logic where we check for frequent fliers."
        #     )
        #     for fields in user["CustomFieldValues"]:
        #         if not fields["CustomFieldTypeId"]:
        #             continue
        #         else:
        #             if not fields["Value"] == "yes":
        #                 continue
        #             elif fields["Value"] == "yes":
        #                 logging.debug(
        #                     f"Getting user activity history for {user["Email"]}"
        #                 )
        #                 user_activity = iiq.get_user_activity(user["UserId"])
        #             else:
        #                 continue
        else:
            logging.warning(
                f"Toggle value set incorrectly. Type: {type(ff_toggle)} | Value: {ff_toggle}"
            )

        if not user_activity:
            logging.debug(
                f"User activity for {user["Email"]} is empty. Continuing to next user."
            )
            continue
        else:
            logging.debug(
                f"User activity for {user["Email"]} has {len(user_activity)} records. Continuing to process."
            )

        for act in user_activity:
            logging.debug(
                f"You've reached an activity record! Here's the value: {act}"
            )
            event = {}
            event["UserId"] = user["UserId"]
            event["Email"] = user["Email"]
            event["Site"] = user["LocationName"]
            if act["UserDetails"] == "AppId: googleSso":
                logging.debug(
                    f"Activity value: {act["UserDetails"]}. Skipping activity."
                )
                continue
            elif act["UserDetails"] == "AppId: aeriesSis":
                logging.debug(
                    f"Activity value: {act["UserDetails"]}. Skipping activity."
                )
                continue
            elif (
                isinstance(act["UserDetails"], str)
                and len(act["UserDetails"]) > 0
            ):
                logging.debug(
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
                        event["Serial Number"] = details_dict["o"].split("#")[
                            1
                        ]
                        frequent_flier_activity.append(event)
                elif len(details_list) > 1:
                    logging.debug(
                        "This logic is for when there's multiple items in the details_list"
                    )
                    for item in details_list:
                        logging.debug(f"item: {item} | type: {type(item)}")
                        if isinstance(item, dict):
                            i = item
                            logging.debug(
                                f"Item is a {type(item)}. Assigned to i"
                            )
                        else:
                            i = json.loads(item)
                            logging.debug(
                                f"Item is a {type(item)}. Converted to {type(i)}"
                            )

                        if i["p"].split(" #")[0] == "Asset":
                            event["Activity"] = "Assigned Asset"
                            event["Serial Number"] = i["p"].split(" #")[1]
                            frequent_flier_activity.append(event)
                            logging.debug(f"Event data: {event}")
                        else:
                            logging.debug(f"i['p'] is {i["p"]} not 'Asset'")
                else:
                    logging.warning(
                        f"Unexpected list length for UserDetails: {len(details_list)}"
                    )
            else:
                logging.warning(
                    f"User Details is not an expected type or value: {act["UserDetails"]}"
                )
        # if frequent_flier_activity: # Drop empty lists
        #     combined_data = combine_event_data(frequent_flier_activity)
        # for act in combined_data:
        #     all_activity.append(act)

        if frequent_flier_activity:  # Try the Gemini simplification
            all_activity.extend(combine_event_data(frequent_flier_activity))
    end = time.time()
    elapsed = end - start
    elapsed = helper.truncate(elapsed, 3)
    logging.debug(f"get_frequent_flier_activity took {elapsed} seconds.")
    return all_activity


frequent_flier_user_activity = get_frequent_flier_activity(
    all_users,  # site_id="f12ca8b4-190e-ef11-96f5-000d3a0e23bd"
)
logging.debug(f"ff_user_func = {frequent_flier_user_activity}")
frequent_flier_events = trim_events(frequent_flier_user_activity)

################################################
# Get Tickets for students & serial number
################################################
for index, event in enumerate(frequent_flier_events):
    logging.debug(index, event)
    asset = iiq.get_asset_by_serial(event["Serial Number"])

    if asset is None:
        logging.info(
            f"Asset {event["Serial Number"]} not found by Serial Number. Searching for asset by Asset Tag."
        )
        asset = iiq.get_asset_by_tag(event["Serial Number"])
        if asset is None:
            logging.warning(
                f"Asset {event["Serial Number"]} not found by Asset Tag or Serial Number. Moving to next event."
            )
            continue

    try:
        if isinstance(asset["Status"]["Name"], str):
            frequent_flier_events[index]["Current Asset Status"] = asset[
                "Status"
            ]["Name"]
    except KeyError:
        frequent_flier_events[index]["Current Asset Status"] = "Unknown"

    try:
        if isinstance(asset["Notes"], str):
            frequent_flier_events[index]["Asset Notes"] = asset["Notes"]
    except KeyError:
        frequent_flier_events[index]["Asset Notes"] = None

    event["Serial Number"] = asset["SerialNumber"]

    # Search for tickets requested by or on behalf of the student, that also match the Asset ID of the Serial Number
    logging.debug(f"UserId {event["UserId"]} | AssetId {asset["AssetId"]}")
    tickets = iiq.get_it_ticket_for_user_and_asset(
        event["UserId"], asset["AssetId"]
    )
    if not tickets or isinstance(tickets, NoneType):
        logging.info(
            f"No tickets associated with both {event["Email"]} and {event["Serial Number"]}. Moving to next event."
        )
        frequent_flier_events[index]["Tickets"] = None
        continue

    # There were results from the search
    ticket_context = []
    for t in tickets:
        body = ""
        try:
            ticket_number = t["TicketNumber"]
            body += ticket_number
            body += " | "
        except KeyError:
            ticket_number = None
        try:
            issue_cagtegory = t["Issue"]["IssueCategoryName"]
            body += issue_cagtegory
            body += " > "
        except KeyError:
            issue_category = None
        try:
            issue_name = t["Issue"]["Name"]
            body += issue_name
            body += " | Description: "
        except KeyError:
            issue_name = None
        try:
            issue_description = t["IssueDescription"]
            body += issue_description
        except KeyError:
            issue_description = None
            body += "None"

        ticket_details = {"Ticket Number": body}
        ticket_context.append(ticket_details)
    if len(ticket_context) == 1:
        frequent_flier_events[index]["Tickets"] = ticket_context[0]
    else:
        frequent_flier_events[index]["Tickets"] = ticket_context
    # frequent_flier_events[index].pop("UserId", None)

# for e in frequent_flier_events:
#     logging.info(e)

helper.json_to_csv(frequent_flier_events, "output/all_sites_ff.csv")

# [
#     {
#         "User": "email@site.com",
#         "Site": "Middle School",
#         "Serial Number": "DEAD1337BF",
#         "Assigned Date": "2024-08-26T11:39:15.027303",
#         "Unassigned Date": "2024-09-09T08:39:28.327557",
#     },
#     {
#         "User": "email@site.com",
#         "Site": "Middle School",
#         "Serial Number": "1337BF",
#         "Assigned Date": "2024-09-09T08:41:23.7549713",
#         "Unassigned Date": "2024-09-25T09:10:23.0312729",
#     },
#     {
#         "User": "email@site.com",
#         "Site": "Middle School",
#         "Serial Number": "DEAD1337",
#         "Assigned Date": "2024-09-25T09:10:54.3942151",
#         "Unassigned Date": None,
#     },
#     {
#         "User": "email2@site.com",
#         "Site": "Middle School",
#         "Serial Number": "DEADBF",
#         "Assigned Date": "2024-08-23T17:04:09.2340565",
#         "Unassigned Date": "2024-09-24T11:11:15.568162",
#     },
#     {
#         "User": "email2@site.com",
#         "Site": "Middle School",
#         "Serial Number": "DE1337AD",
#         "Assigned Date": "2024-08-23T17:01:41.5970898",
#         "Unassigned Date": "2024-09-24T11:16:28.3119495",
#     },
#     {
#         "User": "email2@site.com",
#         "Site": "Middle School",
#         "Serial Number": "BF1337DEAD",
#         "Assigned Date": "2024-08-23T16:55:31.5671654",
#         "Unassigned Date": "2024-10-10T14:32:37.8353694",
#     },
#     {
#         "User": "email2@site.com",
#         "Site": "Middle School",
#         "Serial Number": "DEADBF1337",
#         "Assigned Date": "2024-09-24T11:12:06.6403979",
#         "Unassigned Date": None,
#     },
# ]

end = time.time()
elapsed = end - start
elapsed = helper.truncate(elapsed, 3)
logging.info(f"create_frequent_fliers_report took {elapsed} seconds.")
