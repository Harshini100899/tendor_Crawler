"""
HFIP – Streamlit Dashboard
Four pages: Overview | Search | Opportunities | Analytics
Run: streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─── Path setup ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from database.models import Evaluation, Tender, get_engine, get_session_factory
from database.repository import TenderRepository


# ─── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="HFIP – Healthcare Funding Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #0078D4, #00BCF2);
    padding: 16px 20px;
    border-radius: 10px;
    color: white;
    text-align: center;
}
.metric-card h2 { margin: 0; font-size: 2.2rem; }
.metric-card p  { margin: 4px 0 0; font-size: 0.9rem; opacity: 0.9; }
.score-high   { color: #1b5e20; font-weight: bold; }
.score-medium { color: #e65100; font-weight: bold; }
.score-low    { color: #b71c1c; font-weight: bold; }
.tender-card  { border-left: 4px solid #0078D4; padding: 12px 16px; margin: 8px 0; background: #f8f9fa; border-radius: 0 8px 8px 0; }
</style>
""", unsafe_allow_html=True)


# ─── Database Connection ─────────────────────────────────────────────────────

@st.cache_resource
def get_repo() -> TenderRepository:
    db_path = os.getenv("DATABASE_PATH", str(ROOT / "data" / "hfip.db"))
    return TenderRepository(db_path=db_path)


# ─── Data Helpers ────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def load_tenders_df(source: str = "", keyword: str = "", min_score: int = 0) -> pd.DataFrame:
    repo = get_repo()
    with repo.session() as sess:
        q = sess.query(Tender, Evaluation).outerjoin(
            Evaluation, Tender.id == Evaluation.tender_id
        ).filter(Tender.is_archived == False)

        if source:
            q = q.filter(Tender.source == source)
        if keyword:
            kw = f"%{keyword}%"
            q = q.filter(Tender.title.ilike(kw) | Tender.description.ilike(kw))
        if min_score > 0:
            q = q.filter(Evaluation.score >= min_score)

        rows = q.order_by(Tender.created_at.desc()).limit(500).all()

    records = []
    for tender, evaluation in rows:
        deadline_str = tender.deadline.strftime("%d %b %Y") if tender.deadline else "—"
        pub_str = tender.published_date.strftime("%d %b %Y") if tender.published_date else "—"
        score = evaluation.score if evaluation else None
        records.append({
            "ID": tender.id,
            "Title": tender.title[:120],
            "Source": tender.source.upper(),
            "Organization": tender.organization or "—",
            "Country": tender.country or "—",
            "Deadline": deadline_str,
            "Published": pub_str,
            "Keyword Score": tender.keyword_score,
            "AI Score": score,
            "Category": evaluation.category if evaluation else "—",
            "Relevant": evaluation.relevant if evaluation else None,
            "Summary": evaluation.summary if evaluation else "Not evaluated yet",
            "Effort": evaluation.proposal_effort if evaluation else "—",
            "Consortium": "Yes" if (evaluation and evaluation.consortium_required) else "No",
            "URL": tender.url or "",
            "_deadline_raw": tender.deadline,
        })
    return pd.DataFrame(records)


@st.cache_data(ttl=300)
def load_stats() -> dict:
    repo = get_repo()
    return repo.count_tenders()


@st.cache_data(ttl=300)
def load_sources() -> list:
    repo = get_repo()
    return repo.get_top_sources()


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://img.icons8.com/color/96/medical-heart.png", width=60)
    st.markdown("## 🏥 HFIP")
    st.markdown("*Healthcare Funding Intelligence Platform*")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["📊 Overview", "🔍 Search", "🎯 Opportunities", "📈 Analytics"],
        index=0,
    )

    st.markdown("---")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.caption(f"Last refreshed: {datetime.now().strftime('%H:%M:%S')}")
    st.caption("HFIP v1.0.0")


# ─── Overview Page ───────────────────────────────────────────────────────────

