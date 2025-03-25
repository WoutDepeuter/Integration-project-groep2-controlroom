# Welcome to Heartbeat 8.7.1

Ping remote services for availability and log results to Elasticsearch or send to Logstash.

## Getting Started

To get started with Heartbeat, you need to set up Elasticsearch on
your localhost first. After that, start Heartbeat with:

     ./heartbeat -c heartbeat.yml -e

This will start Heartbeat and send the data to your Elasticsearch
instance. To load the dashboards for Heartbeat into Kibana, run:

    ./heartbeat setup -e

For further steps visit the
[Quick start](https://www.elastic.co/guide/en/beats/heartbeat/master/heartbeat-installation-configuration.html) guide.

## Documentation

Visit [Elastic.co Docs](https://www.elastic.co/guide/en/beats/heartbeat/master/index.html)
for the full Heartbeat documentation.

## Release notes

https://www.elastic.co/guide/en/beats/libbeat/master/release-notes-8.7.1.html
