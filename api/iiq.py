import json
import logging
from time import sleep
from types import NoneType

import app.variables as vars
import requests
from app import config


################################################
# GET / POST API
################################################
def call_api(
    url,
    method="GET",
    iiq_payload="",
    iiq_headers=config.set_headers(),
    params=vars.params,
    timeout=vars.timeout,
    max_timeout=vars.max_timeout,
):
    """Sends HTTP Requests to the IncidentIQ API. Requires a URL to send. Defaults to the "Get" method if none is specified.

    Args:
        url (str): The URL to send the HTTP request to
        method (str, optional): The method of the HTTP request to use. Case sensitive. Can be any of GET, POST, QUERY, PUT, DELETE. Defaults to "get".
        iiq_payload (dict,str,None, optional): The payload used when sending a POST command. Defaults to None, which will remove data from IIQ.
        iiq_headers (dict, optional): Headers for the HTTP request. If none are supplied, will pull default credentials from /secrets/secrets.json. Defaults to config.set_headers().
        params (dict, optional): Starting page and number of results to return. Used to loop through pages if needed. Defaults to {"p": 0,"": 20000}.
        timeout (int, optional): Amount of time in seconds to wait for a timeout during the request. Defaults to 30.
        max_timeout (int, optional): The maximum amount of time to wait before raising an error and breaking the request. Defaults to 600.

    Returns:
        list: A list of items from the HTTP response JSON. Returns None if empty.
    """
    if not isinstance(url, str):
        raise TypeError(f"URL must be type: str, not {type(url)}")
    if not url:
        raise ValueError("URL must not be empty")
    if not isinstance(method, str):
        raise TypeError(f"Method must be type: str, not {type(method)}")
    if not method:
        raise ValueError("Method must not be empty")
    if method.upper() not in ["GET", "POST", "DELETE", "QUERY"]:
        raise ValueError("Method must be one of GET, POST, DELETE, QUERY")
    if not isinstance(iiq_payload, (dict, str, NoneType)):
        raise TypeError(
            f"JSON must be type: dict, str or None, not {type(iiq_payload)}"
        )
    if not isinstance(iiq_headers, dict):
        raise TypeError(f"Headers must be type: dict, not {type(iiq_headers)}")
    if not iiq_headers:
        raise ValueError("Headers must not be empty")
    if not all(key in iiq_headers for key in vars.required_keys):
        missing_keys = [
            key for key in vars.required_keys if key not in iiq_headers
        ]
        raise KeyError(f"Missing required keys: {missing_keys}")
    if not isinstance(params, (dict, NoneType)):
        raise TypeError(f"Params must be type: dict, not {type(params)}")
    if isinstance(params, dict):
        if not all(key in params for key in vars.params):
            missing_keys = [key for key in vars.params if key not in params]
            raise KeyError(f"Missing required keys: {missing_keys}")
    if not isinstance(timeout, int):
        raise TypeError(f"Method must be type: int, not {type(timeout)}")
    if not timeout:
        raise ValueError("Timeout must not be empty")
    if timeout < 0:
        raise ValueError(f"Timeout must be a positive int, not {timeout}")
    if not isinstance(max_timeout, int):
        raise TypeError(f"Method must be type: json, not {type(max_timeout)}")
    if not max_timeout:
        raise ValueError("Max Timeout must not be empty")
    if max_timeout < 0:
        raise ValueError(
            f"Max Timeout must be a positive int, not {max_timeout}"
        )
    if max_timeout < timeout:
        raise ValueError(
            f"Max Timeout ({max_timeout}) must be greater than the timeout ({timeout})"
        )

    iiq_data = []
    page = 1
    while True:
        try:
            if method.upper() == "GET":
                response = requests.get(
                    url, headers=iiq_headers, params=params, timeout=timeout
                )
                response.raise_for_status()  # Raise an exception for error responses
                response_json = (
                    response.json()
                )  # Create a dict from the JSON data
                status_code = response_json["StatusCode"]
                # logging.debug(f"Status Code: {status_code} | URL: {url} | Page: {page} | Amount: {params['$s']} | Timeout: {timeout} | Response: {response_json}")
                logging.debug(f"Status Code: {status_code} | URL: {url}")
            elif method.upper() == "POST":
                # logging.info(f"Attempting to {method} {iiq_payload} as data")
                response = requests.post(
                    url,
                    data=iiq_payload,
                    headers=iiq_headers,
                    timeout=timeout,
                )
                response.raise_for_status()  # Raise an exception for error responses
                response_json = (
                    response.json()
                )  # Create a dict from the JSON data
                logging.debug(
                    f"Status Code: {response_json["StatusCode"]} | Message {response_json["Message"]} | URL: {url}"
                )
                # break
            elif method.upper() == "QUERY":
                response = requests.post(
                    url,
                    iiq_payload,
                    headers=iiq_headers,
                    params=params,
                    timeout=timeout,
                )
                response.raise_for_status()  # Raise an exception for error responses
                response_json = (
                    response.json()
                )  # Create a dict from the JSON data
                # logging.debug(f"Status Code: {status_code} | URL: {url} | Page: {page} | Amount: {params['$s']} | Timeout: {timeout} | Response: {response_json}")
                logging.debug(
                    f"Status Code: {response_json["StatusCode"]} | URL: {url}"
                )
            elif method.upper() == "DELETE":
                response = requests.delete(
                    url, headers=iiq_headers, timeout=timeout
                )
                response.raise_for_status()
                response_json = (
                    response.json()
                )  # Create a dict from the JSON data
                logging.debug(
                    f"Status Code: {response_json["StatusCode"]} | URL: {url}"
                )
            elif method.upper() == "PUT":
                response = requests.put(
                    url, headers=iiq_headers, timeout=timeout
                )
                response.raise_for_status()
                response_json = (
                    response.json()
                )  # Create a dict from the JSON data
                logging.debug(
                    f"Status Code: {response_json["StatusCode"]} | URL: {url}"
                )
            else:
                logging.warning(
                    f"Request method {method} not supported. Breaking."
                )
                break
        except requests.exceptions.Timeout:
            if timeout >= 600:  # Error and Break the loop.
                logging.error(
                    f"Request timeout={timeout} | Retrieving data exceeded {max_timeout} seconds."
                )
                break
            else:
                timeout = timeout * 2
                logging.warning(
                    "API timeout occurred. Backing off for {} seconds.".format(
                        timeout
                    )
                )
                sleep(timeout)
                call_api(
                    url=url,
                    method=method,
                    iiq_payload=iiq_payload,
                    iiq_headers=iiq_headers,
                    params=params,
                    timeout=timeout,
                    max_timeout=max_timeout,
                )  # Retry with larger timeout
        except requests.exceptions.HTTPError as e:
            logging.warning(
                f"HTTPError exception for API {method} call to {url} with payload {iiq_payload} | Message: {e} | Response: {response}"
            )
            if e.response.status_code == 502 and timeout < max_timeout:
                sleep(timeout)
                call_api(
                    url=url,
                    method=method,
                    iiq_payload=iiq_payload,
                    iiq_headers=iiq_headers,
                    params=params,
                    timeout=timeout,
                    max_timeout=max_timeout,
                )
            elif e.response.status_code == 500 and method.upper() == "POST":
                # Try to fix payload by converting it to str
                iiq_payload = json.dumps(iiq_payload)
                call_api(
                    url=url,
                    method=method,
                    iiq_payload=iiq_payload,
                    iiq_headers=iiq_headers,
                    params=params,
                    timeout=timeout,
                    max_timeout=max_timeout,
                )
            else:
                raise
        except Exception as e:
            logging.warning(
                f"An exception occurred for API {method} call to {url} | Message: {e} | Response: {response}"
            )

        response_data = response.json()
        if response_data["ItemCount"] <= 0:
            logging.info(
                f"API {method} call to {url} returned {response_data["ItemCount"]} results."
            )
            return None

        # Extract the current page and page count
        current_page = page
        try:
            page_count = response_data["Paging"]["PageCount"]
        except KeyError:
            page_count = current_page

        # Check if the current page is less than or equal to the page count
        if page < page_count:
            page += 1  # Increment page by 1
            logging.debug(
                f"Current Page: {current_page} | Next Page: {page}| Total Page Count: {page_count}"
            )
            # Iterate through the list of dicts. Append the results to the list.
            for i in response_data["Items"]:
                iiq_data.append(i)
        elif page == page_count:
            # If there was only 1 page, return that page, otherwise return the full list so that the next page can be added.
            # logging.debug("All pages have been fetched.")
            if current_page == 1:
                try:
                    iiq_data = response_data["Items"]
                except KeyError:
                    try:
                        iiq_data = [response_data["Item"]]
                    except KeyError:
                        iiq_data = response_data
                    except Exception as e:
                        raise e
                except Exception as e:
                    logging.error(
                        f"An error occurred while parsing the response data 'Items'. {e}"
                    )
                logging.info(
                    f"API {method} call to {url} returned page {current_page} of {page_count} with {len(iiq_data)} items in the result."
                )
                logging.debug(
                    f"Type: {type(iiq_data)} | Len {len(iiq_data)} | iiq_data: {iiq_data}"
                )
                if not iiq_data:
                    logging.warning("The HTTP request returned an empty list.")
                    return None
                else:
                    return iiq_data
            else:
                logging.info(
                    f"API {method} call to {url} returned page {current_page} of {page_count} with {len(iiq_data)} items in the result."
                )
                logging.debug(
                    f"Type: {type(iiq_data)} | Len {len(iiq_data)} | iiq_data: {iiq_data}"
                )
                if not iiq_data:
                    logging.warning("The HTTP request returned an empty list.")
                    return None
                else:
                    return iiq_data
        else:
            logging.error("An unexpected error has occurred.")
            break


