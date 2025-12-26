from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Depends, HTTPException, status


SECRET_KEY = "341965d7fde165fa036f6d5f47295ec2da7822d1b1726b5ceb8a860e765223ef"#CHANGE ME!!!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

db = {
    "A" : { ###so this top name is what is the actual username in the database i.e. the email
        "name" : "",
        "username" : "A", #username is email must be the same as the main key
        "hashPass":"$2b$12$Kgar3I37N9zxfkDnlHoQ4eUNIRDygrfbOAwEtuz9DFOg92XUowASu", #need to populate this from a signup password
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

pwdContext = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2Scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

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

async def get_current_user(token: str = Depends(oauth2Scheme)):
    credException = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise
            raise credException
        tokenData = TokenData(username=username)
    except JWTError:
        raise credException
    
    user = get_user(db, username=tokenData.username)
    if user is None:
        raise credException
    
    return user


async def get_current_subscribed_user(currentUser: UserInDB = Depends(get_current_user)):
    if not currentUser.subscribed:
        print("Not Subscribed")
        raise HTTPException(status_code=400)
    return currentUser

# pwd = get_pass_hash("admin")
# print(pwd)
# #$2b$12$Kgar3I37N9zxfkDnlHoQ4eUNIRDygrfbOAwEtuz9DFOg92XUowASu