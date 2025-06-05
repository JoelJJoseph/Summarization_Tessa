import streamlit as st
import requests
from PyPDF2 import PdfReader
import os
from dotenv import load_dotenv
import pandas as pd

# Load environment variables from .env file
load_dotenv()

# Retrieve your Google API key securely from environment variables
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Check if API key is set
if not GOOGLE_API_KEY:
    st.error("API key not found. Please set the GOOGLE_API_KEY environment variable.")
    st.stop()

# API configuration
base_url = "https://generativelanguage.googleapis.com"
endpoint = "/v1beta/models/gemini-1.5-flash:generateContent"

def generate_summary(text, prompt):
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "contents": [
            {
                "parts": [
                    {"text": f"{text}\n\n{prompt}"}
                ]
            }
        ]
    }
    try:
        response = requests.post(f"{base_url}{endpoint}?key={GOOGLE_API_KEY}", headers=headers, json=data)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx and 5xx)
        api_response = response.json()

        # Extract summary from API response
        if "candidates" in api_response and len(api_response["candidates"]) > 0:
            content = api_response["candidates"][0].get("content", {})
            if "parts" in content and len(content["parts"]) > 0:
                return content["parts"][0].get("text", "No 'text' field in 'parts'")
            else:
                return "No 'parts' field in 'content'"
        else:
            return "No 'candidates' field in response."
    except requests.exceptions.HTTPError as http_err:
        return f"HTTP error occurred: {http_err}"
    except requests.exceptions.ConnectionError as conn_err:
        return f"Connection error occurred: {conn_err}"
    except requests.exceptions.RequestException as req_err:
        return f"Error occurred: {req_err}"

# Streamlit UI
st.title("Release Note Summarizer and Analyzer")

uploaded_file = st.file_uploader("Upload a Release Note PDF file", type=['pdf'])

if uploaded_file is not None:
    # Read PDF file and extract text using PdfReader
    pdf_reader = PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""

    st.write("PDF text extracted successfully. Showing first 500 characters:")
    st.write(text[:500])  # Displaying first 500 characters for preview

    prompt = st.text_area("Enter your prompt for analysis (e.g., 'Summarize changes and provide in a tabular format'):", value="Provide a detailed pointwise list of changes mentioned in the release notes along with page numbers and code snippets where applicable. Also, create a tabular representation of the changes.")

    if st.button("Generate Summary and Analysis"):
        if prompt:
            with st.spinner("Generating summary and analysis..."):
                summary = generate_summary(text, prompt)
                st.write("Generated Summary and Analysis:")
                st.write(summary)

                # Attempt to extract table data (This part is very basic and may need refinement)
                try:
                    # Very basic table extraction. Needs improvement for complex tables
                    lines = summary.split('\n')
                    table_start = -1
                    for i, line in enumerate(lines):
                        if "APPTABFIELDS" in line:
                            table_start = i
                            break
                    if table_start != -1:
                        table_data = []
                        headers = []
                        for line in lines[table_start:]:
                            if line.startswith("APPTABFIELDS"):
                                headers = line.replace("APPTABFIELDS", "").split(",")
                            elif line.strip():
                                table_data.append(line.split(","))

                        if headers and table_data:
                            df = pd.DataFrame(table_data, columns=headers)
                            st.write("Tabular Representation:")
                            st.dataframe(df)
                except Exception as e:
                    st.write("Could not automatically extract table data. Manual review may be required.")
                    print(f"Table extraction error: {e}")

        else:
            st.warning("Please enter a prompt for summarization and analysis.")