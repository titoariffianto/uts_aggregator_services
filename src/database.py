import aiosqlite
import json
import logging
from .models import Event

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class EventDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection = None
        self._connected = False
        log.info(f"Database initialized at: {db_path}")

    @property
    def connected(self) -> bool:
        """Property untuk cek status koneksi."""
        return self._connected and self._connection is not None

    async def connect(self):
        """Membuka koneksi ke database."""
        if not self._connection:
            self._connection = await aiosqlite.connect(self.db_path)
            await self._connection.execute("PRAGMA foreign_keys = ON;")
            await self._connection.commit()
            self._connected = True
            log.info(f"Connected to database: {self.db_path}")

    async def close(self):
        """Menutup koneksi database."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._connected = False
            log.info(f"Database connection closed: {self.db_path}")

    async def init_db(self):
        """Inisialisasi tabel database."""
        if not self.connected:
            await self.connect()

        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS seen_events (
                    topic TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (topic, event_id)
                )
            """)
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
            """)

            # 🧹 Tambahkan ini agar data lama dibersihkan saat inisialisasi
            await cursor.execute("DELETE FROM seen_events")
            await cursor.execute("DELETE FROM processed_events")

        await self._connection.commit()
        log.info("Database tables initialized and cleaned for test run.")

    async def check_and_mark_duplicate(self, event: Event) -> bool:
        """Cek apakah event sudah pernah diterima sebelumnya."""
        if not self.connected:
            raise Exception("Database not connected")

        try:
            await self._connection.execute(
                "INSERT INTO seen_events (topic, event_id) VALUES (?, ?)",
                (event.topic, event.event_id)
            )
            await self._connection.commit()
            return False  # bukan duplikat
        except aiosqlite.IntegrityError:
            log.warning(f"Duplicate detected: {event.topic}/{event.event_id}")
            return True
        except Exception as e:
            log.error(f"Error checking duplicate: {e}", exc_info=True)
            return True

    async def store_processed_event(self, event: Event):
        """Simpan event yang sudah diproses."""
        if not self.connected:
            raise Exception("Database not connected")

        payload_str = json.dumps(event.payload)
        await self._connection.execute(
            """
            INSERT INTO processed_events (topic, event_id, timestamp, source, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event.topic, event.event_id, event.timestamp.isoformat(), event.source, payload_str)
        )
        await self._connection.commit()

    async def get_events_by_topic(self, topic: str) -> list[dict]:
        """Ambil semua event berdasarkan topik."""
        if not self.connected:
            raise Exception("Database not connected")

        async with self._connection.execute(
            "SELECT topic, event_id, timestamp, source, payload_json FROM processed_events WHERE topic = ?",
            (topic,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "topic": row[0],
                    "event_id": row[1],
                    "timestamp": row[2],
                    "source": row[3],
                    "payload": json.loads(row[4])
                } for row in rows
            ]

    async def get_distinct_topics(self) -> list[str]:
        """Ambil daftar semua topik unik."""
        if not self.connected:
            raise Exception("Database not connected")

        async with self._connection.execute("SELECT DISTINCT topic FROM processed_events") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_total_processed_count(self) -> int:
        """Hitung total event yang telah diproses."""
        if not self.connected:
            raise Exception("Database not connected")

        async with self._connection.execute("SELECT COUNT(id) FROM processed_events") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
