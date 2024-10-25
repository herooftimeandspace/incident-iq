# import csv
# import json
import logging
import os
import os.path
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import base64
# from email.message import EmailMessage


# from google.auth.transport.requests import Request
from google.oauth2 import service_account

# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
#  from googleapiclient.http import MediaFileUpload

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


def load_google_credentials():
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
    # service = build("gmail", "v1", credentials=creds)

    # if not creds or not creds.valid:
    #     if creds and creds.expired and creds.refresh_token:
    #         creds.refresh(Request())
    #     else:
    #         flow = InstalledAppFlow.from_client_secrets_file(
    #             SERVICE_ACCOUNT_FILE, SCOPES
    #         )
    #         creds = flow.run_local_server(port=0)
    #         # Save the credentials for the next run
    #     with open("token.json", "w") as token:
    #         token.write(creds.to_json())

    #     try:
    #         service = build("docs", "v1", credentials=creds)
    #     except HttpError as err:
    #         print(err)
    return creds


# svc_creds = load_google_credentials()
# html = "<p>Here's an HTML Table</p><p></p>"


def gmail_send_message(svc_creds, message):
    """Create and insert a draft email.
     Print the returned draft's message and id.
     Returns: Draft object, including draft id and message meta data.

    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """

    try:
        # create gmail api client
        service = build("gmail", "v1", credentials=svc_creds)

        # message = EmailMessage()

        # message.set_content(html, subtype="html")

        # message["To"] = "lcampbell@wusd.org"
        # message["From"] = "svc-incidentiq@it.wusd.org"
        # message["Subject"] = "HTML TABLE"

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # create_message = {"message": {"raw": encoded_message}}
        create_message = {"raw": encoded_message}
        # pylint: disable=E1101
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )

        print(f'Message Id: {send_message["id"]}')

    except HttpError as error:
        print(f"An error occurred: {error}")
        send_message = None

    return send_message


def create_sheet(folder_id, file_name, creds):
    try:
        # create drive api client
        service = build("drive", "v3", credentials=creds)

        file_metadata = {
            "name": file_name,
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "parents": [folder_id],
        }
        # pylint: disable=maybe-no-member
        file = (
            service.files()
            .create(body=file_metadata, supportsAllDrives=True, fields="id")
            .execute()
        )
        # print(f'File ID: "{file.get("id")}".')
        return file.get("id")

    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def update_values(
    spreadsheet_id, range_name, value_input_option, values, creds
):
    """
    Creates the batch_update the user has access to.
    Load pre-authorized user credentials from the environment.
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
        print(f"An error occurred: {error}")
        return error


# gmail_send_message(svc_creds)


def update_sheet(spreadsheet_id, creds, body):
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
    try:
        service = build("sheets", "v4", credentials=creds)
        result = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        return result
    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        return error
