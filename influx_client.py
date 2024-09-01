import os
import logging
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import ASYNCHRONOUS, SYNCHRONOUS
from influxdb_client.rest import ApiException

# Configure log level from environment variable or default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

# If debug mode, log to a separate file
if log_level == "DEBUG":
    debug_handler = logging.FileHandler("influx_debug.log")
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


class InfluxPoint:
    """Class representing a single InfluxDB data point."""

    def __init__(self, measurement, tags, fields, timestamp=None):
        self.measurement = measurement
        self.tags = tags
        self.fields = fields
        self.timestamp = timestamp
        self._point = [
            {
                "measurement": measurement,
                "tags": tags,
                "time": timestamp,
                "fields": fields,
            }
        ]


class InfluxClient:
    """Class for interacting with InfluxDB."""

    def __init__(self, url, token, org, bucket):
        self._org = org
        self._bucket = bucket
        self._client = InfluxDBClient(url=url, token=token, org=org)

    def check_connection(self):
        """Check that the InfluxDB is running."""
        logger.info("> Checking connection ...")
        self._client.api_client.call_api("/ping", "GET")
        logger.info("Connection is OK.")

    def write_data_batch(self, data_batch, write_option=SYNCHRONOUS):
        """
        Write a batch of data points to InfluxDB.

        Args:
            data_batch (list): A list of data points to write.
            write_option: The write option for InfluxDB (default: SYNCHRONOUS).
        """
        try:
            write_api = self._client.write_api(write_option)
            logger.debug("Writing data to InfluxDB: %s", data_batch)  # Add this line
            write_api.write(self._bucket, self._org, data_batch, write_precision="s")

            # Log job name and status for each point in the batch
            for point in data_batch:
                job_name = point["tags"].get("jobname", "Unknown Job")
                job_status = point["fields"].get("result", "Unknown Status")
                logger.info(
                    "Job '%s' written to bucket '%s' with status: %s.",
                    job_name,
                    self._bucket,
                    job_status,
                )

        except ApiException as e:
            logger.error("Error writing data to InfluxDB: %s", str(e))

    def check_query(self, query):
        """Check that the credentials have permission to query from the bucket."""
        logger.info("> Checking credentials for query ...")
        query_api = self._client.query_api()
        try:
            result = query_api.query(org=self._org, query=query)
            logger.debug("Query result: %s", result)
        except ApiException as e:
            if e.status == 404:
                raise Exception(
                    f"The specified token doesn't have sufficient credentials to read from '{self._bucket}' "
                    f"or specified bucket doesn't exist."
                ) from e
            raise
        logger.info("Query credentials are valid.")

    def close_process(self):
        """Close the InfluxDB client connection."""
        self._client.close()
        logger.info("Closed InfluxDB client connection.")
