# backend/app/main.py
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

import openai
import requests
import os

app = FastAPI()

# Path to frontend files
FRONTEND_PATH = os.environ.get("FRONTEND_BUILD_DIR", "/app/frontend")

# --- API ROUTES ---

# Static data for houses (colors, description, symbols, etc.)
HOUSES = [
    {
        "name": "Gryffindor",
        "colors": "Scarlet and Gold",
        "symbol": "Lion",
        "description": "Gryffindor values courage, nerve, and chivalry. Gryffindor's mascot is a lion, and the Head of House is Minerva McGonagall. The Gryffindor dormitories are in a high tower, and students must use a password to gain entry. Gryffindor corresponds roughly to the element of fire."
    },
    {
        "name": "Slytherin",
        "colors": "Green and Silver",
        "symbol": "Serpent",
        "description": "Slytherin values ambition, cunning, leadership, and resourcefulness. The mascot of Slytherin is a serpent. Severus Snape is the Head of Slytherin House until he becomes headmaster, at which point Horace Slughorn assumes the position. The Slytherin dormitories are accessed by speaking a password in front of a stone wall in the dungeons, which causes a hidden door to open. Slytherin corresponds roughly to the element of water."
    },
    {
        "name": "Hufflepuff",
        "colors": "Yellow and Black",
        "symbol": "Badger",
        "description": "Hufflepuff values hard work, patience, justice, and loyalty. Hufflepuff's mascot is a badger, and the Head of House is Pomona Sprout. Hufflepuff corresponds roughly to the element of earth."
    },
    {
        "name": "Ravenclaw",
        "colors": "Blue and Bronze",
        "symbol": "Eagle",
        "description": "Ravenclaw values intelligence, learning, wisdom, and wit. The house mascot is an eagle in the novels and a raven in the Harry Potter and Fantastic Beasts films. In the novels, the Head of Ravenclaw House is Filius Flitwick. The dormitories are in Ravenclaw Tower, and students must solve a riddle to gain entry. Ravenclaw corresponds roughly to the element of air."
    }
]

@app.get("/api/houses")
def get_houses():
    return HOUSES


@app.get("/api/characters")
def get_characters(
    house: str | None = Query(None, description="Filter by house name"),
    search: str | None = Query(None, description="Filter by character name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Proxy to the Harry Potter API with optional filtering + pagination."""
    if house:
        resp = requests.get(f"https://hp-api.onrender.com/api/characters/house/{house}")
    else:
        resp = requests.get("https://hp-api.onrender.com/api/characters")
    if resp.status_code != 200:
        return {"error": "Failed to fetch characters"}

    characters = resp.json()

    # Optional search
    if search:
        characters = [
            c for c in characters
            if search.lower() in c.get("name", "").lower()
        ]

    # Simple pagination
    start = (page - 1) * page_size
    end = start + page_size
    paged = characters[start:end]

    return {
        "page": page,
        "page_size": page_size,
        "total": len(characters),
        "results": paged
    }


@app.get("/api/character/{id}")
def get_character_by_name(id: str):
    """Fetch one character by id."""
    resp = requests.get(f"https://hp-api.onrender.com/api/character/{id}")
    if resp.status_code != 200:
        return {"error": f"Failed to fetch character with id={id}"}

    return resp.json()

@app.get("/api/characters/{name}")
def get_character_by_name(name: str):
    """Fetch one character by name (exact match)."""
    resp = requests.get("https://hp-api.onrender.com/api/characters")
    if resp.status_code != 200:
        return {"error": "Failed to fetch characters"}

    characters = resp.json()
    for c in characters:
        if c.get("name", "").lower() == name.lower():
            return c
    return {"error": f"Character '{name}' not found"}


# --- FRONTEND ROUTES ---
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_PATH, "index.html"))

@app.get("/{path:path}")
async def serve_static(path: str):
    filepath = os.path.join(FRONTEND_PATH, path)
    if os.path.exists(filepath):
        return FileResponse(filepath)
    # fallback to index.html for unknown routes
    return FileResponse(os.path.join(FRONTEND_PATH, "index.html"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class ChatRequest(BaseModel):
    character: str
    message: str

@app.post("/api/chat")
async def chat_with_character(req: ChatRequest):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"You are {req.character} from Harry Potter. Stay in character when chatting."},
            {"role": "user", "content": req.message}
        ]
    )
    reply = response.choices[0].message.content
    return {"reply": reply}
