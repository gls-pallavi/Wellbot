from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class UserBase(BaseModel):
    name: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class ProfileBase(BaseModel):
    age_group: Optional[str] = None
    gender: Optional[str] = None
    language: Optional[str] = None

class ProfileCreate(ProfileBase):
    user_id: int

class ProfileUpdate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True

class ChatSave(BaseModel):
    user_id: int
    query: str
    response: str
    intent: Optional[str] = None
    entity: Optional[str] = None 

class PredictChatRequest(BaseModel):
    user_id: int
    message: str 

class PredictChatResponse(BaseModel):
    response: str
    intent: str

class FeedbackCreate(BaseModel):
    user_id: int
    user_query: str
    bot_response: str
    feedback: str 

class FeedbackResponse(BaseModel):
    id: int
    user_id: int
    user_query: str
    bot_response: str
    feedback: str
    timestamp: datetime

    class Config:
        orm_mode = True
