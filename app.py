from flask import Flask, render_template, request
import PyPDF2
from google import genai
import os
from skills import skills_list
from jobs_data import jobs


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


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
    file = request.files["resume"]

    pdf_reader = PyPDF2.PdfReader(file)
    text = ""

    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text

    text_lower = text.lower()

    prompt = f"""
    You are a professional career advisor.

    Analyze the following resume and provide:

    1. Strengths
    2. Weaknesses
    3. Suggestions for improvement
    4. Recommended career path

    Resume:
    {text}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        ai_feedback = response.text

    except Exception as e:
        print("Gemini Error:", e)
        ai_feedback = "AI feedback currently unavailable."

    # Skill Extraction
    found_skills = []

    for skill in skills_list:
        if skill in text_lower:
            found_skills.append(skill)

    # Overall Resume Score
    total_system_skills = len(skills_list)
    total_found_skills = len(found_skills)

    overall_score = (
        round((total_found_skills / total_system_skills) * 100, 2)
        if total_system_skills > 0
        else 0
    )

    # Job Matching
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
