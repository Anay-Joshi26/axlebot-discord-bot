#!/bin/bash

./stop.sh # Stop any running Lavalink, Uvicorn, and Discord bot processes

mkdir -p axlebot/logs

# Function to kill all background processes on Ctrl+C
cleanup() {
  echo ""
  echo "Stopping all services..."
  kill "$LAVALINK_PID" "$UVICORN_PID"
  # The bot runs in foreground and should stop automatically with Ctrl+C
  exit 0
}

trap cleanup SIGINT

# Start Lavalink silently
cd axlebot || exit 1
echo "Starting Lavalink silently..."
java -jar Lavalink.jar > /dev/null 2>&1 &
LAVALINK_PID=$!

sleep 2  # wait for Lavalink to start

cd .. || exit 1

# Start Uvicorn with logs
echo "Starting Uvicorn API (logging to axlebot/logs/uvicorn.log)..."
PYTHONPATH=./axlebot uvicorn core.api:app --reload >> axlebot/logs/uvicorn.log 2>&1 &
UVICORN_PID=$!

sleep 1

# Show control message
echo "All services started. Press Ctrl+C to stop everything."

# Start the bot (in foreground)
echo "Starting Discord bot..."
python3 axlebot/bot.py