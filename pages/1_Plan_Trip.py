import streamlit as st
from agent.graph import build_graph

st.set_page_config(page_title="Plan a Trip", layout="wide")
st.title("Plan Your Trip")

st.markdown("""
Describe your trip details, including passengers. 
*Example: "I want a flight from HYD to DEL on 2026-04-15. Passenger: John Doe, ID: John Doe, Age: 30. Find the cheapest option."*
""")

input_text = st.text_area("Trip Details", height=100)
audio_file = st.file_uploader("Or upload an audio clip (Voice Input)", type=['wav', 'mp3', 'm4a'])

if st.button("Start Planning Agent", type="primary"):
    if not input_text and not audio_file:
        st.error("Please provide trip details via text or audio.")
        st.stop()
        
    # In a real app, send audio_file to Gemini for transcription here. 
    # For demo, we rely on the text input.
    user_input = input_text or "Audio transcription placeholder (HYD-DEL...)"
    
    st.session_state["agent_state"]["raw_user_input"] = user_input
    st.session_state["agent_state"]["status"] = "INTAKE"
    
    graph = build_graph()
    state = st.session_state["agent_state"]
    
    with st.spinner("Agent is planning your trip..."):
        # Run the initial phase of the graph (Intake -> Validate -> Search -> Plan -> Approval Gate)
        for output in graph.stream(state):
            for node_name, state_update in output.items():
                st.write(f"✅ Executed: **{node_name}**")
                st.session_state["agent_state"].update(state_update)
                
    final_status = st.session_state["agent_state"]["status"]
    
    if final_status == "AWAITING_APPROVAL":
        st.success("Planning complete! Head to the Approval page.")
        st.page_link("pages/2_Approval.py", label="Go to Approval Page", icon="➡️")
    elif final_status == "BLOCKED":
        st.error(f"Agent Blocked: {st.session_state['agent_state']['status_message']}")
    else:
        st.warning(f"Agent stopped with status: {final_status}")

with st.expander("Current Agent State Variables", expanded=False):
    st.json(st.session_state["agent_state"])