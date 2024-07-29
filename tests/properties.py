import os
from configparser import ConfigParser


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ini_path = ROOT_DIR + "/test_data.ini"

config = ConfigParser()
config.read(ini_path)

INVALID_CRED_MESSAGE = config.get("messages", "invalid_cred")
EMPTY_CRED_MESSAGE = config.get("messages", "empty_username")
VALID_USER = config.get("credentials", "valid_user")
VALID_PASS = config.get("credentials", "valid_pass")
