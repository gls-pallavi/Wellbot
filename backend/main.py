from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import requests
import os
from dotenv import load_dotenv

from backend.routes import router
from backend.db import engine, Base, get_db
from backend.models import User, ChatHistory, Profile

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
RASA_URL = os.getenv("RASA_URL", "http://127.0.0.1:5005/webhooks/rest/webhook")

app = FastAPI(title="WellBot Backend")
Base.metadata.create_all(bind=engine)
app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI is running!"}

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "pong!"}

class ChatRequest(BaseModel):
    user_id: int
    message: str
    lang: str = "en"

class ChatResponse(BaseModel):
    response: str
    intent: str

def fetch_rasa_response(user_id: int, message: str):
    payload = {"sender": str(user_id), "message": message}
    try:
        response = requests.post(RASA_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            bot_response = "\n".join([msg.get("text", "") for msg in data])
            intent = data[0].get("metadata", {}).get("intent", "from_rasa") if data else "from_rasa"
            return bot_response, intent
        else:
            return "🤖 Backend error calling bot.", "error"
    except Exception:
        return "⚠️ Rasa server not reachable.", "error"

@app.post("/predict_chat", response_model=ChatResponse)
def predict_chat(chat: ChatRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == chat.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch response from Rasa
    bot_response, intent_tag = fetch_rasa_response(chat.user_id, chat.message)

    # Save chat history
    new_chat = ChatHistory(
        user_id=chat.user_id,
        query=chat.message,
        response=bot_response,
        intent=intent_tag
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    return {"response": bot_response, "intent": intent_tag}