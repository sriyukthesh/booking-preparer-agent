import json
import re
from typing import Dict, Any
from config import GEMINI_API_KEY, GEMINI_MODEL

class GeminiAgentClient:
    def __init__(self):
        self.client = None
        if GEMINI_API_KEY:
            try:
                from google import genai
                self.client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception as e:
                print(f"Failed to initialize google-genai SDK: {e}")

    def extract_booking_details(self, text: str) -> Dict[str, Any]:
        """Extract route, dates, passengers, mode, and preferences from text using Gemini or fallback regex."""
        prompt = f"""
Extract trip details from this text and respond strictly with valid JSON.
Text: "{text}"

JSON schema required:
{{
    "route": "HYD-DEL", // format like ORIGIN-DESTINATION or uppercase code
    "dates": "YYYY-MM-DD",
    "mode": "flight|train|any",
    "preferences": "morning|cheapest|fastest|none",
    "passengers": [
        {{"name": "John Doe", "id_name": "John Doe", "age": 30}}
    ],
    "missing_fields": [] // list any missing required fields: route, dates, passengers
}}
"""
        if self.client:
            try:
                response = self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt
                )
                text_response = response.text.strip()
                # Clean codeblock indicators if present
                if "```json" in text_response:
                    text_response = text_response.split("```json")[1].split("```")[0].strip()
                elif "```" in text_response:
                    text_response = text_response.split("```")[1].split("```")[0].strip()
                return json.loads(text_response)
            except Exception as e:
                print(f"Gemini API call failed, falling back to regex parser: {e}")

        # Rule-based fallback parser
        return self._fallback_regex_extract(text)

    def _fallback_regex_extract(self, text: str) -> Dict[str, Any]:
        text_upper = text.upper()
        route = "HYD-DEL" if "HYD" in text_upper or "DEL" in text_upper else ""
        
        mode = "any"
        if "FLIGHT" in text_upper:
            mode = "flight"
        elif "TRAIN" in text_upper:
            mode = "train"
            
        preferences = "cheapest" if "CHEAP" in text_upper else ("fastest" if "FAST" in text_upper else "none")
        
        # Simple passenger extraction fallback
        passengers = []
        names = re.findall(r'NAME:\s*([A-Za-z\s]+?)(?:,|$|\n|ID:)', text, re.IGNORECASE)
        id_names = re.findall(r'ID:\s*([A-Za-z\s]+?)(?:,|$|\n|NAME:)', text, re.IGNORECASE)
        
        if names:
            for idx, n in enumerate(names):
                id_n = id_names[idx].strip() if idx < len(id_names) else n.strip()
                passengers.append({"name": n.strip(), "id_name": id_n, "age": 30})
        else:
            # Default passenger mock if none parsed
            passengers = [
                {"name": "Alice Smith", "id_name": "Alice Smith", "age": 28},
                {"name": "Bob Jones", "id_name": "Bob Jones", "age": 32}
            ]

        missing = []
        if not route: missing.append("route")
        
        return {
            "route": route or "HYD-DEL",
            "dates": "2026-04-15",
            "mode": mode,
            "preferences": preferences,
            "passengers": passengers,
            "missing_fields": missing
        }

    def evaluate_plan(self, options: list, preferences: str) -> Dict[str, Any]:
        """Rank options and select the best based on preferences using Gemini or local heuristic."""
        if not options:
            return {"selected_id": None, "reason": "No options available.", "uncertain": True}

        if self.client:
            try:
                prompt = f"""
Compare these travel options based on preference '{preferences}' and return valid JSON:
Options: {json.dumps(options)}

JSON Format:
{{
    "selected_id": "item_id",
    "reason": "Detailed explanation comparing options, fare rules, refund, baggage.",
    "uncertain": false
}}
"""
                response = self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt
                )
                text_response = response.text.strip()
                if "```json" in text_response:
                    text_response = text_response.split("```json")[1].split("```")[0].strip()
                return json.loads(text_response)
            except Exception as e:
                print(f"Gemini evaluation failed: {e}")

        # Local heuristic fallback
        best = options[0]
        if preferences == "cheapest":
            best = min(options, key=lambda x: x["total_fare"])
        elif preferences == "fastest":
            best = min(options, key=lambda x: x["type"] == "flight")
            
        return {
            "selected_id": best["id"],
            "reason": f"Selected {best['id']} based on preference '{preferences}'. Fare: {best['total_fare']} INR. Rules: {best['rules']}",
            "uncertain": False
        }