from flask import Flask, render_template, request
import PyPDF2

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

    return text



if __name__ == "__main__":
    app.run(debug=True)
