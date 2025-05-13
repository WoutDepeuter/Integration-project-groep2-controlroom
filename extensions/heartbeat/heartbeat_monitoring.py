import time

import pika
import logging
from datetime import datetime, timedelta, UTC

import xmltodict

from elastic import get_last_heartbeats
from env import RABBITMQ_EXCHANGE, RABBITMQ_ROUTING_KEY, RABBITMQ_CHANNEL


def send_alert(connection: pika.BlockingConnection, down_services: dict[str, datetime]):

    # TODO: Save current down services, and take diff (don't need to send an email every 10s if the same stuff stays down
    new_down = down_services

    # See template.dto.template for how I choose these values
    data = {
        'dto': {
            'admins': [], # TODO: Get a list of all admin Ids OR emails!
            'services': [
                {
                    'sender': k,
                    'last_seen': v
                } for k, v in new_down.items()
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
        if now - last_seen > timedelta(minutes=1):
            logging.warning(f"Missing heartbeat from: {sender}")
            down_services[sender] = last_seen
        else:
            logging.debug(f"Received heartbeat in time: {sender}")

    if len(down_services) > 0:
        send_alert(connection, down_services)
        pass

    time.sleep(10)