def call_intune_api(
    url,
    method="POST",
    iiq_payload="",
    iiq_headers=config.set_headers(),
    params=vars.params,
    timeout=vars.timeout,
    max_timeout=vars.max_timeout,
):
    """Sends HTTP Requests to the IncidentIQ API. Requires a URL to send. Defaults to the "Get" method if none is specified.

    Args:
        url (str): The URL to send the HTTP request to
        method (str, optional): The method of the HTTP request to use. Case sensitive. Can be any of GET, POST, DELETE. Defaults to "get".
        iiq_payload (dict,str,None, optional): The payload used when sending a POST command. Defaults to None, which will remove data from IIQ.
        iiq_headers (dict, optional): Headers for the HTTP request. If none are supplied, will pull default credentials from /secrets/secrets.json. Defaults to config.set_headers().
        params (dict, optional): Starting page and number of results to return. Used to loop through pages if needed. Defaults to {"p": 0,"": 20000}.
        timeout (int, optional): Amount of time in seconds to wait for a timeout during the request. Defaults to 30.
        max_timeout (int, optional): The maximum amount of time to wait before raising an error and breaking the request. Defaults to 600.

    Returns:
        list: A list of items from the HTTP response JSON. Returns None if empty.
    """
    if not isinstance(url, str):
        raise TypeError(f"URL must be type: str, not {type(url)}")
    if not url:
        raise ValueError("URL must not be empty")
    if not isinstance(method, str):
        raise TypeError(f"Method must be type: str, not {type(method)}")
    if not method:
        raise ValueError("Method must not be empty")
    if method.upper() not in ["GET", "POST", "DELETE", "QUERY"]:
        raise ValueError("Method must be one of GET, POST, DELETE, QUERY")
    if not isinstance(iiq_payload, (dict, str, NoneType)):
        raise TypeError(
            f"JSON must be type: dict, str or None, not {type(iiq_payload)}"
        )
    if not isinstance(iiq_headers, dict):
        raise TypeError(f"Headers must be type: dict, not {type(iiq_headers)}")
    if not iiq_headers:
        raise ValueError("Headers must not be empty")
    if not all(key in iiq_headers for key in vars.required_keys):
        missing_keys = [
            key for key in vars.required_keys if key not in iiq_headers
        ]
        raise KeyError(f"Missing required keys: {missing_keys}")
    if not isinstance(params, dict):
        raise TypeError(f"Params must be type: dict, not {type(params)}")
    if not all(key in params for key in vars.params):
        missing_keys = [key for key in vars.params if key not in params]
        raise KeyError(f"Missing required keys: {missing_keys}")
    if not isinstance(timeout, int):
        raise TypeError(f"Method must be type: int, not {type(timeout)}")
    if not timeout:
        raise ValueError("Timeout must not be empty")
    if timeout < 0:
        raise ValueError(f"Timeout must be a positive int, not {timeout}")
    if not isinstance(max_timeout, int):
        raise TypeError(f"Method must be type: json, not {type(max_timeout)}")
    if not max_timeout:
        raise ValueError("Max Timeout must not be empty")
    if max_timeout < 0:
        raise ValueError(
            f"Max Timeout must be a positive int, not {max_timeout}"
        )
    if max_timeout < timeout:
        raise ValueError(
            f"Max Timeout ({max_timeout}) must be greater than the timeout ({timeout})"
        )

    try:
        if method.upper() == "GET":
            response = requests.get(
                url, headers=iiq_headers, params=params, timeout=timeout
            )
            response.raise_for_status()  # Raise an exception for error responses
            response_json = response.json()  # Create a dict from the JSON data
            status_code = response_json["StatusCode"]
            # logging.debug(f"Status Code: {status_code} | URL: {url} | Amount: {params['$s']} | Timeout: {timeout} | Response: {response_json}")
            logging.debug(f"Status Code: {status_code} | URL: {url}")
        elif method.upper() == "POST":
            response = requests.post(
                url, iiq_payload, headers=iiq_headers, timeout=timeout
            )
            response.raise_for_status()  # Raise an exception for error responses
            response_json = response.json()  # Create a dict from the JSON data
            status_code = response_json["StatusCode"]
            msg = response_json["Message"]
            logging.debug(
                f"Status Code: {status_code} | Message {msg} | URL: {url}"
            )
        elif method.upper() == "QUERY":
            response = requests.post(
                url,
                iiq_payload,
                headers=iiq_headers,
                params=params,
                timeout=timeout,
            )
            response.raise_for_status()  # Raise an exception for error responses
            response_json = response.json()  # Create a dict from the JSON data
            status_code = response_json["StatusCode"]
            logging.debug(f"Status Code: {status_code} | URL: {url}")
        else:
            logging.warning(
                f"Request method {method} not supported. Breaking."
            )
    except requests.exceptions.Timeout:
        if timeout >= 600:  # Error and Break the loop.
            logging.error(
                f"Request timeout={timeout} | Retrieving data exceeded {max_timeout} seconds."
            )
        else:
            timeout = timeout * 2
            logging.warning(
                "API timeout occurred. Backing off for {} seconds.".format(
                    timeout
                )
            )
            sleep(timeout)
            call_api(
                url,
                method,
                iiq_payload,
                iiq_headers,
                params,
                timeout,
                max_timeout,
            )  # Retry with larger timeout
    # except Exception as e:
    #     logging.error(f"Failed API call for {url} | Message: {e}")

    response_data = response.json()
    if not response_data:
        return None
    elif len(response_data) == 1:
        return response_data[0]
    else:
        logging.warning(
            f"Response data from API is malformed. Type: {type(response_data)}, Response: {response_data}"
        )


