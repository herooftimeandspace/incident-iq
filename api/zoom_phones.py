"""Interacts with the Zoom API to pull down phone numbers and device
owners, and renames devices based on their room assignments in IIQ."""

import requests
import base64
import json
import logging

from app import variables as vars


def get_auth_token(secrets: dict) -> str:
    url = f"{vars.zoom_oauth_url}{secrets["AccountId"]}"
    basic_auth_text = (
        secrets["ClientId"] + ":" + secrets["ClientSecret"]
    )
    basic_auth_base64 = base64.b64encode(
        basic_auth_text.encode("utf-8")
    )
    basic_auth_base64 = basic_auth_base64.decode("utf-8")

    payload = {}
    headers = {"Authorization": f"Basic {basic_auth_base64}"}

    response = requests.request(
        "POST", url, headers=headers, data=payload
    )
    if response.status_code == 200:
        response = json.loads(response.text)
    else:
        logging.debug(
            f"Request failed with status code {response.status_code}"
        )
        return None

    # print(response.text)
    return response["access_token"]


def get_phones(auth: str, device_status: str = "assigned") -> list:
    phones = []
    page_size = 100

    url = "https://api.zoom.us/v2/phone/devices"
    headers = {"Authorization": f"Bearer {auth}"}

    default_params = {"type": device_status, "page_size": page_size}
    while True:
        response = requests.get(
            url, headers=headers, params=default_params
        )
        response.raise_for_status()

        if response.status_code == 200:
            data = response.json()
            logging.debug(
                f"Page Size: {data["page_size"]} | Total Records: "
                f"{data["total_records"]} | Phones Len {len(phones)} | "
                f"NextPageToken {data["next_page_token"]}"
            )

            # print(data["devices"])
            phones.extend(data["devices"])

            if len(phones) == data["total_records"]:
                break
            else:
                default_params["next_page_token"] = data[
                    "next_page_token"
                ]

    return phones


def get_user_by_id(auth: str, id: str) -> dict | None:
    url = vars.zoom_users_url + "/" + id
    headers = {"Authorization": f"Bearer {auth}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return None
