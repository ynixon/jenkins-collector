#!/usr/bin/python
import os

from dotenv import load_dotenv
from influx_client import InfluxClient
from jenkins_client import JenkinsClient
from jenkins_collector import collector

'''
    Load env
'''
load_dotenv()
jenkins_url = os.getenv('JENKINS_URL')
jenkins_user = os.getenv('JENKINS_USER')
jenkins_password = os.getenv('JENKINS_PASSWORD')
jenkins_insecure = os.getenv('JENKINS_INSECURE')

influx_token = os.getenv('INFLUX_TOKEN')
influx_server = os.getenv('INFLUX_DB')
org_name = os.getenv('INFLUX_ORG')
bucket_name = os.getenv('BUCKET_NAME')
logPath = os.getenv('COLLECTOR_LOG_PATH')

def main():
    jenkins_client = JenkinsClient(
        jenkins_url, jenkins_user, jenkins_password, jenkins_insecure
    )
    influx_client = InfluxClient(
        influx_server, influx_token, org_name, bucket_name
    )
    collector(jenkins_client, influx_client)

if __name__ == "__main__":
    main()
