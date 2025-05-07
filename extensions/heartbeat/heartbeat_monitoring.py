import time
import requests
import pika
import logging
import os
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO, 
    filename='heartbeat_monitor.log', 
    filemode='a', 
    format='%(asctime)s - %(message)s'
)


ELASTIC_URL = os.environ.get('ELASTIC_URL')
INDEX_NAME = os.environ.get('INDEX_NAME')
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST')
RABBITMQ_USER = os.environ.get('RABBITMQ_USER')
RABBITMQ_PASS = os.environ.get('RABBITMQ_PASS')
RABBITMQ_QUEUE = os.environ.get('RABBITMQ_QUEUE')


def get_last_heartbeats():
    query = {
        "size": 0,
        "aggs": {
            "apps": {
                "terms": {
                    "field": "xml_data.sender.keyword", 
                    "size": 1000
                },
                "aggs": {
                    "last_seen": {
                        "max": {
                            "field": "@timestamp"
                        }
                    }
                }
            }
        },
        "query": {
            "range": {
                "@timestamp": {
                    "gte": "now-2m"
                }
            }
        }
    }

    try:
        res = requests.post(f"{ELASTIC_URL}/{INDEX_NAME}/_search", json=query, timeout=10)
        res.raise_for_status()
        data = res.json()
        heartbeats = {}

        for bucket in data["aggregations"]["apps"]["buckets"]:
            timestamp = bucket["last_seen"].get("value_as_string")
            if timestamp:
                heartbeats[bucket["key"]] = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        return heartbeats
    except Exception as e:
        logging.error(f"Error fetching heartbeats: {e}")
        return {}

def send_alert(sender):
    message = {
        "timestamp": datetime.utcnow().isoformat(),
        "sender": sender,
        "message": f"No heartbeat in the last minute from {sender}"
    }

    logging.warning(f"ALERT SENT: {message}")

    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        channel.basic_publish(
            exchange='',
            routing_key=RABBITMQ_QUEUE,
            body=str(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
    except Exception as e:
        logging.error(f"Error sending alert for {sender}: {e}")


while True:
    logging.info("Heartbeat monitor checking apps")
    heartbeats = get_last_heartbeats()
    now = datetime.utcnow()

    for sender, last_seen in heartbeats.items():
        if now - last_seen > timedelta(minutes=1):
            logging.warning(f"Missing heartbeat from: {sender}")
            send_alert(sender)
        else:
            logging.info(f"OK: {sender}")
            
    time.sleep(10)
#    time.sleep(60)
