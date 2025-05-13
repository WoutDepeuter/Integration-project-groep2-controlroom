import logging
from datetime import datetime

import requests

from env import ELASTIC_URL, INDEX_NAME


def get_last_heartbeats() -> dict[str, datetime]:
    logging.debug(f"Connecting to elasticsearch on URL: {ELASTIC_URL}")

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
                    "gte": "now-7d"
                }
            }
        }
    }

    try:
        res = requests.post(f"{ELASTIC_URL}/{INDEX_NAME}/_search", json=query, timeout=10)
        res.raise_for_status()
        data = res.json()
        heartbeats = {}
        logging.debug(f"Elasticsearch response data: {data}")

        for bucket in data["aggregations"]["apps"]["buckets"]:
            timestamp = bucket["last_seen"].get("value_as_string")
            if timestamp:
                heartbeats[bucket["key"]] = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        return heartbeats
    except Exception as e:
        logging.error(f"Error fetching heartbeats: {e}")
        return {}