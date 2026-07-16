"""
Regex vs Transformer Comparison Script

Loads output/raw_comments.csv, runs both:
  - classify_comment()          (existing regex-based classifier)
  - classify_sentiment_batch()  (new transformer-based sentiment classifier)
on every comment, flags disagreements between the two approaches, and saves
a per-comment comparison to output/comparison_results.csv.

This does NOT modify posts.csv, creators.csv, or any existing analysis logic.
It's a standalone, additive comparison for the GenAI concepts demonstration.
"""

import os
import logging
import pandas as pd

from comment_classifier import classify_comment
from sentiment_classifier import classify_sentiment_batch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_RAW_COMMENTS_CSV = os.path.join(PROJECT_ROOT, "output", "raw_comments.csv")
DEFAULT_OUTPUT_CSV = os.path.join(PROJECT_ROOT, "output", "comparison_results.csv")

# Thresholds used in the disagreement rules below
NEGATIVE_CONFIDENCE_THRESHOLD = 0.7
EMOJI_CONFIDENCE_THRESHOLD = 0.7


def load_raw_comments(csv_path: str = DEFAULT_RAW_COMMENTS_CSV) -> pd.DataFrame:
    """
    Load output/raw_comments.csv into a DataFrame.

    Args:
        csv_path (str): Path to raw_comments.csv

    Returns:
        pd.DataFrame: Columns creator_handle, post_url, comment_text, scraped_at
    """
    if not os.path.isfile(csv_path):
        logger.error(f"Raw comments file not found: {csv_path}")
        raise FileNotFoundError(
            f"{csv_path} does not exist. Run the scraper first to generate raw comments."
        )

    df = pd.read_csv(csv_path, encoding='utf-8')
    logger.info(f"Loaded {len(df)} raw comments from {csv_path}")
    return df


def _flag_disagreement(regex_label: str, transformer_sentiment: str, transformer_confidence: float):
    """
    Apply the two disagreement rules.

    Rule A: regex says "text" or "mixed" AND transformer says "negative" with
            confidence > 0.7 -> regex likely missed a negative sentiment
            (since regex only looks at emoji vs. text structure, not meaning).
    Rule B: regex says "emoji" (i.e. regex treats it as content-less) AND
            transformer is confident (>0.7) about ANY sentiment -> the
            "emoji-only" comment actually carries a clear sentiment signal
            that regex discards entirely.

    Returns:
        (bool, str): (is_disagreement, reason or "")
    """
    if regex_label in ("text", "mixed") and transformer_sentiment == "negative" \
            and transformer_confidence > NEGATIVE_CONFIDENCE_THRESHOLD:
        return True, "regex missed negative sentiment"

    if regex_label == "emoji" and transformer_confidence > EMOJI_CONFIDENCE_THRESHOLD:
        return True, "emoji-only comment still carries clear sentiment signal"

    return False, ""


def run_comparison(raw_comments_df: pd.DataFrame) -> pd.DataFrame:
    """
    Run regex classification and transformer sentiment classification on every
    comment, and flag disagreements between the two.

    Args:
        raw_comments_df (pd.DataFrame): Must contain creator_handle, post_url, comment_text

    Returns:
        pd.DataFrame: creator_handle, post_url, comment_text, regex_label,
                      transformer_sentiment, transformer_confidence,
                      is_disagreement, disagreement_reason
    """
    comments = raw_comments_df['comment_text'].fillna('').astype(str).tolist()
    total = len(comments)
    logger.info(f"Running regex classification on {total} comments...")

    regex_labels = [classify_comment(c) for c in comments]

    logger.info(f"Running transformer sentiment classification on {total} comments (batched)...")
    sentiment_results = classify_sentiment_batch(comments)

    rows = []
    for i in range(total):
        regex_label = regex_labels[i]
        sentiment = sentiment_results[i]['sentiment']
        confidence = sentiment_results[i]['confidence']

        is_disagreement, reason = _flag_disagreement(regex_label, sentiment, confidence)

        rows.append({
            'creator_handle': raw_comments_df.iloc[i].get('creator_handle', ''),
            'post_url': raw_comments_df.iloc[i].get('post_url', ''),
            'comment_text': comments[i],
            'regex_label': regex_label,
            'transformer_sentiment': sentiment,
            'transformer_confidence': confidence,
            'is_disagreement': is_disagreement,
            'disagreement_reason': reason,
        })

    result_df = pd.DataFrame(rows)
    logger.info(f"Comparison complete: {len(result_df)} rows generated.")
    return result_df


def print_summary(comparison_df: pd.DataFrame) -> None:
    """
    Print summary statistics to console:
      - total comments processed
      - disagreement rate (%)
      - breakdown of disagreement types
      - average confidence by sentiment class
    """
    total = len(comparison_df)
    if total == 0:
        print("No comments to summarize.")
        return

    disagreement_count = int(comparison_df['is_disagreement'].sum())
    disagreement_rate = round((disagreement_count / total) * 100, 2)

    print("\n" + "=" * 60)
    print("REGEX vs TRANSFORMER COMPARISON SUMMARY")
    print("=" * 60)
    print(f"Total comments processed: {total}")
    print(f"Disagreements flagged:    {disagreement_count} ({disagreement_rate}%)")

    print("\nBreakdown by disagreement reason:")
    reason_counts = comparison_df[comparison_df['is_disagreement']]['disagreement_reason'].value_counts()
    if reason_counts.empty:
        print("  (none)")
    else:
        for reason, count in reason_counts.items():
            print(f"  - {reason}: {count}")

    print("\nAverage transformer confidence by sentiment class:")
    avg_conf = comparison_df.groupby('transformer_sentiment')['transformer_confidence'].mean().round(4)
    for sentiment, conf in avg_conf.items():
        print(f"  - {sentiment}: {conf}")

    print("=" * 60 + "\n")


def main():
    raw_df = load_raw_comments()
    comparison_df = run_comparison(raw_df)

    os.makedirs(os.path.dirname(DEFAULT_OUTPUT_CSV), exist_ok=True)
    comparison_df.to_csv(DEFAULT_OUTPUT_CSV, index=False, encoding='utf-8')
    logger.info(f"Comparison results saved to {DEFAULT_OUTPUT_CSV}")

    print_summary(comparison_df)


if __name__ == "__main__":
    main()
