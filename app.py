from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random
import string
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(title="Speed Type API", version="1.0.0")

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store CAPTCHA sessions (in production, use Redis or database)
captcha_sessions = {}

# Models
class CaptchaRequest(BaseModel):
    pass

class CaptchaVerify(BaseModel):
    session_id: str
    captcha_input: str

class TypingScore(BaseModel):
    wpm: int
    accuracy: int
    correct_words: int
    errors: int
    time: int
    date: str

class LeaderboardEntry(BaseModel):
    wpm: int
    accuracy: int
    date: str
    time: int

# In-memory leaderboard storage (top 10 scores)
leaderboard = []

# ==================== CAPTCHA ENDPOINTS ====================

@app.post("/api/captcha/generate")
async def generate_captcha():
    """
    Generate a simple CAPTCHA challenge
    Returns a session ID and CAPTCHA text
    """
    # Generate random 6-character CAPTCHA
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    # Generate session ID
    session_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=32))
    
    # Store in session (expires after 5 minutes in production)
    captcha_sessions[session_id] = {
        "text": captcha_text,
        "created_at": datetime.now()
    }
    
    return {
        "session_id": session_id,
        "captcha_text": captcha_text,
        "message": "CAPTCHA generated successfully"
    }

@app.post("/api/captcha/verify")
async def verify_captcha(data: CaptchaVerify):
    """
    Verify CAPTCHA input
    Returns success/failure status
    """
    # Check if session exists
    if data.session_id not in captcha_sessions:
        raise HTTPException(status_code=400, detail="Invalid or expired CAPTCHA session")
    
    # Get stored CAPTCHA
    stored_captcha = captcha_sessions[data.session_id]["text"]
    
    # Verify (case-insensitive)
    if data.captcha_input.upper() == stored_captcha.upper():
        # Remove used session
        del captcha_sessions[data.session_id]
        return {
            "verified": True,
            "message": "CAPTCHA verified successfully"
        }
    else:
        raise HTTPException(status_code=400, detail="Incorrect CAPTCHA")

# ==================== LEADERBOARD ENDPOINTS ====================

@app.post("/api/leaderboard/submit")
async def submit_score(score: TypingScore):
    """
    Submit a typing test score to the global leaderboard
    Returns updated leaderboard position
    """
    # Create leaderboard entry
    entry = {
        "wpm": score.wpm,
        "accuracy": score.accuracy,
        "correct_words": score.correct_words,
        "errors": score.errors,
        "time": score.time,
        "date": score.date,
        "timestamp": datetime.now().isoformat()
    }
    
    # Add to leaderboard
    leaderboard.append(entry)
    
    # Sort by WPM (descending), then by accuracy
    leaderboard.sort(key=lambda x: (x["wpm"], x["accuracy"]), reverse=True)
    
    # Keep only top 50 scores
    if len(leaderboard) > 50:
        leaderboard.pop()
    
    # Find position of submitted score
    position = next((i for i, item in enumerate(leaderboard) if item["timestamp"] == entry["timestamp"]), -1) + 1
    
    return {
        "message": "Score submitted successfully",
        "position": position,
        "total_entries": len(leaderboard)
    }

@app.get("/api/leaderboard/top")
async def get_top_scores(limit: int = 10):
    """
    Get top scores from the leaderboard
    Default returns top 10
    """
    # Return top N scores
    top_scores = leaderboard[:min(limit, len(leaderboard))]
    
    return {
        "count": len(top_scores),
        "scores": top_scores
    }

@app.get("/api/leaderboard/all")
async def get_all_scores():
    """
    Get all leaderboard scores
    """
    return {
        "count": len(leaderboard),
        "scores": leaderboard
    }

# ==================== STATISTICS ENDPOINTS ====================

@app.get("/api/stats")
async def get_statistics():
    """
    Get global statistics
    """
    if not leaderboard:
        return {
            "total_tests": 0,
            "average_wpm": 0,
            "average_accuracy": 0,
            "highest_wpm": 0,
            "total_words_typed": 0
        }
    
    total_tests = len(leaderboard)
    average_wpm = sum(score["wpm"] for score in leaderboard) / total_tests
    average_accuracy = sum(score["accuracy"] for score in leaderboard) / total_tests
    highest_wpm = max(score["wpm"] for score in leaderboard)
    total_words = sum(score["correct_words"] for score in leaderboard)
    
    return {
        "total_tests": total_tests,
        "average_wpm": round(average_wpm, 2),
        "average_accuracy": round(average_accuracy, 2),
        "highest_wpm": highest_wpm,
        "total_words_typed": total_words
    }

# ==================== PARAGRAPHS ENDPOINT ====================

@app.get("/api/paragraphs")
async def get_paragraphs():
    """
    Get available typing test paragraphs
    """
    paragraphs = [
        "The quick brown fox jumps over the lazy dog every single morning. This sentence helps me warm up my fingers and focus on accuracy. I try to type it smoothly without rushing, making sure every key is pressed correctly. Slow and steady always builds better technique.",
        "Respectfully, if you're not hitting that WPM goal, you're kinda sus. But it's giving growth mindset energy so we stan the effort. The way you're typing is ate, no crumbs left. This is your moment to shine and be iconic. Remember, we're all just NPCs in someone else's story, but you're the main character here. Slay the keyboard bestie.",
        "Okay but like, typing fast is literally a flex in this economy. Your keyboard is probably screaming right now but that's the vibe we're going for. This hits different when you're in the zone. No thoughts, just vibes and finger movement. You're doing amazing sweetie, keep that energy up. The algorithm is watching and it's impressed.",
        "Listen, I'm not saying you're the GOAT at typing, but you're definitely giving champion energy. The dedication is unmatched, the speed is incredible, and the accuracy is chef's kiss. This is what peak performance looks like fam. You understood the assignment and came prepared. Respectfully, you're carrying the team right now.",
        "Pov: you're absolutely crushing this typing test and everyone is shook. The way your fingers are moving is giving professional typist realness. This is so fetch and it's definitely going to happen. You're living rent free in everyone's head with these skills. The vibes are immaculate and the energy is unmatched bestie.",
        "Bestie wake up, new typing speed just dropped and it's giving everything. The commitment to excellence is real and we're here for it. Your typing aura is literally glowing right now. This is the content we signed up for. No skips, all hits, just pure typing excellence. You're the moment and the movement."
    ]
    
    return {
        "count": len(paragraphs),
        "paragraphs": paragraphs
    }

# ==================== HEALTH CHECK ====================

@app.get("/")
async def root():
    """
    API health check and welcome message
    """
    return {
        "message": "⚡ Speed Type API is running!",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "html": "/app",
            "captcha_generate": "/api/captcha/generate",
            "captcha_verify": "/api/captcha/verify",
            "submit_score": "/api/leaderboard/submit",
            "top_scores": "/api/leaderboard/top",
            "all_scores": "/api/leaderboard/all",
            "statistics": "/api/stats",
            "paragraphs": "/api/paragraphs"
        }
    }

# ==================== SERVE STATIC FILES ====================

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the main HTML file
@app.get("/app", response_class=HTMLResponse)
async def serve_app():
    """
    Serve the main typing test HTML page
    """
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="index.html not found")

# If you want to serve it at the root too
@app.get("/index", response_class=HTMLResponse)
async def serve_index():
    """
    Alternative endpoint to serve the typing test
    """
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="index.html not found")

# Run with: uvicorn app:app --reload