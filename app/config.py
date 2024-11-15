import json
import logging
import os
import re
import time
from logging.config import dictConfig
from pathlib import Path

import app.helper as helper
import app.variables as app_vars
from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.schedulers.background import BlockingScheduler

parent_dir = str(Path(__file__).parent.parent)
cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_location = os.path.join(parent_dir, app_vars.log_location)
logger = logging.getLogger(__name__)
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


def load_secrets(file: str = "secrets.json") -> dict:
    """Loads secrets from a JSON file in the secrets subdirectory.

    Args:
        file (str): The file to load secrets from. Optional. Defaults to 'secrets.json'

    Returns:
      A dictionary containing the secrets.
    """
    parent_dir = os.path.dirname(__file__)
    grandparent_dir = os.path.dirname(parent_dir)
    secrets_file = os.path.join(grandparent_dir, "secrets", file)
    with open(secrets_file, "r") as f:
        return json.load(f)


def set_headers() -> dict:
    """Sets the headers for making calls to the IncidentIQ API

    Returns:
        header_json (dict): The headers containing the content type and authorization bearer token
    """
    secret = load_secrets()
    bearer_token = secret["bearer_token"]
    header_json = {
        "Content-Type": "application/json",
        "Authorization": bearer_token,
    }
    return header_json


def set_base_url() -> str:
    """Sets the Base URL for interacting with the IIQ API. Base URL is stored in secrets to prevent doxxing / hacking.

    Args:
        base_url_pattern (str): The pattern to match.

    Raises:
        ValueError: The base_url from the secrets file must be a str
        ValueError: The base_url from the secrets file must match the regex pattern in variables.py

    Returns:
        base_url (str): The correctly formed URL string for use as the base of all API calls
    """
    base_url_pattern = r"https://.*\.incidentiq\.com/api/v1.0"
    secret = load_secrets()
    base_url = secret["base_url"]
    if not base_url:
        raise ValueError(f"BaseURL must be a str, not {type(base_url)}")
    elif not bool(re.match(base_url_pattern, base_url)):
        raise ValueError(
            f"BaseURL does not match the pattern {base_url_pattern}"
        )
    else:
        return base_url


def set_logging_config(env: str) -> dict:
    """Sets the logging config based on the environment variable passed in
       from the command line.

    Args:
        env (str): The environment variable passed in

    Raises:
        TypeError: Env should be a string
        ValueError: Env should be some iteration of prod, staging, dev or debug

    Returns:
        dict: The logging configuration to use
    """
    if not isinstance(env, str):
        msg = str("Environment should be type: str, not {}").format(type(env))
        raise TypeError(msg)
    if env not in prod_env_flags and env not in test_env_flags:
        if env is not None:
            msg = str(
                "Invalid environment flag. '{}' was passed but it should "
                "be '--dev', '--staging' or '--prod'"
            ).format(env)
            raise ValueError(msg)

    logging_config = dict(
        version=1,
        formatters={
            "f": {"format": "%(asctime)s - %(levelname)s - %(message)s"}
        },
        handlers={
            "docker": {
                "class": "logging.StreamHandler",
                "formatter": "f",
                "level": logging.INFO,
                "stream": "ext://sys.stdout",
            }
        },
        root={
            "handlers": ["docker"],  # 'console', 'file'
            "level": logging.DEBUG,
            "disable_existing_loggers": False,
        },
    )
    if env in ("-d", "--debug", "-debug"):
        # Set logging to DEBUG. Send to file and docker STDOUT
        logging_config = dict(
            version=1,
            formatters={
                "f": {"format": "%(asctime)s - %(levelname)s - %(message)s"}
            },
            handlers={
                "file": {
                    "class": "logging.FileHandler",
                    "formatter": "f",
                    "level": logging.DEBUG,
                    "filename": log_location + app_vars.log_debug,
                },
                "docker": {
                    "class": "logging.StreamHandler",
                    "formatter": "f",
                    "level": logging.DEBUG,
                    "stream": "ext://sys.stdout",
                },
            },
            root={
                "handlers": ["docker", "file"],  # 'console', 'file'
                "level": logging.DEBUG,
                "disable_existing_loggers": False,
            },
        )
    elif env in ("--dev", "-dev"):
        # Set logging to DEBUG. Send to docker STDOUT
        logging_config = dict(
            version=1,
            formatters={
                "f": {"format": "%(asctime)s - %(levelname)s - %(message)s"}
            },
            handlers={
                "file": {
                    "class": "logging.FileHandler",
                    "formatter": "f",
                    "level": logging.DEBUG,
                    "filename": log_location + app_vars.log_debug,
                },
                "docker": {
                    "class": "logging.StreamHandler",
                    "formatter": "f",
                    "level": logging.DEBUG,
                    "stream": "ext://sys.stdout",
                },
            },
            root={
                "handlers": ["docker"],  # 'console', 'file'
                "level": logging.DEBUG,
                "disable_existing_loggers": False,
            },
        )
    elif env in ("-s", "--staging", "-staging"):
        # Set logging to INFO. Send to docker STDOUT
        logging_config = dict(
            version=1,
            formatters={
                "f": {"format": "%(asctime)s - %(levelname)s - %(message)s"}
            },
            handlers={
                "file": {
                    "class": "logging.FileHandler",
                    "formatter": "f",
                    "level": logging.INFO,
                    "filename": log_location + app_vars.log_info,
                },
                "docker": {
                    "class": "logging.StreamHandler",
                    "formatter": "f",
                    "level": logging.INFO,
                    "stream": "ext://sys.stdout",
                },
            },
            root={
                "handlers": ["docker", "file"],  # 'console', 'file'
                "level": logging.INFO,
                "disable_existing_loggers": False,
            },
        )
    elif env in ("-p", "--prod", "-prod"):
        # Set logging to INFO. Send to docker STDOUT
        logging_config = dict(
            version=1,
            formatters={
                "f": {"format": "%(asctime)s - %(levelname)s - %(message)s"}
            },
            handlers={
                "docker": {
                    "class": "logging.StreamHandler",
                    "formatter": "f",
                    "level": logging.INFO,
                    "stream": "ext://sys.stdout",
                }
            },
            root={
                "handlers": ["docker"],  # 'console', 'file'
                "level": logging.INFO,
                "disable_existing_loggers": False,
            },
        )

    return logging_config


