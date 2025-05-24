import time

import pika
import logging
from datetime import datetime, timedelta, UTC

import xmltodict

from elastic import get_last_heartbeats
from env import ADMIN_EMAILS, RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASS, RABBITMQ_VHOST, RABBITMQ_PORT, RABBITMQ_EXCHANGE, RABBITMQ_ROUTING_KEY, RABBITMQ_CHANNEL

_connection = None
previous_down_services = {}

MAX_RETRIES = 3
RETRY_DELAY = 5  # 5 seconds to try again
MAX_MESSAGE_SIZE = 128 * 1024


def get_connection():
    global _connection
    if _connection is not None:
        if _connection.is_open:
            return _connection
        else:
            try:
                _connection.close()
            except Exception:
                pass
            _connection = None

    try:    
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

def send_alert(down_services: dict[str, datetime]):

    global previous_down_services

    added = {s: t for s, t in down_services.items() if s not in previous_down_services}
    removed = [s for s in previous_down_services if s not in down_services]

    if not added and not removed:
        logging.debug("No changes in down services. Skipping alert.")
        return
    
    if added:
        logging.info(f"New down services: {list(added.keys())}")
    if removed:
        logging.info(f"Recovered services: {removed}")

    previous_down_services = down_services.copy()

    if not added:
        logging.debug("No new services down, skipping alert")
        return

    if not ADMIN_EMAILS:
        logging.warning("ADMIN_EMAILS is empty, cannot send emails")
        return

    # See template.dto.template for how I choose these values
    try:
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
    except Exception as e:
        logging.error(f"Failed to generate XML alert: {e}")
        return   
    if len(xml_str.encode('utf-8')) > MAX_MESSAGE_SIZE:
        logging.error("Generated alert exceeds max size for RabbitMQ, skipping send.")
        return

    _publish_with_retry(xml_str)

def _publish_with_retry(xml_str):
    global _connection

    for attempt in range(1, MAX_RETRIES + 1):
        connection = get_connection()
        if not connection:
            logging.warning(f"Retry {attempt}/{MAX_RETRIES}: Failed to connect to RabbitMQ.")
            time.sleep(RETRY_DELAY * attempt)
            continue

        channel = None
        try:
            channel = connection.channel()
            channel.basic_publish(
                exchange=RABBITMQ_EXCHANGE,
                routing_key=RABBITMQ_ROUTING_KEY,
                body=xml_str,
            )
            logging.info("Alert sent successfully")
            return
        except pika.exceptions.AMQPError as e:
            logging.warning(f"Retry {attempt}/{MAX_RETRIES}: Failed to publish alert: {e}")

            try:
                if connection.is_open:
                    connection.close()
            except Exception:
                pass
            _connection = None

        except Exception as e:
            logging.exception(f"Unexpected error during alert publish: {e}")

            try:
                if connection.is_open:
                    connection.close()
            except Exception:
                pass
            _connection = None
            
        finally:
            if channel:
                try:
                    channel.close()
                except Exception:
                    pass

        time.sleep(RETRY_DELAY * attempt)

    logging.error("Failed to send alert after multiple retries.")

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

    down_services = {
        sender: last_seen
        for sender, last_seen in heartbeats.items()
        if now - last_seen > timedelta(seconds=10)
    }

    for sender in heartbeats:
        if sender in down_services:
            logging.debug(f"Missing heartbeat from: {sender}")
        else:
            logging.debug(f"Received heartbeat in time: {sender}")

    if down_services:
        send_alert(down_services)

#    time.sleep(10) # I will put it on the main.py, I think it is better.
