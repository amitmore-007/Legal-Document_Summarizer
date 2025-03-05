# from flask import Flask, render_template, request, send_file, redirect, url_for, session
# import os
# from dotenv import load_dotenv
# from groq import Groq
# import pdfplumber
# from io import BytesIO
# from flask_sqlalchemy import SQLAlchemy
# from models import db, Summary

# # Load environment variables
# load_dotenv()
# API_KEY = os.getenv("GROQ_API_KEY")

# # Initialize Flask app
# app = Flask(__name__)
# app.secret_key = 'your_secret_key'

# #Configuration
# app.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///summaries.db"
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False

# #Database Initialization
# db.init_app(app)

# #Table creation
# with app.app_context():
#     db.create_all()

# # Function to extract text from PDF
# def extract_text_from_pdf(pdf_file):
#     try:
#         with pdfplumber.open(pdf_file) as pdf:
#             text = "".join(page.extract_text() or "" for page in pdf.pages)
#         return text.strip() if text else "Error: No readable text found in the PDF."
#     except Exception as e:
#         return f"Error reading PDF file: {e}"

# # Function to split large text into chunks
# def split_text(text, max_words=5000):
#     words = text.split()
#     return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

# # Function to generate summary
# def generate_summary(document_content,filename):
#     client = Groq(api_key=API_KEY)
#     summary_template = (
#         "You are an advanced AI assistant specializing in legal document analysis and summarization. "
#         "Your task is to read the provided legal document and generate a concise, accurate, and well-structured summary. "
#         "Make the summary more to the point and short."
#         "Focus on capturing the key legal themes, critical provisions, and important details while maintaining legal accuracy. "
#         "Ensure the summary is precise, objective, and easy to understand, even for those with limited legal knowledge. "
#         "Highlight any major clauses, legal obligations, conclusions, recommendations, or next steps. "
#         "Ensure that the summary adheres to the conventions and tone of legal language.\n\n"
#         "Legal Document Content:\n{document_content}\n\n"
#         "---\n"
#         "Summary:"
#     )

    
#     chunks = split_text(document_content, max_words=500)
#     summaries = []
    
#     for chunk in chunks:
#         prompt = summary_template.format(document_content=chunk)
#         try:
#             completion = client.chat.completions.create(
#                 model="llama-3.3-70b-versatile",
#                 messages=[{"role": "user", "content": prompt}],
#                 temperature=0.3,
#                 max_tokens=6000,
#                 top_p=1,
#                 stream=True,
#                 stop=None,
#             )
#             response_chunks = [message.choices[0].delta.content or "" for message in completion]
#             summaries.append("".join(response_chunks).strip())
#         except Exception as e:
#             summaries.append(f"Error generating summary: {e}")
    
#     full_summary= " ".join(summaries)

#     #Save to Database
#     new_summary=Summary(filename=filename,original_text=document_content,summary_text=full_summary)
#     db.session.add(new_summary)
#     db.session.commit()

#     return full_summary

# @app.route('/', methods=['GET', 'POST'])
# def index():
#     if request.method == 'POST':
#         file = request.files['file']
#         if file and file.filename.endswith('.pdf'):
#             document_content = extract_text_from_pdf(file)
#             if document_content.startswith("Error"):
#                 return render_template('index.html', error=document_content)
#             summary = generate_summary(document_content,file.filename)
#             return render_template('index.html', legal_text=document_content, summary=summary)
#     return render_template('index.html')

# @app.route('/download', methods=['POST'])
# def download():
#     summary = request.form['summary']
#     file_type = request.form['file_type']
#     filename = f'summary.{file_type}'
    
#     if file_type == 'txt':
#         file_data = summary.encode()
#         return send_file(BytesIO(file_data), as_attachment=True, download_name=filename, mimetype="text/plain")

#     elif file_type == 'pdf':
#         from fpdf import FPDF
#         pdf = FPDF()
#         pdf.add_page()
#         pdf.set_auto_page_break(auto=True, margin=15)
#         pdf.set_font("Arial", size=12)
#         pdf.multi_cell(0, 10, summary)
        
#         output = BytesIO()
#         pdf_output = pdf.output(dest='S').encode('latin1')  # Get PDF as bytes
#         output.write(pdf_output)
#         output.seek(0)  # Reset cursor position

#         return send_file(output, as_attachment=True, download_name=filename, mimetype="application/pdf")

#     else:
#         return "Invalid file type", 400

