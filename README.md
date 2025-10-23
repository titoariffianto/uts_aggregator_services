# UTS - Layanan Aggregator Event

Ini adalah implementasi layanan aggregator event berbasis Python (FastAPI) dan Docker untuk memenuhi tugas UTS.

## Fitur Utama

-   **API (FastAPI)**: Menyediakan endpoint `POST /publish`, `GET /events`, dan `GET /stats`.
-   **Async Processing**: Menggunakan `asyncio.Queue` untuk memisahkan penerimaan dan pemrosesan event.
-   **Idempotency & Deduplikasi**: Menggunakan database SQLite (`seen_events`) untuk memastikan event dengan `(topic, event_id)` yang sama hanya diproses sekali.
-   **Persistence**: Database SQLite disimpan dalam Docker Volume (`aggregator-data`), memastikan data (termasuk status deduplikasi) bertahan (persistent) bahkan jika container di-restart atau dibuat ulang.
-   **Dockerized**: Dibangun dengan `Dockerfile` non-root dan `docker-compose.yml` untuk orkestrasi yang mudah.
-   **Bonus**: Termasuk layanan `publisher` dalam Docker Compose untuk menguji sistem dengan 5000 event (20% duplikat).

## Arsitektur

Sistem ini menggunakan dua layanan Docker Compose:

1.  `aggregator`: Layanan FastAPI utama yang menerima, mengantri, mendeduplikasi, dan menyimpan event.
2.  `publisher`: Skrip Python yang mengirimkan data uji (5000 event) ke layanan `aggregator` untuk demonstrasi.

Data disimpan di volume Docker bernama `aggregator-data` yang di-mount ke `/app/data` di dalam container `aggregator`.

## Cara Menjalankan (dengan Docker Compose)

Ini adalah cara yang direkomendasikan dan mencakup skenario bonus.

1.  **Pastikan Docker Desktop berjalan.**

2.  **Build dan jalankan layanan (detached mode):**
    Di terminal PowerShell, dari root folder proyek:

    ```powershell
    docker-compose up --build -d
    ```

3.  **Lihat log (opsional):**
    Anda dapat melihat log dari kedua layanan:

    ```powershell
    # Melihat log aggregator (API)
    docker-compose logs -f aggregator
    
    # Melihat log publisher (skrip pengirim data)
    # Anda akan melihat hasil tes performa di sini
    docker-compose logs -f publisher
    ```

4.  **Sistem sedang berjalan.**
    Layanan `publisher` akan otomatis mengirim 5000 event. Setelah selesai, Anda bisa menguji API.

## Cara Menjalankan (Hanya Aggregator dengan Docker CLI)

Jika Anda tidak ingin menggunakan Docker Compose.

1.  **Build Image:**
    ```powershell
    docker build -t uts-aggregator .
    ```

2.  **Buat Volume (jika belum ada):**
    Penting untuk persistensi data.
    ```powershell
    docker volume create aggregator-data
    ```

3.  **Run Container:**
    Perintah ini menjalankan container, memetakan port `8080`, dan memasang volume `aggregator-data` ke `/app/data`.

    ```powershell
    docker run -d -p 8080:8080 -v aggregator-data:/app/data --name my-aggregator-app uts-aggregator
    ```

## Endpoints API

Asumsikan berjalan di `localhost:8080`.

### 1. Publish Events

Mengirim satu atau batch event.

-   **Endpoint**: `POST /publish`
-   **Contoh (Single Event - pakai `Invoke-RestMethod` PowerShell):**

    ```powershell
    $event = @{
        topic     = "powershell_test"
        event_id  = "ps-event-123"
        source    = "my-laptop"
        payload   = @{ info = "testing from powershell" }
    } | ConvertTo-Json

    Invoke-RestMethod -Uri http://localhost:8080/publish -Method Post -Body $event -ContentType "application/json"
    ```

-   **Contoh (Batch Event):**

    ```powershell
    $batch = @(
        @{ topic = "batch_test"; event_id = "b-1"; source = "ps"; payload = @{} },
        @{ topic = "batch_test"; event_id = "b-2"; source = "ps"; payload = @{} }
    ) | ConvertTo-Json

    Invoke-RestMethod -Uri http://localhost:8080/publish -Method Post -Body $batch -ContentType "application/json"
    ```

### 2. Get Stats

Melihat statistik layanan.

-   **Endpoint**: `GET /stats`
-   **Contoh (PowerShell):**

    ```powershell
    Invoke-RestMethod -Uri http://localhost:8080/stats
    ```

### 3. Get Processed Events

Melihat event unik yang telah diproses berdasarkan topik.

-   **Endpoint**: `GET /events?topic=...`
-   **Contoh (PowerShell):**

    ```powershell
    # Ganti 'powershell_test' dengan topik yang Anda kirim
    Invoke-RestMethod -Uri "http://localhost:8080/events?topic=powershell_test"
    ```

## Menjalankan Unit Tests (Lokal)

1.  Pastikan Anda memiliki `pytest`, `pytest-asyncio`, dan `httpx` di venv lokal Anda.
    ```powershell
    pip install pytest pytest-asyncio httpx
    ```
2.  Set PYTHONPATH agar import `src` berfungsi:
    ```powershell
    $env:PYTHONPATH = ".;" + $env:PYTHONPATH
    ```
3.  Jalankan pytest:
    ```powershell
    pytest
    ```

## Link Video Demo

(Cantumkan link YouTube Anda di sini)