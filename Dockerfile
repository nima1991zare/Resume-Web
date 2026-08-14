FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY tools ./tools

# data dir for SQLite — mount a persistent volume/disk here in production,
# otherwise the database resets on every redeploy
RUN mkdir -p /app/data /app/static/uploads

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-server-header"]
