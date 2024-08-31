#!/usr/bin/python
import os
import time  # Import time module

from influx_client import InfluxClient
from jenkins_client import JenkinsClient
from jenkins_collector import collector


def load_environment_variables():
    """
    Load environment variables from the Docker environment.
    """
    required_env_vars = [
        "JENKINS_URL",
        "JENKINS_USER",
        "JENKINS_PASSWORD",
        "INFLUX_TOKEN",
        "INFLUX_DB",
        "INFLUX_ORG",
        "BUCKET_NAME",
    ]
    env_vars = {}
    missing_vars = []

    for var in required_env_vars:
        value = os.getenv(var)
        if value:
            env_vars[var] = value
        else:
            missing_vars.append(var)

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    return env_vars


def main():
    # Start the timer
    start_time = time.time()

    # Load environment variables
    env_vars = load_environment_variables()

    # Create Jenkins and InfluxDB clients
    jenkins_client = JenkinsClient(
        env_vars["JENKINS_URL"], env_vars["JENKINS_USER"], env_vars["JENKINS_PASSWORD"]
    )
    influx_client = InfluxClient(
        env_vars["INFLUX_DB"],
        env_vars["INFLUX_TOKEN"],
        env_vars["INFLUX_ORG"],
        env_vars["BUCKET_NAME"],
    )

    # Run the collector
    collector(jenkins_client, influx_client)

    # Calculate and print total execution time
    end_time = time.time()
    total_time = end_time - start_time
    print(f"Total time: {total_time:.2f} seconds")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred while running the Jenkins Collector: {str(e)}")
