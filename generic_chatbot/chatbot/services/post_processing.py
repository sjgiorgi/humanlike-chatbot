from nltk.tokenize import sent_tokenize
import nltk
import re
from typing import List

nltk.download('punkt_tab')


# Make sure you’ve run: python -m nltk.downloader punkt


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
