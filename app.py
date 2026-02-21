from flask import Flask, render_template, request
import PyPDF2
from google import genai  
import os
import re
from skills import skills_list
from jobs_data import jobs

# 1. Setup Client
# Reminder: Regenerate this key in AI Studio as it's been exposed!
client = genai.Client(api_key="AIzaSyDYfvCKjJjc3W4WNrbNyDiBfE3rfClxZsM")

app = Flask(__name__)

def calculate_match(user_skills, job_skills):
    matched_skills = set(user_skills).intersection(set(job_skills))
    match_percentage = (len(matched_skills) / len(job_skills)) * 100 if job_skills else 0
    return round(match_percentage, 2), list(matched_skills)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    # Validation
    if "resume" not in request.files:
        return "No file uploaded", 400
    
    file = request.files["resume"]
    if file.filename == '':
        return "No selected file", 400
    
    # 2. Extract Text from PDF
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = "".join([page.extract_text() or "" for page in pdf_reader.pages])
    except Exception as e:
        print(f"PDF Error: {e}")
        return "Error processing PDF file", 500

    text_lower = text.lower()
    truncated_text = text[:3000]

    # 3. AI Analysis
    prompt = f"""
    You are a professional career advisor. Analyze this resume:
    1. Strengths
    2. Weaknesses
    3. Suggestions
    4. Recommended career path

    Resume:
    {truncated_text}
    """
    
    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",  # Add 'models/' prefix
            contents=prompt,
            
        )
        ai_feedback = response.text
    except Exception as e:
        print("Gemini Error:", e)
        ai_feedback = "AI feedback currently unavailable."

    # 4. Skill Extraction (Regex for exact matches)
    found_skills = []
    for skill in skills_list:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.append(skill)

    # 5. Job Matching Logic
    job_results = []
    for job, required_skills in jobs.items():
        match_percent, matched = calculate_match(found_skills, required_skills)
        job_results.append({
            "job": job,
            "match": match_percent,
            "matched_skills": matched,
            "missing_skills": list(set(required_skills) - set(found_skills))
        })

    job_results.sort(key=lambda x: x["match"], reverse=True)
    recommended_job = job_results[0] if job_results else None

    # 6. Score for Template (Fixes UndefinedError)
    overall_score = recommended_job['match'] if recommended_job else 0

    return render_template(
        "result.html",
        resume_text=text,
        skills=found_skills,
        jobs=job_results,
        overall_score=overall_score,
        recommended_job=recommended_job,
        ai_feedback=ai_feedback
    )

if __name__ == "__main__":
    app.run(debug=True)