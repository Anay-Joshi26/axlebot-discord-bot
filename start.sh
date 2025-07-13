#!/bin/bash

mkdir -p logs

# Start Lavalink silently
cd axlebot || exit 1
echo "Starting Lavalink silently..."
java -jar Lavalink.jar > /dev/null 2>&1 &

sleep 2  # wait for Lavalink to start

cd .. || exit 1

# Start Uvicorn with logs
echo "Starting Uvicorn API (logging to axlebot/logs/uvicorn.log)..."
PYTHONPATH=./axlebot uvicorn core.api:app --reload > axlebot/logs/uvicorn.log 2>&1 &

sleep 1

# Start the bot normally (can log this too if you like)
echo "Starting Discord bot..."
python3 axlebot/bot.py
