import requests
import time
import random
import uuid
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

AGGREGATOR_URL = "http://aggregator:8080"
TOTAL_EVENTS = 5000
DUPLICATE_PERCENTAGE = 0.2
NUM_DUPLICATES = int(TOTAL_EVENTS * DUPLICATE_PERCENTAGE)
NUM_UNIQUE = TOTAL_EVENTS - NUM_DUPLICATES

TOPICS = ["user_logins", "payment_processed", "inventory_update"]
SOURCES = ["service-A", "service-B", "service-C"]

def wait_for_aggregator():
    log.info(f"Waiting for aggregator at {AGGREGATOR_URL}...")
    retries = 10
    wait_time = 3
    for i in range(retries):
        try:
            response = requests.get(f"{AGGREGATOR_URL}/stats")
            if response.status_code == 200:
                log.info("Aggregator is UP!")
                return True
        except requests.ConnectionError:
            log.warning(f"Aggregator not ready. Retrying in {wait_time}s... ({i+1}/{retries})")
            time.sleep(wait_time)
    log.error("Aggregator did not start. Exiting.")
    return False

def generate_event():
    return {
        "topic": random.choice(TOPICS),
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "source": random.choice(SOURCES),
        "payload": {"data": "some_value_" + str(random.randint(1, 1000))}
    }

def send_batch(events: list):
    try:
        response = requests.post(f"{AGGREGATOR_URL}/publish", json=events)
        if response.status_code == 202:
            log.info(f"Successfully sent batch of {len(events)} events.")
        else:
            log.warning(f"Failed to send batch. Status: {response.status_code}, Body: {response.text}")
    except requests.RequestException as e:
        log.error(f"Error sending batch: {e}")

def main():
    if not wait_for_aggregator():
        return

    log.info(f"Starting to send {TOTAL_EVENTS} events with {DUPLICATE_PERCENTAGE*100}% duplicates...")
    
    unique_events = [generate_event() for _ in range(NUM_UNIQUE)]
    events_to_duplicate = random.sample(unique_events, NUM_DUPLICATES)
    all_events_to_send = unique_events + events_to_duplicate
    random.shuffle(all_events_to_send)
    
    log.info(f"Total unique: {len(unique_events)}, Total duplicates: {len(events_to_duplicate)}, Total to send: {len(all_events_to_send)}")

    batch_size = 100
    for i in range(0, len(all_events_to_send), batch_size):
        batch = all_events_to_send[i:i+batch_size]
        send_batch(batch)
        time.sleep(0.1)

    log.info("--- Test Data Sending Complete ---")
    log.info("Waiting 10 seconds for aggregator to process the queue...")
    time.sleep(10)

    try:
        stats_res = requests.get(f"{AGGREGATOR_URL}/stats")
        log.info("--- FINAL STATS FROM AGGREGATOR ---")
        log.info(stats_res.json())
        log.info("-------------------------------------")
        
        stats_data = stats_res.json()
        assert stats_data["received_total"] == TOTAL_EVENTS
        assert stats_data["unique_processed"] == NUM_UNIQUE
        assert stats_data["duplicate_dropped"] == NUM_DUPLICATES
        log.info("Verification SUCCESSFUL!")

    except Exception as e:
        log.error(f"Failed to get final stats: {e}")
        log.info("Verification FAILED.")

if __name__ == "__main__":
    main()
