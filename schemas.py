from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str


class RegisterResponse(BaseModel):
    username: str
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class RoomCreate(BaseModel):
    name: str


class RoomResponse(BaseModel):
    id: int
    name: str
    owner_id: int


class MessageCreate(BaseModel):
    text: str


class MessageResponse(BaseModel):
    id: int
    room_id: int
    user_id: int
    text: str
    created_at: str