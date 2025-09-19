from typing import List, Dict, Any
import random

import nltk
from nltk.tokenize import sent_tokenize

nltk.download("punkt_tab")


# Make sure you've run: python -m nltk.downloader punkt


def human_like_chunks(text: str) -> List[str]:
    sentences = sent_tokenize(text)
    chunks: List[str] = []
    buffer: List[str] = []

    for i, sent in enumerate(sentences):
        sent = sent.strip()
        # standalone short sentence
        if len(sent.split()) <= 6 and not buffer:
            chunks.append(sent)
        elif "?" in sent and i == len(sentences) - 1:
            if buffer:
                chunks.append(" ".join(buffer))
                buffer = []
            chunks.append(sent)
        else:
            buffer.append(sent)
            if len(buffer) >= 2:
                chunks.append(" ".join(buffer))
                buffer = []

    if buffer:
        chunks.append(" ".join(buffer))
    return chunks


def calculate_typing_delays(
    user_message: str,
    response_segments: List[str],
    bot_config: Any
) -> Dict[str, Any]:
    """
    Calculate realistic typing delays with separate reading and writing phases.

    Args:
        user_message: The user's input message
        response_segments: List of response text segments to be displayed
        bot_config: Bot configuration object with delay parameters

    Returns:
        Dictionary containing reading time, minimum reading delay, and 
        response segments with individual writing delays
    """
    if not bot_config.humanlike_delay:
        return create_instant_display_response(response_segments)

    # Reading time calculation
    words = len(user_message.split())
    base_reading_time = words * (60 / bot_config.reading_words_per_minute)
    reading_jitter = random.uniform(
        bot_config.reading_jitter_min, bot_config.reading_jitter_max)
    reading_thinking = random.uniform(
        bot_config.reading_thinking_min, bot_config.reading_thinking_max)
    reading_time = base_reading_time + reading_jitter + reading_thinking

    # Calculate writing delays for each response segment
    response_segments_with_delays = []
    for segment in response_segments:
        segment_word_count = len(segment.split())
        base_writing_time = segment_word_count * \
            (60 / bot_config.writing_words_per_minute)
        writing_jitter = random.uniform(
            bot_config.writing_jitter_min, bot_config.writing_jitter_max)
        writing_thinking = random.uniform(
            bot_config.writing_thinking_min, bot_config.writing_thinking_max)
        writing_delay = base_writing_time + writing_jitter + writing_thinking

        inter_segment_delay = random.uniform(
            bot_config.intra_message_delay_min,
            bot_config.intra_message_delay_max
        )

        response_segments_with_delays.append({
            'content': segment,
            'writing_delay': writing_delay,
            'inter_segment_delay': inter_segment_delay
        })

    return {
        'reading_time': reading_time,
        'min_reading_delay': bot_config.min_reading_delay,
        'response_segments': response_segments_with_delays
    }


def create_instant_display_response(response_segments: List[str]) -> Dict[str, Any]:
    """
    Create response configuration for instant display when humanlike delay is disabled.

    Args:
        response_segments: List of response text segments

    Returns:
        Dictionary with zero delays for instant display
    """
    return {
        'reading_time': 0.0,
        'min_reading_delay': 0.0,
        'response_segments': [
            {
                'content': segment,
                'writing_delay': 0.0,
                'inter_segment_delay': 0.0
            }
            for segment in response_segments
        ]
    }
