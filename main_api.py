from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
import hashlib
import pandas as pd

app = FastAPI(title="Phone Hashing API")

from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Phone Hashing API",
        version="1.0.0",
        description="API for hashing phone numbers",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
    }

    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"ApiKeyAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

API_KEY = "my-secret-api-key-123"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_SALT = "my_secret_salt"

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

def sha256_hash(value: str) -> str:
    return hashlib.sha256((value + SECRET_SALT).encode()).hexdigest()

@app.post("/hash")
def hash_single_phone(
    phone: str,
    api_key: str = Depends(verify_api_key)
):
    phone = phone.strip()
    if not phone.isdigit():
        raise HTTPException(status_code=400, detail="Invalid phone number")

    return {"hashed_phone": sha256_hash(phone)}

@app.post("/hash_csv")
def hash_csv(file_path: str = Query(...)):
    df = pd.read_csv(file_path)
    if "phone" not in df.columns:
        raise HTTPException(status_code=400, detail="CSV must have 'phone' column")

    df["hashed_phone"] = df["phone"].astype(str).apply(sha256_hash)
    df.to_csv("hashed_output.csv", index=False)

    return {"message": "CSV hashed successfully"}
