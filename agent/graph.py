from langgraph.graph import StateGraph, END
from agent.state import BookingState
from agent.gemini_client import GeminiAgentClient
from agent.scraper import TravelSiteScraper
from agent.db import log_trace, check_idempotency, set_idempotency

gemini_client = GeminiAgentClient()
scraper = TravelSiteScraper()

# --- NODE DEFINITIONS ---

def intake_node(state: BookingState) -> BookingState:
    """Node 1: Extract trip details from raw text/voice."""
    log_trace(state["session_id"], "intake", state, "Parsing user input text/audio...")
    extracted = gemini_client.extract_booking_details(state["raw_user_input"])
    
    state["route"] = extracted.get("route", "")
    state["dates"] = extracted.get("dates", "")
    state["mode"] = extracted.get("mode", "any")
    state["preferences"] = extracted.get("preferences", "none")
    if not state.get("passengers"):
        state["passengers"] = extracted.get("passengers", [])
        
    missing = extracted.get("missing_fields", [])
    if missing:
        state["status"] = "BLOCKED"
        state["missing_fields"] = missing
        state["status_message"] = f"Missing required fields: {', '.join(missing)}. Please provide them."
    else:
        state["status"] = "VALIDATING"
        state["status_message"] = "Intake complete. Proceeding to ID validation."
    
    return state

def validate_node(state: BookingState) -> BookingState:
    """Node 2: Verify passenger names against provided ID spellings."""
    log_trace(state["session_id"], "validate", state, "Validating passenger names against IDs...")
    
    mismatches = []
    for pax in state["passengers"]:
        name = pax.get("name", "").strip().lower()
        id_name = pax.get("id_name", "").strip().lower()
        if name != id_name:
            mismatches.append(f"Passenger '{pax.get('name')}' does not match ID spelling '{pax.get('id_name')}'")
            
    if mismatches:
        state["status"] = "BLOCKED"
        state["status_message"] = "VALIDATION FAILED: " + "; ".join(mismatches)
    else:
        state["status"] = "SEARCHING"
        state["status_message"] = "ID names validated successfully. Searching travel options."
        
    return state

def search_node(state: BookingState) -> BookingState:
    """Node 3: Scrape schedules and fares from travel site."""
    log_trace(state["session_id"], "search", state, "Scraping options from site...")
    
    options = scraper.search_inventory(state["route"], state["mode"])
    state["search_results"] = options
    
    if not options:
        state["status"] = "UNCERTAIN"
        state["status_message"] = f"No options found for route {state['route']} and mode {state['mode']}."
    else:
        state["status"] = "PLANNING"
        state["status_message"] = f"Found {len(options)} options. Evaluating plan."
        
    return state

def plan_node(state: BookingState) -> BookingState:
    """Node 4: Compare options, check fare rules, rank, and calculate overall fare."""
    log_trace(state["session_id"], "plan", state, "Comparing fare rules and ranking options...")
    
    eval_res = gemini_client.evaluate_plan(state["search_results"], state["preferences"])
    
    if eval_res.get("uncertain"):
        state["status"] = "UNCERTAIN"
        state["status_message"] = "Could not identify optimal option due to missing evidence."
        return state

    selected_id = eval_res.get("selected_id")
    selected = next((opt for opt in state["search_results"] if opt["id"] == selected_id), state["search_results"][0])
    
    state["selected_option"] = selected
    state["plan_explanation"] = eval_res.get("reason", "")
    
    pax_count = max(len(state["passengers"]), 1)
    base_fare = selected["base_fare"]
    tax = selected["tax"]
    total_per_pax = base_fare + tax
    overall_total = total_per_pax * pax_count
    
    state["fare_breakdown"] = {
        "base_fare": base_fare,
        "tax": tax,
        "fee": 0.0,
        "total_per_pax": total_per_pax,
        "overall_total": overall_total
    }
    
    state["status"] = "AWAITING_APPROVAL"
    state["status_message"] = "Itinerary planned. Awaiting human approval."
    return state

def approval_gate_node(state: BookingState) -> BookingState:
    """Node 5: Human Approval Gate."""
    log_trace(state["session_id"], "approval_gate", state, "Evaluating approval gate status...")
    # This node acts as a pass-through/checkpoint for status checking
    if state["status"] == "APPROVED":
        state["status_message"] = "Approval received. Proceeding to fill details."
    elif state["status"] == "REJECTED":
        state["status_message"] = "Booking rejected by human operator."
    else:
        state["status"] = "AWAITING_APPROVAL"
        state["status_message"] = "STOPPED: Human approval required to proceed."
    return state

def fill_details_node(state: BookingState) -> BookingState:
    """Node 6: Fill passenger details into travel site booking form."""
    log_trace(state["session_id"], "fill_details", state, "Submitting details to travel site form...")
    
    item_id = state["selected_option"]["id"]
    draft_id = scraper.fill_passenger_details(item_id, state["passengers"])
    
    if draft_id:
        state["draft_id"] = draft_id
        state["status"] = "VERIFYING"
        state["status_message"] = f"Details filled. Form draft generated with ID {draft_id}. Verifying draft."
    else:
        state["status"] = "UNCERTAIN"
        state["status_message"] = "Failed to create draft booking on site."
        
    return state

