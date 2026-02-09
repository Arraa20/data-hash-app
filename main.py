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

# Normalize phone like Meta (E.164 style)
def normalize_phone(phone: str) -> str:
    phone = re.sub(r"\D", "", phone)
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

# SHA256 hash
def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

# CSV filename sanitizer
def sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\d-]", "_", name.split(".")[0])

# Single hash API
@app.post("/hash", dependencies=[Depends(verify_api_key)])
def hash_single(phone: str):
    phone = normalize_phone(phone)
    return {"hashed_phone": sha256_hash(phone)}

# CSV hash endpoint
@app.post("/hash_csv", dependencies=[Depends(verify_api_key)])
async def hash_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV allowed")

    prefix = sanitize_filename(file.filename)
    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8")
    writer = csv.writer(temp_out)

    # Read header
    reader = csv.reader((line.decode("utf-8", errors="replace").strip() for line in file.file))
    headers = next(reader)
    col_type = []
    out_headers = []

    for h in headers:
        h_lower = h.lower()
        if "phone" in h_lower or "mobile" in h_lower:
            col_type.append("phone")
            out_headers.append("hashed_phone")
        elif "email" in h_lower:
            col_type.append("email")
            out_headers.append("hashed_email")
        else:
            col_type.append(None)

    if not out_headers:
        raise HTTPException(status_code=400, detail="No phone or email column found")

    writer.writerow(out_headers)

    for row in reader:
        if not row:
            continue
        hashed_row = []
        for i, val in enumerate(row):
            if not val.strip():
                continue
            if col_type[i] == "phone":
                hashed_row.append(sha256_hash(normalize_phone(val)))
            elif col_type[i] == "email":
                hashed_row.append(sha256_hash(normalize_email(val)))
        if hashed_row:
            writer.writerow(hashed_row)

    temp_out.close()

    return FileResponse(
        path=temp_out.name,
        filename=f"{prefix}_hashed.csv",
        media_type="text/csv"
    )