def set_env_vars(env: str) -> dict:
    """Sets certain variables based on the flag passed in at the command line.
    Defaults to the development / debug environment variables if not specified

    Args:
        env (str): The environment variable to set

    Raises:
        TypeError: The environment variable must be a str

    Returns:
        dict: All the environment variables as a config.
    """
    if not isinstance(env, str):
        msg = str("Env should be a string, not {}.").format(env)
        raise TypeError(msg)

    # global workspace_id
    # global index_sheet
    # global minutes
    # global env_msg
    # global push_tickets_sheet
    secrets = load_secrets()

    # Set secrets based on flag passed in from command line
    if env in test_env_flags:
        token = secrets["dev_bearer_token"]
        env_msg = f"Environment flag set to '{env}'. Using dev_bearer_token"
    elif env in prod_env_flags or env is None:
        token = secrets["bearer_token"]
        env_msg = f"Environment flag set to '{env}'. Using bearer_token"
    else:
        # flag = env
        token = secrets["dev_bearer_token"]
        env = "--dev"
        env_msg = f"Environment flag '{env} 'is invalid, defaulting to --dev"
    env_dict = {"env": env, "env_msg": env_msg, "token": token}
    return env_dict


def init(args: list) -> dict:
    """Initializes the app and creates global environment variables to use
       elsewhere in the app based on the flag passed in on the command line.

    Args:
        args (list): List of args passed by sys.args[1:]

    Returns:
        dict: The total configuration dict with all global variables
    """
    start = time.time()
    global config
    global env
    global logging_config
    global scheduler
    global logger

    # Default to Dev if no flag passed on init
    try:
        env = args[0]
    except IndexError:
        env = "--dev"
    config = set_env_vars(env)

    # Get the logging config and try to create a new file for logs if the
    # config requires it.
    logging_config = set_logging_config(env)
    try:
        os.mkdir(log_location)
        f = open(log_location + app_vars.log_info, "w")
        f.close
        dictConfig(logging_config)
    except FileExistsError:
        dictConfig(logging_config)

    logger = logging.getLogger(__name__)

    # Set parameters for the task scheduler
    executors = {
        "default": ThreadPoolExecutor(20),
        "processpool": ProcessPoolExecutor(2),
    }
    job_defaults = {
        "coalesce": True,
        "max_instances": 5,
        "misfire_grace_time": None,
    }
    scheduler = BlockingScheduler(
        executors=executors, job_defaults=job_defaults
    )

    config["scheduler"] = scheduler
    config["logging"] = logging_config

    # Load secrets.json and extract relevant secrets
    secrets = load_secrets()
    config["bearer_token"] = secrets["bearer_token"]

    end = time.time()
    elapsed = end - start
    elapsed = helper.truncate(elapsed, 2)
    logging.debug("[Initialization] took {} seconds".format(elapsed))

    return config
