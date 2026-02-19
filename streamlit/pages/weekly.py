import streamlit as st
import pandas as pd
from api import get_monthly
from components.charts import generate_visualizations

st.title("Monthly Wrapped")

data = get_monthly()

st.markdown("Monthly Listening Summary")

col1, col2, col3 = st.columns(3)

col1.metric("Total Minutes", data["total_minutes"])
col2.metric("Average Per Week", data["average_per_week"])
col3.metric("Average Per Day", data["average_per_day"])

df = pd.DataFrame(data["weekly_minutes"])

generate_visualizations(
    df,
    x_col="week",
    y_col="minutes",
    title_prefix="Monthly Listening"
)
