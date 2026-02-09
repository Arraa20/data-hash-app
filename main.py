from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import hashlib
import csv
import os
import tempfile
import re

app = FastAPI(title="Meta Phone & Email Hashing API")

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

# Normalize phone like Meta (E.164 style, Sri Lanka)
def normalize_phone(phone: str) -> str:
    phone = re.sub(r"\D", "", phone)  # remove non-digits
    if phone.startswith("0"):
        phone = "94" + phone[1:]
    elif phone.startswith("7") and len(phone) == 9:
        phone = "94" + phone
    elif phone.startswith("94"):
        pass
    return phone

# Normalize email
def normalize_email(email: str) -> str:
    return email.strip().lower()

# SHA256 Meta compatible
def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

# Single hash API (phone only)
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

    # Read first line as header to detect columns
    first_line = file.file.readline().decode("utf-8", errors="replace").strip()
    headers = [h.strip() for h in first_line.split(",")]

    # Detect phone and email column indices
    phone_idx = None
    email_idx = None
    for i, h in enumerate(headers):
        h_lower = h.lower()
        if "phone" in h_lower or "mobile" in h_lower:
            phone_idx = i
        elif "email" in h_lower:
            email_idx = i

    if phone_idx is None and email_idx is None:
        raise HTTPException(status_code=400, detail="No phone or email columns detected")

    # Write output header
    out_header = []
    if phone_idx is not None:
        out_header.append("hashed_phone")
    if email_idx is not None:
        out_header.append("hashed_email")
    writer.writerow(out_header)

    # STREAM processing (fast, low RAM)
    for line in file.file:
        decoded = line.decode("utf-8", errors="replace").strip()
        if not decoded:
            continue
        parts = decoded.split(",")

        hashed_row = []
        # Phone
        if phone_idx is not None and len(parts) > phone_idx:
            phone = normalize_phone(parts[phone_idx].strip())
            hashed_row.append(sha256_hash(phone) if phone else "")
        # Email
        if email_idx is not None and len(parts) > email_idx:
            email = normalize_email(parts[email_idx].strip())
            hashed_row.append(sha256_hash(email) if email else "")

        if hashed_row:
            writer.writerow(hashed_row)

    temp_out.close()

    return FileResponse(
        path=temp_out.name,
        media_type="text/csv",
        filename="meta_hashed_output.csv"
    )
