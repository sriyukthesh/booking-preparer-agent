import streamlit as st

st.set_page_config(page_title="Architecture", layout="wide")
st.title("Agent Architecture Diagram")

mermaid_code = """
```mermaid
stateDiagram-v2
    [*] --> Intake
    Intake --> Validate : Extracted JSON
    Validate --> Blocked : ID Mismatch (TC2)
    Validate --> Search : IDs Valid
    Search --> Plan : Scraped HTML Data
    Plan --> ApprovalGate : Awaiting Human
    
    ApprovalGate --> FillDetails : Approved (TC1)
    ApprovalGate --> [*] : Rejected
    
    FillDetails --> Verify : Form Draft ID
    Verify --> ApprovalGate : Fare Changed! (TC3)
    Verify --> PaymentRecovery : Fare Verified
    
    PaymentRecovery --> [*] : Local DB Idempotency Key Exists
    PaymentRecovery --> [*] : Site History Check Confirmed (TC4)
    PaymentRecovery --> UserPays : No PNR (Proceed to Pay)
    UserPays --> [*]
"""

st.markdown(mermaid_code)