################################################
# Locations API
################################################
def get_all_locations():
    """Queries the IIQ API for all physical locations and their metadata

    Returns:
        list: List of dicts.
    """
    location_data = call_api(vars.locations_url)
    return location_data


def get_all_locations_ids():
    """Gets all Location IDs

    Returns:
        list: A list of location IDs only if they are type:str
    """
    location_data = call_api(vars.locations_url)
    logging.debug(location_data)
    location_ids = []
    for loc in location_data:
        if isinstance(loc["LocationId"], str):
            location_ids.append(loc["LocationId"])
    return location_ids


def get_location_by_id(location_id):
    url = vars.locations_url + "/" + location_id
    location_data = call_api(url)
    return location_data


def get_rooms_at_location(location_id):
    """Gets all rooms in a physical locaiton by location_id

    Args:
        location_id (string): The ID of the physical site to query rooms.

    Returns:
        list: List of dicts. Information about the rooms at that location
    """
    url = vars.locations_url + "/" + location_id + "/rooms"
    all_rooms = call_api(url)
    return all_rooms


def get_room_by_id(room_id):
    """Gets information about a specific room by its ID

    Args:
        room_id (string): The ID of the room to query

    Returns:
        dict: Specific details about the room
    """
    url = vars.rooms_url + "/" + room_id  # Requires RoomID in the URL to post
    room_data = call_api(url)
    return room_data


