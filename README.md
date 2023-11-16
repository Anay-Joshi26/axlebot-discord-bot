## AxleBot - Discord Music Bot

AxleBot is a Discord bot designed to play music from Spotify and YouTube, search for lyrics, and manage playlists. It is built using the Discord.py library and integrates with Spotify and YouTube APIs for music playback.

Note: It is my first time building such a bot, so there may be imperfections/inconsistencies etc with the code.

### Features

- Play music from Spotify and YouTube
- Search and display lyrics for the currently playing song
- Queue management with options to skip, pause, resume, and stop playback
- Spotify playlist support
- YouTube playlist support (including YouTube Music)
- Shuffle queue functionality
- Repeat songs

### Prerequisites
Before running AxleBot, make sure you have the following dependencies installed:

Python 3.11 (persoanlly used)
Discord.py
yt_dlp
pytube
spotipy
PIL (Python Imaging Library)
(Along with some others)
*Note: FFMPEG must be installed and the path must be given*

### Install the dependencies using:

```bash
pip install discord.py yt-dlp pytube spotipy pillow
```

### Setup

1. Install the required packages

2. Get your Spotify API credentials:

Create a Spotify Developer account: Spotify Developer Dashboard
Create a new application and note down the Client ID and Client Secret.
Replace the `client_id` and `client_secret` variables in your code with the obtained Spotify credentials.

3. Get your Discord bot token:

Create a new Discord bot on the Discord Developer Portal
Copy the bot token.
Replace the `client.run("YOUR_DISCORD_BOT_TOKEN")` line in your code with your Discord bot token.

4. Run the bot, using 
```bash
python your_bot_script_name.py
```

### Usage
Note, the bot currently only works in one server, but plans exist add functionality to work in multiple servers at once
Use -p or -play to play a song from Spotify, YouTube, or a playlist.
Use -q or -queue to display the current song queue.
Use -l or -lyrics to show lyrics for the current song.
Use other commands like -skip, -pause, -resume, -stop, etc., to control playback.
For a full list of commands, use -help within a text channel

### Contributors
@Anay-Joshi26