#!/bin/bash

#echo "Killing Lavalink..."
if pgrep -f 'java -jar Lavalink.jar' > /dev/null; then
    pkill -f 'java -jar Lavalink.jar'
    echo "Lavalink was running and has been killed."
else
    echo "Lavalink is not running."
fi

#echo "Killing Uvicorn API..."
if pgrep -f 'uvicorn core.api:app' > /dev/null; then
    pkill -f 'uvicorn core.api:app'
    echo "Uvicorn API was running and has been killed."
else
    echo "Uvicorn API is not running."
fi

#echo "Killing Discord bot..."
if pgrep -f 'python3 axlebot/bot.py' > /dev/null; then
    pkill -f 'python3 axlebot/bot.py'
    echo "Discord bot was running and has been killed."
else
    echo "Discord bot is not running."
fi

echo "Done"
