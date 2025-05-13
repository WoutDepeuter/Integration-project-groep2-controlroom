import time

import pika
import logging
from datetime import datetime, timedelta, UTC

import xmltodict

from elastic import get_last_heartbeats
from env import RABBITMQ_EXCHANGE, RABBITMQ_ROUTING_KEY, RABBITMQ_CHANNEL, ADMIN_EMAILS

previous_down_services = {}

def send_alert(connection: pika.BlockingConnection, down_services: dict[str, datetime]):
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

    try:
        # TODO: Is it fine to open a new channel for this? Should I pass through the channel object instead?
        channel = connection.channel()
        channel.basic_publish(
            exchange=RABBITMQ_EXCHANGE,
            routing_key=RABBITMQ_ROUTING_KEY,
            body=xml_str,
        )
    except Exception:
        logging.exception("Failed to mail, how to monitor this???????", exc_info=True)

def heartbeat_loop(connection: pika.BlockingConnection):
    logging.debug("Heartbeat monitor checking apps")
    heartbeats = get_last_heartbeats()
    logging.debug(f"Received heartbeats from {list(heartbeats.keys())}")
    now = datetime.now(UTC)

    down_services: dict[str, datetime] = {}
    for sender, last_seen in heartbeats.items():
        if now - last_seen > timedelta(seconds=10):
            logging.debug(f"Missing heartbeat from: {sender}")
            down_services[sender] = last_seen
        else:
            logging.debug(f"Received heartbeat in time: {sender}")

    if len(down_services) > 0:
        send_alert(connection, down_services)
        pass

    time.sleep(10)


