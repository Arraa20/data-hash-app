from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import hashlib
import csv
import os
import tempfile
import re

app = FastAPI(title="Meta Phone Hashing API")

# ENV API KEY
API_KEY = os.getenv("API_KEY")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Verify API Key
def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# Normalize phone like Meta (E.164 style)
def normalize_phone(phone: str) -> str:
    phone = re.sub(r"\D", "", phone)  # remove non-digits
    
    # Sri Lanka normalization examples
    if phone.startswith("0"):
        phone = "94" + phone[1:]
    elif phone.startswith("7") and len(phone) == 9:
        phone = "94" + phone
    elif phone.startswith("94"):
        pass
    
    return phone

# SHA256 Meta compatible
def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

# Single hash API
@app.post("/hash", dependencies=[Depends(verify_api_key)])
def hash_single(phone: str):
    phone = normalize_phone(phone)
    return {"hashed_phone": sha256_hash(phone)}

# CSV HASH ENDPOINT
@app.post("/hash_csv", dependencies=[Depends(verify_api_key)])
async def hash_csv(file: UploadFile = File(...)):

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV allowed")

    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8")
    writer = csv.writer(temp_out)
    writer.writerow(["hashed_phone"])  # only hashed output

    # STREAM processing (very fast, low RAM)
    for line in file.file:
        decoded = line.decode("utf-8").strip()
        if not decoded or "phone" in decoded.lower():
            continue

        # assume first column is phone
        phone = decoded.split(",")[0].strip()
        phone = normalize_phone(phone)

        if phone:
            hashed = sha256_hash(phone)
            writer.writerow([hashed])

    temp_out.close()

    return FileResponse(
        path=temp_out.name,
        media_type="text/csv",
        filename="meta_hashed_output.csv"
    )
