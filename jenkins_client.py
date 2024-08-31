import logging
from jenkins import Jenkins, JenkinsException, NotFoundException
from utils import get_json
import os  # For environment variable handling
from datetime import datetime  # Import datetime for caching

# Configure log level from environment variable or default to INFO
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

# If debug mode, log to a separate file
if log_level == 'DEBUG':
    debug_handler = logging.FileHandler('jenkins_client_debug.log')
    debug_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    debug_handler.setFormatter(formatter)
    logger.addHandler(debug_handler)

# Default console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(log_level)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class JenkinsClient:
    """Class for interacting with a Jenkins server."""

    def __init__(self, jenkins_base_url, username=None, password=None, token=None, insecure=False):
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
        self._cache_ttl = int(os.getenv('CACHE_TTL', 3600))  # Cache time-to-live in seconds
        self._job_cache = {}  # Initialize job cache

    def get_server_instance(self):
        """
        Get the Jenkins server instance.

        Returns:
            Jenkins: A Jenkins server instance.
        """
        try:
            if self._username and self._password:
                return Jenkins(self._jenkins_base_url, self._username, self._password, timeout=30)
            elif self._username and self._token:
                return Jenkins(self._jenkins_base_url, self._username, self._token, timeout=30)
            elif self._username and not (self._password or self._token):
                return Jenkins(self._jenkins_base_url, self._username, timeout=30)
            else:
                return Jenkins(self._jenkins_base_url, timeout=30)
        except Exception as e:
            logger.error('Unable to connect to Jenkins server', exc_info=True)
            raise e

    def _is_job_relevant(self, job_name):
        """
        Determine if a job is relevant based on name pattern and job type.

        Args:
            job_name (str): The name of the job.

        Returns:
            bool: True if relevant, False otherwise.
        """
        if '/' in job_name:
            last_segment = job_name.split('/')[-1]
            try:
                job_info = self._server_instance.get_job_info(job_name)  # Get job info to check its type
                job_type = job_info['_class'].lower()  # Class type can provide a clue about job type (freestyle, pipeline, etc.)

                # Check if job type is freestyle or pipeline and if the naming pattern matches
                return (job_type in ['hudson.model.freestyleproject', 'org.jenkinsci.plugins.workflow.job.workflowjob']) and \
                       (last_segment in ["master", "develop"] or last_segment.startswith("release"))
            except NotFoundException:
                logger.warning(f"Job '{job_name}' not found, skipping.")
                return False  # Skip jobs that are not found
            except JenkinsException as e:
                logger.error(f"Error fetching job info for '{job_name}': {e}")
                return False  # Skip jobs with errors
        return True  # Return True for jobs without slashes

    def get_filtered_jobs(self):
        """
        Get a list of all relevant jobs on the Jenkins server based on naming patterns.

        Returns:
            list: A list of job names.
        """
        all_jobs = self._server_instance.get_all_jobs()
        valid_jobs = [get_json('fullname', job) for job in all_jobs if self._is_job_relevant(get_json('fullname', job))]
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
        if jobname in self._job_cache and (datetime.now() - self._job_cache[jobname]['timestamp']).total_seconds() < self._cache_ttl:
            return self._job_cache[jobname]['builds']

        try:
            if self.is_folder(jobname):
                logger.info(f"{jobname} is a folder, has no build data")
                self._job_cache[jobname] = {'builds': [], 'timestamp': datetime.now()}
                return []
            else:
                job_info = self._server_instance.get_job_info(jobname)
                builds = get_json('builds', job_info)
                if not builds:
                    logger.debug(f"Job {jobname} has no build data.")
                    self._job_cache[jobname] = {'builds': [], 'timestamp': datetime.now()}
                    return []
                build_numbers = [get_json('number', build) for build in builds]
                self._job_cache[jobname] = {'builds': build_numbers, 'timestamp': datetime.now()}
                return build_numbers
        except JenkinsException as e:
            logger.error(f"Job {jobname} does not exist: {str(e)}")
            return []
        except TypeError as e:
            logger.error(f"Error fetching builds for job {jobname}: {str(e)}")
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
