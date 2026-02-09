from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import hashlib, csv, os, re, tempfile, requests, json

app = FastAPI(title="Data Hashing & Meta Upload API")

# ENV API KEY
API_KEY = os.getenv("API_KEY")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")  # FB Marketing API token
AD_ACCOUNT_ID = os.getenv("AD_ACCOUNT_ID")  # Ad Account ID
CUSTOM_AUDIENCE_ID = os.getenv("CUSTOM_AUDIENCE_ID")  # Target Audience

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

# Normalize phone (Sri Lanka style)
def normalize_phone(phone: str) -> str:
    phone = re.sub(r"\D", "", phone)
    if phone.startswith("0"):
        return "94" + phone[1:]
    elif phone.startswith("7") and len(phone) == 9:
        return "94" + phone
    elif phone.startswith("94"):
        return phone
    return phone

# Normalize email
def normalize_email(email: str) -> str:
    return email.strip().lower()

# SHA256 hashing
def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

# Single hash API
@app.post("/hash", dependencies=[Depends(verify_api_key)])
def hash_single(phone: str = None, email: str = None):
    if phone:
        phone = normalize_phone(phone)
        return {"hashed_phone": sha256_hash(phone)}
    if email:
        email = normalize_email(email)
        return {"hashed_email": sha256_hash(email)}
    raise HTTPException(status_code=400, detail="Provide phone or email")

# CSV hash & download
@app.post("/hash_csv", dependencies=[Depends(verify_api_key)])
async def hash_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV allowed")

    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8")
    writer = csv.writer(temp_out)
    writer.writerow(["hashed_phone_or_email"])

    for line in file.file:
        try:
            decoded = line.decode("utf-8").strip()
        except UnicodeDecodeError:
            decoded = line.decode("latin1").strip()
        if not decoded or "phone" in decoded.lower() or "email" in decoded.lower():
            continue
        first_col = decoded.split(",")[0].strip()
        if "@" in first_col:
            hashed = sha256_hash(normalize_email(first_col))
        else:
            hashed = sha256_hash(normalize_phone(first_col))
        writer.writerow([hashed])

    temp_out.close()
    return FileResponse(path=temp_out.name, media_type="text/csv", filename="hashed_output.csv")

# CSV hash & push to Meta
@app.post("/hash_and_upload_csv", dependencies=[Depends(verify_api_key)])
async def hash_and_upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV allowed")

    hashed_list = []
    total_rows = 0

    for line in file.file:
        try:
            decoded = line.decode("utf-8").strip()
        except UnicodeDecodeError:
            decoded = line.decode("latin1").strip()
        if not decoded or "phone" in decoded.lower() or "email" in decoded.lower():
            continue
        first_col = decoded.split(",")[0].strip()
        if "@" in first_col:
            hashed_list.append(sha256_hash(normalize_email(first_col)))
        else:
            hashed_list.append(sha256_hash(normalize_phone(first_col)))
        total_rows += 1

    # Push to Meta Custom Audience
    url = f"https://graph.facebook.com/v17.0/{CUSTOM_AUDIENCE_ID}/users"
    payload = {
        "payload": json.dumps({
            "schema": ["EMAIL", "PHONE"],
            "data": [[v] for v in hashed_list]  # Each value as a separate list
        }),
        "access_token": ACCESS_TOKEN
    }

    response = requests.post(url, data=payload)
    if response.status_code != 200:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": response.text, "rows_processed": total_rows}
        )

    # Example: Facebook returns number of matched users
    match_info = response.json()
    matched = match_info.get("num_received", 0)

    match_rate = f"{(matched/total_rows*100):.2f}%" if total_rows else "0%"

    return {
        "status": "success",
        "rows_processed": total_rows,
        "matched_rows": matched,
        "match_rate": match_rate
    }
