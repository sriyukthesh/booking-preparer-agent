import streamlit as st
from agent.db import get_traces

st.set_page_config(page_title="Agent Trace", layout="wide")
st.title("Step-by-Step Agent Trace Log")

session_id = st.session_state.get("session_id")
st.write(f"Tracing logic and evidence for session: **{session_id}**")

traces = get_traces(session_id)

if traces:
    header = st.columns([2, 1, 5])
    header[0].markdown("**Timestamp**")
    header[1].markdown("**Step**")
    header[2].markdown("**Message**")
    for trace in traces:
        row = st.columns([2, 1, 5])
        row[0].write(trace["timestamp"])
        row[1].write(trace["node_name"])
        row[2].write(trace["message"])

    st.subheader("Detailed Evidence Log")
    for t in traces:
        with st.expander(f"[{t['timestamp']}] {t['node_name'].upper()}: {t['message']}"):
            st.json(t['state_data'])
else:
    st.info("No traces found for this session.")