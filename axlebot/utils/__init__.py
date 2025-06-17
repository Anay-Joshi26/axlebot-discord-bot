"""
A file for utility functions
"""

from typing import Tuple
from datetime import datetime, timedelta
# USE CONVERTORS FROM DISCORD PYTHON LIBRARY

def discord_tag_to_id(tag: str) -> Tuple[int, str] | Tuple[None, None]:
    """
    Discord tags allow you to mention users, channels, roles, etc. in a specific format.
    This function extracts the ID from a Discord tag.
    Args:
        tag (str): The Discord tag in the format <@123456789012345678> or <#123456789012345678>.
    Returns:
        (int, type): The extracted ID as an integer, and the type of the tag (user, channel).
    """
    if tag.startswith("<@&") and tag.endswith(">"):
        # Role mention
        role_id = int(tag[3:-1])
        return role_id, "role"
    elif tag.startswith("<@") and tag.endswith(">"):
        # User mention
        user_id = int(tag[2:-1])
        return user_id, "user"
    elif tag.startswith("<#") and tag.endswith(">"):
        # Channel mention
        channel_id = int(tag[2:-1])
        return channel_id, "channel"
    else:
        return None, None
    
def parse_tag(tag: str, expect) -> int:
    """
    Parses a Discord tag and returns the ID.
    Args:
        tag (str): The Discord tag in the format <@123456789012345678> or <#123456789012345678> or 123456789012345678.
    Returns:
        (int, type): The extracted ID as an integer, and the type of the tag (user, channel).
    """
    discord_id, tag_type = discord_tag_to_id(tag)

    if discord_id is not None and tag_type != expect:
        raise ValueError(f"Expected Discord '{expect}', but got Discord '{tag_type}'")

    if discord_id is None:
        return tag, expect
    
    return discord_id, tag_type

def convert_duration(duration):
    hours = duration // 3600
    minutes = (duration % 3600) // 60
    seconds = duration % 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"

def time_string_to_seconds(time_str: str) -> int:
    """
    Parses a time string in either MM:SS or HH:MM:SS format into seconds.
    :param time_str: The time string to parse.
    :return: The total number of seconds represented by the time string.
    """
    if len(time_str.split(":")) == 2:  # MM:SS format
        time_obj = datetime.strptime(time_str, "%M:%S")
        return time_obj.minute * 60 + time_obj.second
    elif len(time_str.split(":")) == 3:  # HH:MM:SS format
        time_obj = datetime.strptime(time_str, "%H:%M:%S")
        return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
    else:
        raise ValueError("Time format not recognized. Use MM:SS or HH:MM:SS")
    
def parse_seek_time(time_str: str) -> float:
    """
    Parses a time string in various formats (SECONDS, MM:SS, HH:MM:SS, SECONDS.FRACTION) into total seconds.

    :param time_str: The time string to parse.
    :return: The total number of seconds represented by the time string.
    :raises ValueError: If the time string is in an invalid format.
    """
    parts = time_str.split(":")

    try:
        if len(parts) == 1:
            # SECONDS or SECONDS.FRACTION
            return float(parts[0])
        elif len(parts) == 2:
            # MM:SS
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        elif len(parts) == 3:
            # HH:MM:SS or HH:MM:SS.mmm
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        else:
            raise ValueError("Invalid time format")
    except ValueError:
        raise ValueError("Failed to parse time string")