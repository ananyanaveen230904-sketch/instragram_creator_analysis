"""
Sentiment Classifier Module (Transformer-based)

Adds a transformer-based sentiment signal alongside the existing regex-based
comment_classifier.py, WITHOUT replacing it. Used to compare where a
transformer model adds value over simple regex/emoji-based classification.

Model: cardiffnlp/twitter-roberta-base-sentiment-latest
  - Trained on tweets, so it generalizes reasonably well to short, informal
    social comments like Instagram captions/comments.
  - Labels returned directly as "negative" / "neutral" / "positive".
"""

import logging
from transformers import pipeline

logger = logging.getLogger(__name__)

MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"

# The model's max token length (RoBERTa-base uses 512, but this checkpoint's
# tokenizer config caps effective input around 512 tokens including special tokens).
MAX_TOKENS = 512

# Batch size for pipeline inference. Kept modest since we're on CPU only.
BATCH_SIZE = 16

_DEFAULT_RESULT = {"sentiment": "neutral", "confidence": 0.0}

logger.info(f"Loading sentiment model '{MODEL_NAME}' (CPU)... this happens once at import time.")

# Loaded once at module level (not per-call), forced to CPU via device=-1
_sentiment_pipeline = pipeline(
    task="sentiment-analysis",
    model=MODEL_NAME,
    tokenizer=MODEL_NAME,
    device=-1,          # -1 = CPU
    framework="pt",      # force PyTorch, skip TensorFlow entirely
    truncation=True,     # gracefully truncate long comments instead of erroring
    max_length=MAX_TOKENS,
)

logger.info("Sentiment model loaded successfully.")


def _is_valid_text(text) -> bool:
    """Basic guard against empty/malformed input."""
    return isinstance(text, str) and text.strip() != ""


def classify_sentiment(text: str) -> dict:
    """
    Classify the sentiment of a single comment.

    Args:
        text (str): Comment text.

    Returns:
        dict: {"sentiment": "positive"/"negative"/"neutral", "confidence": float}
              Returns {"sentiment": "neutral", "confidence": 0.0} for empty/malformed input.
    """
    if not _is_valid_text(text):
        return dict(_DEFAULT_RESULT)

    try:
        output = _sentiment_pipeline(text.strip())[0]
        return {
            "sentiment": output["label"].lower(),
            "confidence": round(float(output["score"]), 4),
        }
    except Exception as e:
        logger.warning(f"Sentiment classification failed for a comment: {e}")
        return dict(_DEFAULT_RESULT)


def classify_sentiment_batch(texts: list) -> list:
    """
    Classify sentiment for a batch of comments in one pipeline call (faster than
    calling classify_sentiment() in a loop for large comment sets).

    Empty/malformed entries are filtered out before batching and re-inserted as
    {"sentiment": "neutral", "confidence": 0.0} at their original position, so the
    returned list always matches the input list 1:1 in length and order.

    Args:
        texts (list): List of comment text strings.

    Returns:
        list: List of {"sentiment": str, "confidence": float} dicts, same order as input.
    """
    if not texts:
        return []

    results = [dict(_DEFAULT_RESULT) for _ in texts]

    # Track which indices actually need model inference
    valid_indices = [i for i, t in enumerate(texts) if _is_valid_text(t)]
    valid_texts = [texts[i].strip() for i in valid_indices]

    if not valid_texts:
        return results

    try:
        outputs = _sentiment_pipeline(valid_texts, batch_size=BATCH_SIZE)
    except Exception as e:
        logger.warning(f"Batch sentiment classification failed, falling back to neutral defaults: {e}")
        return results

    for idx, output in zip(valid_indices, outputs):
        try:
            results[idx] = {
                "sentiment": output["label"].lower(),
                "confidence": round(float(output["score"]), 4),
            }
        except Exception as e:
            logger.warning(f"Could not parse sentiment output at index {idx}: {e}")
            # leave as default neutral

    return results
