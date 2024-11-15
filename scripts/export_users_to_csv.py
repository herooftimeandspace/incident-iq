import json
import logging
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from api import iiq
from app import helper as helper

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

# def get_fieldnames(e):
#   value_string = str(e)
#   # Split the string at the colon
#   parts = value_string.split(":")

#   # Extract the part after the colon and remove leading/trailing whitespace
#   fields_string = parts[1].strip()

#   # Convert the string to a list
#   headers = fields_string.split(", ")
#   return headers

# def update_fieldnames(user_data,add_headers=[]):
#   temp_dict = user_data[0]
#   if add_headers:
#     # add headers to user_data
#     for i in add_headers:
#       i = i.strip("'")
#       temp_dict[i] = None
#     fieldnames = temp_dict.keys()
#   else:
#     fieldnames = temp_dict.keys()

#   return fieldnames

# def write_csv(user_data, csv_file, fieldnames):
#   with open(csv_file, 'w', newline='') as csvfile:
#     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

#     # Write the header row
#     writer.writeheader()

#     # Write the data rows

#     for row in user_data:
#       writer.writerow(row)


# def json_to_csv(user_data, csv_file,fieldnames=[]):
#   """Converts a JSON object to a CSV file.

#   Args:
#     json_data: The JSON object to convert.
#     csv_file: The path to the CSV file.
#   """
#   if not fieldnames:
#     logging.debug("Fieldnames passed as empty list")
#     fieldnames = user_data[0].keys()
#   # Extract the field names from the first item in the JSON data
#     try:
#       write_csv(user_data, csv_file, fieldnames)
#     except ValueError as e:
#       logging.error(e)
#       if "field" in str(e):  # Check if the error is due to missing fields
#         #Extract fieldnames from error
#         headers = get_fieldnames(e)

#         #Add missing headers to user_data as keys
#         fieldnames = update_fieldnames(user_data, headers)

#         json_to_csv(user_data, csv_file, fieldnames=fieldnames)
#       else:
#         # Re-raise the error if it's not related to missing fields
#         raise e
#   else:
#     logging.debug(f"Fieldnames passed as list: {fieldnames}")
#     try:
#       write_csv(user_data, csv_file, fieldnames)
#     except ValueError as e:
#       logging.error(e)
#       if "field" in str(e):  # Check if the error is due to missing fields
#         #Extract fieldnames from error
#         headers = get_fieldnames(e)

#         #Add missing headers to user_data as keys
#         fieldnames = update_fieldnames(user_data, headers)

#         json_to_csv(user_data, csv_file,fieldnames=fieldnames)
#       else:
#         raise e

# Create a logs subdirectory if it doesn't exist
output_dir = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(output_dir, exist_ok=True)

user_data = iiq.get_all_users()  # list of dicts

# dump JSON for debugging
with open(output_dir + "/dump.json", "w") as dump:
    json.dump(user_data, dump, ensure_ascii=False, indent=4)

helper.json_to_csv(user_data, os.path.join(output_dir, "output.csv"))
