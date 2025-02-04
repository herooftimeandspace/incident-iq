import csv
import logging
import math
from datetime import datetime, timedelta


def get_fieldnames(e: str) -> list:
    """Gets fieldnames for CSV headers

    Args:
        e (str): The string of all headers

    Returns:
        list: A list of headers
    """
    value_string = str(e)
    # Split the string at the colon
    parts = value_string.split(":")

    # Extract the part after the colon and remove leading/trailing whitespace
    fields_string = parts[1].strip()

    # Convert the string to a list
    headers = fields_string.split(", ")
    return headers


def update_fieldnames(user_data: list, add_headers: list = []) -> list:
    """Updates the list of field name headers with new keys

    Args:
        user_data (list): A list of rows in a CSV spreadsheet
        add_headers (list, optional): Additional headers to add to the
            list from the CSV keys. Defaults to [].

    Returns:
        list: The list of field names for the headers.
    """
    temp_dict = user_data[0]
    if add_headers:
        # add headers to user_data
        for i in add_headers:
            i = i.strip("'")
            temp_dict[i] = None
        fieldnames = temp_dict.keys()
    else:
        fieldnames = temp_dict.keys()

    return fieldnames


def write_csv(user_data: dict, csv_file: str, fieldnames: list):
    """Writes the CSV to disc

    Args:
        user_data (dict): The JSON to write to CSV
        csv_file (str): The path to the CSV file
        fieldnames (list): The list of field names to use as headers
    """
    with open(csv_file, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write the header row
        writer.writeheader()

        # Write the data rows

        for row in user_data:
            writer.writerow(row)


def json_to_csv(user_data: dict, csv_file: str, fieldnames: list = []):
    """Converts a JSON object to a CSV file.

    Args:
      user_data (dict): The dict/JSON object to convert.
      csv_file: The path to the CSV file.

    Args:
        user_data (dict): The JSON object to convert
        csv_file (str): The path to the CSV file
        fieldnames (list, optional): List of field names for the CSV
            headers. Defaults to [].

    Raises:
        ValueError: Raises a ValueError if the field names are in the
            list of headers
        e: Raises all other exceptions
    """
    if isinstance(user_data, dict):
        user_data = [user_data]
    if not fieldnames:
        logging.debug("Fieldnames passed as empty list")
        fieldnames = user_data[0].keys()
        # Extract the field names from the first item in the JSON data
        try:
            write_csv(user_data, csv_file, fieldnames)
        except ValueError as e:
            logging.error(e)
            if "field" in str(
                e
            ):  # Check if the error is due to missing fields
                # Extract fieldnames from error
                headers = get_fieldnames(e)

                # Add missing headers to user_data as keys
                fieldnames = update_fieldnames(user_data, headers)

                json_to_csv(user_data, csv_file, fieldnames=fieldnames)
            else:
                # Re-raise the error if it's not related to missing
                # fields
                raise e
    else:
        logging.debug(f"Fieldnames passed as list: {fieldnames}")
        try:
            write_csv(user_data, csv_file, fieldnames)
        except ValueError as e:
            logging.error(e)
            if "field" in str(
                e
            ):  # Check if the error is due to missing fields
                # Extract fieldnames from error
                headers = get_fieldnames(e)

                # Add missing headers to user_data as keys
                fieldnames = update_fieldnames(user_data, headers)

                json_to_csv(user_data, csv_file, fieldnames=fieldnames)
            else:
                raise e


def is_within_last_N_days(date_string: str, days: int) -> bool:
    """Checks if a given date string is within the last N days.

    Args:
      date_string (str): The date string in ISO 8601 format.
      days (int): The number of days to check

    Returns:
      True if the date is within the last N days, False otherwise.
    """
    if not isinstance(days, int):
        raise TypeError(
            f"Optional parameter '{repr(days)}' is type {type(days)}, not int."
        )
    if not isinstance(date_string, str):
        return False
    if not len(date_string) >= 11:
        return False

    date = datetime.fromisoformat(date_string)
    current_date = datetime.now()
    difference = current_date - date
    return difference.days <= days


def convert_to_html(data: list) -> str:
    """Converts a list of dictionaries to an HTML table string.

    Args:
        data: A list of dictionaries containing user activity information.

    Returns:
        A string containing the HTML table representation of the data.
    """
    if not isinstance(data, list):
        raise TypeError(
            f"Required parameter {repr(data)} is type {type(data)} not list"
        )
    if not data:
        raise ValueError(
            f"Required parameter value is invalid. Value: {data}"
        )
    html = "<table>"
    html += "<tr>"
    for key in data[0].keys():  # Get headers from the first dictionary
        html += f"<th>{key}</th>"
    html += "</tr>"

    for item in data:
        html += "<tr>"
        for value in item.values():
            # Handle None values for Unassigned Date
            html += f"<td>{value if value else 'N/A'}</td>"
        html += "</tr>"

    html += "</table>"
    return html


def convert_to_sheets(data: list) -> list:
    """Converts a list of dicts containing row data to a new list for
        upload to Google Sheets

    Args:
        data (list): A list of dicts containing the row headers as keys
            and row data as values

    Raises:
        TypeError: Required parameter 'data' must be a list
        TypeError: An individual item in the 'data' list is not a dict

    Returns:
        list: The first item in the list is the headers, the remaining
            items in the list are the rows
    """
    if not isinstance(data, list):
        raise TypeError(f"{repr(data)} is type {type(data)}, not list")
    # for index, event in enumerate(frequent_flier_events)
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise TypeError(
                f"Item at index {index} is type {type(item)}, not dict"
            )
    values = []
    header_row = []
    if not data:
        return values
    headers = data[0].keys()
    for h in headers:
        header_row.append(h)
    values.append(header_row)

    for i in data:
        row = []
        for v in i.values():
            if v is None:
                row.append("")
            else:
                row.append(v)
        values.append(row)
    return values


def truncate(number: int, decimals: int = 0) -> int:
    """Return a value truncated to a specific number of decimal places.

    Args:
        number (int): The number to truncate
        decimals (int, optional): The number of decimal places to
            truncate. Defaults to 0.

    Raises:
        TypeError: Number must be a float
        TypeError: Decimals must be an int
        ValueError: Validates that the decimal is 0 or more.

    Returns:
        int: The number, truncated to the number of decimal places.
    """

    # Validate data types before attempting to process.
    if not isinstance(decimals, int):
        raise TypeError(f"Decimal must be an int, not {type(decimals)}")
    if not isinstance(number, float):
        raise TypeError(f"Number must be an float, not {type(number)}")
    if decimals <= 0:
        raise ValueError(
            f"Decimal places has to be 1 or more, not {decimals}"
        )

    factor = 10.0**decimals
    return math.trunc(number * factor) / factor


def get_timestamp(number: int) -> str:
    """Subtracts the number intput from the current time to generate a
       timestamp N number of minutes ago.

    Args:
        number (int): Number of seconds

    Raises:
        TypeError: Validates number is an int
        ValueError: Ensures minutes is > 0

    Returns:
        string: an ISO8601 compliant timestamp
    """
    if not isinstance(number, int):
        raise TypeError(
            f"Number of minutes must be an integer, not {type(number)}"
        )
    elif number <= 0:
        raise ValueError(
            f"Number of minutes must be greater than zero, not {number}"
        )

    date = datetime.now()
    delta = timedelta(minutes=number)
    modified_since = date - delta
    modified_since = modified_since.replace(
        microsecond=0
    )  # .isoformat()
    modified_since_iso = modified_since.replace(
        microsecond=0
    ).isoformat()
    return modified_since, modified_since_iso
