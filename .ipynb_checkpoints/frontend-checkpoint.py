import streamlit as st
import requests

st.title("Phone Number Hashing")

# API config
API_URL = "https://data-hash-app-production.up.railway.app/hash_csv"
API_KEY = st.text_input("Enter your API Key", type="password")

uploaded_file = st.file_uploader("Upload CSV file", type="csv")

if uploaded_file and API_KEY:
    if st.button("Hash CSV"):
        try:
            files = {"file": uploaded_file}
            headers = {"api-key": API_KEY}
            response = requests.post(API_URL, files=files, headers=headers)

            if response.status_code == 200:
                st.success("CSV hashed successfully!")
                st.download_button(
                    label="Download Hashed CSV",
                    data=response.content,
                    file_name="hashed_output.csv",
                    mime="text/csv"
                )
            else:
                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
        except Exception as e:
            st.error(f"Something went wrong: {e}")
