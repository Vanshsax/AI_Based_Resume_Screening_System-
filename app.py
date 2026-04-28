from flask import Flask, render_template, request, send_file
import os
import re
import time
import tempfile
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
from difflib import SequenceMatcher

# PDF REPORT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import zipfile
from io import BytesIO

app = Flask(__name__)

app.secret_key = os.urandom(24)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------------
# DISPLAY SKILLS (UI FIX)
# -------------------------------
DISPLAY_SKILLS = {
    "cplusplus": "C++",
    "javascript": "JavaScript",
    "nodejs": "Node.js",
    "react": "React",
    "python": "Python",
    "sql": "SQL",
    "machinelearning": "Machine Learning"
}

# -------------------------------
# SKILL SYNONYMS (AI)
# -------------------------------
SKILL_SYNONYMS = {
    "machinelearning": ["ml", "machine learning", "deep learning"],
    "python": ["python", "py"],
    "javascript": ["js", "javascript"],
    "react": ["react", "reactjs", "react.js"],
    "nodejs": ["node", "nodejs", "node.js"],
    "cplusplus": ["c++", "cpp"],
    "sql": ["sql", "mysql", "postgresql"]
}

# -------------------------------
# SKILL CATEGORIES (ADVANCED)
# -------------------------------
SKILL_CATEGORIES = {
    "frontend": ["react", "javascript"],
    "backend": ["nodejs", "python", "sql"],
    "ai": ["machinelearning"]
}

# -------------------------------
# NORMALIZE SKILL
# -------------------------------
def normalize_skill(skill):
    skill = skill.lower().strip()

    replacements = {
        "c++": "cplusplus",
        "node.js": "nodejs",
        "react.js": "react",
        "js": "javascript"
    }

    for k, v in replacements.items():
        skill = skill.replace(k, v)

    skill = re.sub(r'[^a-z0-9]', '', skill)
    return skill

# -------------------------------
# FUZZY MATCH (AI)
# -------------------------------
def is_similar(a, b):
    return SequenceMatcher(None, a, b).ratio() > 0.8

# -------------------------------
# SMART MATCHING
# -------------------------------
def skill_match(skill, resume_text):
    skill = normalize_skill(skill)

    if skill in resume_text:
        return True

    if skill in SKILL_SYNONYMS:
        for variant in SKILL_SYNONYMS[skill]:
            if normalize_skill(variant) in resume_text:
                return True

    # 🔥 FUZZY MATCH
    for word in resume_text.split():
        if is_similar(skill, word):
            return True

    return False

# -------------------------------
# FORMAT FOR UI
# -------------------------------
def format_skills(skill_list):
    return [DISPLAY_SKILLS.get(skill, skill.upper()) for skill in skill_list]

# -------------------------------
# CATEGORY DETECTION
# -------------------------------
def detect_categories(skills):
    category_count = {
        "frontend": 0,
        "backend": 0,
        "ai": 0
    }

    for skill in skills:
        for category, items in SKILL_CATEGORIES.items():
            if skill in items:
                category_count[category] += 1

    return category_count

# -------------------------------
# PDF TEXT EXTRACTION
# -------------------------------
def extract_text_from_pdf(file_path):
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
    except Exception as e:
        print("PDF Error:", e)
    return text

# -------------------------------
# HOME
# -------------------------------
@app.route("/")
def home():
    return render_template("index.html")

