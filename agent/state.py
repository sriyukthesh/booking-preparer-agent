from typing import TypedDict, List, Dict, Any, Optional

class Passenger(TypedDict):
    name: str
    id_name: str
    age: int

class ItineraryOption(TypedDict):
    id: str
    type: str  # 'flight' or 'train'
    route: str
    departure: str
    arrival: str
    base_fare: float
    tax: float
    total_fare: float
    rules: str
    source_url: str
    retrieved_at: str

class FareBreakdown(TypedDict):
    base_fare: float
    tax: float
    fee: float
    total_per_pax: float
    overall_total: float

class BookingState(TypedDict):
    # Session & Case Metadata
    session_id: str
    test_case_id: Optional[str]
    
    # Input details from user
    raw_user_input: str
    route: str
    dates: str
    mode: str  # 'flight', 'train', or 'any'
    preferences: str
    passengers: List[Passenger]
    
    # Status flags & Messages
    status: str  # 'INTAKE', 'VALIDATING', 'BLOCKED', 'SEARCHING', 'PLANNING', 'UNCERTAIN', 'AWAITING_APPROVAL', 'APPROVED', 'REJECTED', 'FILLING', 'VERIFYING', 'PAYMENT_PENDING', 'COMPLETED'
    status_message: str
    missing_fields: List[str]
    
    # Search & Planning Results
    search_results: List[ItineraryOption]
    selected_option: Optional[ItineraryOption]
    plan_explanation: str
    fare_breakdown: Optional[FareBreakdown]
    
    # Execution Tracking
    draft_id: Optional[str]
    verified_total: Optional[float]
    approval_required_reason: Optional[str]
    
    # Recovery & Idempotency
    idempotency_key: Optional[str]
    existing_pnr: Optional[str]
    retry_count: int
    
    # Audit Trail
    trace_logs: List[Dict[str, Any]]