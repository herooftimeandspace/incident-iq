import json
import logging
import sys
from collections import Counter
from pathlib import Path
from types import NoneType
import time
import datetime

sys.path.append(str(Path(__file__).parent.parent))

from api import iiq as iiq
from api import google_api as elgoog
from app import helper as helper
from app import variables as vars

start = time.time()

# Configure logging
logger = logging.getLogger(__name__)


def run():
    start = time.time()
    # Faculty and Staff
    payload_dict = {
        "Filters": [
            {"Facet": "role", "Id": "6d5fee76-e05e-43c0-b8e9-b8447746e502"},
            {"Facet": "role", "Id": "6d5fee76-e05e-43c0-b8e9-b8447746e503"},
        ]
    }
    # class_data = iiq.call_api(vars.class_url)
    users = iiq.call_api(
        vars.users_url, method="QUERY", iiq_payload=payload_dict
    )

    for staff in users:
        url = vars.class_for_user_url + "/" + staff["UserId"]
        courses = iiq.call_api(url)
        classroom_numbers = []
        if (
            not courses
        ):  # User does not have courses assigned to them in the SIS
            continue
        for c in courses:
            classroom_numbers.append(c["LocationDetails"])
        course_rooms = list(set(classroom_numbers))
        logging.debug(course_rooms)

    end = time.time()
    elapsed = end - start
    elapsed = helper.truncate(elapsed, 3)
    logging.debug(f"room_updates.run() took {elapsed} seconds.")


# iiq.modify_assigned_rooms(user_id, room_id)
