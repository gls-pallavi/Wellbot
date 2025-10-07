import json
from pathlib import Path
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

KB_PATH = Path(__file__).parent.parent / "kb"    
DB_PATH = Path(__file__).parent.parent.parent / "backend" / "wellbot.db" 


class ActionFetchKB(Action):

    def name(self) -> Text:
        return "action_fetch_kb"

    def get_user_language(self, tracker: Tracker) -> str:
        """
        Always fetch language from DB first.
        Only fallback to slot or message detection if DB fails (shouldn't happen).
        """
        user_id = tracker.sender_id
        language = None
        conn = None
        try:
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT language FROM profiles WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row and row[0]:
                language = row[0].lower()
        except Exception as e:
            print(f"Error fetching language from DB: {e}")
        finally:
            if conn:
                conn.close()

        if not language:
            language = tracker.get_slot("language") 
        if not language:
            try:
                from langdetect import detect
                user_msg = tracker.latest_message.get("text", "")
                lang_code = detect(user_msg)
                language = "hi" if lang_code.startswith("hi") else "en"
            except:
                language = "en"

        language_map = {"english": "en", "hindi": "hi"}
        language = language_map.get(language.lower(), "en")
        return language

    def load_kb(self, intent: str) -> List[Dict[Text, Any]]:
        """Load KB entries for a given intent"""
        kb_file = KB_PATH / f"{intent}.json"
        if not kb_file.exists():
            print(f"[DEBUG] KB file not found: {kb_file}")
            return []
        with open(kb_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("entries", [])

    def match_entry(self, tracker: Tracker, entries: List[Dict[Text, Any]]) -> Dict[Text, Any]:
        """Match user entity with KB entry ID or keywords"""
        entities = tracker.latest_message.get("entities", [])
        entity_values = [e.get("value", "").lower() for e in entities]

        for entry in entries:
            entry_id = entry.get("id", "").lower()
            for ev in entity_values:
                if ev == entry_id:
                    return entry

        user_msg = tracker.latest_message.get("text", "").lower()
        for entry in entries:
            keywords = [k.lower() for k in entry.get("keywords", [])]
            for kw in keywords:
                if kw in user_msg:
                    return entry

        return {
            "en": "Sorry, I couldn't find the information. Please consult a professional.",
            "hi": "क्षमा करें, मैं जानकारी नहीं ढूंढ पाई। कृपया किसी विशेषज्ञ से परामर्श करें।"
        }

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        intent = tracker.latest_message.get("intent", {}).get("name")
        if not intent:
            dispatcher.utter_message(text="Sorry, I couldn't understand your question.")
            return []

        entries = self.load_kb(intent)
        matched_entry = self.match_entry(tracker, entries)

        language = self.get_user_language(tracker)
        response_text = matched_entry.get(language, matched_entry.get("en"))

        dispatcher.utter_message(text=response_text)
        return [SlotSet("language", language)]


class ActionMoodResponse(Action):

    def name(self) -> Text:
        return "action_mood_response"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict):

        language = "en" 
        user_id = tracker.sender_id
        try:
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT language FROM profiles WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row and row[0]:
                language = "en" if row[0].lower() == "english" else "hi"
        except Exception as e:
            print(f"Error fetching language from DB: {e}")
        finally:
            if conn:
                conn.close()

        if not language:
            language = tracker.get_slot("language") or "en"

        intent = tracker.latest_message.get('intent', {}).get('name')

        responses = {
            "greeting": ("utter_greeting_en", "utter_greeting_hi"),
            "goodbye": ("utter_goodbye_en", "utter_goodbye_hi"),
            "mood_great": ("utter_mood_great_en", "utter_mood_great_hi"),
            "mood_unhappy": ("utter_mood_unhappy_en", "utter_mood_unhappy_hi")
        }

        if intent in responses:
            en_resp, hi_resp = responses[intent]
            dispatcher.utter_message(response=en_resp if language == "en" else hi_resp)

        return [SlotSet("language", language)]
