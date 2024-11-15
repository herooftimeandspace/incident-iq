# Path to CSV file (or use local directory)
csv_file = "users_and_rooms.csv"

# Configure Base URL for all API calls. Note the URL does not include a trailing backslash
base_url = "https://wusd-org.incidentiq.com/api/v1.0"
# dev_base_url = "https://demo.iiqstaging.com/api/v1.0"
# Location URLs
locations_url = base_url + "/locations"
rooms_url = locations_url + "/rooms"
# User URLs
users_url = base_url + "/users"
search_url = base_url + "/search/v2"
roles_url = base_url + "/sites/roles"
# Classes URLs
class_url = base_url + "/sis/classes"
class_for_user_url = class_url + "/for/user"
# Asset URLs
assets_url = base_url + "/assets"
assets_url_by_serial = assets_url + "/serial"
assets_url_by_tag = assets_url + "/assettag"
assets_url_status_type = assets_url + "/status/types"
assets_url_for_user_id = assets_url + "/for"
assets_url_by_room_id = assets_url + "/rooms"
ms_api_search = "https://wusd-org.incidentiq.com/apps/microsoftIntune/api/microsoftIntune/data/assets/search"
# Ticket URLs
tickets_url = base_url + "/tickets"
all_open_it_tickets = "{'ProductId':'88df910c-91aa-e711-80c2-0004ffa00010','Schema':'OpenWithModify','OnlyShowDeleted':false,'Filters':[],'FilterByProduct':true,'ShowChildTickets':true}"

# Global Variables to refer to if not defined in functions
params = {"p": 0, "$s": 20000}
timeout = 30
max_timeout = 600
required_keys = ["Content-Type", "Authorization"]
event_days = 45  # Number of days to lookback for checking records
event_threshold = 2  # Number of events before a user is flagged

# Environment flags. Double check they match with app.config
dev_env_flags = [
    "-d",
    "-debug",
    "-dev",
    "--d",
    "--debug",
    "--dev",
]
stage_env_flags = [
    "-s",
    "-staging",
    "--s",
    "--staging",
]
test_env_flags = list(set(dev_env_flags + stage_env_flags))
prod_env_flags = ["-p", "-prod", "--p", "--prod"]


log_location = "logs/"
"""Location to save logs
    """
log_info = "info.log"
"""The main log written to disk
    """

log_debug = "debug.log"
"""The debug log written to disk
    """

log_error = "error.log"
"""The error log written to disk
    """

log_warning = "warning.log"
"""The warning log written to disk
    """

# Specific function variables that might get reused.
data_tab_name = "Data"  # frequent_fliers.run()
