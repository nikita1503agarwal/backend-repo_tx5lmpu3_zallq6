import os
from datetime import datetime, date
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import db, create_document, get_documents
from schemas import UserProfile, Reading

app = FastAPI(title="Astrology API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Astrology API is running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

# Simple zodiac mapping for dates (sun sign). This is approximate.
ZODIAC_DATES = [
    ("capricorn", (date(2000, 12, 22), date(2001, 1, 19))),
    ("aquarius", (date(2001, 1, 20), date(2001, 2, 18))),
    ("pisces", (date(2001, 2, 19), date(2001, 3, 20))),
    ("aries", (date(2001, 3, 21), date(2001, 4, 19))),
    ("taurus", (date(2001, 4, 20), date(2001, 5, 20))),
    ("gemini", (date(2001, 5, 21), date(2001, 6, 20))),
    ("cancer", (date(2001, 6, 21), date(2001, 7, 22))),
    ("leo", (date(2001, 7, 23), date(2001, 8, 22))),
    ("virgo", (date(2001, 8, 23), date(2001, 9, 22))),
    ("libra", (date(2001, 9, 23), date(2001, 10, 22))),
    ("scorpio", (date(2001, 10, 23), date(2001, 11, 21))),
    ("sagittarius", (date(2001, 11, 22), date(2001, 12, 21))),
]

SIGNS = [s for s, _ in ZODIAC_DATES]

class BirthInfo(BaseModel):
    name: Optional[str] = None
    birthdate: date

@app.post("/api/detect-sign")
def detect_sign(info: BirthInfo):
    d = info.birthdate
    # Normalize year to 2001 reference to compare ranges easily
    ref = date(2001, d.month, d.day)
    # Capricorn spans Dec 22 - Jan 19 crossing the year, so handle separately
    for sign, (start_ref, end_ref) in ZODIAC_DATES:
        # shift start/end years to 2001 window
        start = date(2001, start_ref.month, start_ref.day)
        end = date(2001, end_ref.month, end_ref.day)
        if start <= ref <= end:
            return {"sign": sign}
    # Handle capricorn late December
    if date(2001, 12, 22) <= ref <= date(2001, 12, 31):
        return {"sign": "capricorn"}
    raise HTTPException(status_code=400, detail="Invalid date")

class HoroscopeRequest(BaseModel):
    sign: str
    scope: str = "daily"  # daily, weekly, monthly

@app.post("/api/horoscope")
def get_horoscope(req: HoroscopeRequest):
    sign = req.sign.lower()
    if sign not in SIGNS:
        raise HTTPException(status_code=400, detail="Unknown sign")
    # Simple generated horoscope text (no external API). In real apps, call provider.
    today = datetime.utcnow().strftime("%Y-%m-%d")
    content = (
        f"{sign.title()} {req.scope.title()} Horoscope for {today}: "
        f"Energy favors thoughtful planning. Stay open to small surprises; "
        f"a conversation could point you toward a useful opportunity."
    )
    reading = Reading(sign=sign, date=today, content=content)
    try:
        reading_id = create_document("reading", reading)
    except Exception:
        reading_id = None
    return {"date": today, "sign": sign, "scope": req.scope, "content": content, "id": reading_id}

@app.get("/api/readings")
def list_readings(sign: Optional[str] = Query(None)):
    filt = {"sign": sign} if sign else {}
    try:
        docs = get_documents("reading", filt, limit=50)
        # Convert ObjectId to str where needed
        for d in docs:
            if "_id" in d:
                d["id"] = str(d.pop("_id"))
        return {"items": docs}
    except Exception:
        return {"items": []}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
