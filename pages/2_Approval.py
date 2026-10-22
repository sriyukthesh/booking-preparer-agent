import streamlit as st
from agent.graph import (
    build_resume_graph,
)
from config import BASE_URL

st.set_page_config(page_title="Itinerary & Approval", layout="wide")
st.title("Itinerary and Fare Breakdown")

state = st.session_state.get("agent_state", {})

if state.get("status") not in ["AWAITING_APPROVAL", "PAYMENT_PENDING", "COMPLETED", "VERIFYING", "FILLING"]:
    st.info("No itinerary awaits approval right now. Please plan a trip first.")
    st.stop()

# --- TC3 Fare Change Alert ---
if state.get("approval_required_reason"):
    st.error(f"🚨 ALERT: {state['approval_required_reason']}")

# --- Itinerary Display ---
st.subheader("Selected Option")
opt = state.get("selected_option")
if opt:
    cols = st.columns(5)
    cols[0].metric("Route", opt['route'])
    cols[1].metric("Type", opt['type'].title())
    cols[2].metric("Departure", opt['departure'])
    cols[3].metric("Arrival", opt['arrival'])
    cols[4].metric("Rules", opt['rules'])

st.subheader("Fare Breakdown")
fare = state.get("fare_breakdown")
if fare:
    cols = st.columns(4)
    cols[0].metric("Base Fare (Per Pax)", f"₹{fare['base_fare']}")
    cols[1].metric("Tax (Per Pax)", f"₹{fare['tax']}")
    cols[2].metric("Total Per Pax", f"₹{fare['total_per_pax']}")
    cols[3].metric("Overall Total", f"₹{fare['overall_total']}")
    
st.write(f"**Agent Reasoning:** {state.get('plan_explanation')}")

# --- Action Buttons ---
st.divider()

if state.get("status") == "AWAITING_APPROVAL":
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Approve & Book", type="primary"):
            st.session_state["agent_state"]["status"] = "APPROVED"
            st.session_state["agent_state"]["approval_required_reason"] = None
            
            resume_graph = build_resume_graph()
            with st.spinner("Executing post-approval actions (Filling, Verifying)..."):
                for output in resume_graph.stream(st.session_state["agent_state"]):
                    for node_name, state_update in output.items():
                        st.session_state["agent_state"].update(state_update)
            st.rerun()
    with col2:
        if st.button("Reject"):
            st.session_state["agent_state"]["status"] = "REJECTED"
            st.warning("Booking Rejected.")

elif state.get("status") == "PAYMENT_PENDING":
    st.success("Verification successful! The agent has stopped as payment requires human action.")
    draft_id = state.get("draft_id")
    st.markdown(f"### [🔗 Click Here to Pay securely on the Mock Site]({BASE_URL}/verify/{draft_id})")
    
    if st.button("Simulate Payment Retry (Test Idempotency)"):
        resume_graph = build_resume_graph()
        with st.spinner("Checking recovery logic..."):
            for output in resume_graph.stream(st.session_state["agent_state"]):
                for node_name, state_update in output.items():
                    st.session_state["agent_state"].update(state_update)
        st.rerun()

elif state.get("status") == "COMPLETED":
    st.success(f"Booking Completed! Confirmed PNR: {state.get('existing_pnr')}")