import requests
import streamlit as st

BASE_URL = "http://127.0.0.1:8000"


def _headers():
    return {
        "Authorization": f"Bearer {st.session_state.get('token')}"
    }


def get_weekly():
    res = requests.get(f"{BASE_URL}/wrapped/weekly/", headers=_headers())
    return res.json()


def get_monthly():
    res = requests.get(f"{BASE_URL}/wrapped/monthly/", headers=_headers())
    return res.json()
