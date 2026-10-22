# Agent Architecture

## Overview
The architecture is built on a **State Machine via LangGraph** to maintain explicit control over the agent's actions, ensuring deterministic human-in-the-loop capabilities. 

## Stack
- **Orchestration**: LangGraph (Explicit DAG node transitions)
- **Intelligence**: Gemini 2.5 Flash via `google-genai` SDK (JSON extraction, option reasoning)
- **Interaction**: BeautifulSoup & Requests (Site interaction adapter)
- **UI & State Display**: Streamlit
- **Persistence**: SQLite (Trace logs, Idempotency DB, test results)

## Graph Nodes & Workflow
1. **Intake**: Gemini parses natural text/audio transcripts into structured JSON.
2. **Validate**: Rule-based node that blocks execution if ID spelling mismatches.
3. **Search**: Action node that interfaces with the Mock API adapter to retrieve HTML.
4. **Plan**: Gemini analyzes fares and rules against user preferences (cheapest, fastest).
5. **Approval Gate (Interrupt)**: Execution halts. Awaits UI intervention.
6. **Fill Details**: Submits the POST form with passenger arrays.
7. **Verify**: Independently parses the verification page to ensure no hidden fees were injected.
8. **Payment Recovery**: Idempotent checkpoint evaluating SQLite and remote site history to prevent double-booking.