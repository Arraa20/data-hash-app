from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import hashlib
import csv
import os
import tempfile
import re
import json
import requests

app = FastAPI(title="Meta Hash & Upload API")

# -------------------------
# ENV API KEY & Meta Config
# -------------------------
API_KEY = os.getenv("API_KEY")
ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
CUSTOM_AUDIENCE_ID = os.getenv("FB_CUSTOM_AUDIENCE_ID")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

# -------------------------
# CORS
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# API Key Verification
# -------------------------
def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# -------------------------
# Normalization Functions
# -------------------------
def normalize_phone(phone: str) -> str:
    phone = re.sub(r"\D", "", phone)
    if phone.startswith("0"):
        phone = "94" + phone[1:]
    elif phone.startswith("7") and len(phone) == 9:
        phone = "94" + phone
    elif phone.startswith("94"):
        pass
    return phone

def normalize_email(email: str) -> str:
    return email.strip().lower()

def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

# -------------------------
# CSV Hash & Download Endpoint
# -------------------------
@app.post("/hash_csv", dependencies=[Depends(verify_api_key)])
async def hash_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV allowed")

    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8")
    writer = csv.writer(temp_out)
    writer.writerow(["hashed_email", "hashed_phone"])

    total_rows = 0

    for line in file.file:
        try:
            decoded = line.decode("utf-8").strip()
        except UnicodeDecodeError:
            decoded = line.decode("latin1").strip()

        if not decoded or "phone" in decoded.lower() or "email" in decoded.lower():
            continue

        first_col = decoded.split(",")[0].strip()
        total_rows += 1

        if "@" in first_col:
            hashed_email = sha256_hash(normalize_email(first_col))
            hashed_phone = ""
        else:
            hashed_phone = sha256_hash(normalize_phone(first_col))
            hashed_email = ""

        writer.writerow([hashed_email, hashed_phone])

    temp_out.close()

    return FileResponse(
        path=temp_out.name,
        media_type="text/csv",
        filename="hashed_output.csv"
    )

# -------------------------
# Hash & Push to Meta Endpoint
# -------------------------
@app.post("/hash_and_upload_csv", dependencies=[Depends(verify_api_key)])
async def hash_and_upload(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV allowed")

    data_rows = []
    total_rows = 0

    for line in file.file:
        try:
            decoded = line.decode("utf-8").strip()
        except UnicodeDecodeError:
            decoded = line.decode("latin1").strip()

        if not decoded or "phone" in decoded.lower() or "email" in decoded.lower():
            continue

        first_col = decoded.split(",")[0].strip()
        total_rows += 1

        if "@" in first_col:
            hashed_email = sha256_hash(normalize_email(first_col))
            hashed_phone = ""
        else:
            hashed_phone = sha256_hash(normalize_phone(first_col))
            hashed_email = ""

        data_rows.append([hashed_email, hashed_phone])

    # Push to Meta Custom Audience
    fb_url = f"https://graph.facebook.com/v17.0/{CUSTOM_AUDIENCE_ID}/users"
    payload = {
        "payload": json.dumps({
            "schema": ["EMAIL", "PHONE"],
            "data": data_rows
        }),
        "access_token": ACCESS_TOKEN
    }

    try:
        response = requests.post(fb_url, data=payload, timeout=300)
        fb_result = response.json()
    except Exception as e:
        fb_result = {"status": "error", "detail": str(e)}

    return JSONResponse({
        "rows_processed": total_rows,
        "meta_response": fb_result
    })
