FROM python:3.11-slim

WORKDIR /app

RUN adduser --disabled-password --gecos '' appuser
RUN mkdir /app/data && chown -R appuser:appuser /app/data

COPY --chown=appuser:appuser requirements.txt ./

USER appuser
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=appuser:appuser src/ ./src/

ENV DB_PATH=/app/data/aggregator.db

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--use-colors"]
