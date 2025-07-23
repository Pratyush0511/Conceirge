import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import httpx
from auth import router as auth_router

load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION")

# MongoDB connection
client_db = MongoClient(MONGO_URI)
db = client_db[DB_NAME]
collection = db[COLLECTION_NAME]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)

# Serve static HTML
@app.get("/", response_class=FileResponse)
async def serve_home():
    return FileResponse("static/index.html")


# Gemini request body
class ChatRequest(BaseModel):
    message: str

# Function to get response from Gemini API
async def get_gemini_response(user_message: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

    headers = {"Content-Type": "application/json"}

    system_prompt = (
        "You are a polite, professional hotel concierge for **The Grand Horizon Hotel**, "
        "a 5-star luxury hotel located in Mumbai. Help guests with check-in/check-out info, "
        "restaurant hours, spa bookings, transport arrangements, sightseeing suggestions, and more. "
        "The hotel offers: Deluxe Rooms, Presidential Suites, Rooftop Dining, 24x7 Room Service, "
        "Free Wi-Fi, Airport Pickup, and a Wellness Spa. Check-in is 2 PM, check-out is 11 AM. "
        "Address: Marine Drive, Mumbai, Maharashtra. Phone: +91-9876543210."
    )

    body = {
        "contents": [
            {"role": "user", "parts": [{"text": system_prompt}]},
            {"role": "user", "parts": [{"text": user_message}]}
        ]
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=headers, json=body)
        res.raise_for_status()
        data = res.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


# Chat endpoint using Gemini
@app.post("/chat")
async def chat(request: ChatRequest, req: Request):
    try:
        username = req.query_params.get("username")

        response_text = await get_gemini_response(request.message)

        # Save to MongoDB
        collection.insert_one({
            "username": username,
            "user_message": request.message,
            "bot_response": response_text,
            "timestamp": datetime.utcnow()
        })

        return {"response": response_text}
    except Exception as e:
        print("Chat error:", e)
        raise HTTPException(status_code=500, detail=str(e))


# Admin endpoint to get all chat logs
@app.get("/admin/chats")
def get_chat_history():
    try:
        chats = list(collection.find({}, {"_id": 0}))
        for chat in chats:
            if "timestamp" in chat:
                chat["timestamp"] = chat["timestamp"].isoformat()
        return JSONResponse(content={"chats": chats})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
