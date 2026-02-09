from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import hashlib
import csv
import os
import tempfile
import re

app = FastAPI(title="Meta Data Hashing API")

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

# Single hash API
@app.post("/hash", dependencies=[Depends(verify_api_key)])
def hash_single(value: str, type: str = "phone"):
    """
    Hash a single phone or email.
    type: "phone" or "email"
    """
    if type == "phone":
        value = normalize_phone(value)
    elif type == "email":
        value = normalize_email(value)
    else:
        raise HTTPException(status_code=400, detail="type must be 'phone' or 'email'")

    return {"hashed": sha256_hash(value)}

# CSV HASH ENDPOINT
@app.post("/hash_csv", dependencies=[Depends(verify_api_key)])
async def hash_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV allowed")

    # Use uploaded filename as prefix for output
    prefix = os.path.splitext(file.filename)[0]
    temp_out = tempfile.NamedTemporaryFile(
        delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8"
    )
    writer = csv.writer(temp_out)

    first_line = True
    headers = []
    col_type = []

    # Stream processing
    for line in file.file:
        decoded = line.decode("utf-8", errors="replace").strip()
        if not decoded:
            continue

        row = [x.strip() for x in decoded.split(",")]

        if first_line:
            headers = row
            # Detect column types
            col_type = []
            output_headers = []
            for h in headers:
                h_lower = h.lower()
                if "phone" in h_lower or "mobile" in h_lower:
                    col_type.append("phone")
                    output_headers.append("hashed_phone")
                elif "email" in h_lower:
                    col_type.append("email")
                    output_headers.append("hashed_email")
                else:
                    col_type.append(None)
            writer.writerow(output_headers)
            first_line = False
            continue

        hashed_row = []
        for i, val in enumerate(row):
            if col_type[i] == "phone":
                norm = normalize_phone(val)
                hashed_row.append(sha256_hash(norm))
            elif col_type[i] == "email":
                norm = normalize_email(val)
                hashed_row.append(sha256_hash(norm))
        if hashed_row:
            writer.writerow(hashed_row)

    temp_out.close()

    return FileResponse(
        path=temp_out.name,
        media_type="text/csv",
        filename=f"{prefix}_hashed.csv"
    )
