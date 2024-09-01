import logging
import os  # For environment variable handling
from datetime import datetime  # Import datetime for caching
from jenkins import Jenkins, JenkinsException, NotFoundException
from utils import get_json


# Configure log level from environment variable or default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

# If debug mode, log to a separate file
if log_level == "DEBUG":
    debug_handler = logging.FileHandler("jenkins_client_debug.log")
    debug_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    debug_handler.setFormatter(formatter)
    logger.addHandler(debug_handler)

# Default console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(log_level)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class JenkinsClient:
    """Class for interacting with a Jenkins server."""

    def __init__(
        self, jenkins_base_url, username=None, password=None, token=None, insecure=False
    ):
        """
        Initialize the JenkinsClient with connection details.

        Args:
            jenkins_base_url (str): The base URL of the Jenkins server.
            username (str, optional): The username for authentication.
            password (str, optional): The password for authentication.
            token (str, optional): The token for authentication.
            insecure (bool, optional): Whether to allow insecure connections.
        """
        self._insecure = insecure
        self._password = password
        self._token = token
        self._username = username
        self._jenkins_base_url = jenkins_base_url
        self._server_instance = self.get_server_instance()
        self._cache_ttl = int(os.getenv("CACHE_TTL", "3600"))  # Cache TTL

        self._job_cache = {}  # Initialize job cache

    def get_server_instance(self):
        """
        Get the Jenkins server instance.

        Returns:
            Jenkins: A Jenkins server instance.
        """
        try:
            if self._username and self._password:
                return Jenkins(
                    self._jenkins_base_url, self._username, self._password, timeout=30
                )
            elif self._username and self._token:
                return Jenkins(
                    self._jenkins_base_url, self._username, self._token, timeout=30
                )
            elif self._username and not (self._password or self._token):
                return Jenkins(self._jenkins_base_url, self._username, timeout=30)
            else:
                return Jenkins(self._jenkins_base_url, timeout=30)
        except Exception as e:
            logger.error("Unable to connect to Jenkins server", exc_info=True)
            raise e

    def _is_job_relevant(self, job_name, job_info):
        """
        Determine if a job is relevant based on its type and status.

        Args:
            job_name (str): The name of the job.
            job_info (dict): Information about the job, including '_class' and 'color'.

        Returns:
            bool: True if relevant, False otherwise.
        """
        # Check if job is disabled
        job_status = job_info.get("color", "").lower()
        if "disabled" in job_status:
            logger.debug(
                "Skipping disabled job: %s with status: %s", job_name, job_status
            )
            return False

        # Include all jobs, regardless of folders, except disabled ones
        logger.debug("Including job: %s with status: %s", job_name, job_status)
        return True

    def get_filtered_jobs(self):
        """
        Get a list of all relevant jobs on the Jenkins server based on naming patterns.

        Returns:
            list: A list of job names.
        """
        all_jobs = self._server_instance.get_all_jobs()
        valid_jobs = []

        for job in all_jobs:
            job_name = get_json("fullname", job)
            job_info = job  # Ensure job_info is extracted here
            if self._is_job_relevant(
                job_name, job_info
            ):  # Pass both job_name and job_info
                valid_jobs.append(job_name)
            else:
                logger.debug(
                    "Job '%s' is not relevant or is disabled, skipping.", job_name
                )

        return valid_jobs

    def get_list_build(self, jobname):
        """
        Get a list of recent builds for a job.

        Args:
            jobname (str): The name of the job.

        Returns:
            list: A list of build numbers.
        """
        # Check if cached
        if (
            jobname in self._job_cache
            and (datetime.now() - self._job_cache[jobname]["timestamp"]).total_seconds()
            < self._cache_ttl
        ):
            return self._job_cache[jobname]["builds"]

        try:
            if self.is_folder(jobname):
                logger.info("%s is a folder, has no build data", jobname)
                self._job_cache[jobname] = {"builds": [], "timestamp": datetime.now()}
                return []
            else:
                job_info = self._server_instance.get_job_info(jobname)
                builds = get_json("builds", job_info)
                logger.debug(
                    "Builds for job '%s': %s", jobname, builds
                )  # Add this line
                if not builds:
                    logger.debug("Job %s has no build data.", jobname)
                    self._job_cache[jobname] = {
                        "builds": [],
                        "timestamp": datetime.now(),
                    }
                    return []
                build_numbers = [get_json("number", build) for build in builds]
                self._job_cache[jobname] = {
                    "builds": build_numbers,
                    "timestamp": datetime.now(),
                }
                return build_numbers
        except JenkinsException as e:
            logger.error("Job %s does not exist: %s", jobname, str(e))
            return []
        except TypeError as e:
            logger.error("Error fetching builds for job %s: %s", jobname, str(e))
            return []

    def is_folder(self, job_name):
        """
        Check if a job is a folder.

        Args:
            job_name (str): The name of the job.

        Returns:
            bool: True if the job is a folder, False otherwise.
        """
        return self._server_instance.is_folder(job_name)

    def build_info(self, jobname, build_number):
        """
        Get information about a specific build of a job.

        Args:
            jobname (str): The name of the job.
            build_number (int): The build number.

        Returns:
            dict: A dictionary containing build information.
        """
        return self._server_instance.get_build_info(jobname, build_number)
