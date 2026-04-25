from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from fastapi import FastAPI, HTTPException
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone
from fastapi import WebSocket, WebSocketDisconnect
import json

app = FastAPI()

DATABASE_URL = "postgresql://chatuser:chatpassword@127.0.0.1:5433/chatdb"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "my_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    owner_id = Column(Integer)

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    text = Column(String)
    created_at = Column(String)


Base.metadata.create_all(bind=engine)

class UserCreate(BaseModel):
    username: str
    password: str
class RegisterResponse(BaseModel):
    username: str
    message: str
class LoginRequest(BaseModel):
    username: str
    password: str
class LoginResponse(BaseModel):
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


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, room_id: int, websocket: WebSocket):
        await websocket.accept()

        if room_id not in self.active_connections:
            self.active_connections[room_id] = []

        self.active_connections[room_id].append(websocket)

    def disconnect(self, room_id: int, websocket: WebSocket):
        self.active_connections[room_id].remove(websocket)

    async def send_message(self, room_id: int, message: str):
        for connection in self.active_connections.get(room_id, []):
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/")
def read_root():
    return {"message": "Hello, chat app!"}


@app.get("/hello/{name}")
def say_hello(name: str):
    return {"message": f"Hello {name}"}



def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.post("/register", response_model=RegisterResponse)
def register(user: UserCreate):
    db = SessionLocal()

    existing_user = db.query(User).filter(User.username == user.username).first()

    if existing_user:
        raise HTTPException(status_code=400,  detail="Username already exists")
    
    hashed_password = pwd_context.hash(user.password)

    new_user = User(
        username=user.username,
        password=hashed_password
    )

    db.add(new_user)
    db.commit()

    return {
        "username": user.username,
        "message": "User registered successful"
    }

@app.post("/login", response_model=TokenResponse)
def login(user_data: OAuth2PasswordRequestForm = Depends()):
    db=SessionLocal()

    existing_user = db.query(User).filter(User.username == user_data.username).first()

    if not existing_user:
        raise HTTPException(status_code=400, detail="Invalid username or password")
    
    existing_user_password = pwd_context.verify(user_data.password, existing_user.password)

    if not existing_user_password:
        raise HTTPException(status_code=400, detail="Invalid username or password");

    access_token = create_access_token(data={"sub": existing_user.username})

    return{
        "access_token": access_token,
        "token_type": "bearer"
    }



def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials"
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise credentials_exception

    return user


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

            await manager.send_message(room_id, json.dumps(message_payload))

    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)

    finally:
        db.close()