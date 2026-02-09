from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import hashlib, csv, os, tempfile, re
import requests

app = FastAPI(title="Meta Phone & Email Hashing API with Upload")

# =====================
# ENV API KEY
# =====================
API_KEY = os.getenv("API_KEY")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")  # Your Meta token
META_AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")  # e.g., act_1234567890
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

# =====================
# CORS
# =====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# Verify API Key
# =====================
def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# =====================
# Helpers
# =====================
def normalize_phone(phone: str) -> str:
    phone = re.sub(r"\D", "", phone)
    if phone.startswith("0"):
        phone = "94" + phone[1:]
    elif phone.startswith("7") and len(phone) == 9:
        phone = "94" + phone
    return phone

def normalize_email(email: str) -> str:
    return email.strip().lower()

def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

# =====================
# SINGLE HASH ENDPOINT
# =====================
@app.post("/hash", dependencies=[Depends(verify_api_key)])
def hash_single(phone: str = Form(...)):
    phone = normalize_phone(phone)
    return {"hashed_phone": sha256_hash(phone)}

# =====================
# CSV DOWNLOAD MODE
# =====================
@app.post("/hash_csv", dependencies=[Depends(verify_api_key)])
async def hash_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV allowed")

    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8")
    writer = csv.writer(temp_out)
    writer.writerow(["hashed_phone", "hashed_email"])

    for line in file.file:
        try:
            decoded = line.decode("utf-8").strip()
        except UnicodeDecodeError:
            decoded = line.decode("latin1").strip()

        if not decoded or "phone" in decoded.lower():
            continue

        cols = decoded.split(",")
        phone, email = cols[0].strip(), cols[1].strip() if len(cols) > 1 else ""
        hashed_phone = sha256_hash(normalize_phone(phone)) if phone else ""
        hashed_email = sha256_hash(normalize_email(email)) if email else ""
        writer.writerow([hashed_phone, hashed_email])

    temp_out.close()
    return FileResponse(
        path=temp_out.name,
        media_type="text/csv",
        filename="meta_hashed_output.csv"
    )

# =====================
# UPLOAD TO META CUSTOM AUDIENCE
# =====================
@app.post("/hash_csv_upload", dependencies=[Depends(verify_api_key)])
async def hash_csv_upload(file: UploadFile = File(...), audience_name: str = Form(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV allowed")

    # 1️⃣ Prepare hashed data
    hashed_data = []
    for line in file.file:
        try:
            decoded = line.decode("utf-8").strip()
        except UnicodeDecodeError:
            decoded = line.decode("latin1").strip()

        if not decoded or "phone" in decoded.lower():
            continue

        cols = decoded.split(",")
        phone, email = cols[0].strip(), cols[1].strip() if len(cols) > 1 else ""
        if phone:
            hashed_data.append({"hash_type": "PHONE", "value": sha256_hash(normalize_phone(phone))})
        if email:
            hashed_data.append({"hash_type": "EMAIL", "value": sha256_hash(normalize_email(email))})

    if not hashed_data:
        raise HTTPException(status_code=400, detail="No valid phone/email found in CSV")

    # 2️⃣ Create Custom Audience on Meta
    create_url = f"https://graph.facebook.com/v17.0/act_{META_AD_ACCOUNT_ID}/customaudiences"
    payload = {
        "name": audience_name,
        "subtype": "CUSTOM",
        "description": "Hashed phones/emails uploaded via API",
        "customer_file_source": "USER_PROVIDED_ONLY",
        "access_token": META_ACCESS_TOKEN
    }
    response = requests.post(create_url, data=payload).json()
    if "id" not in response:
        raise HTTPException(status_code=500, detail=f"Meta API error: {response}")

    audience_id = response["id"]

    # 3️⃣ Add users to Custom Audience
    add_url = f"https://graph.facebook.com/v17.0/{audience_id}/users"
    # Meta API expects JSON of format { "payload": { "schema": ..., "data": [...] } }
    data_payload = {
        "payload": {
            "schema": ["EMAIL", "PHONE"],  # Meta supports both
            "data": [[h["value"]] for h in hashed_data]  # each row as list
        },
        "access_token": META_ACCESS_TOKEN
    }
    add_response = requests.post(add_url, json=data_payload).json()

    return JSONResponse({
        "audience_id": audience_id,
        "audience_name": audience_name,
        "rows_uploaded": len(hashed_data),
        "meta_response": add_response
    })
