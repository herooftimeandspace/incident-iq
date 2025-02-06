from email.message import EmailMessage
import logging
import os
import os.path
import sys
import base64
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logger = logging.getLogger(__name__)


def load_google_credentials():
    """Loads the service account credentials from the secrets.json file

    Returns:
        service_account.Credentials: A credentials object that permits
            API access to Google services.
    """
    SCOPES = [
        "https://www.googleapis.com/auth/admin.directory.user.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
    ]

    parent_dir = os.path.dirname(__file__)
    grandparent_dir = os.path.dirname(parent_dir)
    SERVICE_ACCOUNT_FILE = os.path.join(
        grandparent_dir, "secrets", "svc-incidentiq-976dbf837333.json"
    )
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )

    creds = creds.with_subject("svc-incidentiq@it.wusd.org")
    return creds


def gmail_send_message(
    svc_creds: service_account.Credentials, message: EmailMessage
):
    """Creates and sends an email via a service account

    Args:
        svc_creds (serviceaccount.Credentials): The service account
            retrieved from secrets.json
        message (EmailMessage): The message to send via Gmail

    Returns:
        dict: A dict object, including draft id and message meta data.
    """

    try:
        # create gmail api client
        service = build("gmail", "v1", credentials=svc_creds)

        # encoded message
        encoded_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode()

        create_message = {"raw": encoded_message}
        # pylint: disable=E1101
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )

    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        send_message = None

    return send_message


def create_sheet(
    folder_id: str, file_name: str, creds: service_account.Credentials
):
    """Creates a sheet within a given folder or Google Shared Drive

    Args:
        folder_id (str): The ID of the folder to create the sheet
        file_name (str): The name of the Sheet
        creds (serviceaccount.Credentials): The service account
            retrieved from secrets.json

    Returns:
        str: The ID of the created file
    """
    try:
        # create drive api client
        service = build("drive", "v3", credentials=creds)

        file_metadata = {
            "name": file_name,
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "parents": [folder_id],
        }
        # pylint: disable=maybe-no-member
        # supportsAllDrives=True to create in Google Shared Drives
        file = (
            service.files()
            .create(
                body=file_metadata, supportsAllDrives=True, fields="id"
            )
            .execute()
        )
        return file.get("id")

    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        return None


def update_values(
    spreadsheet_id: str,
    range_name: str,
    value_input_option: str,
    values: list,
    creds: service_account.Credentials,
):
    """Updates values within a Google spreadsheet

    Args:
        spreadsheet_id (str): The ID of the spreadhseet
        range_name (str): The sheet range to update, e.g. Sheet1!A:Z or
            Sheet1!1:1000
        value_input_option (str): One of "USER_ENTERED" or "RAW"
        values (list): An array of values to update in the range
        creds (serviceaccount.Credentials): The service account
            retrieved from secrets.json

    Returns:
        dict: Returns a dictionary of updated cell results.
    """
    # pylint: disable=maybe-no-member
    try:
        service = build("sheets", "v4", credentials=creds)

        body = {"values": values}
        result = (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body,
            )
            .execute()
        )
        logging.info(f"{result.get('updatedCells')} cells updated.")
        return result
    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        return error


# gmail_send_message(svc_creds)


def update_sheet(
    spreadsheet_id: str, creds: service_account.Credentials, body: list
):
    """Updates a Google Sheet

    Args:
        spreadsheet_id (str): The ID of the spreadsheet
        creds (serviceaccount.Credentials): The service account
            retrieved from secrets.json
        body (list): The array of data to update the sheet

    Returns:
        dict: The metadata of the update action.
    """
    try:
        service = build("sheets", "v4", credentials=creds)
        result = (
            service.spreadsheets()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body,
            )
            .execute()
        )
        return result
    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        return error


def get_spreadsheet(spreadsheet_id, creds):
    """Get spreadsheet information from Google

    Args:
        spreadsheet_id (str): The ID of the spreadsheet
        creds (serviceaccount.Credentials): Google credentials
            retrieved via secrets.json

    Returns:
        dict: The spreadsheet metadata
    """
    try:
        service = build("sheets", "v4", credentials=creds)
        result = (
            service.spreadsheets()
            .get(spreadsheetId=spreadsheet_id)
            .execute()
        )
        return result
    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        return error


def clear_spreadsheet_tab(
    spreadsheet_id: str,
    tab_name: str,
    creds: service_account.Credentials,
):
    sheet = get_spreadsheet(spreadsheet_id, creds)
    if not tab_name or tab_name == "Sheet 1":
        logging.warning(
            f"Attempted to clear the default tab {tab_name} for "
            f"{sheet['name']}. Operation aborted. Please rename "
            "the default tab."
        )
        return None
    try:
        service = build("sheets", "v4", credentials=creds)
        result = (
            service.spreadsheets()
            .values()
            .clear(spreadsheetId=spreadsheet_id, range=tab_name)
            .execute()
        )
        return result
    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        return error
