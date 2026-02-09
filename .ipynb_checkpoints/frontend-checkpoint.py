import streamlit as st
import requests

st.set_page_config(page_title="Data Hashing Tool", layout="centered")
st.title("Data Hashing Tool")
st.caption("Upload a CSV with phone numbers or emails. Output can be downloaded or pushed to Meta.")

# Replace with your FastAPI service public URL from Railway
API_URL_DOWNLOAD = "https://data-hash-app-fastapi-production.up.railway.app/hash_csv"
API_URL_META = "https://data-hash-app-fastapi-production.up.railway.app/hash_and_upload_csv"

# User inputs
api_key = st.text_input("API Key", type="password")
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

if uploaded_file and api_key:

    # BUTTON 1: Hash & Download
    if st.button("Hash & Download CSV"):
        with st.spinner("Hashing CSV..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file, "text/csv")}
                headers = {"X-API-Key": api_key}
                response = requests.post(API_URL_DOWNLOAD, files=files, headers=headers, timeout=300)

                if response.status_code == 200:
                    st.success("✅ CSV hashed successfully!")
                    st.download_button(
                        label="⬇️ Download Hashed CSV",
                        data=response.content,
                        file_name="hashed_output.csv",
                        mime="text/csv"
                    )
                else:
                    st.error(f"❌ Error {response.status_code}")
                    st.code(response.text)

            except Exception as e:
                st.error("❌ Something went wrong")
                st.code(str(e))

    # BUTTON 2: Hash & Push to Meta
    if st.button("Hash & Push to Meta"):
        with st.spinner("Hashing CSV and uploading to Meta..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file, "text/csv")}
                headers = {"X-API-Key": api_key}
                response = requests.post(API_URL_META, files=files, headers=headers, timeout=300)

                if response.status_code == 200:
                    st.success("✅ CSV hashed and uploaded to Meta!")
                    st.json(response.json())  # shows match stats like rows processed, matched %
                else:
                    st.error(f"❌ Error {response.status_code}")
                    st.code(response.text)

            except Exception as e:
                st.error("❌ Something went wrong")
                st.code(str(e))

else:
    st.info("Enter your API key and upload a CSV to begin.")
