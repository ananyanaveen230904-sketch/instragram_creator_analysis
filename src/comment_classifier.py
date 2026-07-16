"""
Comment Classifier Module

Classifies Instagram comments into three categories:
- Text: Contains letters/numbers but no emojis
- Emoji: Contains only emojis
- Mixed: Contains both emojis and text
"""

import re


def classify_comment(text):
    """
    Classify a comment into one of three categories: text, emoji, or mixed.
    
    Args:
        text (str): The comment text to classify
        
    Returns:
        str: One of "text", "emoji", or "mixed"
    """
    if not text or not isinstance(text, str):
        return "text"
    
    # Remove whitespace for analysis
    text_stripped = text.strip()
    if not text_stripped:
        return "text"
    
    # Regex pattern to match emojis (including most Unicode emoji ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
        "\U00002600-\U000026FF"  # miscellaneous symbols
        "\U00002700-\U000027BF"  # dingbats
        "]+",
        flags=re.UNICODE
    )
    
    # Find all emojis in the text
    emojis = emoji_pattern.findall(text_stripped)
    has_emoji = len(emojis) > 0
    
    # Remove emojis to check for text content
    text_without_emoji = emoji_pattern.sub('', text_stripped)
    # Remove common punctuation and whitespace
    text_clean = re.sub(r'[^\w\s]', '', text_without_emoji)
    text_clean = text_clean.strip()
    
    has_text = len(text_clean) > 0 and any(c.isalnum() for c in text_clean)
    
    # Classification logic
    if has_emoji and has_text:
        return "mixed"
    elif has_emoji and not has_text:
        return "emoji"
    else:
        return "text"

