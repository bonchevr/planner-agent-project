FROM python:3.11-slim

WORKDIR /app

# gosu lets the entrypoint drop from root → appuser after fixing volume ownership
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root system user to run the application
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# The data directory is created here; the entrypoint will chown it at runtime
# after Docker has mounted the named volume (which is owned by root by default).
RUN mkdir -p /app/data

ENV APP_ENV=production

EXPOSE 8000

# Runs as root only long enough to chown /app/data, then drops to appuser
ENTRYPOINT ["/entrypoint.sh"]
