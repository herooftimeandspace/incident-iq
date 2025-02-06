import logging
import sys
from pathlib import Path
import time

sys.path.append(str(Path(__file__).parent.parent))

from api import zoom_phones as zoom
from api import google_api as elgoog
from app import config as config
from app import helper as helper

# from app import variables as vars

start = time.time()

# Configure logging
logger = logging.getLogger(__name__)


def run(env: str = "--dev"):
    """Runs the script from the apscheduler schedule.

    Args:
        env (str, optional): Environment string. Used to branch code
            paths. Defaults to "--dev".
    """
    start = time.time()
    logging.info(f"Starting {__name__} with {env} flag")

    # Load Zoom ClientID and ClientSecret to get a new auth token
    secrets = config.load_secrets("zoom.json")
    auth_token = zoom.get_auth_token(secrets)

    # Load Google credentials to manipulate Google Sheets and set SheetID
    svc_creds = elgoog.load_google_credentials()
    phone_directory_sheet_id = (
        "1DtvzRro0ARO0AeNnooQjpDU7PoNFcPO6KWuWsCa7k3M"
    )

    # Get all phones, assigned or not.
    devices = zoom.get_phones(auth_token)
    unassigned_devices = zoom.get_phones(
        auth_token, device_status="unassigned"
    )
    devices.extend(unassigned_devices)
    for phone in devices:
        if "assignee" not in phone.keys():
            logging.debug(
                f"{phone['mac_address']} | {phone['status']} | "
                f"{phone['display_name']} | "
            )
        else:
            logging.debug(
                f"{phone['mac_address']} | {phone['status']} | "
                f"{phone['display_name']} | "
                f"{phone['assignee']['name']} | "
                f"{phone['assignee']['extension_number']}"
            )

    phone_users = zoom.get_phone_users(auth_token)
    phone_data = []
    for user in phone_users:
        # User might have more than one DID. Concat
        phone_numbers = ""
        for number in user["phone_numbers"]:
            phone_numbers = number["number"] + " "

        # Skip deactivated users when generating the list
        if user["status"] == "deactivate":
            logging.debug(
                f"{user['id']} | {user['status']} | "
                f"{user['email']} | "
                f"{user['name']} | {user['site']['name']} | "
                f"{user['extension_number']} | {phone_numbers.strip()}"
            )
            continue

        # Pull name from Zoom Web as opposed to user-defined in Zoom phone.
        # zoom.get_zoom_user(user["id"], auth_token)["Name"]
        user_zoom_web = zoom.get_zoom_user(user["id"], auth_token)
        logging.debug(
            f"{user['id']} | {user_zoom_web['Status']} | "
            f"{user['email']} | "
            f"{user_zoom_web['Name']} | {user['site']['name']} | "
            f"{user['extension_number']} | {phone_numbers.strip()}"
        )
        # Second check. If Zoom web account status is not active, skip.
        if user_zoom_web["Status"] != "active":
            continue

        # Build a streamlined dict to update Google Sheets
        user_details = {}
        user_details["Name"] = user_zoom_web["Name"]
        user_details["Site"] = user["site"]["name"]
        user_details["Extension"] = user["extension_number"]
        user_details["Phone Number(s)"] = phone_numbers.strip()
        user_details["Permanent"] = "N"
        user_details["Type"] = "Person"
        phone_data.append(user_details)

    # Include site shared line groups and call queues
    slg = zoom.get_shared_line_groups(auth_token)
    for line in slg:
        slg_details = {}
        slg_details["Name"] = line["display_name"]
        slg_details["Site"] = line["site"]["name"]
        slg_details["Extension"] = line["extension_number"]
        if "phone_numbers" not in line.keys():
            slg_details["Phone Number(s)"] = None
        else:
            phone_numbers = ""
            for number in line["phone_numbers"]:
                phone_numbers = number["number"] + " "
            slg_details["Phone Number(s)"] = phone_numbers.strip()
        slg_details["Permanent"] = "Y"
        slg_details["Type"] = "Shared Line Group"
        logging.debug(
            f"{slg_details['Name']} | {slg_details['Site']} | "
            f"{slg_details['Extension']} | {slg_details['Phone Number(s)']}"
        )
        phone_data.append(slg_details)

    auto_receptionists = zoom.get_auto_receptionist(auth_token)
    for line in auto_receptionists:
        ar_details = {}
        ar_details["Name"] = line["name"]
        ar_details["Site"] = line["site"]["name"]
        ar_details["Extension"] = line["extension_number"]
        if "phone_numbers" not in line.keys():
            ar_details["Phone Number(s)"] = None
        else:
            phone_numbers = ""
            for number in line["phone_numbers"]:
                phone_numbers = number["number"] + " "
            ar_details["Phone Number(s)"] = phone_numbers.strip()
        ar_details["Permanent"] = "Y"
        ar_details["Type"] = "Auto Receptionist"
        logging.debug(
            f"{ar_details['Name']} | {ar_details['Site']} | "
            f"{ar_details['Extension']} | {ar_details['Phone Number(s)']}"
        )
        phone_data.append(ar_details)

    call_queues = zoom.get_call_queues(auth_token)
    for line in call_queues:
        cq_details = {}
        cq_details["Name"] = line["name"]
        cq_details["Site"] = line["site"]["name"]
        cq_details["Extension"] = line["extension_number"]
        if "phone_numbers" not in line.keys():
            cq_details["Phone Number(s)"] = None
        else:
            phone_numbers = ""
            for number in line["phone_numbers"]:
                phone_numbers = number["number"] + " "
            cq_details["Phone Number(s)"] = phone_numbers.strip()
        cq_details["Permanent"] = "Y"
        cq_details["Type"] = "Call Queue"
        logging.debug(
            f"{cq_details['Name']} | {cq_details['Site']} | "
            f"{cq_details['Extension']} | {cq_details['Phone Number(s)']}"
        )
        phone_data.append(cq_details)

    # Convert the dict to a list Google Sheets can parse
    values = helper.convert_to_sheets(phone_data)

    # Clear the Data tab of the sheet to remove deprovisioned accounts.
    clear_result = elgoog.clear_spreadsheet_tab(
        phone_directory_sheet_id, "Data", svc_creds
    )
    if clear_result:
        logging.debug("Successfully cleared the sheet tab.")

    # Update the Data tab
    result = elgoog.update_values(
        phone_directory_sheet_id,
        "Data!A:F",
        "USER_ENTERED",
        values,
        svc_creds,
    )
    logging.info(result)
    end = time.time()
    elapsed = end - start
    elapsed = helper.truncate(elapsed, 3)
    logging.debug(f"room_updates.run() took {elapsed} seconds.")
