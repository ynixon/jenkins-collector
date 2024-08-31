#!/bin/bash

# Run indefinitely
while true; do
  echo "Running Jenkins Collector script..."
  /usr/local/bin/python3 /jenkins_collector/main.py

  # Sleep for 5 minutes (300 seconds)
  sleep 300
done

