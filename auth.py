from fastapi import APIRouter, Request, HTTPException, status, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

templates = Jinja2Templates(directory="templates")

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
user_collection = db["users"]

class LoginRequest(BaseModel):
    username: str
    password: str

@router.get("/login", response_class=HTMLResponse)
async def show_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login_user(request: Request):
    form = await request.json()
    username = form.get("username")
    password = form.get("password")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")

    user = user_collection.find_one({"username": username})

    if user:
        if user["password"] != password:
            raise HTTPException(status_code=401, detail="Incorrect password")
        print("Returning user login")
    else:
        # First-time user registration
        user_collection.insert_one({
            "username": username,
            "password": password,
            "first_login": datetime.utcnow()
        })
        print("First-time user registered")

    # ✅ Redirect to index.html with query param
    return RedirectResponse(
        url=f"/static/index.html?username={username}",
        status_code=status.HTTP_303_SEE_OTHER
    )
