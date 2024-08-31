FROM python:3.8-slim

RUN apt-get update && apt-get -y install cron vim
WORKDIR /jenkins_collector/
COPY . .
COPY crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/local/bin/python3 -m pip install --upgrade pip
RUN pip3 install -r requirements.txt

# Create the logs directory
RUN mkdir -p /root/logs

# ENTRYPOINT [ "/bin/sh",  "entrypoint.sh" ]

RUN /usr/bin/crontab /etc/cron.d/crontab
# run crond as main process of container
CMD ["cron", "-f"]

