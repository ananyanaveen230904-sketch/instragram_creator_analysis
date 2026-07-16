"""
Streamlit Dashboard: Instagram Engagement Analysis
  - Regex vs Transformer sentiment comparison
  - Per-creator EQS and sentiment-adjusted EQS
  - Natural language Q&A over the dataset (text-to-SQL via Gemini)

Reads:
  - output/posts.csv
  - output/creators.csv
  - output/comparison_results.csv   (from src/run_comparison.py)
  - output/creators_with_sentiment_eqs.csv  (from src/build_sentiment_eqs.py)
  - output/analytics.db  (from src/db_setup.py, used by the Ask AI section)

Layout: sidebar navigation, single content area (one section rendered at a time).
"""

import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from query_engine import answer_question  # noqa: E402

POSTS_CSV = os.path.join(PROJECT_ROOT, "output", "posts.csv")
CREATORS_CSV = os.path.join(PROJECT_ROOT, "output", "creators.csv")
COMPARISON_CSV = os.path.join(PROJECT_ROOT, "output", "comparison_results.csv")
CREATORS_EQS_CSV = os.path.join(PROJECT_ROOT, "output", "creators_with_sentiment_eqs.csv")
ANALYTICS_DB = os.path.join(PROJECT_ROOT, "output", "analytics.db")

# Color palette used consistently across all charts
COLOR_PRIMARY = "#6366F1"       # indigo
COLOR_SECONDARY = "#14B8A6"     # teal
COLOR_POSITIVE = "#22C55E"      # green
COLOR_NEGATIVE = "#EF4444"      # red
COLOR_NEUTRAL = "#94A3B8"       # slate gray
COLOR_ACCENT = "#F59E0B"        # amber

SENTIMENT_COLOR_MAP = {
    "positive": COLOR_POSITIVE,
    "negative": COLOR_NEGATIVE,
    "neutral": COLOR_NEUTRAL,
}
REGEX_COLOR_MAP = {
    "text": COLOR_PRIMARY,
    "emoji": COLOR_ACCENT,
    "mixed": COLOR_SECONDARY,
}

PLOTLY_TEMPLATE = "plotly_dark"

st.set_page_config(
    page_title="Instagram Engagement Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for a more polished, professional look
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1300px;
    }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1A1D29 0%, #21253A 100%);
        border: 1px solid #2D3348;
        border-radius: 12px;
        padding: 1rem 1.25rem;
    }
    [data-testid="stMetricLabel"] {
        font-weight: 500;
        opacity: 0.75;
    }
    h1, h2, h3 {
        font-weight: 700 !important;
    }
    [data-testid="stSidebar"] {
        border-right: 1px solid #2D3348;
    }
    .stButton > button {
        border-radius: 8px;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #2D3348;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data
def load_csv(path):
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path, encoding='utf-8')


posts_df = load_csv(POSTS_CSV)
creators_df = load_csv(CREATORS_CSV)
comparison_df = load_csv(COMPARISON_CSV)
creators_eqs_df = load_csv(CREATORS_EQS_CSV)

if comparison_df is None:
    st.error(f"Could not find {COMPARISON_CSV}. Run `python src/run_comparison.py` first.")
    st.stop()

disagreements_df = comparison_df[comparison_df['is_disagreement']].copy()


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.title("📊 Engagement Analysis")
st.sidebar.caption("Instagram creator engagement & sentiment insights")

PAGES = [
    "🏠 Overview",
    "🔍 Regex vs Transformer",
    "⚠️ Disagreements",
    "👤 Creators & EQS",
    "💬 Ask AI",
]
page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")

st.sidebar.divider()
st.sidebar.caption(
    "Sentiment model: `cardiffnlp/twitter-roberta-base-sentiment-latest`\n\n"
    "Q&A model: Gemini 2.5 Flash"
)