if page == "📊 Overview":
    st.title("📊 Overview")
    st.markdown("*Real-time healthcare funding intelligence dashboard*")

    stats = load_stats()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
          <h2>{stats.get('total', 0)}</h2>
          <p>Total Tenders</p>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
          <h2>{stats.get('evaluated', 0)}</h2>
          <p>AI Evaluated</p>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
          <h2>{stats.get('relevant', 0)}</h2>
          <p>Relevant Opportunities</p>
        </div>""", unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
          <h2>{stats.get('high_score', 0)}</h2>
          <p>High Score (≥80)</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Source breakdown
    sources = load_sources()
    if sources:
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("📡 Tenders by Source")
            src_df = pd.DataFrame(sources)
            fig = px.pie(src_df, values="count", names="source", hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(height=300, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

    # Recent high-value opportunities
    st.subheader("🚨 Recent High-Value Opportunities (AI Score ≥ 80)")
    df = load_tenders_df(min_score=80)
    if df.empty:
        st.info("No high-scoring opportunities found yet. Run the pipeline to collect tenders.")
    else:
        for _, row in df.head(5).iterrows():
            score = row["AI Score"] or 0
            score_class = "score-high" if score >= 90 else ("score-medium" if score >= 75 else "score-low")
            url_link = f'<a href="{row["URL"]}" target="_blank">View →</a>' if row["URL"] else ""
            st.markdown(f"""
            <div class="tender-card">
              <strong>{row["Title"]}</strong><br>
              <span>🏢 {row["Organization"]} &nbsp;|&nbsp; 🌍 {row["Country"]} &nbsp;|&nbsp; 📡 {row["Source"]}</span><br>
              <span>📅 Deadline: <b>{row["Deadline"]}</b> &nbsp;|&nbsp; Score: <b class="{score_class}">{score}/100</b> &nbsp;|&nbsp; {url_link}</span><br>
              <small style="color:#555">{row["Summary"][:200]}</small>
            </div>""", unsafe_allow_html=True)


# ─── Search Page ─────────────────────────────────────────────────────────────

elif page == "🔍 Search":
    st.title("🔍 Search Tenders")

    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        keyword = st.text_input("🔎 Keyword search (title, description, organization)", placeholder="e.g. clinical decision support")
    with col2:
        source_filter = st.selectbox("Source", ["All", "TED", "BUND", "GBA", "BMFTR"])
    with col3:
        min_score = st.number_input("Min AI Score", min_value=0, max_value=100, value=0, step=10)

    source_val = "" if source_filter == "All" else source_filter.lower()
    df = load_tenders_df(source=source_val, keyword=keyword, min_score=int(min_score))

    st.markdown(f"**{len(df)} results found**")

    if not df.empty:
        display_cols = ["Title", "Source", "Organization", "Country", "Deadline", "AI Score", "Category", "URL"]
        display_df = df[display_cols].copy()
        st.dataframe(
            display_df,
            use_container_width=True,
            height=500,
            column_config={
                "URL": st.column_config.LinkColumn("Link"),
                "AI Score": st.column_config.NumberColumn("AI Score", format="%d/100"),
            },
        )
    else:
        st.info("No tenders found matching your criteria.")


# ─── Opportunities Page ──────────────────────────────────────────────────────

elif page == "🎯 Opportunities":
    st.title("🎯 Top Healthcare AI Opportunities")

    col1, col2 = st.columns(2)
    with col1:
        score_threshold = st.slider("Minimum AI Score", 0, 100, 70)
    with col2:
        category_options = [
            "All Categories", "Healthcare AI", "Digital Health", "Medical Imaging",
            "Health Data & Interoperability", "Biomedical Research", "Health Informatics", "Other Health",
        ]
        cat_filter = st.selectbox("Category", category_options)

    df = load_tenders_df(min_score=score_threshold)

    if cat_filter != "All Categories":
        df = df[df["Category"] == cat_filter]

    if df.empty:
        st.info("No opportunities match the selected filters.")
    else:
        st.markdown(f"**{len(df)} opportunities**")
        for _, row in df.iterrows():
            score = row["AI Score"] or 0
            with st.expander(f"⭐ [{score}/100] {row['Title']}", expanded=False):
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Source", row["Source"])
                col_b.metric("AI Score", f"{score}/100")
                col_c.metric("Deadline", row["Deadline"])

                st.markdown(f"**Organization:** {row['Organization']}  &nbsp;|&nbsp;  **Country:** {row['Country']}")
                st.markdown(f"**Category:** `{row['Category']}`  &nbsp;|&nbsp;  **Effort:** `{row['Effort']}`  &nbsp;|&nbsp;  **Consortium:** `{row['Consortium']}`")
                st.markdown("**Summary:**")
                st.info(row["Summary"])
                if row["URL"]:
                    st.markdown(f"[🔗 View Original Tender]({row['URL']})")


# ─── Analytics Page ──────────────────────────────────────────────────────────

elif page == "📈 Analytics":
    st.title("📈 Analytics & Trends")

    df = load_tenders_df()

    if df.empty:
        st.info("No data available yet. Run the pipeline to collect tenders.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏷️ Top Categories")
            cat_df = df[df["Category"] != "—"]["Category"].value_counts().reset_index()
            cat_df.columns = ["Category", "Count"]
            fig = px.bar(cat_df, x="Count", y="Category", orientation="h",
                         color="Count", color_continuous_scale="Blues")
            fig.update_layout(height=350, yaxis={"categoryorder": "total ascending"}, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("📡 Sources Distribution")
            src_df = df["Source"].value_counts().reset_index()
            src_df.columns = ["Source", "Count"]
            fig2 = px.bar(src_df, x="Source", y="Count", color="Source",
                          color_discrete_sequence=px.colors.qualitative.Pastel)
            fig2.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        col3, col4 = st.columns(2)

        with col3:
            st.subheader("⭐ AI Score Distribution")
            scored = df[df["AI Score"].notna()]
            if not scored.empty:
                fig3 = px.histogram(scored, x="AI Score", nbins=20,
                                    color_discrete_sequence=["#0078D4"])
                fig3.add_vline(x=80, line_dash="dash", line_color="red", annotation_text="Alert Threshold")
                fig3.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig3, use_container_width=True)

        with col4:
            st.subheader("📅 Upcoming Deadlines (Relevant)")
            deadline_df = df[(df["Relevant"] == True) & (df["_deadline_raw"].notna())].copy()
            if not deadline_df.empty:
                deadline_df = deadline_df.sort_values("_deadline_raw").head(10)
                fig4 = px.bar(
                    deadline_df,
                    x="Deadline",
                    y="AI Score",
                    color="Source",
                    hover_data=["Title"],
                    text="AI Score",
                )
                fig4.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("No upcoming deadlines for relevant tenders.")

        st.markdown("---")
        st.subheader("🏢 Top Funding Organizations")
        org_df = df[df["Organization"] != "—"]["Organization"].value_counts().head(10).reset_index()
        org_df.columns = ["Organization", "Count"]
        st.dataframe(org_df, use_container_width=True, hide_index=True)
