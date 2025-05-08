import os

ELASTIC_URL = os.environ.get('ELASTIC_URL')
INDEX_NAME = os.environ.get('INDEX_NAME')
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST')
RABBITMQ_VHOST = os.environ.get('RABBITMQ_VHOST')
RABBITMQ_USER = os.environ.get('RABBITMQ_USER')
RABBITMQ_PASS = os.environ.get('RABBITMQ_PASS')
RABBITMQ_CHANNEL = os.environ.get('RABBITMQ_CHANNEL') or "mailing.mail"
RABBITMQ_EXCHANGE = os.environ.get('RABBITMQ_EXCHANGE') or "monitoring"
RABBITMQ_ROUTING_KEY = os.environ.get('RABBITMQ_ROUTING_KEY') or "heartbeat_alart"