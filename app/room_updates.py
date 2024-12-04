import logging
import sys
from pathlib import Path
import time

sys.path.append(str(Path(__file__).parent.parent))

from api import iiq as iiq
from app import helper as helper
from app import variables as vars

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
    all_users = iiq.call_api(vars.users_url, method="GET")
    all_rooms = []
    locations = iiq.get_all_locations()
    for loc in locations:
        rooms = iiq.get_rooms_at_location(loc["LocationId"])
        if rooms:
            for r in rooms:
                all_rooms.append(r)
        else:
            continue  # skip there are no rooms at the location

    staff_and_faculty = []
    # Check if the user is staff or faculty
    for staff in all_users:
        if (
            staff["RoleId"] == "6d5fee76-e05e-43c0-b8e9-b8447746e502"
            or staff["RoleId"] == "6d5fee76-e05e-43c0-b8e9-b8447746e503"
        ):
            staff_and_faculty.append(staff)
        else:
            continue  # Not staff or faculty

    iiq_rooms_to_assign_staff = []
    for staff in staff_and_faculty:
        # TODO: Update this when new room numbers go up on the walls
        # Summer 2025
        try:
            if staff["Location"]["Name"] not in [
                "Windsor High School",
                "Windsor Oaks Academy",
                "Big Picture Learning",
            ]:
                logging.debug(
                    f"{staff["Name"]} is not at the high school."
                )
                continue  # Skip staff who aren't on the correct room scheme
        except KeyError:
            logging.warning(
                f"{staff["Name"]} {staff["UserId"]} doesn't have a location "
                "set."
            )
            continue
        url = vars.class_for_user_url + "/" + staff["UserId"]
        sis_courses = iiq.call_api(url)
        course_classroom_numbers = []
        staff_course_rooms = []
        if not sis_courses:
            logging.debug(
                f"{staff["Name"]} {staff["UserId"]} does not have courses "
                "assigned to them in the SIS."
            )
            continue
        for assigned_course in sis_courses:
            course_classroom_numbers.append(
                {
                    "LocationId": assigned_course["LocationId"],
                    "CourseRoomNumber": assigned_course[
                        "LocationDetails"
                    ],
                }
            )

        try:
            assigned_rooms = staff["Options"]["Locations"][
                "FavoriteLocations"
            ]
        except KeyError:
            assigned_rooms = []

        for cn in course_classroom_numbers:
            for room in all_rooms:
                # Match if course room in the SIS matches IIQ
                # AND if the course room and IIQ room are at the same site
                if (
                    cn["CourseRoomNumber"] == room["Name"]
                    # and cn["LocationId"] == staff["LocationId"]
                    and cn["LocationId"] == room["LocationId"]
                ):
                    logging.debug(
                        f"Course Room Number: {cn["CourseRoomNumber"]} | "
                        f"Course Site Id: {cn["LocationId"]} | "
                        f"Site Room Number: {room["Name"]} | "
                        f"RoomId: {room["LocationRoomId"]} | "
                        f"SiteId: {room["LocationId"]}"
                    )
                    staff_course_rooms.append(room["LocationRoomId"])

        if assigned_rooms and staff_course_rooms:
            if list(set(sorted(assigned_rooms))) == list(
                set(sorted(staff_course_rooms))
            ):
                logging.info(
                    "Assigned and course rooms are equal. No updates needed."
                )
                continue  # Skip if we don't need to update the assigned rooms
            common_elements = [
                item
                for item in assigned_rooms
                if item in staff_course_rooms
            ]
        elif assigned_rooms and not staff_course_rooms:
            common_elements = assigned_rooms
        elif not assigned_rooms and staff_course_rooms:
            common_elements = staff_course_rooms
        else:
            # TODO: Collect all SIS room numbers that don't match IIQ
            # and generate a report
            common_elements = []
            logging.info(
                f"Staff ({staff["Name"]}, {staff["UserId"]}) has no assigned "
                f"rooms and no courses with valid IIQ room numbers."
            )
            continue
        common_elements = list(set(common_elements))
        iiq_rooms_to_assign_staff.append(
            {
                "UserId": staff["UserId"],
                "Name": staff["Name"],
                "Site Name": staff["Location"]["Name"],
                "AssignedRooms": common_elements,
            }
        )

    for users_to_modify in iiq_rooms_to_assign_staff:
        logging.info(users_to_modify)
        # TODO: Actually update the users.
        # DO NOT RUN THIS BECAUSE ROOM NUMBERS ARE NOT CONSISTENT AT WMS
        # iiq.modify_assigned_rooms(users_to_modify["UserId"],
        #                           users_to_modify["AssignedRooms"])

    end = time.time()
    elapsed = end - start
    elapsed = helper.truncate(elapsed, 3)
    logging.debug(f"room_updates.run() took {elapsed} seconds.")
