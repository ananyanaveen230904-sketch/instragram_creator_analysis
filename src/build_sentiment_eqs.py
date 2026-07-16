"""
Build Sentiment-Adjusted EQS per Creator

Joins output/comparison_results.csv (per-comment sentiment data) with
output/creators.csv (existing EQS scores) on creator_handle, aggregates
sentiment percentages per creator, applies calculate_sentiment_adjusted_eqs(),
and saves output/creators_with_sentiment_eqs.csv.

This is purely additive — it does not modify creators.csv or posts.csv.
"""

import os
import logging
import pandas as pd

from post_analyzer import calculate_sentiment_adjusted_eqs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CREATORS_CSV = os.path.join(PROJECT_ROOT, "output", "creators.csv")
DEFAULT_COMPARISON_CSV = os.path.join(PROJECT_ROOT, "output", "comparison_results.csv")
DEFAULT_OUTPUT_CSV = os.path.join(PROJECT_ROOT, "output", "creators_with_sentiment_eqs.csv")


def _compute_sentiment_pcts(group: pd.DataFrame) -> dict:
    """Given all comparison rows for one creator, compute positive/negative/neutral %."""
    total = len(group)
    if total == 0:
        return {'positive_pct': 0.0, 'negative_pct': 0.0, 'neutral_pct': 0.0}

    counts = group['transformer_sentiment'].value_counts()
    positive_pct = round((counts.get('positive', 0) / total) * 100, 2)
    negative_pct = round((counts.get('negative', 0) / total) * 100, 2)
    neutral_pct = round((counts.get('neutral', 0) / total) * 100, 2)

    return {'positive_pct': positive_pct, 'negative_pct': negative_pct, 'neutral_pct': neutral_pct}


def build_creators_with_sentiment_eqs(
    creators_csv: str = DEFAULT_CREATORS_CSV,
    comparison_csv: str = DEFAULT_COMPARISON_CSV,
    output_csv: str = DEFAULT_OUTPUT_CSV
) -> pd.DataFrame:
    """
    Join creators.csv with aggregated sentiment data from comparison_results.csv
    and compute sentiment_adjusted_eqs per creator.

    Args:
        creators_csv (str): Path to existing creators.csv
        comparison_csv (str): Path to comparison_results.csv (from run_comparison.py)
        output_csv (str): Path to write creators_with_sentiment_eqs.csv

    Returns:
        pd.DataFrame: creator_handle, original_eqs, sentiment_adjusted_eqs,
                      positive_pct, negative_pct, neutral_pct
    """
    if not os.path.isfile(creators_csv):
        raise FileNotFoundError(f"{creators_csv} not found. Run the scraper first.")
    if not os.path.isfile(comparison_csv):
        raise FileNotFoundError(f"{comparison_csv} not found. Run run_comparison.py first.")

    creators_df = pd.read_csv(creators_csv, encoding='utf-8')
    comparison_df = pd.read_csv(comparison_csv, encoding='utf-8')

    logger.info(f"Loaded {len(creators_df)} creators and {len(comparison_df)} comparison rows.")

    rows = []
    for _, creator_row in creators_df.iterrows():
        creator_handle = creator_row['creator_handle']
        original_eqs = float(creator_row.get('avg_EQS', 0.0))

        creator_comments = comparison_df[comparison_df['creator_handle'] == creator_handle]

        if creator_comments.empty:
            logger.warning(
                f"No comparison data found for creator '{creator_handle}'; "
                f"sentiment_adjusted_eqs will equal original_eqs (no adjustment)."
            )
            sentiment_pcts = {'positive_pct': 0.0, 'negative_pct': 0.0, 'neutral_pct': 0.0}
        else:
            sentiment_pcts = _compute_sentiment_pcts(creator_comments)

        sentiment_adjusted_eqs = calculate_sentiment_adjusted_eqs(
            existing_eqs=original_eqs,
            positive_pct=sentiment_pcts['positive_pct'],
            negative_pct=sentiment_pcts['negative_pct'],
            neutral_pct=sentiment_pcts['neutral_pct'],
        )

        rows.append({
            'creator_handle': creator_handle,
            'original_eqs': original_eqs,
            'sentiment_adjusted_eqs': sentiment_adjusted_eqs,
            'positive_pct': sentiment_pcts['positive_pct'],
            'negative_pct': sentiment_pcts['negative_pct'],
            'neutral_pct': sentiment_pcts['neutral_pct'],
        })

    result_df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    result_df.to_csv(output_csv, index=False, encoding='utf-8')
    logger.info(f"Saved {len(result_df)} creator rows to {output_csv}")

    return result_df


def main():
    build_creators_with_sentiment_eqs()


if __name__ == "__main__":
    main()
