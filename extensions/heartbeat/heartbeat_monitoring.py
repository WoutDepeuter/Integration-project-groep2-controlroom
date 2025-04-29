import time
import requests
import pika
from datetime import datetime, timedelta

ELASTIC_URL = 'http://localhost:9200'
INDEX_NAME = 'logs-*'
APPS = ['controlroom', 'facturatie', 'CRM', 'frontend', 'planning', 'kassa', 'mailing']
RABBITMQ_HOST = 'localhost'
RABBITMQ_QUEUE = 'heartbeat.alerts'

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
        res = requests.post(
            f"{ELASTIC_URL}/{INDEX_NAME}/_search",
            json=query,
            timeout=10
        )
        res.raise_for_status()
        data = res.json()
        return data['hits']['total']['value'] > 0
    except Exception:
        return True

def send_alert(sender):
    message = {
        "timestamp": datetime.utcnow().isoformat(),
        "sender": sender,
        "status": "missing_heartbeat",
        "message": f"No heartbeat in the last minute from {sender}"
    }

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

while True:
    for sender in APPS:
        if not check_heartbeat(sender):
            send_alert(sender)
    time.sleep(60)
