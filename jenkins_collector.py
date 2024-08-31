import os
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# Configure log level from environment variable or default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Set up the root logger
root_logger = logging.getLogger()
root_logger.setLevel(log_level)

# Clear any existing handlers to avoid duplicated logs
if root_logger.hasHandlers():
    root_logger.handlers.clear()

# Default console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(log_level)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

# If debug mode, log to a separate file
if log_level == "DEBUG":
    debug_handler = logging.FileHandler("jenkins_collector_debug.log")
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)
    root_logger.addHandler(debug_handler)

logger = root_logger


class BuildInfo:
    """Class representing build information."""

    def __init__(
        self,
        jobname,
        build_id,
        url,
        timestamp,
        duration,
        estimatedDuration,
        queueId,
        result,
        displayName,
    ):
        """
        Initialize the BuildInfo with build details.

        Args:
            jobname (str): The name of the Jenkins job.
            build_id (int): The build ID.
            url (str): The URL to the build.
            timestamp (int): The timestamp of the build.
            duration (int): The duration of the build.
            estimatedDuration (int): The estimated duration of the build.
            queueId (int): The queue ID of the build.
            result (str): The result of the build.
            displayName (str): The display name of the build.
        """
        self.jobname = jobname
        self.build_id = build_id
        self.url = url
        self.timestamp = timestamp
        self.duration = duration
        self.estimatedDuration = estimatedDuration
        self.queueId = queueId
        self.result = result
        self.displayName = displayName


def is_recent_build(build_info, days=7):
    """
    Check if a build is recent within the specified number of days.

    Args:
        build_info (dict): The build information.
        days (int): The number of days to check against.

    Returns:
        bool: True if the build is recent, False otherwise.
    """
    build_timestamp = datetime.fromtimestamp(build_info["timestamp"] / 1000)
    return build_timestamp >= datetime.now() - timedelta(days=days)


def gen_build_data(build_info, job, build_id):
    """
    Generate build data for InfluxDB.

    Args:
        build_info (dict): The build information.
        job (str): The job name.
        build_id (int): The build ID.

    Returns:
        dict: A dictionary containing the data to write to InfluxDB.
    """
    return {
        "measurement": "jenkins",
        "tags": {"jobname": job, "build_id": build_id, "url": build_info["url"]},
        "time": round(build_info["timestamp"] / 1000),
        "fields": {
            "duration": build_info["duration"],
            "estimatedDuration": build_info["estimatedDuration"],
            "result": build_info["result"],
        },
    }


def process_build(jenkins_client, influx_client, job, build):
    """
    Process a single build: fetch information, generate data, and write to InfluxDB.

    Args:
        jenkins_client (JenkinsClient): The Jenkins client.
        influx_client (InfluxClient): The InfluxDB client.
        job (str): The job name.
        build (int): The build number.
    """
    try:
        build_info = jenkins_client.build_info(job, build)
        if is_recent_build(build_info):
            data = gen_build_data(build_info, job, build)
            influx_client.write_data_batch([data])
    except Exception as e:
        logger.warning("Error processing build %s for job %s: %s", build, job, str(e))


def collector(jenkins_client, influx_client):
    """
    Collect data from Jenkins jobs and write it to InfluxDB.

    Args:
        jenkins_client (JenkinsClient): The Jenkins client.
        influx_client (InfluxClient): The InfluxDB client.
    """
    # Corrected method name
    list_job = jenkins_client.get_filtered_jobs()

    with ThreadPoolExecutor(max_workers=5) as executor:
        for job in list_job:
            list_build = jenkins_client.get_list_build(job)
            if not list_build:
                logger.info("No builds found for job: %s", job)
                continue
            for build in list_build:
                executor.submit(
                    process_build, jenkins_client, influx_client, job, build
                )
