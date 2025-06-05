import streamlit as st
import requests
from PyPDF2 import PdfReader
import os
from dotenv import load_dotenv
import pandas as pd
import markdown

# --- Configuration ---
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if not GOOGLE_API_KEY:
    st.error("API key not found. Please set the GOOGLE_API_KEY environment variable in a .env file.")
    st.stop() # Stop the app if no API key

base_url = "https://generativelanguage.googleapis.com"
endpoint = "/v1beta/models/gemini-1.5-flash:generateContent"

# --- Function to Generate Summary ---
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
        response.raise_for_status()
        api_response = response.json()

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

# --- Streamlit UI ---
st.set_page_config(page_title="PDF Summarizer with Gemini", layout="centered")

st.title("📄 PDF Summarizer with Tessa 🚀")

st.write(
    "Upload a PDF document, and I'll summarize it using Google's Gemini 1.5 Flash model. "
    "You can also provide a custom prompt for the summary."
)

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

default_prompt = (
    "Provide a detailed pointwise list of changes mentioned in the release notes along with page numbers "
    "and code snippets where applicable. Also, create a tabular representation of the changes."
)
prompt_input = st.text_area("Custom Prompt for Summary:", value=default_prompt, height=150)

if uploaded_file is not None:
    if st.button("Generate Summary"):
        with st.spinner("Extracting text and generating summary..."):
            try:
                pdf_reader = PdfReader(uploaded_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() or ""
                
                if not text:
                    st.warning("Could not extract any text from the PDF. Please try a different file.")
                else:
                    summary = generate_summary(text, prompt_input)
                    
                    st.subheader("Summary")
                    # Display the summary as Markdown
                    st.markdown(summary)

                    # Attempt to extract and display table
                    try:
                        lines = summary.split('\n')
                        table_start = -1
                        for i, line in enumerate(lines):
                            if "APPTABFIELDS" in line:
                                table_start = i
                                break
                        
                        if table_start != -1:
                            table_data = []
                            headers = []
                            # Find headers and data, skipping empty lines
                            for line in lines[table_start:]:
                                if line.startswith("APPTABFIELDS"):
                                    headers = [h.strip() for h in line.replace("APPTABFIELDS", "").split(",") if h.strip()]
                                elif line.strip(): # Check if line is not empty
                                    row_data = [d.strip() for d in line.split(",") if d.strip()]
                                    if row_data: # Ensure there's actual data after stripping
                                        table_data.append(row_data)

                            if headers and table_data:
                                # Ensure all rows have the same number of columns as headers
                                # This is a basic check; more robust parsing might be needed for complex tables
                                cleaned_table_data = []
                                for row in table_data:
                                    if len(row) == len(headers):
                                        cleaned_table_data.append(row)
                                    else:
                                        st.warning(f"Skipping a row due to column mismatch: {row}. Expected {len(headers)} columns, got {len(row)}.")

                                if cleaned_table_data:
                                    df = pd.DataFrame(cleaned_table_data, columns=headers)
                                    st.subheader("Extracted Table")
                                    st.dataframe(df)
                                else:
                                    st.info("No valid table data found after parsing.")
                            else:
                                st.info("Could not parse a table from the summary. 'APPTABFIELDS' was found, but no complete table data or headers followed.")
                        else:
                            st.info("No 'APPTABFIELDS' keyword found in the summary to extract a table.")
                    except Exception as e:
                        st.error(f"Error during table extraction: {e}")

            except Exception as e:
                st.error(f"An error occurred: {e}")
else:
    st.info("Please upload a PDF file to get started.")

st.markdown("---")