# ---------------------------------------------------------------------------
# PAGE: Overview
# ---------------------------------------------------------------------------
if page == "🏠 Overview":
    st.title("Overview")
    st.caption("High-level snapshot of the engagement analysis pipeline.")

    total_comments = len(comparison_df)
    disagreement_count = int(comparison_df['is_disagreement'].sum())
    disagreement_rate = round((disagreement_count / total_comments) * 100, 2) if total_comments else 0.0
    avg_confidence = round(comparison_df['transformer_confidence'].mean(), 3) if total_comments else 0.0
    total_creators = creators_df['creator_handle'].nunique() if creators_df is not None else 0
    total_posts = posts_df['post_url'].nunique() if posts_df is not None else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Comments", f"{total_comments:,}")
    m2.metric("Disagreement Rate", f"{disagreement_rate}%")
    m3.metric("Avg. Confidence", f"{avg_confidence}")
    m4.metric("Creators Analyzed", f"{total_creators}")
    m5.metric("Posts Analyzed", f"{total_posts}")

    st.divider()

    if posts_df is not None and not posts_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("EQS vs. Comment Volume per Post")
            fig = px.scatter(
                posts_df,
                x="total_comments",
                y="EQS",
                color="pass",
                size="unique_commenters_ratio",
                hover_data=["creator_handle"],
                color_discrete_map={"Pass": COLOR_POSITIVE, "Fail": COLOR_NEGATIVE},
                template=PLOTLY_TEMPLATE,
            )
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=380)
            st.plotly_chart(fig, width='stretch')

        with col2:
            st.subheader("EQS Distribution Across All Posts")
            fig = px.histogram(
                posts_df,
                x="EQS",
                nbins=15,
                color_discrete_sequence=[COLOR_PRIMARY],
                template=PLOTLY_TEMPLATE,
            )
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=380, bargap=0.05)
            st.plotly_chart(fig, width='stretch')
    else:
        st.info("posts.csv not found — post-level charts unavailable.")


# ---------------------------------------------------------------------------
# PAGE: Regex vs Transformer
# ---------------------------------------------------------------------------
elif page == "🔍 Regex vs Transformer":
    st.title("Regex vs. Transformer Classification")
    st.caption(
        "Comparing the existing regex-based comment classifier against a transformer-based "
        "sentiment model."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Regex Classifier Distribution")
        regex_counts = comparison_df['regex_label'].value_counts().reset_index()
        regex_counts.columns = ['label', 'count']
        fig = px.pie(
            regex_counts, names='label', values='count', hole=0.55,
            color='label', color_discrete_map=REGEX_COLOR_MAP,
            template=PLOTLY_TEMPLATE,
        )
        fig.update_traces(textinfo='percent+label')
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=360, showlegend=False)
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.subheader("Transformer Sentiment Distribution")
        sentiment_counts = comparison_df['transformer_sentiment'].value_counts().reset_index()
        sentiment_counts.columns = ['sentiment', 'count']
        fig = px.pie(
            sentiment_counts, names='sentiment', values='count', hole=0.55,
            color='sentiment', color_discrete_map=SENTIMENT_COLOR_MAP,
            template=PLOTLY_TEMPLATE,
        )
        fig.update_traces(textinfo='percent+label')
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=360, showlegend=False)
        st.plotly_chart(fig, width='stretch')

    st.divider()

    st.subheader("Where They Disagree: Regex Label × Transformer Sentiment")
    cross_tab = comparison_df.groupby(['regex_label', 'transformer_sentiment']).size().reset_index(name='count')
    fig = px.bar(
        cross_tab, x='regex_label', y='count', color='transformer_sentiment',
        barmode='group', color_discrete_map=SENTIMENT_COLOR_MAP,
        template=PLOTLY_TEMPLATE,
        labels={'regex_label': 'Regex Label', 'count': 'Number of Comments', 'transformer_sentiment': 'Transformer Sentiment'},
    )
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=400)
    st.plotly_chart(fig, width='stretch')

    st.divider()

    st.subheader("Transformer Confidence Distribution")
    fig = px.histogram(
        comparison_df, x='transformer_confidence', color='transformer_sentiment',
        nbins=20, color_discrete_map=SENTIMENT_COLOR_MAP, barmode='overlay',
        opacity=0.7, template=PLOTLY_TEMPLATE,
        labels={'transformer_confidence': 'Confidence Score'},
    )
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=380)
    st.plotly_chart(fig, width='stretch')


