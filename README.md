# Axlebot Discord Music Bot

Axlebot is a feature-rich Discord music bot that supports YouTube and Spotify playback, custom playlists, queue management, and more. It is designed for easy use and high performance in your Discord server.

## Features
- Play music from YouTube and Spotify links or search queries
- Create, manage, and play custom playlists
- Queue, skip, move, and shuffle songs
- View song lyrics and now playing info
- Advanced queue controls (move, remove, repeat, seek, etc.)
- Permission checks and cooldowns to prevent spam
- Supports both single songs and full playlists

## How It Works
- The bot uses Discord's voice API to join your server's voice channel and play audio.
- Songs are fetched and streamed using YouTube and Spotify APIs (via Lavalink and other libraries).
- A dedicated FastAPI service is used to fetch lyrics (and previously handled all song info fetching).
- Users interact with the bot using commands (e.g., `-play`, `-queuepl`, `-skip`, `-playlist`, etc.).
- Most commands have simpler aliases for easier use (e.g., `-p` for `-play` and many more...)
- Playlists and queues are managed in memory but playlists can also be persisted to a database.
- The bot uses async programming for efficient concurrent song fetching and playback to work on many servers simultaneously.

## Getting Started

### Prerequisites
- Python 3.11+ (mainly for `asyncio` features)
- Discord bot token (create one at https://discord.com/developers/applications)
- Lavalink server (for audio streaming)
- FFmpeg installed and available in your PATH
- Dependencies inside the `requirements.txt` file

### Installation
1. Clone this repository:
   ```bash
   git clone <repo-url>
   cd axlebot-discord-bot
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your bot:
   - Copy `account_key.json` and `application.yml` with your credentials and settings.
   - Set your Discord bot token in the config file or as an environment variable.
   - Ensure `Lavalink.jar` is present and configured (see Lavalink docs).

*Note: The `application.yml` in `main` is simply an example*

### Running the Bot

Ensure you are in the `/axlebot-discord-bot` directory.

To run the bot and all its services run:

```bash
./start.sh
```

To stop the bot and all its services run:

```bash
./stop.sh
```

*Note: Both shell scripts should have executable permissions*

**Alternatively, to run each service separately, follow the below steps**

1. Start the Lavalink server (in a separate terminal):
   ```bash
   java -jar Lavalink.jar
   ```
2. Start the FastAPI lyrics service (in a separate terminal):
   ```bash
   PYTHONPATH=./axlebot uvicorn core.api:app --reload
   ```
3. Start the bot (in a separate terminal):
   ```bash
   python axlebot/bot.py
   ```

The FastAPI service is written to be an integrated module, but it can be run separately if needed.

### Usage
- Invite the bot to your server using the OAuth2 URL from the Discord developer portal.
- Use commands in any text channel:
  - `-play <song or URL>`: Play a song or add to queue
  - `-queuepl <playlist name>`: Queue a custom playlist
  - `-skip`: Skip the current song
  - `-playlist`: View or manage playlists
  - `-move <from> <to>`: Move a song in the queue
  - `-shuffle`: Shuffle the queue
  - `-lyrics`: Show lyrics for the current song
  - ...and many more (see `cogs/*.py` for all commands)
  - See all commands via `-help`

## FastAPI Service
- The FastAPI service is used to fetch lyrics for songs.
- Start it with:
  ```bash
  uvicorn axlebot.core.api:app
  ```
- In previous versions (see other branches), this service also handled all song info fetching.

## Contributing
Pull requests and suggestions are welcome! Please open an issue or PR for bug fixes or new features.
