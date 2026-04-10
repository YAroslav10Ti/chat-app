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
class LoginResponce(BaseModel):
    username: str
    message: str
class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@app.get("/")
def read_root():
    return {"message": "Hello, chat app!"}


@app.get("/hello/{name}")
def say_hello(name: str):
    return {"message": f"Hello {name}"}

@app.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username
    }


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
def login(user_data: LoginRequest):
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
    
