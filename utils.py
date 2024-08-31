import logging
import sys
from datetime import datetime
import rfc3339
import os  # Import os to manage directories

'''
Configure logging handler
'''
def get_date_string(date_object):
    """
    Convert datetime object to RFC3339 formatted string.

    Args:
        date_object (datetime): The datetime object.

    Returns:
        str: RFC3339 formatted date string.
    """
    return rfc3339.rfc3339(date_object)

logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()
fileName = get_date_string(datetime.now()) + '_jenkins_collector'
logPath = '/jenkins_collector/logs'  # Corrected path to logs directory

# Ensure the logs directory exists
if not os.path.exists(logPath):
    os.makedirs(logPath)

fileHandler = logging.FileHandler("{0}/{1}.log".format(logPath, fileName))
fileHandler.setFormatter(logFormatter)

'''
Avoid duplicated logs
'''
if rootLogger.hasHandlers():
    rootLogger.handlers.clear()
rootLogger.addHandler(fileHandler)
consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)
logging.getLogger().setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def get_json(element, json_data):
    """
    Safely get an element from JSON data.

    Args:
        element (str): The key to retrieve.
        json_data (dict): The JSON data.

    Returns:
        any: The value associated with the key, or None if not found.
    """
    try:
        if element in json_data:
            return json_data[element]
    except Exception as e:
        logging.info(f"Error accessing JSON element '{element}': {str(e)}")
        raise e
