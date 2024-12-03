import json
import logging
from multiprocessing import Value
import sys
from collections import Counter
from pathlib import Path
from types import NoneType
import time
import datetime

sys.path.append(str(Path(__file__).parent.parent))

from api import iiq as iiq
from api import (
    google_api as elgoog,
)  # importing as 'google' breaks everything
from app import helper as helper
from app import variables as vars
from email.message import EmailMessage

start = time.time()

# Configure logging
logger = logging.getLogger(__name__)


def set_script_config(env: str = "--dev") -> dict:
    if not isinstance(env, str):
        raise TypeError(f"Env is {type(env)} not str.")
    if env not in list(set(vars.test_env_flags + vars.prod_env_flags)):
        raise ValueError(
            f"Env is {env}, should be one of"
            f"{list(set(vars.test_env_flags + vars.prod_env_flags))}"
        )
    iiq_config = {}
    today = datetime.date.today()
    date_string = today.strftime("%Y-%m-%d")
    iiq_config["today"] = today
    iiq_config["date_string"] = date_string
    iiq_config["file_name"] = date_string + " Frequent Fliers"
    iiq_config["sheet_range"] = "A:J"
    iiq_config["From"] = "svc-incidentiq@it.wusd.org"

    if env in vars.test_env_flags:
        iiq_config["folder_id"] = "0AF6IDj3Siv_nUk9PVA"
        iiq_config["file_name"] = iiq_config["file_name"] + f" {env}"
        iiq_config["BCC"] = "lcampbell@wusd.org"
        iiq_config["Subject"] = (
            f"[INFO][{env}] {date_string} § Frequent Fliers Report"
        )
    elif env in vars.dev_env_flags:
        # Dev stuff
        pass
    elif env in vars.stage_env_flags:
        # Stage stuff
        pass
    elif env in vars.prod_env_flags:
        # Prod stuff
        iiq_config["BCC"] = "device-wranglers@wusd.org"
        iiq_config["Subject"] = (
            f"[INFO] {date_string} Frequent Fliers Report"
        )
        iiq_config["folder_id"] = "0AMCxmb-RqkwpUk9PVA"

    return iiq_config


