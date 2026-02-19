import streamlit as st
import pandas as pd
import plotly.express as px
from api import get_monthly

st.title("📆 Monthly Wrapped")

data = get_monthly()


col1, col2, col3 = st.columns(3)
col1.metric("🔥 Top Artist", data["top_artist"])
col2.metric("🎵 Top Track", data["top_track"])
col3.metric("⏳ Total Minutes", data["total_minutes"])


df_artists = pd.DataFrame(data["artist_distribution"])

fig = px.pie(
    df_artists,
    names="artist",
    values="minutes",
    title="Artist Listening Distribution"
)

st.plotly_chart(fig, use_container_width=True)


df_weekly = pd.DataFrame(data["weekly_minutes"])

fig2 = px.line(
    df_weekly,
    x="week",
    y="minutes",
    title="Weekly Listening Trend"
)

st.plotly_chart(fig2, use_container_width=True)