# ---------------------------------------------------------------------------
# PAGE: Disagreements
# ---------------------------------------------------------------------------
elif page == "⚠️ Disagreements":
    st.title("Flagged Disagreements")
    st.caption("Comments where the regex classifier and transformer model disagreed.")

    if disagreements_df.empty:
        st.info("No disagreements found between the regex classifier and the transformer model.")
    else:
        m1, m2 = st.columns(2)
        m1.metric("Total Disagreements", f"{len(disagreements_df):,}")
        m2.metric(
            "Share of All Comments",
            f"{round(len(disagreements_df) / len(comparison_df) * 100, 2)}%"
        )

        st.subheader("Disagreement Reason Breakdown")
        reason_counts = disagreements_df['disagreement_reason'].value_counts().reset_index()
        reason_counts.columns = ['reason', 'count']
        fig = px.bar(
            reason_counts, x='count', y='reason', orientation='h',
            color='reason', color_discrete_sequence=[COLOR_PRIMARY, COLOR_ACCENT],
            template=PLOTLY_TEMPLATE,
        )
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=280, showlegend=False,
                           yaxis_title="", xaxis_title="Number of Comments")
        st.plotly_chart(fig, width='stretch')

        st.divider()
        st.subheader("Browse Flagged Comments")

        search_col, reason_col = st.columns([2, 1])
        with search_col:
            search_term = st.text_input("Search comment text", "")
        with reason_col:
            reason_options = ["All"] + sorted(disagreements_df['disagreement_reason'].unique().tolist())
            selected_reason = st.selectbox("Filter by reason", reason_options)

        filtered_df = disagreements_df
        if search_term:
            filtered_df = filtered_df[
                filtered_df['comment_text'].str.contains(search_term, case=False, na=False)
            ]
        if selected_reason != "All":
            filtered_df = filtered_df[filtered_df['disagreement_reason'] == selected_reason]

        st.dataframe(
            filtered_df[[
                'comment_text', 'regex_label', 'transformer_sentiment',
                'transformer_confidence', 'disagreement_reason'
            ]],
            width='stretch',
            height=400,
        )
        st.caption(f"Showing {len(filtered_df)} of {len(disagreements_df)} flagged disagreements")


# ---------------------------------------------------------------------------
# PAGE: Creators & EQS
# ---------------------------------------------------------------------------
elif page == "👤 Creators & EQS":
    st.title("Creators & Engagement Quality Score")
    st.caption("Original EQS vs. sentiment-adjusted EQS, and per-creator sentiment breakdown.")

    if creators_df is not None and not creators_df.empty:
        st.subheader("EQS Range per Creator (Best / Avg / Worst)")
        fig = go.Figure()
        for _, row in creators_df.iterrows():
            fig.add_trace(go.Scatter(
                x=[row['creator_handle'], row['creator_handle']],
                y=[row['worst_EQS'], row['best_EQS']],
                mode='lines',
                line=dict(color=COLOR_NEUTRAL, width=3),
                showlegend=False,
                hoverinfo='skip',
            ))
        fig.add_trace(go.Scatter(
            x=creators_df['creator_handle'], y=creators_df['avg_EQS'],
            mode='markers', marker=dict(color=COLOR_PRIMARY, size=14, symbol='diamond'),
            name='Average EQS',
        ))
        fig.add_trace(go.Scatter(
            x=creators_df['creator_handle'], y=creators_df['best_EQS'],
            mode='markers', marker=dict(color=COLOR_POSITIVE, size=10),
            name='Best EQS',
        ))
        fig.add_trace(go.Scatter(
            x=creators_df['creator_handle'], y=creators_df['worst_EQS'],
            mode='markers', marker=dict(color=COLOR_NEGATIVE, size=10),
            name='Worst EQS',
        ))
        fig.update_layout(
            template=PLOTLY_TEMPLATE, height=380,
            margin=dict(t=10, b=10, l=10, r=10),
            yaxis_title="EQS", xaxis_title="",
        )
        st.plotly_chart(fig, width='stretch')

    st.divider()

    if creators_eqs_df is None:
        st.warning(
            f"Could not find {CREATORS_EQS_CSV}. Run `python src/build_sentiment_eqs.py` "
            f"(after run_comparison.py) to generate this data."
        )
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Original vs. Sentiment-Adjusted EQS")
            eqs_melted = creators_eqs_df.melt(
                id_vars='creator_handle',
                value_vars=['original_eqs', 'sentiment_adjusted_eqs'],
                var_name='eqs_type', value_name='score'
            )
            eqs_melted['eqs_type'] = eqs_melted['eqs_type'].map({
                'original_eqs': 'Original EQS', 'sentiment_adjusted_eqs': 'Sentiment-Adjusted EQS'
            })
            fig = px.bar(
                eqs_melted, x='creator_handle', y='score', color='eqs_type',
                barmode='group', color_discrete_sequence=[COLOR_NEUTRAL, COLOR_PRIMARY],
                template=PLOTLY_TEMPLATE,
                labels={'creator_handle': '', 'score': 'EQS', 'eqs_type': ''},
            )
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=380)
            st.plotly_chart(fig, width='stretch')

        with col2:
            st.subheader("Sentiment Mix per Creator")
            sentiment_melted = creators_eqs_df.melt(
                id_vars='creator_handle',
                value_vars=['positive_pct', 'negative_pct', 'neutral_pct'],
                var_name='sentiment', value_name='percentage'
            )
            sentiment_melted['sentiment'] = sentiment_melted['sentiment'].str.replace('_pct', '')
            fig = px.bar(
                sentiment_melted, x='creator_handle', y='percentage', color='sentiment',
                barmode='stack', color_discrete_map=SENTIMENT_COLOR_MAP,
                template=PLOTLY_TEMPLATE,
                labels={'creator_handle': '', 'percentage': '% of Comments', 'sentiment': ''},
            )
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=380)
            st.plotly_chart(fig, width='stretch')

        st.divider()
        st.subheader("Full Creator Table")
        st.dataframe(
            creators_eqs_df[[
                'creator_handle', 'original_eqs', 'sentiment_adjusted_eqs',
                'positive_pct', 'negative_pct', 'neutral_pct'
            ]],
            width='stretch',
        )