################################################
# Users API
################################################
def get_all_users():
    """Gets all users from the User API

    Returns:
        list: A list of dicts. One dict per user
    """
    user_data = call_api(vars.users_url)
    return user_data  # list of dicts


def get_user_id_by_email(email):
    """Gets user data from IIQ by their email address

    Args:
        email (str): The email address of the user.

    Returns:
        str: The UserID of the user
    """
    url = vars.search_url  # Search Endpoint for locating userID by email
    data = json.dumps(
        {"Query": email, "Facets": 4, "IncludeMatchedItems": False}
    )
    user_id = call_api(url, method="POST", iiq_payload=data)
    return user_id[0]["Id"]


def get_assigned_rooms_for_user_id(user_id):
    """Gets all rooms assigned to the user by the user's ID

    Args:
        user_id (str): The ID string of the user to query

    Returns:
        list: A list of dicts. One dict per RoomID returned.
    """
    url = (
        vars.users_url + "/" + user_id + "/rooms"
    )  # Requires UserID in the URL to post
    response = call_api(url)
    if not response:
        return "No rooms assigned."
    else:
        return response


def modify_assigned_rooms(user_id, room_id):
    """Calls an API to assign a user to a room, or remove all rooms from user.
       Defaults to removing all rooms for a given user.

    Args:
        user_id (str): The ID of the user to modify
        room_id (list, str, None): The room or list of rooms to add to a user. If None, removes all rooms.
    """
    if not room_id:
        # Remove assigned rooms
        url = (
            vars.users_url + "/" + user_id + "/rooms"
        )  # Requires UserID in the URL to post
        payload = json.dumps([])
        call_api(url, method="POST", iiq_payload=payload)
    elif type(room_id) is str:
        # Add a single assigned room
        url = (
            vars.users_url + "/" + user_id + "/rooms"
        )  # Requires UserID in the URL to post
        logging.debug(url)
        payload = json.dumps([room_id])  # Wrap room ID in a list
        call_api(url, method="POST", iiq_payload=payload)
    elif type(room_id) is list:
        # Add a list of rooms to the user
        url = (
            vars.users_url + "/" + user_id + "/rooms"
        )  # Requires UserID in the URL to post
        logging.debug(url)
        payload = json.dumps(room_id)
        call_api(url, method="POST", iiq_payload=payload)


