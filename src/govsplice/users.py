# /src/govsplice/users.py
"""This module implements most of the backend for user accounts except the actual endpoints."""

from datetime import datetime, timedelta

from pydantic import BaseModel

from jose import JWTError, jwt

from passlib.context import CryptContext

from fastapi.security import OAuth2PasswordBearer
from fastapi import Request, Depends, HTTPException, status


from govsplice import config

SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = config.ALGORITHM

db = {
    "A" : {
        "name" : "",
        "username" : "A", #Must be the same as the key in the top level dict
        "hashPass":"$2b$12$Kgar3I37N9zxfkDnlHoQ4eUNIRDygrfbOAwEtuz9DFOg92XUowASu", #"admin"
        "subscribed": True
    }
}

class Token(BaseModel):
    access_token:str #this naming standard required for auth libraries
    token_type:str

class TokenData(BaseModel):
    username: str | None = None

class User(BaseModel):
    username: str
    name: str
    subscribed: bool

class UserInDB(User):
    hashPass: str

class UserCreate(BaseModel):
    username: str
    name: str
    password: str

pwdContext = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2Scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

def check_pass(plainPass, hashedPass):
    return pwdContext.verify(plainPass, hashedPass)

def get_pass_hash(plainPass):
    return pwdContext.hash(plainPass)

def get_user(db, username: str):
    if username in db:
        userData = db[username]
        return UserInDB(**userData)
    
def auth_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not check_pass(password, user.hashPass):
        return False
    return user

def create_access_token(data: dict):
    toEncode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    toEncode.update({"exp":expire})
    return jwt.encode(toEncode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(request: Request): # Change param from 'token' to 'request'
    # 1. Try to get token from Header (standard)
    auth_header = request.headers.get("Authorization")
    
    # 2. If no header, try to get it from Cookie
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        cookie_token = request.cookies.get("access_token")
        if cookie_token and cookie_token.startswith("Bearer "):
            token = cookie_token.split(" ")[1]

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401)
    
    user = get_user(db, username=username)
    if user is None:
        raise HTTPException(status_code=401)
    
    return user

async def get_current_subscribed_user(currentUser: UserInDB = Depends(get_current_user)):
    if not currentUser.subscribed:
        print("Not Subscribed")
        raise HTTPException(status_code=400)
    return currentUser