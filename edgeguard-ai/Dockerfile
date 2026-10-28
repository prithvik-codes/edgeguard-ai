FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY scripts ./scripts
COPY tests ./tests
RUN mkdir -p /app/data/raw /app/models/versions /app/models/registry /app/logs
ENV PYTHONPATH=/app DATA_DIR=/app/data MODEL_DIR=/app/models LOG_DIR=/app/logs
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