# -------------------------------
# ANALYZE
# -------------------------------
@app.route("/analyze", methods=["POST"])
def analyze():

    raw_required = request.form.get("required_skills", "")
    raw_bonus = request.form.get("bonus_skills", "")

    required_skills = [normalize_skill(s) for s in re.split(r'[,\s]+', raw_required) if s.strip()]
    bonus_skills = [normalize_skill(s) for s in re.split(r'[,\s]+', raw_bonus) if s.strip()]

    files = request.files.getlist("resumes")
    results = []

    for file in files:

        if file.filename == "":
            continue

        filename = str(int(time.time())) + "_" + secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        try:
            file.save(file_path)
        except Exception as e:
            print("Save error:", e)
            continue

        original_text = extract_text_from_pdf(file_path)

        if not original_text:
            continue

        # CLEAN TEXT
        resume_text = original_text.lower()
        resume_text = resume_text.replace("c++", "cplusplus")
        resume_text = resume_text.replace("node.js", "nodejs")
        resume_text = resume_text.replace("react.js", "react")

        resume_text = re.sub(r'[^a-z0-9\s]', ' ', resume_text)
        resume_text = re.sub(r'\s+', ' ', resume_text).strip()

        resume_words = set(resume_text.split())

        # MATCHING
        matched_required = []
        matched_bonus = []

        for skill in required_skills:
            if skill_match(skill, resume_text):
                matched_required.append(skill)

        for skill in bonus_skills:
            if skill_match(skill, resume_text):
                matched_bonus.append(skill)

        missing_skills = [s for s in required_skills if s not in matched_required]

        # CATEGORY ANALYSIS
        category_strength = detect_categories(matched_required)

        # SCORING
        unique_matches = len(set(matched_required))
        required_score = (unique_matches / len(required_skills)) * 60 if required_skills else 0

        bonus_score = (len(set(matched_bonus)) / len(bonus_skills)) * 15 if bonus_skills else 0

        keyword_hits = sum(min(resume_text.count(skill), 2) for skill in required_skills)
        keyword_score = min(keyword_hits * 1.5, 10)

        ats_score = sum(3 for sec in ["experience", "education", "project", "skills"] if sec in resume_text)

        word_count = len(resume_words)
        length_score = 5 if 200 < word_count < 1200 else 0

        # 🔥 CATEGORY BONUS
        category_bonus = sum(1 for v in category_strength.values() if v > 0) * 2

        final_score = round(
            required_score +
            bonus_score +
            keyword_score +
            ats_score +
            length_score +
            category_bonus,
            2
        )

        decision = "Selected" if final_score >= 50 else "Rejected"

        results.append({
            "file": file.filename,
            "matched_required_skills": format_skills(matched_required),
            "missing_required_skills": format_skills(missing_skills),
            "final_score": final_score,
            "decision": decision,
            "categories": category_strength
        })

    results.sort(
        key=lambda x: (x["final_score"], len(x["matched_required_skills"])),
        reverse=True
    )

    return render_template("result.html", results=results)

# -------------------------------
# PDF REPORT
# -------------------------------
@app.route("/download_report", methods=["POST"])
def download_report():

    data = request.json

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = temp_file.name

    doc = SimpleDocTemplate(pdf_path)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("AI Resume Screening Report", styles['Title']))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Candidate: {data['file']}", styles['Normal']))
    content.append(Paragraph(f"Score: {data['final_score']}%", styles['Normal']))
    content.append(Paragraph(f"Decision: {data['decision']}", styles['Normal']))

    content.append(Spacer(1, 10))

    content.append(Paragraph("Matched Skills:", styles['Heading3']))
    content.append(Paragraph(", ".join(data['matched_required_skills']) or "None", styles['Normal']))

    content.append(Spacer(1, 10))

    content.append(Paragraph("Missing Skills:", styles['Heading3']))
    content.append(Paragraph(", ".join(data['missing_required_skills']) or "None", styles['Normal']))

    doc.build(content)

    return send_file(pdf_path, as_attachment=True, download_name="resume_report.pdf")

@app.route("/download_all_reports", methods=["POST"])
def download_all_reports():

    results = request.json  # full results list

    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as zf:

        for candidate in results:

            # Create PDF in memory
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            pdf_path = temp_file.name

            doc = SimpleDocTemplate(pdf_path)
            styles = getSampleStyleSheet()

            content = []

            content.append(Paragraph("AI Resume Screening Report", styles['Title']))
            content.append(Spacer(1, 10))

            content.append(Paragraph(f"Candidate: {candidate['file']}", styles['Normal']))
            content.append(Paragraph(f"Score: {candidate['final_score']}%", styles['Normal']))
            content.append(Paragraph(f"Decision: {candidate['decision']}", styles['Normal']))

            content.append(Spacer(1, 10))

            content.append(Paragraph("Matched Skills:", styles['Heading3']))
            content.append(Paragraph(", ".join(candidate['matched_required_skills']) or "None", styles['Normal']))

            content.append(Spacer(1, 10))

            content.append(Paragraph("Missing Skills:", styles['Heading3']))
            content.append(Paragraph(", ".join(candidate['missing_required_skills']) or "None", styles['Normal']))

            doc.build(content)

            # Add to ZIP
            zf.write(pdf_path, arcname=f"{candidate['file']}.pdf")

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name="all_reports.zip",
        mimetype="application/zip"
    )

# -------------------------------
# RUN
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)