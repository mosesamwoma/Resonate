import streamlit as st

def load_css():
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.set_page_config(page_title="Resonate", layout="wide")

st.title("Welcome to Resonate!")

query_params = st.query_params

if "token" in query_params:
    st.session_state["token"] = query_params["token"]
    st.query_params.clear() 
    st.rerun()

if "token" not in st.session_state:
    login_url = "http://127.0.0.1:8000/login/"
    st.markdown(f"[Login with Spotify]({login_url})")
    st.stop()

st.success("Logged in successfully! ✅")
st.balloons()
st.write("Select Weekly or Monthly from the sidebar.")
