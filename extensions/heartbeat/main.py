import logging
import os
import time

from heartbeat_monitoring import heartbeat_loop
from setup import setup, init_connection

logging.basicConfig(
    level=logging.getLevelNamesMapping().get(os.environ.get('LOG_LEVEL'), logging.INFO),
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


def main():
    logging.info("Starting Heartbeat monitor")

    connection = init_connection()
    setup(connection)

    logging.info("Starting check loop, running every 10s")
    try:
        while True:
            heartbeat_loop()
            time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        connection.close()
        logging.info("Shutting down Heartbeat monitor")


if __name__ == "__main__":
    main()