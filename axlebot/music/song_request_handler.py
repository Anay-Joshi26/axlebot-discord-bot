import re

# Query types
YT_SONG, SPOT_SONG, YT_PLAYLIST, SPOT_PLAYLIST, STD_YT_QUERY = range(5)

def determine_query_type(query):
    # Check for Spotify Playlist
    if "open.spotify.com/playlist/" in query or "open.spotify.com/album/" in query:
        return SPOT_PLAYLIST
    
    # Check for YouTube Playlist
    elif ("youtube.com" in query or "youtu.be" in query) and "list=" in query:
        return YT_PLAYLIST
    
    # Check for YouTube Song (Standard or Short URL)
    elif "youtube.com" in query or "youtu.be" in query:
        return YT_SONG
    
    # Check for Spotify Song
    elif "open.spotify.com/track/" in query:
        return SPOT_SONG
    
    # Default: Standard YouTube Query
    else:
        return STD_YT_QUERY

def convert_to_standard_youtube_url(query):
    """
    Converts various YouTube URLs to the standard format:
    https://www.youtube.com/watch?v=ID
    """
    # Match short YouTube URLs (https://youtu.be/ID)
    match = re.match(r"https?://youtu\.be/([\w-]+)", query)
    if match:
        video_id = match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"

    # Match full YouTube URLs with `v=ID`
    match = re.search(r"v=([\w-]+)", query)
    if match:
        video_id = match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"

    # Return None if no valid video ID is found
    return None

def extract_title_and_artist(name, artist):
    words_to_ignore = ["(offical video)", "(offical audio)", "(lyrics)", "(offical music video)", "official", "audio", "video", "lyrics", "music video", \
                           "(video)", "(audio)", "(lyric video)", "(lyric)", "(music video)", "(official lyric video)", "(official lyric)", "()", "~", "( )", "( Music )", \
                            "visualiser", "visualizer", "(visualiser)", "(visualizer)", "[]", "[ ]", f"{artist}", " - ", "ft.", "feat.", "-"]
    name_to_use = name

    for word in words_to_ignore:
        name_to_use = re.sub(re.escape(word), "", name_to_use, flags=re.IGNORECASE).strip()
        if "ft." in name_to_use:
            name_to_use = name_to_use[:name_to_use.index("ft.")]
        elif "feat." in name_to_use:
            name_to_use = name_to_use[:name_to_use.index("feat.")]

    return name_to_use, artist

