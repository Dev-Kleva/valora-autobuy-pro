FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl bash tar ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY main.py ./
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
RUN chmod +x ./backend/start.sh

EXPOSE 8080

CMD ["bash", "./backend/start.sh"]