# @app.route('/summaries')
# def view_summaries():
#     summaries=Summary.query.order_by(Summary.created_at.desc()).all()
#     return render_template('summaries.html',summaries=summaries)

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         session['user'] = request.form['username']
#         return redirect(url_for('index'))
#     return render_template('login.html')

# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         return redirect(url_for('login'))
#     return render_template('register.html')

# if __name__ == '__main__':
#     app.run(debug=True)








from flask import Flask, render_template, request
import os
import pdfplumber
import time
import nltk
import torch
from dotenv import load_dotenv
from bert_score import score as bert_score
from flask_sqlalchemy import SQLAlchemy
from models import db, Summary
from groq import Groq

# Fix for NLTK Punkt Error
nltk.download('punkt')

# Load environment variables
load_dotenv()

import os
 # Ensures .env is properly reloaded

# ✅ Load API Key from .env
API_KEY = "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"

# ✅ Validate API Key
if not API_KEY:
    raise ValueError("❌ API Key is missing or incorrect. Please check your .env file.")

print(f"✅ API Key Loaded: {API_KEY[:5]}...{API_KEY[-5:]}")  # Debugging: Show only partial key


# Initialize Flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///summaries.db"
db.init_app(app)

with app.app_context():
    db.create_all()

def extract_text_from_pdf(pdf_file):
    """Extracts text from a PDF file"""
    with pdfplumber.open(pdf_file) as pdf:
        text = "".join(page.extract_text() or "" for page in pdf.pages)
    return text.strip() if text else "Error: No readable text found."

def split_text(text, max_words=500):
    """Splits text into smaller chunks"""
    words = text.split()
    return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

def compute_bertscore(original, summary):
    """Compute BERTScore between the original and summarized text"""
    P, R, F1 = bert_score([summary], [original], lang="en", model_type="microsoft/deberta-xlarge-mnli")
    return P.item(), R.item(), F1.item()

def generate_summary(document_content, filename):
    """Generates a legal summary and computes BERTScore"""
    client = Groq(api_key=API_KEY)
    original_length = len(document_content.split())
    target_length = original_length // 2  # Ensure summary is half the original length

    summary_template = (
        "You are an advanced AI legal assistant. Your task is to generate a summary that is exactly half the length "
        "of the original document while preserving all critical legal aspects, terminology, clauses, obligations, "
        "and conditions. Ensure the summary remains precise, legally accurate, and maintains legal language. "
        "Provide a structured and professional summary without omitting key legal points. \n\n"
        "Original Legal Document:\n{document_content}\n\n"
        "---\nLegal Summary (Half-length):"
    )

    chunks = split_text(document_content, max_words=500)
    summaries = []
    
    for chunk in chunks:
        prompt = summary_template.format(document_content=chunk)
        
        for attempt in range(3):  # Retry mechanism
            try:
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1000,
                )
                summaries.append(completion.choices[0].message.content.strip())
                break
            except Exception as e:
                if "rate_limit_exceeded" in str(e):
                    time.sleep(10)  # Wait and retry
                elif "invalid_api_key" in str(e):
                    raise ValueError("❌ Invalid API Key! Please check your Groq API Key.")
                else:
                    summaries.append(f"Error generating summary: {e}")
                    break

    full_summary = " ".join(summaries)

    # Calculate Accuracy (Simple Word Count Based)
    accuracy = min(len(full_summary.split()) / target_length, 1.0)

    # Compute BERTScore
    bert_p, bert_r, bert_f1 = compute_bertscore(document_content, full_summary)

    # Print Evaluation Metrics
    print(f"✅ Accuracy: {accuracy:.2f}")
    print(f"✅ BERTScore - Precision: {bert_p:.4f}, Recall: {bert_r:.4f}, F1: {bert_f1:.4f}")

    # Save to Database
    new_summary = Summary(
        filename=filename,
        original_text=document_content,
        summary_text=full_summary,
        accuracy=accuracy
    )
    db.session.add(new_summary)
    db.session.commit()

    return full_summary, accuracy, (bert_p, bert_r, bert_f1)

@app.route('/', methods=['GET', 'POST'])
def index():
    """Main Flask route for file upload and summary generation"""
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.pdf'):
            document_content = extract_text_from_pdf(file)
            if document_content.startswith("Error"):
                return render_template('index.html', error=document_content)
            
            # Generate Summary
            summary, accuracy, (bert_p, bert_r, bert_f1) = generate_summary(document_content, file.filename)

            return render_template(
                'index.html', 
                legal_text=document_content, 
                summary=summary, 
                accuracy=accuracy,
                bert_p=bert_p, 
                bert_r=bert_r, 
                bert_f1=bert_f1
            )
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=False)


