from flask import Flask, render_template, request, redirect, url_for
import requests
from PyPDF2 import PdfReader
import os
from dotenv import load_dotenv
import pandas as pd
import markdown

app = Flask(__name__)

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if not GOOGLE_API_KEY:
    raise ValueError("API key not found. Please set the GOOGLE_API_KEY environment variable.")

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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return redirect(request.url)
        
        pdf_file = request.files['pdf_file']
        if pdf_file.filename == '':
            return redirect(request.url)
        
        if pdf_file and pdf_file.filename.endswith('.pdf'):
            pdf_reader = PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            
            prompt = request.form.get('prompt', "Provide a detailed pointwise list of changes mentioned in the release notes along with page numbers and code snippets where applicable. Also, create a tabular representation of the changes.")
            summary = generate_summary(text, prompt)
            
            table_html = ""
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
                    for line in lines[table_start:]:
                        if line.startswith("APPTABFIELDS"):
                            headers = line.replace("APPTABFIELDS", "").split(",")
                        elif line.strip():
                            table_data.append(line.split(","))
                    if headers and table_data:
                        df = pd.DataFrame(table_data, columns=headers)
                        table_html = df.to_html(classes='table table-striped')
            except Exception as e:
                print(f"Table extraction error: {e}")
            
            return render_template('results.html', summary=markdown.markdown(summary), table_html=table_html)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)