# Solution & Agent Workflow

Our solution strictly enforces the "Agent Preparer, Human Payer" paradigm required by the hackathon. 

By designing the agent as a LangGraph DAG, we broke down a traditionally black-box LLM operation into 8 transparent, verifiable nodes. Every node writes to an immutable SQLite trace log, which the UI visualizes to build user trust. 

**Core Innovations:**
1. **The Verification Node**: Before handing the final payment link to the user, the agent independently reads the final checkout DOM. If the total fare differs from the planned fare (e.g., dynamic pricing surge), it automatically reroutes the user back to the Approval Gate (Test Case 3).
2. **Idempotency & Recovery Engine**: If a user's network drops during payment (Test Case 4), the agent intercepts any retry request. It cross-references an internal SQLite token with the travel site's Booking History HTML table. If a PNR exists, it halts duplicate execution, ensuring safe financial boundaries. 
3. **Graceful Fallbacks**: The agent implements Regex fallbacks if Gemini API rate-limits are hit, ensuring the UX never completely breaks.