import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from pdfminer.high_level import extract_text
import spacy
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flashing messages

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

nlp = spacy.load("en_core_web_sm")

# Ensure uploads directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Check for allowed file types (PDFs)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route for homepage
@app.route('/')
def index():
    return render_template('index.html')

# Route for uploading and processing the PDF
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        page_from = int(request.form['page_from'])
        page_to = int(request.form['page_to'])
        marks = int(request.form['marks'])

        return redirect(url_for('questions', filename=filename, marks=marks, page_from=page_from, page_to=page_to))

    flash('Allowed file types are PDFs')
    return redirect(request.url)

# Extract text from PDF
def extract_pdf_text(filepath, page_from, page_to):
    text = extract_text(filepath, page_numbers=range(page_from - 1, page_to))
    return text

# Analyze the text and extract important sentences
def analyze_text(text):
    doc = nlp(text)
    important_sentences = [sent.text for sent in doc.sents if len(sent) > 10]
    return important_sentences

# Generate fill-in-the-blank questions
def generate_questions(sentences):
    questions = []
    for sentence in sentences:
        doc = nlp(sentence)
        nouns = [token.text for token in doc if token.pos_ == "NOUN"]

        if nouns:
            noun_to_remove = random.choice(nouns)
            question = sentence.replace(noun_to_remove, "______")
            questions.append(question)

    return questions

# Allocate marks to the generated questions
def allocate_marks(questions, total_marks):
    num_questions = len(questions)
    marks_per_question = total_marks // num_questions
    remainder = total_marks % num_questions

    questions_with_marks = []
    for i, question in enumerate(questions):
        allocated_marks = marks_per_question + (1 if i < remainder else 0)
        questions_with_marks.append({
            'number': i + 1,
            'text': question,
            'marks': allocated_marks
        })

    return questions_with_marks

# Route for displaying the generated questions
@app.route('/questions')
def questions():
    filename = request.args.get('filename')
    marks = int(request.args.get('marks'))
    page_from = int(request.args.get('page_from'))
    page_to = int(request.args.get('page_to'))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Extract text from the PDF
    try:
        text = extract_pdf_text(filepath, page_from, page_to)
    except Exception as e:
        flash(f'Error processing PDF: {e}')
        return redirect(url_for('index'))

    # Analyze the text to extract key sentences
    important_sentences = analyze_text(text)

    if not important_sentences:
        flash('No significant sentences found for question generation.')
        return redirect(url_for('index'))

    # Generate questions from the important sentences
    generated_questions = generate_questions(important_sentences)

    if not generated_questions:
        flash('Unable to generate questions from the extracted text.')
        return redirect(url_for('index'))

    # Allocate marks to the generated questions
    questions_with_marks = allocate_marks(generated_questions, marks)

    return render_template('questions.html', questions=questions_with_marks, total_marks=marks)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
