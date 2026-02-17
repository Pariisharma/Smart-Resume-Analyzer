from flask import Flask, render_template, request
import PyPDF2
from skills import skills_list
from jobs_data import jobs

def calculate_match(user_skills, job_skills):
    matched_skills = set(user_skills).intersection(set(job_skills))
    match_percentage = (len(matched_skills) / len(job_skills)) * 100
    return round(match_percentage, 2), list(matched_skills)


app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["resume"]

    pdf_reader = PyPDF2.PdfReader(file)
    text = ""

    for page in pdf_reader.pages:
        text += page.extract_text()

    text_lower = text.lower()

    found_skills = []

    for skill in skills_list:
        if skill in text_lower:
            found_skills.append(skill)

    job_results = []

    for job, required_skills in jobs.items():
        match_percent, matched = calculate_match(found_skills, required_skills)

        job_results.append({
            "job": job,
            "match": match_percent,
            "matched_skills": matched,
            "missing_skills": list(set(required_skills) - set(found_skills))
        })

    return render_template(
        "result.html",
        resume_text=text,
        skills=found_skills,
        jobs=job_results
    )



if __name__ == "__main__":
    app.run(debug=True)
