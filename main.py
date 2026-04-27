import json
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError

from fastapi.responses import FileResponse

from database import Base, engine, SessionLocal
from models import User, Room, Message
from schemas import (
    UserCreate,
    RegisterResponse,
    TokenResponse,
    RoomCreate,
    RoomResponse,
    MessageCreate,
    MessageResponse,
)
from auth import (
    pwd_context,
    create_access_token,
    get_current_user,
    SECRET_KEY,
    ALGORITHM,
)
from websocket_manager import manager


app = FastAPI()

Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root():
    return {"message": "Hello, chat app!"}



@app.post("/register", response_model=RegisterResponse)
def register(user: UserCreate):
    db = SessionLocal()

    existing_user = db.query(User).filter(User.username == user.username).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = pwd_context.hash(user.password)

    new_user = User(
        username=user.username,
        password=hashed_password
    )

    db.add(new_user)
    db.commit()

    return {
        "username": user.username,
        "message": "User registered successfully"
    }


@app.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()

    existing_user = db.query(User).filter(User.username == form_data.username).first()

    if not existing_user:
        raise HTTPException(status_code=400, detail="Invalid username or password")

    is_password_correct = pwd_context.verify(
        form_data.password,
        existing_user.password
    )

    if not is_password_correct:
        raise HTTPException(status_code=400, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": existing_user.username})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username
    }


@app.post("/rooms", response_model=RoomResponse)
def create_room(room: RoomCreate, current_user: User = Depends(get_current_user)):
    db = SessionLocal()

    existing_room = db.query(Room).filter(Room.name == room.name).first()

    if existing_room:
        raise HTTPException(status_code=400, detail="Room already exists")

    new_room = Room(
        name=room.name,
        owner_id=current_user.id
    )

    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    return new_room


@app.get("/rooms", response_model=list[RoomResponse])
def get_rooms(current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    rooms = db.query(Room).all()
    return rooms


@app.post("/rooms/{room_id}/messages", response_model=MessageResponse)
def create_message(
    room_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()

    room = db.query(Room).filter(Room.id == room_id).first()

    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    created_at = datetime.now(timezone.utc).isoformat()

    new_message = Message(
        room_id=room_id,
        user_id=current_user.id,
        text=message.text,
        created_at=created_at
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return new_message


@app.get("/rooms/{room_id}/messages", response_model=list[MessageResponse])
def get_room_messages(
    room_id: int,
    current_user: User = Depends(get_current_user)
):
    db = SessionLocal()

    room = db.query(Room).filter(Room.id == room_id).first()

    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    messages = db.query(Message).filter(Message.room_id == room_id).all()
    return messages


@app.websocket("/ws/rooms/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: int, token: str):
    db = SessionLocal()

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            await websocket.close()
            return

    except JWTError:
        await websocket.close()
        return

    current_user = db.query(User).filter(User.username == username).first()

    if current_user is None:
        await websocket.close()
        return

    room = db.query(Room).filter(Room.id == room_id).first()

    if room is None:
        await websocket.close()
        return

    await manager.connect(room_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()

            created_at = datetime.now(timezone.utc).isoformat()

            new_message = Message(
                room_id=room_id,
                user_id=current_user.id,
                text=data,
                created_at=created_at
            )

            db.add(new_message)
            db.commit()
            db.refresh(new_message)

            message_payload = {
                "id": new_message.id,
                "room_id": new_message.room_id,
                "user_id": new_message.user_id,
                "username": current_user.username,
                "text": new_message.text,
                "created_at": new_message.created_at
            }

            await manager.send_message(
                room_id,
                json.dumps(message_payload)
            )

    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)

    finally:
        db.close()



@app.get("/chat")
def chat():
    return FileResponse("chat.html")