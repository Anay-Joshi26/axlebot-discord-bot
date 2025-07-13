#!/bin/bash

echo "Killing Lavalink..."
pkill -f 'java -jar Lavalink.jar'

echo "Killing Uvicorn API..."
pkill -f 'uvicorn core.api:app'

echo "Killing Discord bot..."
pkill -f 'python3 axlebot/bot.py'

echo "All processes terminated."