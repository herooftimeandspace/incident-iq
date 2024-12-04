# import csv
# import json
import logging
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app import config
from api import zoom_phones
from api import iiq
# from app import variables as vars

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

secrets = config.load_secrets("zoom.json")
auth_token = zoom_phones.get_auth_token(secrets)
assigned_phones = zoom_phones.get_phones(auth_token)
debug_logs = []
for ass_ph in assigned_phones:
    # Check if phone isn't assigned to a user
    if ass_ph["assignee"]["extension_type"] == "commonArea":
        # TODO: Unassign device from user in IIQ
        logging.debug(
            f"Device S/N {ass_ph["mac_address"]} is a Common Area phone in "
            f"Zoom."
        )
        # iiq.update_owner(iiq_device["id"], owner_id=None)
        continue

    # Get phone assinged user from Zoom
    owner = zoom_phones.get_user_by_id(
        auth_token, ass_ph["assignee"]["id"]
    )
    if not owner:
        # TODO: Unassign device from user in IIQ
        logging.debug(
            f"Device S/N {ass_ph["mac_address"]} is not assigned to a user in "
            f"Zoom"
        )
        zoom_owner = "Unassigned"
        continue
    else:
        zoom_owner = owner["email"]

    # Get IIQ Device
    iiq_device = iiq.get_asset_by_serial(ass_ph["mac_address"])
    if not iiq_device:
        # TODO: Add device to IIQ
        logging.debug(
            f"Device S/N {ass_ph["mac_address"]} is doesn't exist in IIQ"
        )
        continue
    elif iiq_device.get("Owner") is None:
        logging.debug(
            f"Device S/N {ass_ph["mac_address"]} is unassigned in IIQ"
        )
        iiq_owner = "Unassigned"
    else:
        iiq_owner = iiq_device["Owner"]["Email"]

    # Check if Zoom owner and IIQ owner are the same
    if zoom_owner == iiq_owner:
        continue
    else:
        # TODO: Update IIQ with Zoom owner
        iiq_new_owner = iiq.get_user_id_by_email(zoom_owner)
        if not iiq_new_owner:
            debug_logs.append(
                f"S/N {ass_ph["mac_address"]} | Zoom Owner: {zoom_owner} not "
                f"found in IIQ. Check Zoom account | IIQ Owner: {iiq_owner}"
            )

        else:
            # iiq.update_owner(iiq_device["id"], iiq_new_owner)
            debug_logs.append(
                f"S/N {ass_ph["mac_address"]} | Zoom Owner: {zoom_owner} | "
                f"IIQ Owner: {iiq_owner} | IIQNewOwnerID: {iiq_new_owner}"
            )

unassigned_phones = zoom_phones.get_phones(
    auth_token, device_status="unassigned"
)
for unass_ph in unassigned_phones:
    iiq_device = iiq.get_asset_by_serial(unass_ph["mac_address"])
    if not iiq_device:
        # TODO: Add device to IIQ
        continue  # Device doesn't exist in IIQ
    if iiq_device.get("Owner") is None:
        continue  # Device is already unassigned
    if unass_ph.get("assignee") is None:
        ph_type = "Unassigned"
    elif unass_ph.get("assignees") is None:
        ph_type = "Unassigned"
    else:
        ph_type = unass_ph["assignee"]["extension_type"]
    debug_logs.append(
        f"Action Required: Unassign owner in IIQ | S/N "
        f"{unass_ph["mac_address"]} | Type: {ph_type} | "
        f"Device Name: {unass_ph["display_name"]}"
    )
    # iiq.update_owner(iiq_device["Id"], owner_id=None)

for log in debug_logs:
    logging.info(log)
