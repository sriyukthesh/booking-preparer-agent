import os
import sys
import json
import uuid
import threading
from urllib.parse import urlsplit

# Ensure parent dir is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.state import BookingState
from agent.graph import build_graph, build_resume_graph
from agent.scraper import TravelSiteScraper
from agent.db import save_test_result
from config import BASE_URL
from mock_site.app import app as mock_site_app
from werkzeug.serving import make_server

scraper = TravelSiteScraper()

def execute_full_run(state: BookingState, approve: bool = True):
    graph = build_graph()
    resume_graph = build_resume_graph()
    
    # Phase 1
    for output in graph.stream(state):
        for state_update in output.values():
            state.update(state_update)
            
    if state["status"] == "AWAITING_APPROVAL" and approve:
        state["status"] = "APPROVED"
        # Phase 2
        for output in resume_graph.stream(state):
            for state_update in output.values():
                state.update(state_update)
                
    return state

def run_tests():
    results = []
    
    print("Resetting mock site config...")
    scraper.set_admin_config(fare_increase=False, payment_pending=False)

    print("\n--- Running TC1: Approved Normal Trip ---")
    state1 = BookingState(
        session_id=str(uuid.uuid4()), test_case_id="TC1", status="INTAKE",
        raw_user_input="Flight HYD to DEL on 2026-04-15. Passengers: NAME: Alice, ID: Alice, Age 30. NAME: Bob, ID: Bob, Age 30. Cheapest.",
        route="", dates="", mode="any", preferences="none", passengers=[], missing_fields=[], search_results=[],
        selected_option=None, plan_explanation="", fare_breakdown=None, draft_id=None, verified_total=None,
        approval_required_reason=None, idempotency_key=None, existing_pnr=None, retry_count=0, trace_logs=[]
    )
    final1 = execute_full_run(state1, approve=True)
    res1 = {"TC": "TC1", "Expected": "COMPLETED", "Actual": final1["status"], "Pass": final1["status"] == "COMPLETED"}
    results.append(res1)
    save_test_result("TC1", res1["Expected"], res1["Actual"], str(res1["Pass"]), final1)
    print(f"TC1 PASS: {res1['Pass']}")

    print("\n--- Running TC2: ID Mismatch ---")
    state2 = BookingState(
        session_id=str(uuid.uuid4()), test_case_id="TC2", status="INTAKE",
        raw_user_input="Flight HYD to DEL. Passenger: NAME: Alice, ID: Alicia, Age 30.",
        route="", dates="", mode="any", preferences="none", passengers=[], missing_fields=[], search_results=[],
        selected_option=None, plan_explanation="", fare_breakdown=None, draft_id=None, verified_total=None,
        approval_required_reason=None, idempotency_key=None, existing_pnr=None, retry_count=0, trace_logs=[]
    )
    final2 = execute_full_run(state2, approve=True)
    res2 = {"TC": "TC2", "Expected": "BLOCKED", "Actual": final2["status"], "Pass": final2["status"] == "BLOCKED"}
    results.append(res2)
    save_test_result("TC2", res2["Expected"], res2["Actual"], str(res2["Pass"]), final2)
    print(f"TC2 PASS: {res2['Pass']}")

    print("\n--- Running TC3: Fare Increase Before Payment ---")
    scraper.set_admin_config(fare_increase=True, payment_pending=False)
    state3 = BookingState(
        session_id=str(uuid.uuid4()), test_case_id="TC3", status="INTAKE",
        raw_user_input="Flight HYD to DEL. Passengers: NAME: Alice, ID: Alice, Age 30.",
        route="", dates="", mode="any", preferences="none", passengers=[], missing_fields=[], search_results=[],
        selected_option=None, plan_explanation="", fare_breakdown=None, draft_id=None, verified_total=None,
        approval_required_reason=None, idempotency_key=None, existing_pnr=None, retry_count=0, trace_logs=[]
    )
    final3 = execute_full_run(state3, approve=True)
    res3 = {"TC": "TC3", "Expected": "AWAITING_APPROVAL", "Actual": final3["status"], "Pass": "fare increased" in str(final3.get("approval_required_reason", "")).lower()}
    results.append(res3)
    save_test_result("TC3", res3["Expected"], res3["Actual"], str(res3["Pass"]), final3)
    print(f"TC3 PASS: {res3['Pass']}")

    print("\n--- Running TC4: Payment Pending / Idempotency ---")
    scraper.set_admin_config(fare_increase=False, payment_pending=True)
    # Mocking that payment was attempted by manually triggering the mock site endpoint,
    # but since no PNR is returned, the agent recovery node will check history.
    state4 = BookingState(
        session_id=str(uuid.uuid4()), test_case_id="TC4", status="INTAKE",
        raw_user_input="Flight HYD to DEL. Passengers: NAME: Alice, ID: Alice, Age 30.",
        route="", dates="", mode="any", preferences="none", passengers=[], missing_fields=[], search_results=[],
        selected_option=None, plan_explanation="", fare_breakdown=None, draft_id=None, verified_total=None,
        approval_required_reason=None, idempotency_key=None, existing_pnr=None, retry_count=0, trace_logs=[]
    )
    # First run creates the idempotency key and hits pending
    final4_run1 = execute_full_run(state4, approve=True)
    
    # Second run simulates user retrying payment
    final4_run2 = execute_full_run(final4_run1, approve=True)
    pass4 = final4_run2["status"] == "COMPLETED" or final4_run2["status"] == "PAYMENT_PENDING"
    res4 = {"TC": "TC4", "Expected": "Handled Idempotency", "Actual": final4_run2["status"], "Pass": pass4}
    results.append(res4)
    save_test_result("TC4", res4["Expected"], res4["Actual"], str(res4["Pass"]), final4_run2)
    print(f"TC4 PASS: {res4['Pass']}")

    # Write out JSON report
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=4)
        
    # Write out MD report
    with open("test_results_report.md", "w") as f:
        f.write("# Agent Test Results\n")
        for r in results:
            f.write(f"- **{r['TC']}**: Expected={r['Expected']}, Actual={r['Actual']} -> **PASS={r['Pass']}**\n")
            
    print("\nReports written to test_results.json and test_results_report.md")

if __name__ == "__main__":
    parsed_url = urlsplit(BASE_URL)
    host = parsed_url.hostname or "127.0.0.1"
    port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
    server = None
    server_thread = None
    try:
        import requests

        try:
            requests.get(BASE_URL, timeout=1).raise_for_status()
        except requests.RequestException:
            server = make_server(host, port, mock_site_app)
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()
        run_tests()
    finally:
        if server is not None:
            server.shutdown()
            server_thread.join(timeout=5)