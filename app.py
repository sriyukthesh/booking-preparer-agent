import streamlit as st
import threading
import time
import requests
import uuid
from mock_site.app import app as flask_app
from agent.db import init_db

# Initialize database
init_db()

# Start the Flask mock site automatically in a background thread
if "flask_started" not in st.session_state:
    def run_flask():
        flask_app.run(port=5000, use_reloader=False, threaded=True)
    
    try:
        # Check if already running
        requests.get("http://127.0.0.1:5000/")
        st.session_state["flask_started"] = True
    except requests.ConnectionError:
        t = threading.Thread(target=run_flask, daemon=True)
        t.start()
        time.sleep(1.5)  # Wait for Flask to boot
        st.session_state["flask_started"] = True

# Initialize Agent Session State
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())

if "agent_state" not in st.session_state:
    st.session_state["agent_state"] = {
        "session_id": st.session_state["session_id"],
        "test_case_id": None,
        "raw_user_input": "",
        "route": "",
        "dates": "",
        "mode": "any",
        "preferences": "none",
        "passengers": [],
        "status": "INTAKE",
        "status_message": "Ready to plan your trip.",
        "missing_fields": [],
        "search_results": [],
        "selected_option": None,
        "plan_explanation": "",
        "fare_breakdown": None,
        "draft_id": None,
        "verified_total": None,
        "approval_required_reason": None,
        "idempotency_key": None,
        "existing_pnr": None,
        "retry_count": 0,
        "trace_logs": []
    }

st.set_page_config(page_title="Booking Preparer AI", layout="wide")

st.title("Train & Flight Booking Preparer")
st.markdown("Welcome to the Agentic AI Hackathon 2026 solution for Commerce & Consumer AI.")
st.markdown("👈 **Select a page from the sidebar to begin.**")
st.info(f"🟢 Mock Travel Site is running at http://127.0.0.1:5000 | Current Session: {st.session_state['session_id']}")