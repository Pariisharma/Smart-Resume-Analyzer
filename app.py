from flask import Flask, render_template, request
import PyPDF2
from skills import skills_list


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

    return render_template("result.html", resume_text=text, skills=found_skills)




if __name__ == "__main__":
    app.run(debug=True)
