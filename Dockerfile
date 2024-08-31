FROM python:3.8-slim

# Install cron and vim
RUN apt-get update && apt-get -y install cron vim

# Set the working directory
WORKDIR /jenkins_collector/

# Copy all files to the container
COPY . .

# Install Python dependencies
RUN /usr/local/bin/python3 -m pip install --upgrade pip
RUN pip3 install -r requirements.txt

# Create the logs directory
RUN mkdir -p /root/logs

# Copy the entrypoint script and make it executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run the entrypoint script
CMD ["/entrypoint.sh"]

