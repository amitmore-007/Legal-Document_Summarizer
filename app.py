from flask import Flask, render_template, request, send_file, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from groq import Groq
import pdfplumber
from io import BytesIO
from fpdf import FPDF  # Import FPDF for PDF generation
import tempfile  # For temporary file handling

# Load environment variables
load_dotenv(override=False)  # Ensures .env is properly reloaded
API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY or "gsk_" not in API_KEY:
    raise ValueError("❌ Invalid API Key! Check your .env file.")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

    def __repr__(self):
        return f"User('{self.username}')"

# Create the database
with app.app_context():
    db.create_all()

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            text = "".join(page.extract_text() or "" for page in pdf.pages)
        return text.strip() if text else "Error: No readable text found in the PDF."
    except Exception as e:
        return f"Error reading PDF file: {e}"

# Function to split large text into chunks
def split_text(text, max_words=5000):
    words = text.split()
    return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

# Function to generate summary
def generate_summary(document_content):
    client = Groq(api_key=API_KEY)
    summary_template = (
        "You are an AI legal assistant specializing in legal document summarization. "
        "Your task is to generate a structured and legally accurate summary of the provided document, "
        "preserving key legal points, obligations, and conclusions.\n\n"
        "Legal Document:\n{document_content}\n\n"
        "---\nSummary:"
    )

    chunks = split_text(document_content, max_words=500)
    summaries = []
    
    for chunk in chunks:
        prompt = summary_template.format(document_content=chunk)
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4000,  # Reduced from 6000 to prevent overuse
                top_p=1
            )
            summaries.append(completion.choices[0].message.content.strip())
        except Exception as e:
            summaries.append(f"Error generating summary: {e}")
    
    return " ".join(summaries)

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.pdf'):
            document_content = extract_text_from_pdf(file)
            if document_content.startswith("Error"):
                return render_template('index.html', error=document_content)
            summary = generate_summary(document_content)
            return render_template('index.html', legal_text=document_content, summary=summary)
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)  # Default method: pbkdf2:sha256
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/download', methods=['POST'])
def download():
    summary = request.form.get('summary', '').strip()  # Ensure we get a valid summary
    file_type = request.form.get('file_type', 'txt').strip().lower()
    filename = f'summary.{file_type}'

    if not summary:
        return "Error: No summary provided.", 400

    if file_type == 'txt':
        # Create a BytesIO object and write the summary to it
        file_data = BytesIO(summary.encode("utf-8"))
        return send_file(
            file_data, 
            as_attachment=True, 
            download_name=filename, 
            mimetype="text/plain"
        )

    elif file_type == 'pdf':
        try:
            # Create a temporary file to store the PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.multi_cell(0, 10, summary)  # Add summary text to PDF
                pdf.output(tmp_file.name)  # Save PDF to the temporary file
                tmp_file.seek(0)  # Reset file pointer

                # Send the temporary file to the client
                return send_file(
                    tmp_file.name, 
                    as_attachment=True, 
                    download_name=filename, 
                    mimetype="application/pdf"
                )
        except Exception as e:
            return f"Error generating PDF: {e}", 500

    else:
        return "Invalid file type", 400

if __name__ == '__main__':
    app.run(debug=True)