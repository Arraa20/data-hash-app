import streamlit as st
import pandas as pd
import hashlib

st.set_page_config(page_title="Phone Hasher", layout="centered")
st.title("Phone Number Hasher (Manual CSV + API Compatible)")

SECRET_SALT = "my_secret_salt"  # must match API


def sha256_hash(value: str) -> str:
    return hashlib.sha256((value + SECRET_SALT).encode()).hexdigest()


uploaded_file = st.file_uploader("Upload CSV with 'phone' column", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        if "phone" not in df.columns:
            st.error("CSV must contain a 'phone' column")
        else:
            df["hashed_phone"] = df["phone"].astype(str).apply(sha256_hash)
            st.success("Phone numbers hashed successfully!")
            st.dataframe(df)

            # Provide download link
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Hashed CSV",
                data=csv,
                file_name="hashed_phones.csv",
                mime="text/csv"
            )
    except Exception as e:
        st.error(f"Error processing CSV: {e}")