def get_role_ids():
    roles = call_api(vars.roles_url)
    role_dict = {}
    for role in roles:
        role_dict[role["Name"]] = role["RoleId"]
    return role_dict


def get_user_activity(user_id):
    activity_url = vars.users_url + "/" + user_id + "/activities"
    user_activity = call_api(activity_url, "GET")
    return user_activity


################################################
# Classes API
################################################
def get_all_classes():
    """Get all classes from IIQ. Classes are imported from the SIS

    Returns:
        all_classes (list): A list of dicts representing classes and associated metadata
    """
    all_classes = call_api(vars.class_url)
    return all_classes


def get_class_info(class_id):
    """Get info about a specific class ID

    Args:
        class_id (str): The Class ID str to query

    Returns:
        class_info (doct): The class metadata
    """
    url = vars.class_url + "/" + class_id
    class_info = call_api(url)
    return class_info


def get_classes_for_user(user_id):
    """Gets all classes currently assinged to a faculty member

    Args:
        user_id (str): The UserID to query

    Returns:
        classes_for_user (list): A list of class metadata for all classes assigned to the faculty member
        None: No classes were found for the current UserID
    """
    url = vars.class_for_user_url + "/" + user_id
    classes_for_user = call_api(url)
    if not classes_for_user:
        logging.debug(f"UserID {user_id} has no classes")
        return None
    else:
        return classes_for_user


################################################
# Assets API
################################################
def get_assets(filter=[]):
    """Get all assets from Incident IQ

    Args:
        filter (list, optional): A list of filter arguments to pare down the results, if provided. Defaults to [].

    Returns:
        assets (list): A list of dicts representing assets.
    """
    url = vars.assets_url
    filter = json.dumps(filter)  # Convert the list of filters to JSON
    assets = call_api(url, method="QUERY", iiq_payload=filter)
    return assets


