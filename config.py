import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Adapter Configuration for the Mock Travel Site
SITE_CONFIG = {
    "base_url": BASE_URL,
    "search_url": f"{BASE_URL}/search",
    "book_url": f"{BASE_URL}/book",
    "verify_url_pattern": f"{BASE_URL}/verify/{{draft_id}}",
    "pay_url_pattern": f"{BASE_URL}/pay/{{draft_id}}",
    "history_url": f"{BASE_URL}/history",
    "admin_config_url": f"{BASE_URL}/admin/config",
    
    # CSS Selectors for BeautifulSoup
    "selectors": {
        "search_item": ".search-result-item",
        "item_id": ".item-id",
        "route": ".item-route",
        "item_type": ".item-type",
        "departure": ".item-departure",
        "arrival": ".item-arrival",
        "base_fare": ".item-base-fare",
        "tax": ".item-tax",
        "rules": ".item-rules",
        "verify_base": "#verify-base-fare",
        "verify_tax": "#verify-tax",
        "verify_total": "#verify-total",
        "history_row": ".history-row",
        "history_pnr": ".history-pnr",
        "history_status": ".history-status",
        "history_route": ".history-route",
        "history_type": ".history-type",
        "history_departure": ".history-departure",
        "history_arrival": ".history-arrival"
    }
}