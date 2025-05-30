"""
A file for utility functions
"""

def discord_tag_to_id(tag: str) -> int:
    """
    Discord tags allow you to mention users, channels, roles, etc. in a specific format.
    This function extracts the ID from a Discord tag.
    Args:
        tag (str): The Discord tag in the format <@123456789012345678> or <#123456789012345678>.
    Returns:
        (int, type): The extracted ID as an integer, and the type of the tag (user, channel).
    """
    if tag.startswith("<@") and tag.endswith(">"):
        # User mention
        user_id = int(tag[2:-1])
        return user_id, "user"
    elif tag.startswith("<#") and tag.endswith(">"):
        # Channel mention
        channel_id = int(tag[2:-1])
        return channel_id, "channel"
    elif tag.startswith("<@&") and tag.endswith(">"):
        # Role mention
        role_id = int(tag[3:-1])
        return role_id, "role"
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