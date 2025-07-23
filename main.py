import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pymongo import MongoClient
from datetime import datetime
from fastapi.responses import JSONResponse
from auth import router as auth_router
from fastapi import Request

load_dotenv()

app = FastAPI()


app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=FileResponse)
async def serve_home():
    return FileResponse("static/index.html")

app.include_router(auth_router)


genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro")
# uri = os.getenv("MONGO_URI")
# client_db = MongoClient(uri)
# db = client_db[os.getenv("MONGO_DB")]
# collection = db[os.getenv("MONGO_COLLECTION")]

print("MONGO_URI =", os.getenv("MONGO_URI"))
print("MONGO_DB =", os.getenv("MONGO_DB"))
print("MONGO_COLLECTION =", os.getenv("MONGO_COLLECTION"))


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: ChatRequest, req: Request):
    try:
        username = req.query_params.get("username")

        chat = model.start_chat(history=[])
        response = chat.send_message(
            f"""
            You are a polite, professional hotel concierge for The Grand Horizon Hotel, a 5-star luxury hotel located in Mumbai.
            Help guests with check-in/check-out info, restaurant hours, spa bookings, transport arrangements, sightseeing suggestions, and more.
            The hotel offers: Deluxe Rooms, Presidential Suites, Rooftop Dining, 24x7 Room Service, Free Wi-Fi, Airport Pickup, and a Wellness Spa.
            Check-in is 2 PM, check-out is 11 AM. Address: Marine Drive, Mumbai, Maharashtra. Phone: +91-9876543210.

            Guest says: {request.message}
            """
        )

        bot_response = response.text

        # collection.insert_one({
        #     "username": username,
        #     "user_message": request.message,
        #     "bot_response": bot_response,
        #     "timestamp": datetime.utcnow()
        # })

        return {"response": bot_response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
@app.get("/admin/chats")
def get_chat_history():
    try:
        print("Trying to fetch chat history from MongoDB...")
        chats = list(collection.find({}, {"_id": 0}))

        for chat in chats:
            if "timestamp" in chat:
                chat["timestamp"] = chat["timestamp"].isoformat()

        print("Fetched chats:", chats)
        return JSONResponse(content={"chats": chats})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


