from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import json
from pathlib import Path
import traceback
import requests, os


from backend.db import get_db
from backend.models import User, Profile, ChatHistory
from backend.schemas import UserCreate, UserLogin, ProfileBase, PredictChatRequest, PredictChatResponse
from backend.auth import hash_password, verify_password, create_access_token, decode_access_token
from dotenv import load_dotenv
from backend.models import Feedback
from backend.schemas import FeedbackCreate, FeedbackResponse

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
RASA_URL = os.getenv("RASA_URL", "http://127.0.0.1:5005/webhooks/rest/webhook")
router = APIRouter()

#Auth Routes
@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(user.password)
    new_user = User(name=user.name, email=user.email, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    new_profile = Profile(user_id=new_user.id)
    db.add(new_profile)
    db.commit()

    return {"message": "User registered successfully", "user_id": new_user.id}

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Email not registered. Please register first.")
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    token = create_access_token(data={"sub": db_user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": db_user.id
    }

def get_current_user_email(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    token = authorization.split(" ")[1]
    email = decode_access_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return email

#Profile Routes
@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email)
):
    db_user = db.query(User).filter(User.email == email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_profile = db.query(Profile).filter(Profile.user_id == db_user.id).first()
    if not db_profile or (
        not db_profile.age_group and not db_profile.gender and not db_profile.language
    ):
        return {}

    return {
        "user_id": db_user.id,
        "age_group": db_profile.age_group,
        "gender": db_profile.gender,
        "language": db_profile.language
    }

@router.put("/profile")
def update_profile(
    profile_data: ProfileBase,
    db: Session = Depends(get_db),
    email: str = Depends(get_current_user_email)
):
    db_user = db.query(User).filter(User.email == email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_profile = db.query(Profile).filter(Profile.user_id == db_user.id).first()
    if not db_profile:
        db_profile = Profile(user_id=db_user.id)
        db.add(db_profile)

    db_profile.age_group = profile_data.age_group
    db_profile.gender = profile_data.gender
    db_profile.language = profile_data.language

    db.commit()
    db.refresh(db_profile)

    return {"message": "Profile updated successfully", "user_id": db_user.id}

#Chatbot Route
@router.post("/predict_chat", response_model=PredictChatResponse)
def predict_chat(chat: PredictChatRequest, db: Session = Depends(get_db)):
    message = chat.message
    user_id = chat.user_id

    db_profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    language_map = {"english": "en", "hindi": "hi"}
    language_key = "en" 

    if db_profile and db_profile.language:
        language_key = language_map.get(db_profile.language.lower(), "en")

    response_text = ""
    try:
        payload = {
            "sender": str(user_id),
            "message": message,
            "metadata": {"language": language_key}  
        }
        rasa_resp = requests.post(RASA_URL, json=payload, timeout=5)
        if rasa_resp.status_code == 200:
            data = rasa_resp.json()
            response_texts = []

            if data:
                for msg in data:
                    if isinstance(msg.get("text"), dict):
                        response_texts.append(
                            msg["text"].get(language_key, msg["text"].get("en", "Sorry, I don't know the answer."))
                        )
                    else:
                        response_texts.append(msg.get("text", ""))

                response_text = "\n".join(response_texts).strip()
            else:
                response_text = "Sorry, I don't know the answer." if language_key == "en" else "माफ़ करें, जानकारी उपलब्ध नहीं है।"
        else:
            response_text = "Backend error. Please try again." if language_key == "en" else "सर्वर त्रुटि। कृपया बाद में प्रयास करें।"
    except requests.exceptions.RequestException:
        response_text = "Backend not reachable. Please try again later." if language_key == "en" else "सर्वर उपलब्ध नहीं है। कृपया बाद में प्रयास करें।"

    intent_tag = "unknown_intent"
    entity_data = None
    try:
        parse_payload = {"text": message, "sender": str(user_id)}
        rasa_parse = requests.post("http://localhost:5005/model/parse", json=parse_payload, timeout=5)
        if rasa_parse.status_code == 200:
            parse_data = rasa_parse.json()
            intent_tag = parse_data.get("intent", {}).get("name", "unknown_intent")
            entities = parse_data.get("entities", [])
            entity_data = json.dumps(entities) if entities else None
    except Exception as e:
        print(f"[WARN] Could not fetch intent/entities: {e}")

    try:
        new_chat = ChatHistory(
            user_id=user_id,
            query=message,
            response=response_text,
            intent=intent_tag,
            entity=entity_data,
            timestamp=datetime.utcnow()
        )
        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)
    except Exception:
        db.rollback()
        print("Warning: Could not save chat history.")
        traceback.print_exc()

    return PredictChatResponse(
        response=response_text,
        intent=intent_tag
    )

@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db)):
    new_feedback = Feedback(
        user_id=feedback.user_id,
        user_query=feedback.user_query,
        bot_response=feedback.bot_response,
        feedback=feedback.feedback
    )
    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)
    return new_feedback