def get_asset_status_types():
    """Gets all types of assets in IncidentIQ

    Returns:
        asset_types (list): A list of dicts containing asset types and metadata
    """
    url = vars.assets_url_status_type
    asset_types = call_api(url)
    return asset_types


def get_asset_by_id(asset_id):
    """Get a specific asset by the provided ID.

    Args:
        asset_id (str): The asset ID string to query

    Returns:
        asset (dict): The asset returned by the query
    """
    url = vars.assets_url + "/" + asset_id
    asset = call_api(url, params=None)
    return asset


def get_asset_by_serial(serial_number):
    """Get a specific asset by the provided serial number

    Args:
        serial_number (str): The serial number to query

    Returns:
        asset (dict): The asset returned by the query
    """
    url = vars.assets_url_by_serial + "/" + serial_number
    asset = call_api(url, params=None)
    if isinstance(asset, list) and len(asset) == 1:
        return asset[0]
    elif isinstance(asset, list):
        return asset
    else:
        return None


def get_asset_by_tag(asset_tag):
    """Get a specific asset by the provided asset tag

    Args:
        serial_number (str): The asset tag to query

    Returns:
        asset (dict): The asset returned by the query
    """
    url = vars.assets_url_by_tag + "/" + asset_tag
    asset = call_api(url, params=None)
    if isinstance(asset, list) and len(asset) == 1:
        return asset[0]
    elif isinstance(asset, list):
        return asset
    else:
        return None


def get_asset(asset_id):
    """Gets an asset by it's ID. ID can be any of IIQ AssetId, Serial Number or Asset Tag

    Args:
        asset_id (str): The Asset ID to look up.

    Returns:
        dict: A dictionary of asset details
    """
    asset = get_asset_by_id(asset_id)
    if asset is not None:
        return asset
    else:
        logging.info(
            f"Asset {asset_id} not found by IIQ AssetId. Searching for asset by Serial Number."
        )
        asset = get_asset_by_serial(asset_id)
        if asset is not None:
            return asset
        else:
            logging.info(
                f"Asset {asset_id} not found by Serial Number {asset_id}. Searching for asset by Asset Tag."
            )
            asset = get_asset_by_tag(asset_id)
            if asset is not None:
                return asset
            else:
                logging.warning(
                    f"Asset {asset_id} not found by Asset Tag, Serial Number or IIQ AssetId. Returning None."
                )
                return None


def update_owner(asset_id, owner_id):
    """Updates the owner of an asset by the owner's user ID. If the owner_id is None, removes the owner from the asset

    Args:
        asset_id (str): The Asset ID to update
        owner_id (str, None): The User ID to assign to the asset. If none, unassigns the asset
    """
    url = vars.assets_url + "/" + asset_id + "/owner"
    payload = json.dumps({"OwnerId": owner_id})
    response = call_api(url, method="POST", iiq_payload=payload)
    logging.debug(response["Message"])


################################################
# Tickets API
################################################
def get_all_open_tickets():
    url = vars.tickets_url
    payload = json.dumps(vars.all_open_it_tickets)
    response = call_api(url, method="POST", iiq_payload=payload)
    return response


def get_it_tickets_for_user_id(user_id):
    url = vars.tickets_url
    search_payload = {"Filters": [{"Facet": "user", "Id": user_id}]}
    # payload = json.dumps(search_payload.tostring())
    response = call_api(url, method="POST", iiq_payload=search_payload)
    return response


def get_it_ticket_for_user_and_asset(user_id, asset_id):
    url = vars.tickets_url
    search_payload = {
        "Filters": [
            {"Facet": "asset", "Id": asset_id},
            {"Facet": "user", "Id": user_id},
        ]
    }
    search_payload = json.dumps(search_payload)
    logging.debug(
        f"search_payload type {type(search_payload)} | value: {search_payload}"
    )
    response = requests.post(
        url, data=search_payload, headers=config.set_headers()
    )
    response_json = response.json()
    if response_json["ItemCount"] <= 0:
        logging.info(
            f"API POST call to {url} returned {response_json["ItemCount"]} results."
        )
        return None
    elif response_json["ItemCount"] >= 1:
        logging.info(
            f"API POST call to {url} returned {response_json["ItemCount"]} result(s)."
        )
        return response_json["Items"]