def combine_event_data(frequent_flier_activity: list) -> list:
    """Combines check in and check out events into a single dict.
        Merge is based on asset serial number.
        Sets 'Unassigned Asset' to None if it is still checked out to
            the student.

    Args:
        frequent_flier_activity (list): A list of dicts with discrete
            assigned or unassigned asset entries

    Raises:
        TypeError: Parameter must be a list.
        ValueError: Parameter must not be empty.

    Returns:
        list: A list of dicts. Each dict represents a combined
        check-in/check-out activity per device serial number
    """
    start = time.time()
    if not isinstance(frequent_flier_activity, list):
        raise TypeError(
            f"Required parameter '{repr(frequent_flier_activity)}' is type "
            f"{type(frequent_flier_activity)}, not list."
        )
    if not frequent_flier_activity:
        raise ValueError(
            f"Required parameter '{repr(frequent_flier_activity)}' is empty."
        )
    combined_data = []
    assigned_assets = {}
    # For events in the list, combine event to a single record based on
    # serial number and append UserId, Name, Email, Site Location,
    # Serial Number, Assigned Date & Unassigned Date
    for event in frequent_flier_activity:
        logging.debug(f"Single event data: {event}")
        if event["Activity"] == "Assigned Asset":
            assigned_assets[event["Serial Number"]] = event
        elif event["Activity"] == "Unassigned Asset":
            assigned_event = assigned_assets.get(event["Serial Number"])
            if assigned_event:
                combined_event = {
                    "UserId": event["UserId"],
                    "Name": event["Name"],
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
                "Name": event["Name"],
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


def trim_events(
    combined_data: list,
    threshold: int = vars.event_threshold,
    days: int = vars.event_days,
) -> list:
    """Trims the device assigned or unassigned events based on the
        threshold and days criteria.

    Args:
        combined_data (list): A list of events to parse
        threshold (int, optional): The number of times a user must
            appear in the list before they are considered a
            frequent_flier. Defaults to 2.
        days (int, optional): Events older than this value are
            discarded. Defaults to 45.

    Raises:
        TypeError: Parameter must be a list
        ValueError: Parameter must not be empty
        TypeError: Parameter must be an int
        ValueError: Parameter must be >= 2
        TypeError: Parameter must be an int
        ValueError: Parameter must be < 0 or > 0, but != 0

    Returns:
        list: A list of dicts representing users who have had multiple
            check-out events within the last N days
    """
    start = time.time()
    if not isinstance(combined_data, list):
        raise TypeError(
            f"Required parameter '{repr(combined_data)}' is type "
            f"{type(combined_data)}, not list."
        )
    if not combined_data:
        logging.warning(
            f"Required parameter '{repr(combined_data)}' is empty."
        )
        return []
    if not isinstance(threshold, int):
        raise TypeError(
            f"Optional parameter '{repr(threshold)}' is type "
            f"{type(threshold)}, not int."
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
            f"Optional parameter '{repr(days)}' must be a positive or "
            f"negative int, not {days}"
        )
    logging.debug(f"Trimming to events in the last {days} days")
    curated_events = []
    frequent_fliers = []
    # Check if Assigned Date was within the last N days
    for event in combined_data:
        if helper.is_within_last_N_days(event["Assigned Date"], days):
            curated_events.append(event)
    logging.debug(f"Events with valid dates: {curated_events}")

    user_counts = Counter(item["Email"] for item in curated_events)
    # Discard records if they are below the event threshold.
    frequent_fliers = [
        item
        for item in curated_events
        if user_counts[item["Email"]] > threshold
    ]
    logging.debug(
        f"Valid events above the the threshold: {frequent_fliers}"
    )
    end = time.time()
    elapsed = end - start
    elapsed = helper.truncate(elapsed, 3)
    logging.debug(f"trim_events() took {elapsed} seconds.")
    return frequent_fliers


def get_frequent_flier_activity(
    site_id: str = None, days: int = vars.event_days
) -> list:
    """Get records of users who have had multiple device check-in and
        check-out events within the last N days.

    Args:
        site_id (str, optional): Site ID to limit the query. Used
            during debugging. Defaults to None.
        days (int, optional): The number of days in the past to check
            records. Defaults to vars.event_days.

    Raises:
        TypeError: all_users must be a list
        ValueError: all_users must not be empty
        TypeError: site_id must be a str

    Returns:
        list: A list of all events for users within scope.
    """
    start = time.time()
    all_users = iiq.get_all_users()  # Query IIQ API for all users
    location_ids = (
        iiq.get_all_locations_ids()
    )  # Query IIQ API for site IDs
    student_role_id = "6d5fee76-e05e-43c0-b8e9-b8447746e501"

    # Type and Value checks
    if not isinstance(all_users, list):
        raise TypeError(
            f"Required parameter {repr(all_users)} is type {type(all_users)}, "
            "not list."
        )
    if not all_users:
        raise ValueError("Required parameter 'all_users' is empty.")
    if not isinstance(site_id, (str, NoneType)):
        raise TypeError(
            f"Optional parameter {repr(site_id)} is type {type(site_id)}, "
            "not str or None."
        )
    if site_id not in location_ids and site_id is not None:
        logging.warning(
            f"Optional parameter {repr(site_id)} is set to {site_id}. That "
            "value is not in the list of valid location IDs. Setting to None"
        )
        site_id = None
    all_activity = []

    # Parse through users. Discard non-students, students with no
    # device activity, students with no updates to their account in IIQ
    # in the last N days, or if configured, students not at site_id.
    for user in all_users:
        frequent_flier_activity = []
        user_activity = None
        if user["RoleId"] != student_role_id:
            logging.debug(f"User {user["Email"]} is not a student.")
            continue
        elif user["LocationId"] != site_id and site_id is not None:
            logging.debug(
                f"User {user["Email"]} is not at site_id: {site_id}."
            )  # For testing purposes.
            continue
        elif user["LocationId"] != site_id and site_id is None:
            logging.debug(
                f"User {user["Email"]} is in scope. Site_id == {site_id}"
            )
        elif not helper.is_within_last_N_days(
            user["ModifiedDate"], days
        ):
            logging.debug(
                f"User {user["Email"]} modified date > {days} days."
            )
            continue
        else:
            logging.debug(
                f"User {user["Email"]} meets the criteria for evaluation"
            )

        user_activity = iiq.get_user_activity(user["UserId"])

        if not user_activity:
            logging.debug(
                f"User activity for {user["Email"]} is empty. Continuing."
            )
            continue
        else:
            logging.debug(
                f"User activity for {user["Email"]} has {len(user_activity)} "
                "records. Continuing to process."
            )

        # Parse through activity records and discard everything but asset
        # un/assignments
        for act in user_activity:
            logging.debug(
                f"You've reached an activity record! Here's the value: {act}"
            )
            event = {}
            event["UserId"] = user["UserId"]
            event["Name"] = user["Name"]
            event["Email"] = user["Email"]
            event["Site"] = user["LocationName"]
            if (
                act["UserDetails"] == "AppId: googleSso"
            ):  # Skip SSO updates
                logging.debug(
                    f"Activity value: {act["UserDetails"]}. Skipping activity."
                )
                continue
            elif (
                act["UserDetails"] == "AppId: aeriesSis"
            ):  # Skip SIS updates
                logging.debug(
                    f"Activity value: {act["UserDetails"]}. Skipping activity."
                )
                continue
            elif (
                isinstance(act["UserDetails"], str)
                and len(act["UserDetails"]) > 0
            ):  # TypeCheck. Activity shouldn't be a str > 0
                logging.debug(
                    f"Activity is a string, and has a length greater than 0. "
                    f"{len(act["UserDetails"])} | type: "
                    f"{type(act["UserDetails"])} "
                    f"| value: {act["UserDetails"]}"
                )
                continue  # skip
            elif (
                len(act["UserDetails"]) == 0
            ):  # We might need a better way to check this.
                logging.debug(
                    f"Activty len is {len(act["UserDetails"])}."
                )
                event["Date"] = act["ActivityDate"]
                # Parse Activity string
                details_list = json.loads(act["Details"])
                logging.debug(
                    f"Details List len {len(details_list)} | type: "
                    f"{type(details_list)} | value: {details_list}"
                )
                if len(details_list) == 1:  # 1 item in the list
                    details_dict = details_list[0]
                    if details_dict["p"] == "Unassigned Asset":
                        event["Activity"] = details_dict["p"]
                        event["Serial Number"] = details_dict[
                            "o"
                        ].split("#")[1]
                        frequent_flier_activity.append(event)
                elif len(details_list) > 1:  # > 1 item in the list
                    for item in details_list:
                        logging.debug(
                            f"item: {item} | type: {type(item)}"
                        )
                        if isinstance(item, dict):
                            i = item
                            logging.debug(
                                f"Item is a {type(item)}. Assigned to i"
                            )
                        else:
                            i = json.loads(item)
                            logging.debug(
                                f"Item is a {type(item)}. Converted to "
                                f"{type(i)}"
                            )

                        if i["p"].split(" #")[0] == "Asset":
                            event["Activity"] = "Assigned Asset"
                            event["Serial Number"] = i["p"].split(" #")[
                                1
                            ]
                            frequent_flier_activity.append(event)
                            logging.debug(f"Event data: {event}")
                        else:
                            logging.debug(
                                f"i['p'] is {i["p"]} not 'Asset'"
                            )
                else:
                    logging.warning(
                        f"Unexpected list length for UserDetails: "
                        f"{len(details_list)}"
                    )
            else:
                logging.warning(
                    f"User Details is not an expected type or value: "
                    f"{act["UserDetails"]}"
                )

        if frequent_flier_activity:  # Remove duplicates from the list
            all_activity.extend(
                combine_event_data(frequent_flier_activity)
            )
    end = time.time()
    elapsed = end - start
    elapsed = helper.truncate(elapsed, 3)
    logging.debug(
        f"get_frequent_flier_activity() took {elapsed} seconds."
    )
    return all_activity


################################################
# Get Tickets for students & serial number
################################################
def get_related_tickets(frequent_flier_events: list) -> list:
    """Queries the API for the user ID and asset serial number, and
        returns any associated tickets

    Args:
        frequent_flier_events (list): The list of events, which
            includes user ID and serial number

    Returns:
        list: The events list with ticket detail appended to each row,
            if any are returned from the API
    """
    # Create an index for the list so we can reference/insert data
    # correctly
    for index, event in enumerate(frequent_flier_events):
        logging.debug(index, event)
        asset = iiq.get_asset_by_serial(event["Serial Number"])

        # Try multiple methods to find the asset
        if asset is None:
            logging.info(
                f"Asset {event["Serial Number"]} not found by Serial Number. "
                "Searching for asset by Asset Tag."
            )
            asset = iiq.get_asset_by_tag(event["Serial Number"])
            if asset is None:
                logging.warning(
                    f"Asset {event["Serial Number"]} not found by Asset Tag "
                    "or Serial Number. Moving to next event."
                )
                continue

        try:
            if isinstance(asset["Status"]["Name"], str):
                frequent_flier_events[index]["Current Asset Status"] = (
                    asset["Status"]["Name"]
                )
        except KeyError:
            frequent_flier_events[index]["Current Asset Status"] = (
                "Unknown"
            )

        try:
            if isinstance(asset["Notes"], str):
                frequent_flier_events[index]["Asset Notes"] = asset[
                    "Notes"
                ]
        except KeyError:
            frequent_flier_events[index]["Asset Notes"] = None

        event["Serial Number"] = asset["SerialNumber"]

        # Search for tickets requested by or on behalf of the user,
        # that also match the Asset ID of the Serial Number
        logging.debug(
            f"UserId {event["UserId"]} | AssetId {asset["AssetId"]}"
        )
        tickets = iiq.get_it_ticket_for_user_and_asset(
            event["UserId"], asset["AssetId"]
        )
        if not tickets or isinstance(tickets, NoneType):
            logging.info(
                f"No tickets associated with both {event["Email"]} and "
                f"{event["Serial Number"]}. Moving to next event."
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
                issue_category = t["Issue"]["IssueCategoryName"]
                body += issue_category
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
            new_body = ""
            for char in body:
                if char != "{" or char != "}":
                    new_body += char
            ticket_context.append(new_body)
        if len(ticket_context) == 1:
            frequent_flier_events[index]["Tickets"] = ticket_context[0]
        else:
            frequent_flier_events[index]["Tickets"] = ticket_context
    return frequent_flier_events


def create_subsheets(
    sheet_id: str, svc_creds, data_tab_name: str = "Data"
):
    """Creates tabs on the Google Sheet for each site and hides the
        data tab to prevent errors

    Args:
        sheet_id (str): The ID of the sheet to modify
        svc_creds (service_account.Credentials): The service account
            retrieved from secrets.json
        data_tab_name (str, optional): Name of the tab to hide.
            Defaults to "Data".
    """
    locations = iiq.get_all_locations()
    # Filter out non-school locations
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
        # Insert a query function to the first cell of the sheet to
        # pull and filter data from data_tab_name.
        # List must be a 2D array, even when updating a single cell
        query = [
            [
                f"=query('{data_tab_name}'!1:1000,\"select B,C,E,F,G,H,I,J "
                f"where D='{loc["Name"]}' order by B,F\",1)"
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


def send_email(svc_creds, iiq_config: dict) -> dict:
    """Sends an email via BCC to end users alerting them of a new
        Frequent Fliers report

    Args:
        svc_creds (service_account.Credentials): The service account
            retrieved from /secrets
        iiq_config (dict): Config for routing email based on previously defined
            env variable.

    Raises:
        TypeError: iiq_config must be a dict

    Returns:
        response_msg (dict): The response JSON from the Google API
    """
    if not isinstance(iiq_config, dict):
        raise TypeError(
            f"IIQ_Config is type: {type(iiq_config)} not dict"
        )
    if "BCC" not in iiq_config:
        raise KeyError("'BCC' not in the list of keys for iiq_config.")
    if "From" not in iiq_config:
        raise KeyError("'From' not in the list of keys for iiq_config.")
    if "Subject" not in iiq_config:
        raise KeyError(
            "'Subject' not in the list of keys for iiq_config."
        )
    body = """
            <h1>&sect; Frequent Fliers Report</h1>
            <p>A new Frequent Fliers report is available in the shared 
            Google Drive. Click the link below to view the drive, and all 
            previous reports. See the tabs at the bottom of each report for 
            your site.</p>
            <p><a title="&sect; Frequent Fliers Google Drive" 
            href="https://drive.google.com/drive/folders/0AMCxmb-RqkwpUk9PVA" 
            target="_blank">&sect; Frequent Fliers Google Drive</a></p>
            <p>Please note, this&nbsp;report is provided for your information 
            only. IT does not take action on this report unless requested. 
            Please <a href="https://wusd-org.incidentiq.com/agent/dashboard" 
            target="_blank">submit a ticket</a> with IT if you would like 
            support in managing a student's devices or account.</p>
            <p>Thanks for your time,</p>
            <p>The Tech Team</p>
            """
    message = EmailMessage()

    message.set_content(body, subtype="html")
    message["From"] = iiq_config["From"]
    message["BCC"] = iiq_config["BCC"]
    message["Subject"] = iiq_config["Subject"]

    logging.info(
        f"Sending email from {message["From"]} to {message["BCC"]} with "
        f"subject {message["Subject"]}"
    )
    response_msg = elgoog.gmail_send_message(svc_creds, message)
    return response_msg


def run(env: str = "--dev"):
    """Runs the script from the apscheduler schedule.

    Args:
        env (str, optional): Environment string. Used to branch code
            paths. Defaults to "--dev".
    """
    start = time.time()
    logging.info(f"Starting {__name__} with {env} flag")

    # Create dicts for updating Google Sheets
    rename_first_sheet = {
        "requests": [
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": 0,
                        "title": vars.data_tab_name,
                    },
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
    sort_range = {
        "requests": [
            {
                "sortRange": {
                    "range": {
                        # "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": 0,
                    },
                    "sortSpecs": [
                        {
                            "dimensionIndex": 2,
                            "sortOrder": "ASCENDING",
                        },
                        {
                            "dimensionIndex": 1,
                            "sortOrder": "ASCENDING",
                        },
                        {
                            "dimensionIndex": 4,
                            "sortOrder": "ASCENDING",
                        },
                    ],
                }
            }
        ]
    }

    # Get the service account credentials
    svc_creds = elgoog.load_google_credentials()

    # Get Frequent Fliers, Optionally limit scope to a specific site_id
    frequent_flier_user_activity = get_frequent_flier_activity(
        # site_id="f12ca8b4-190e-ef11-96f5-000d3a0e23bd"
    )

    # Trim events down to only those that meet our criteria
    frequent_flier_events = trim_events(frequent_flier_user_activity)

    # Get tickets related to the remaining events
    ff_events = get_related_tickets(frequent_flier_events)

    # Set config based on environment variable
    iiq_config = set_script_config(env)

    sheet_id = elgoog.create_sheet(
        iiq_config["folder_id"], iiq_config["file_name"], svc_creds
    )
    values = helper.convert_to_sheets(ff_events)
    result = elgoog.update_values(
        sheet_id,
        iiq_config["sheet_range"],
        "USER_ENTERED",
        values,
        svc_creds,
    )
    logging.info(result)

    # Sort results
    sort_result = elgoog.update_sheet(sheet_id, svc_creds, sort_range)
    logging.debug(sort_result)

    # Rename the first sheet to the data_tab_name
    update_tab = elgoog.update_sheet(
        sheet_id, svc_creds, body=rename_first_sheet
    )
    logging.debug(update_tab)

    # Create tabs for each site
    create_subsheets(sheet_id, svc_creds, vars.data_tab_name)
    elgoog.update_sheet(sheet_id, svc_creds, body=hide_first_sheet)

    # Send email notification. Use env to route the email for testing.
    email_response = send_email(svc_creds, iiq_config)
    logging.debug(email_response)

    end = time.time()
    elapsed = end - start
    elapsed = helper.truncate(elapsed, 3)
    logging.info(
        f"create_frequent_fliers_report took {elapsed} seconds."
    )
