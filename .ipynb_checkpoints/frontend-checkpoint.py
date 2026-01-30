import streamlit as st
import requests

st.set_page_config(page_title="Phone Hashing Tool", layout="centered")

st.title("📞 Phone Number Hashing Tool")
st.caption("Upload a CSV with a `phone` column. Output will be SHA-256 hashed.")

# Replace with your FastAPI service public URL from Railway
API_URL = "https://data-hash-app-fastapi-production.up.railway.app"

api_key = st.text_input("API Key", type="password")
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

if uploaded_file and api_key:
    if st.button("Hash CSV"):
        with st.spinner("Hashing phone numbers..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file, "text/csv")}
                headers = {"X-API-Key": api_key}

                response = requests.post(
                    API_URL,
                    files=files,
                    headers=headers,
                    timeout=300
                )

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
else:
    st.info("👆 Enter API key and upload a CSV to begin")
