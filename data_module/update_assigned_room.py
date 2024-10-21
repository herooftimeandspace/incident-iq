import requests
import pandas as pd
import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

# Create a logs subdirectory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(logs_dir, exist_ok=True)

# Create a file handler for each log level
debug_handler = logging.FileHandler(os.path.join(logs_dir, "debug.log"), mode='a')
debug_handler.setLevel(logging.DEBUG)
info_handler = logging.FileHandler(os.path.join(logs_dir, "info.log"), mode='a')
info_handler.setLevel(logging.INFO)
warning_handler = logging.FileHandler(os.path.join(logs_dir, "warning.log"), mode='a')
warning_handler.setLevel(logging.WARNING)
error_handler = logging.FileHandler(os.path.join(logs_dir, "error.log"), mode='a')
error_handler.setLevel(logging.ERROR)

# Add the handlers to the root logger
logging.getLogger().addHandler(debug_handler)
logging.getLogger().addHandler(info_handler)
logging.getLogger().addHandler(warning_handler)
logging.getLogger().addHandler(error_handler)

# Path to CSV file (or use local directory)
csv_file = "users_and_rooms.csv"
# bearer_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4OTljNTFlYi01ZGEzLTQzMGUtYmViYS0zYzNiMjIzZTNhNDUiLCJzY29wZSI6Imh0dHBzOi8vd3VzZC1vcmcuaW5jaWRlbnRpcS5jb20iLCJzdWIiOiI0ODhjOGVlMy0yZjBlLWVmMTEtOTZmNS0wMDBkM2EwZTIzYmQiLCJqdGkiOiI1ZjRkZGQ2ZS1hMTRlLWVmMTEtOTkxYS0wMDBkM2EwZjRiMjAiLCJpYXQiOjE3MjIzNjQwNzguNjEsImV4cCI6MTgxNjk3MjA3OC42MTN9.6srINDKpPfGOfvjstOn-TYIJf-gBBGcVveRsihnnS-E"  # Replace with your actual bearer token

#Configure Base URL for all API calls. Note the URL does not include a trailing backslash
base_url = "https://wusd-org.incidentiq.com/api/v1.0"

def load_secrets():
  """Loads secrets from a JSON file in the secrets subdirectory.

  Returns:
    A dictionary containing the secrets.
  """

  secrets_file = os.path.join(os.path.dirname(__file__), "secrets", ".secrets.json")
  with open(secrets_file, "r") as f:
    return json.load(f)

# Example usage
secrets = load_secrets()
bearer_token = secrets["bearer_token"]

def get_user_id(email, bearer_token):
  """Calls an API to get the user ID based on email.

  Args:
    email: The email address of the user.
    bearer_token: The bearer token for authentication.

  Returns:
    The user ID as a string.
  """

  url = base_url + "/search/v2"  # Search Endpoint for locating userID by email
  logging.debug(url)
  header_json = {
  'Content-Type': 'application/json',
  'Authorization': bearer_token,
  }
  data = {
    "Query": email,
    "Facets": 4,
    "IncludeMatchedItems": False
    }
  try:
    response = requests.post(url, headers=header_json, json=data)
    response.raise_for_status()  # Raise an exception for error responses
    response_json = response.json()
    # print(response_json)
    id_value = response_json["Items"][0]["Id"]
    name_value = response_json["Items"][0]["Name"]
    logging.debug(f"Name: {name_value}, UserID: {id_value}")
    return id_value
  except Exception as e:
    logging.error(f"Failed to get user ID for email {email}: {e}")
    return None

def assign_user_to_room(user_id, room_id, bearer_token):
  """Calls an API to assign a user to a room.

  Args:
    user_id: The user ID of the user.
    room_id: The room ID of the room.
    bearer_token: The bearer token for authentication.
  """

  url = base_url + "/users/" + user_id + "/rooms"  # Requires UserID in the URL to post
  logging.debug(url)
  header_json = {
    'Content-Type': 'application/json',
    'Authorization': bearer_token,
  }
  payload = json.dumps([room_id])
  try:
    response = requests.post(url, headers=header_json, data=payload)
    response.raise_for_status()  # Raise an exception for error responses
    response_json = response.json()
    status_code = response_json["StatusCode"]
    logging.debug(f"UserID: {user_id}, RoomID: {room_id}")
    logging.info(f"Status Code: {status_code}")
  except Exception as e:
    logging.error(f"Failed to assign user {user_id} to room {room_id}: {e}")



def process_csv_file(csv_file, bearer_token):
  """Processes a CSV file containing email and room ID information.

  Args:
    csv_file: The path to the CSV file.
    bearer_token: The bearer token for authentication.
  """

  df = pd.read_csv(csv_file)

  for index, row in df.iterrows():
    email = row["Email"]
    room_id = row["RoomID"]

    user_id = get_user_id(email, bearer_token)
    assign_user_to_room(user_id, room_id, bearer_token)

process_csv_file(csv_file, bearer_token)