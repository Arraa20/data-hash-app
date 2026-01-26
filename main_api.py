from fastapi import FastAPI, HTTPException, Query
import hashlib
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Phone Hashing API")

# Enable CORS so Streamlit or other clients can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_SALT = "my_secret_salt"  # keep private


def sha256_hash(value: str) -> str:
    """Hash phone number with SHA-256 + salt"""
    return hashlib.sha256((value + SECRET_SALT).encode()).hexdigest()


@app.post("/hash")
def hash_single_phone(phone: str = Query(..., description="Phone number to hash")):
    phone = phone.strip()
    if not phone.isdigit():
        raise HTTPException(status_code=400, detail="Invalid phone number")
    return {"hashed_phone": sha256_hash(phone)}


@app.post("/hash_csv")
def hash_csv(file_path: str = Query(..., description="Path to CSV with 'phone' column")):
    try:
        df = pd.read_csv(file_path)
        if "phone" not in df.columns:
            raise HTTPException(status_code=400, detail="CSV must have 'phone' column")
        df["hashed_phone"] = df["phone"].astype(str).apply(sha256_hash)
        output_path = "hashed_output.csv"
        df.to_csv(output_path, index=False)
        return {"message": f"Hashed CSV saved as {output_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
