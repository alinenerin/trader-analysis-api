FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api.py .
COPY core ./core
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} api:app"]
