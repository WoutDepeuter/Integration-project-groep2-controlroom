import time
import requests
import pika

from datetime import datetime, timedelta

ELASTIC_URL = 'http://elasticsearch:9200'
INDEX_NAME = 'logs-*'
RABBITMQ_HOST = 'rabbitmq'
RABBITMQ_USER = 'attendify'
RABBITMQ_PASS = 'uXe5u1oWkh32JyLA'
RABBITMQ_QUEUE = 'heartbeat.failure'

def get_active_apps():
    query = {
        "size": 0,
        "aggs": {
            "apps": {
                "terms": {
                    "field": "sender.keyword", 
                    "size": 1000
                }
            }
        },
        "query": {
            "range": {
                "@timestamp": {
                    "gte": "now-1h"
                }
            }
        }
    }

    try:
        res = requests.post(f"{ELASTIC_URL}/{INDEX_NAME}/_search", json=query)
        res.raise_for_status()
        data = res.json()
        return [bucket['key'] for bucket in data['aggregations']['apps']['buckets']]
    except Exception as e:
        print(f"Error fetching active apps: {e}")
        return []

def check_heartbeat(sender):
    now = datetime.utcnow()
    one_minute_ago = now - timedelta(minutes=1)
    query = {
        "query": {
            "bool": {
                "filter": [
                    {"term": {"sender": sender}},
                    {
                        "range": {
                            "@timestamp": {
                                "gte": one_minute_ago.isoformat(),
                                "lte": now.isoformat()
                            }
                        }
                    }
                ]
            }
        },
        "size": 1,
        "_source": ["@timestamp"]
    }
    try:
        res = requests.post(f"{ELASTIC_URL}/{INDEX_NAME}/_search", json=query, timeout=10)
        res.raise_for_status()
        data = res.json()
        heartbeat_found = data['hits']['total']['value'] > 0
        logging.info(f"Heartbeat for {sender}: {'OK' if heartbeat_found else 'Missing'}")  
        return heartbeat_found
    except Exception:
        logging.error(f"Error checking heartbeat for {sender}")
        return True

def send_alert(sender):
    message = {
        "timestamp": datetime.utcnow().isoformat(),
        "sender": sender,
        "status": "missing_heartbeat",
        "message": f"No heartbeat in the last minute from {sender}"
    }

    print(f"ALERT SENT: {message}")

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
    except Exception:
        pass


#    logging.basicConfig(level=logging.INFO)
    

while True:
    import logging

    logging.basicConfig(level=logging.INFO, filename='heartbeat_monitor.log', filemode='a', format='%(asctime)s - %(message)s')

    logger = logging.getLogger(__name__)
    logging.info("Heartbeat monitor checking apps")
    apps = get_active_apps()
    print(f"Active apps: {apps}")
    for sender in apps:
        if not check_heartbeat(sender):
            print(f"Missing heartbeat from: {sender}")
            send_alert(sender)
        else:
            print(f"[{datetime()}] OK: {sender}")    
    time.sleep(10)
#    time.sleep(60)
