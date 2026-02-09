from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import hashlib
import csv
import os
import tempfile
import re

app = FastAPI(title="Meta Fast Phone & Email Hashing API")

# ------------------- API Key -------------------
API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# ------------------- CORS -------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------- Helpers -------------------
def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    phone = re.sub(r"\D", "", phone)
    if phone.startswith("0"):
        phone = "94" + phone[1:]
    elif phone.startswith("7") and len(phone) == 9:
        phone = "94" + phone
    elif phone.startswith("94"):
        pass
    return phone

def normalize_email(email: str) -> str:
    if not email:
        return ""
    return email.strip().lower()

def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

# ------------------- Single Hash -------------------
@app.post("/hash", dependencies=[Depends(verify_api_key)])
def hash_single(phone: str):
    phone = normalize_phone(phone)
    return {"hashed_phone": sha256_hash(phone)}

# ------------------- CSV Hash -------------------
@app.post("/hash_csv", dependencies=[Depends(verify_api_key)])
async def hash_csv(file: UploadFile = File(...)):

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV allowed")

    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8")
    writer = csv.writer(temp_out)

    # ------------------- Detect header -------------------
    first_line = await file.read(1024)
    file.file.seek(0)
    header_line = first_line.decode("utf-8").splitlines()[0]
    headers = [h.strip().lower() for h in header_line.split(",")]

    phone_idx = next((i for i, h in enumerate(headers) if "phone" in h or "mobile" in h), 0)
    email_idx = next((i for i, h in enumerate(headers) if "email" in h), None)

    # Output header
    writer.writerow(["hashed_phone", "hashed_email" if email_idx is not None else ""])

    # ------------------- Stream CSV -------------------
    for line in file.file:
        decoded = line.decode("utf-8").strip()
        if not decoded or any(skip_word in decoded.lower() for skip_word in ["phone", "mobile", "email"]):
            continue

        parts = decoded.split(",")
        phone = normalize_phone(parts[phone_idx].strip()) if len(parts) > phone_idx else ""
        email = normalize_email(parts[email_idx].strip()) if email_idx is not None and len(parts) > email_idx else ""

        hashed_phone = sha256_hash(phone) if phone else ""
        hashed_email = sha256_hash(email) if email else ""

        writer.writerow([hashed_phone, hashed_email])

    temp_out.close()

    return FileResponse(
        path=temp_out.name,
        media_type="text/csv",
        filename="meta_hashed_output.csv"
    )