def verify_node(state: BookingState) -> BookingState:
    """Node 7: Re-read booking page independently and verify itinerary & total fare."""
    log_trace(state["session_id"], "verify", state, "Re-reading draft page independently...")
    
    draft_id = state["draft_id"]
    verification = scraper.verify_booking(draft_id)
    
    actual_total = verification["total"]
    expected_total = state["fare_breakdown"]["overall_total"]
    state["verified_total"] = actual_total
    
    # TC3: Detect fare rise
    if abs(actual_total - expected_total) > 0.01:
        log_trace(state["session_id"], "verify", state, f"FARE CHANGED: Expected {expected_total}, actual {actual_total}")
        state["approval_required_reason"] = f"Fare increased from {expected_total} INR to {actual_total} INR!"
        state["fare_breakdown"]["overall_total"] = actual_total
        state["status"] = "AWAITING_APPROVAL"
        state["status_message"] = f"RE-APPROVAL REQUIRED: Fare increased from {expected_total} to {actual_total} INR."
    else:
        state["status"] = "PAYMENT_PENDING"
        state["status_message"] = "Verification successful! Ready for user payment on site."
        
    return state

def payment_recovery_node(state: BookingState) -> BookingState:
    """Node 8: Idempotent payment recovery check for pending payments."""
    log_trace(state["session_id"], "payment_recovery", state, "Checking booking history before payment retry...")
    
    key = state.get("idempotency_key") or f"idempotency_{state['session_id']}"
    state["idempotency_key"] = key
    
    # 1. Check local DB idempotency key
    if check_idempotency(key):
        log_trace(state["session_id"], "payment_recovery", state, "Idempotency key found in local DB. Booking already processed.")
        state["status"] = "COMPLETED"
        state["status_message"] = "Existing booking found via local idempotency record. No duplicate attempt made."
        return state
        
    # 2. Check site booking history
    history = scraper.check_booking_history()
    confirmed = [b for b in history if b["status"] == "CONFIRMED"]
    
    if confirmed:
        pnr = confirmed[0]["pnr"]
        state["existing_pnr"] = pnr
        set_idempotency(key, "RECOVERY_CHECK", "CONFIRMED")
        state["status"] = "COMPLETED"
        state["status_message"] = f"Booking confirmed in site history with PNR {pnr}. Avoided duplicate booking!"
    else:
        set_idempotency(key, "RECOVERY_CHECK", "PENDING_RETRY")
        state["status"] = "PAYMENT_PENDING"
        state["status_message"] = "No confirmed booking found in site history. Safe to present payment page to user."
        
    return state

# --- LANGGRAPH WORKFLOW ROUTING ---

def route_after_intake(state: BookingState) -> str:
    if state["status"] == "BLOCKED":
        return END
    return "validate"

def route_after_validate(state: BookingState) -> str:
    if state["status"] == "BLOCKED":
        return END
    return "search"

def route_after_search(state: BookingState) -> str:
    if state["status"] == "UNCERTAIN":
        return END
    return "plan"

def route_after_plan(_: BookingState) -> str:
    return "approval_gate"

def route_after_approval(state: BookingState) -> str:
    if state["status"] == "APPROVED":
        return "fill_details"
    return END

def route_after_fill(state: BookingState) -> str:
    if state["status"] == "UNCERTAIN":
        return END
    return "verify"

def route_after_verify(state: BookingState) -> str:
    if state["status"] == "AWAITING_APPROVAL":
        return "approval_gate"
    return "payment_recovery"

def build_graph():
    workflow = StateGraph(BookingState)
    
    workflow.add_node("intake", intake_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("search", search_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("approval_gate", approval_gate_node)
    workflow.add_node("fill_details", fill_details_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("payment_recovery", payment_recovery_node)
    
    workflow.set_entry_point("intake")
    
    workflow.add_conditional_edges("intake", route_after_intake)
    workflow.add_conditional_edges("validate", route_after_validate)
    workflow.add_conditional_edges("search", route_after_search)
    workflow.add_conditional_edges("plan", route_after_plan)
    workflow.add_conditional_edges("approval_gate", route_after_approval)
    workflow.add_conditional_edges("fill_details", route_after_fill)
    workflow.add_conditional_edges("verify", route_after_verify)
    workflow.add_edge("payment_recovery", END)
    
    return workflow.compile()


def build_resume_graph():
    workflow = StateGraph(BookingState)
    workflow.add_node("approval_gate", approval_gate_node)
    workflow.add_node("fill_details", fill_details_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("payment_recovery", payment_recovery_node)
    workflow.set_entry_point("approval_gate")
    workflow.add_conditional_edges("approval_gate", route_after_approval)
    workflow.add_conditional_edges("fill_details", route_after_fill)
    workflow.add_conditional_edges("verify", route_after_verify)
    workflow.add_edge("payment_recovery", END)
    return workflow.compile()