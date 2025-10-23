import asyncio
import os
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Request
from contextlib import asynccontextmanager

from .models import Event, PublishPayload
from .database import EventDatabase

DB_PATH = os.getenv("DB_PATH", "/app/data/aggregator.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

event_queue = asyncio.Queue(maxsize=10000)
db = EventDatabase(DB_PATH)
stats = {
    "received_total": 0,
    "unique_processed": 0,
    "duplicate_dropped": 0,
    "start_time": datetime.utcnow()
}

async def event_consumer():
    log.info("Event consumer started...")
    while True:
        try:
            event = await event_queue.get()
            is_duplicate = await db.check_and_mark_duplicate(event)
            if is_duplicate:
                stats["duplicate_dropped"] += 1
                log.info(f"Duplicate event dropped: {event.topic}/{event.event_id}")
            else:
                await db.store_processed_event(event)
                stats["unique_processed"] += 1
                log.info(f"New event processed: {event.topic}/{event.event_id}")
            event_queue.task_done()
        except asyncio.CancelledError:
            log.info("Event consumer shutting down...")
            break
        except Exception as e:
            log.error(f"Error in event consumer: {e}", exc_info=True)
            await asyncio.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"Starting up... Connecting to database at {DB_PATH}")
    await db.connect()
    await db.init_db()
    try:
        stats["unique_processed"] = await db.get_total_processed_count()
        log.info(f"Re-hydrated stats: Found {stats['unique_processed']} processed events in database.")
    except Exception as e:
        log.error(f"Could not re-hydrate stats from DB: {e}")
    consumer_task = asyncio.create_task(event_consumer())
    yield
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        log.info("Consumer task successfully cancelled.")
    await db.close()
    log.info("Shutdown complete.")

app = FastAPI(
    title="Event Aggregator Service",
    description="Service for receiving, deduplicating, and storing events.",
    lifespan=lifespan
)

@app.post("/publish", status_code=202)
async def publish_events(payload: PublishPayload, request: Request):
    events_to_process = [payload] if isinstance(payload, Event) else payload
    if not events_to_process:
        raise HTTPException(status_code=400, detail="No events provided")
    for event in events_to_process:
        try:
            await event_queue.put(event)
            stats["received_total"] += 1
        except asyncio.QueueFull:
            log.error("Event queue is full! Dropping event.")
            raise HTTPException(status_code=503, detail="Service busy, event queue full.")
    return {"status": "queued", "received_count": len(events_to_process)}

@app.get("/events")
async def get_processed_events(topic: str = Query(..., description="Topic to filter events")):
    try:
        events = await db.get_events_by_topic(topic)
        return {"topic": topic, "events": events, "count": len(events)}
    except Exception as e:
        log.error(f"Error getting events: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve events.")

@app.get("/stats")
async def get_service_stats():
    uptime_seconds = (datetime.utcnow() - stats["start_time"]).total_seconds()
    try:
        distinct_topics = await db.get_distinct_topics()
    except Exception as e:
        log.error(f"Error getting distinct topics: {e}")
        distinct_topics = []
    return {
        "received_total": stats["received_total"],
        "unique_processed": stats["unique_processed"],
        "duplicate_dropped": stats["duplicate_dropped"],
        "queue_size_current": event_queue.qsize(),
        "processed_topics": distinct_topics,
        "uptime_seconds": uptime_seconds
    }

@app.get("/")
def read_root():
    return {"message": "Welcome to the Event Aggregator Service!"}