# ---------------------------------------------------------------------------
# PAGE: Ask AI (natural language Q&A, text-to-SQL via Gemini)
# ---------------------------------------------------------------------------
elif page == "💬 Ask AI":
    st.title("Ask a Question About Your Data")
    st.caption(
        "Ask anything about posts, creators, sentiment comparisons, or EQS scores. "
        "Your question is turned into a SQL query behind the scenes."
    )

    if not os.path.isfile(ANALYTICS_DB):
        st.warning(
            f"Could not find {ANALYTICS_DB}. Run `python src/db_setup.py` first "
            f"to build the queryable database from your CSV outputs."
        )
    else:
        if "qa_history" not in st.session_state:
            st.session_state.qa_history = []
        if "qa_pending_question" not in st.session_state:
            st.session_state.qa_pending_question = ""

        EXAMPLE_QUESTIONS = [
            "Which creator has the highest sentiment-adjusted EQS?",
            "How many comments were flagged as disagreements between regex and transformer?",
            "What percentage of comments are positive vs negative?",
            "Which post has the highest total comments?",
            "What is the average EQS across all creators?",
        ]

        st.markdown("**Try an example question:**")
        example_cols = st.columns(len(EXAMPLE_QUESTIONS))
        for i, example_q in enumerate(EXAMPLE_QUESTIONS):
            with example_cols[i]:
                if st.button(example_q, key=f"example_btn_{i}", width='stretch'):
                    st.session_state.qa_pending_question = example_q

        question_input = st.text_input(
            "Your question",
            value=st.session_state.qa_pending_question,
            key="qa_question_input",
            placeholder="e.g. Which creator has the highest sentiment-adjusted EQS?",
        )

        submit_clicked = st.button("Ask", type="primary")

        if submit_clicked and question_input.strip():
            with st.spinner("Thinking..."):
                result = answer_question(question_input.strip())
            st.session_state.qa_history.insert(0, result)
            st.session_state.qa_pending_question = ""

        if st.session_state.qa_history:
            latest = st.session_state.qa_history[0]

            st.markdown("### Answer")
            st.success(latest['answer'])

            with st.expander("Show generated SQL and raw results"):
                st.code(latest['sql'], language="sql")
                st.dataframe(latest['raw_results'], width='stretch')

        if len(st.session_state.qa_history) > 1:
            st.markdown("---")
            st.markdown("**Session History**")
            history_container = st.container(height=300)
            with history_container:
                for past in st.session_state.qa_history[1:]:
                    st.markdown(f"**Q:** {past['question']}")
                    st.markdown(f"**A:** {past['answer']}")
                    st.markdown("---")
