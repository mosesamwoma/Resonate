import streamlit as st
import plotly.express as px

def generate_visualizations(df, x_col, y_col, title_prefix):
    st.markdown(f"##  {title_prefix} Insights")

    col1, col2 = st.columns(2)

    fig_bar = px.bar(
        df,
        x=x_col,
        y=y_col,
        text=y_col,
        title=f"{title_prefix} - Bar Chart"
    )

    fig_line = px.line(
        df,
        x=x_col,
        y=y_col,
        markers=True,
        title=f"{title_prefix} - Trend Line"
    )

    with col1:
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.plotly_chart(fig_line, use_container_width=True)

    fig_pie = px.pie(
        df,
        names=x_col,
        values=y_col,
        title=f"{title_prefix} - Distribution"
    )

    st.plotly_chart(fig_pie, use_container_width=True)
