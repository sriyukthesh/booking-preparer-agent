import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Any, Optional
from config import SITE_CONFIG


class TravelSiteScraper:
    def __init__(self):
        self.config = SITE_CONFIG
        self.session = requests.Session()

    def search_inventory(self, route: str, mode: str) -> list[dict[str, Any]]:
        """Scrape inventory options from mock site search endpoint."""
        url = f"{self.config['search_url']}?route={route}&mode={mode}"
        resp = self.session.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        retrieved_at = datetime.now().isoformat()
        selectors = self.config["selectors"]

        items = soup.select(selectors["search_item"])
        for item in items:
            try:
                item_id = item.select_one(selectors["item_id"]).text.strip()
                item_type = item.select_one(selectors["item_type"]).text.strip()
                item_route = item.select_one(selectors["route"]).text.strip()
                departure = item.select_one(selectors["departure"]).text.strip()
                arrival = item.select_one(selectors["arrival"]).text.strip()
                base_fare = float(item.select_one(selectors["base_fare"]).text.strip())
                tax = float(item.select_one(selectors["tax"]).text.strip())
                rules = item.select_one(selectors["rules"]).text.strip()

                results.append({
                    "id": item_id,
                    "type": item_type,
                    "route": item_route,
                    "departure": departure,
                    "arrival": arrival,
                    "base_fare": base_fare,
                    "tax": tax,
                    "total_fare": base_fare + tax,
                    "rules": rules,
                    "source_url": url,
                    "retrieved_at": retrieved_at,
                })
            except (AttributeError, ValueError, TypeError):
                # Skip malformed items instead of crashing
                continue

        return results

    def fill_passenger_details(
        self, item_id: str, passengers: list[dict[str, Any]]
    ) -> Optional[str]:
        """Submit passenger form to mock site and return draft ID."""
        url = f"{self.config['book_url']}/{item_id}"
        form_data = {"pax_count": len(passengers)}

        for idx, pax in enumerate(passengers):
            form_data[f"pax_name_{idx}"] = pax.get("name", "")
            form_data[f"pax_age_{idx}"] = pax.get("age", 30)

        resp = self.session.post(url, data=form_data, allow_redirects=True)

        # Draft ID is in redirected URL (/verify/<draft_id>)
        if "/verify/" in resp.url:
            draft_id = resp.url.split("/verify/")[-1].split("?")[0]
            return draft_id
        return None

    def verify_booking(self, draft_id: str) -> dict[str, Any]:
        """Re-read booking draft page independently to check fare breakdown."""
        url = self.config["verify_url_pattern"].format(draft_id=draft_id)
        resp = self.session.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        selectors = self.config["selectors"]

        base_fare = float(soup.select_one(selectors["verify_base"]).text.strip())
        tax = float(soup.select_one(selectors["verify_tax"]).text.strip())
        total = float(soup.select_one(selectors["verify_total"]).text.strip())

        return {
            "draft_id": draft_id,
            "base_fare": base_fare,
            "tax": tax,
            "total": total,
            "verified_url": url,
            "timestamp": datetime.now().isoformat(),
        }

    def check_booking_history(self) -> list[dict[str, Any]]:
        """Scrape site booking history to see if a booking was confirmed."""
        url = self.config["history_url"]
        resp = self.session.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        bookings = []
        rows = soup.select(self.config["selectors"]["history_row"])

        for r in rows:
            try:
                pnr = r.select_one(self.config["selectors"]["history_pnr"]).text.strip()
                status = r.select_one(self.config["selectors"]["history_status"]).text.strip()
                bookings.append({
                    "pnr": pnr,
                    "route": r.select_one(self.config["selectors"]["history_route"]).text.strip(),
                    "type": r.select_one(self.config["selectors"]["history_type"]).text.strip(),
                    "departure": r.select_one(self.config["selectors"]["history_departure"]).text.strip(),
                    "arrival": r.select_one(self.config["selectors"]["history_arrival"]).text.strip(),
                    "status": status,
                })
            except AttributeError:
                continue

        return bookings

    def set_admin_config(
        self, fare_increase: bool = False, payment_pending: bool = False
    ):
        """Update mock site flags for testing cases TC3 and TC4."""
        url = self.config["admin_config_url"]
        self.session.post(
            url,
            json={
                "fare_increase_active": fare_increase,
                "payment_pending_active": payment_pending,
            },
        )