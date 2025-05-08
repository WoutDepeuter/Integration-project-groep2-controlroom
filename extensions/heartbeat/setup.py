import logging

import pika
import xmltodict

from env import RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASS, RABBITMQ_EXCHANGE, \
    RABBITMQ_ROUTING_KEY, RABBITMQ_VHOST, RABBITMQ_CHANNEL


def init_connection() -> pika.BlockingConnection:
    """
    Creates a new connection to RabbitMQ based on the env vars, throws if failed
    :return:
    """

    if RABBITMQ_HOST is None or RABBITMQ_HOST == "":
        raise AttributeError("The RABBITMQ_HOST environment variable has not been set")
    if RABBITMQ_USER is None or RABBITMQ_USER == "":
        raise AttributeError("The RABBITMQ_USER environment variable has not been set")
    if RABBITMQ_PASS is None or RABBITMQ_PASS == "":
        raise AttributeError("The RABBITMQ_PASS environment variable has not been set")
    if RABBITMQ_EXCHANGE is None or RABBITMQ_EXCHANGE == "":
        raise AttributeError("The RABBITMQ_EXCHANGE environment variable has not been set")
    if RABBITMQ_ROUTING_KEY is None or RABBITMQ_ROUTING_KEY == "":
        raise AttributeError("The RABBITMQ_ROUTING_KEY environment variable has not been set")


    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        virtual_host=RABBITMQ_VHOST,
        port=30001,
        credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    ))

    channel = connection.channel()
    channel.queue_bind(RABBITMQ_CHANNEL, RABBITMQ_EXCHANGE, RABBITMQ_ROUTING_KEY)
    return connection

def setup(connection: pika.BlockingConnection):
    """
    Registers the template with mailing
    """


    try:
        template = {
            "dto": {
                "exchange": RABBITMQ_EXCHANGE,
                "routingKey": RABBITMQ_ROUTING_KEY,
                "version": 1, # DONT FORGET TO INCREMENT WHEN CHANGING TEMPLATE BELOW
                "displayName": "Services down: Heartbeat failed",
                "contentType": "TEXT_HTML",
                "subject": "Services down! Immediate action required",
                "template": """
            <h1>
                Immediate action required!
            </h1>
            <h5>
                <span th:text:"#{data.get("services").size()}"></span> services have not send a heartbeat in the last minute
            </h5>

            <ul>
                <li th:each="service : ${data.get("services")}">
                    <span th:text:"#{service.get("sender").asText()}></span>
                    has been down since
                    <span th:text:"#{service.get("last_seen").asText()}></span>
                </li>
            </ul>
            """,
                "userLocation": "admins",
                "userLocationType": "ARRAY"
            }
        }

        xml_str = xmltodict.unparse(template, pretty=True)
        logging.debug("Templating dto \n%s", xml_str)

        channel = connection.channel()
        channel.basic_publish(
            exchange='',
            routing_key='mailing.template',
            body=xml_str
        )

    except Exception as e:
        logging.error("Failed to setup heartbeat monitor")
        raise e