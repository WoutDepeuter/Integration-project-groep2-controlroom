import time

import pika
import logging
from datetime import datetime, timedelta, UTC

import xmltodict

from elastic import get_last_heartbeats
from env import ADMIN_EMAILS, RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASS, RABBITMQ_VHOST, RABBITMQ_PORT, RABBITMQ_EXCHANGE, RABBITMQ_ROUTING_KEY, RABBITMQ_CHANNEL

_connection = None

def get_connection():
    global _connection
    try:
        if _connection is None or _connection.is_closed:
            logging.info("Connecting to RabbitMQ...")
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                virtual_host=RABBITMQ_VHOST,
                credentials=credentials,
                heartbeat=60
            )
            _connection = pika.BlockingConnection(parameters)
        return _connection
    except Exception as e:
        logging.error(f"Could not connect to RabbitMQ: {e}")
        _connection = None
        return None

previous_down_services = {}

def send_alert(down_services: dict[str, datetime]):

    global previous_down_services

    added = {}
    removed = []

    for service, last_seen in down_services.items():
        if service not in previous_down_services:
            added[service] = last_seen

    for service in previous_down_services:
        if service not in down_services:
            removed.append(service)


    if not added and not removed:
        logging.debug("No changes in down services. Skipping alert.")
        return
    
    if added:
        logging.info(f"New down services: {list(added.keys())}")
    if removed:
        logging.info(f"Recovered services: {removed}")

    previous_down_services = down_services.copy()

    if added == {}:
        logging.debug("No new services down, skipping alert")
        return

    if len(ADMIN_EMAILS) == 0:
        logging.warning("ADMIN_EMAILS is empty, cannot send emails")
        return

    # See template.dto.template for how I choose these values
    data = {
        'dto': {
            'admins': ADMIN_EMAILS,
            'services': [
                {
                    'sender': k,
                    'last_seen': v
                } for k, v in down_services.items()
            ]
        }
    }

    xml_str = xmltodict.unparse(data, pretty=True)
    logging.debug("Heartbeat mail dto \n%s", xml_str)

    connection = get_connection()
    if connection is None:
        logging.error("No connection with RabbitMQ, It skips sending the alert")
        return

    try:
        channel = connection.channel()
        channel.basic_publish(
            exchange=RABBITMQ_EXCHANGE,
            routing_key=RABBITMQ_ROUTING_KEY,
            body=xml_str,
        )
    except pika.exceptions.StreamLostError:
        logging.warning("Connection lost during the sending, trying again...")
        connection.close()
        connection = get_connection()
        if connection:
            channel = connection.channel()
            channel.basic_publish(
                exchange=RABBITMQ_EXCHANGE,
                routing_key=RABBITMQ_ROUTING_KEY,
                body=xml_str,
            )
        else:
            logging.error("Could not reconnect to send the message")
    except Exception:
        logging.exception("Error sending alert")

def heartbeat_loop():
    logging.debug("Heartbeat monitor checking apps")

    try:
        heartbeats = get_last_heartbeats()
    except Exception as e:
        logging.error(f"Failed to fetch heartbeats from Elasticsearch: {e}")
        return

    if not heartbeats:
        logging.warning("No heartbeats received — skipping alert to avoid false positives.")
        return
    
    logging.debug(f"Received heartbeats from {list(heartbeats.keys())}")
    now = datetime.now(UTC)

    down_services: dict[str, datetime] = {}
    for sender, last_seen in heartbeats.items():
        if now - last_seen > timedelta(seconds=10):
            logging.debug(f"Missing heartbeat from: {sender}")
            down_services[sender] = last_seen
        else:
            logging.debug(f"Received heartbeat in time: {sender}")

    if down_services:
        send_alert(down_services)

#    time.sleep(10) # I will put it on the main.py, I think it is better.


