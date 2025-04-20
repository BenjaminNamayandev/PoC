from flask import Flask, jsonify, send_file, request, url_for
import os, time, re
import PyPDF2, openai, pandas as pd

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            pt = page.extract_text()
            if pt:
                text += pt + "\n"
    return text

def parse_markdown_table(md):
    lines = md.splitlines()
    tbl = []
    headers = []
    in_table = False
    for line in lines:
        if line.strip().startswith("|"):
            parts = [p.strip() for p in line.strip().split("|")[1:-1]]
            if not in_table:
                headers = parts
                in_table = True
            else:
                if all(re.match(r"^[-:]+$", p) for p in parts):
                    continue
                tbl.append(parts)
        elif in_table:
            break
    return pd.DataFrame(tbl, columns=headers)

@app.route("/analyze", methods=["GET"])
def analyze():
    pdf_path = os.path.join(os.path.dirname(__file__), "whs.pdf")
    text = extract_text_from_pdf(pdf_path)
    prompt = (
        "You are a financial analyst. Given the following business case, provide:\n"
        "1. Projected financial statements for the next fiscal year (e.g., income statement).\n"
        "2. A concise analysis (under 500 words) on how to optimize profits.\n\n"
        f"Business case text:\n{text}"
    )
    start = time.time()
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.7,
    )
    elapsed = time.time() - start
    content = resp.choices[0].message.content
    df = parse_markdown_table(content)
    csv_path = os.path.join(os.path.dirname(__file__), "projections.csv")
    df.to_csv(csv_path, index=False)
    full_url = request.url_root.rstrip('/') + url_for('download')
    return jsonify({"analysis": content, "elapsed": elapsed, "spreadsheet_url": full_url})

@app.route("/download", methods=["GET"])
def download():
    path = os.path.join(os.path.dirname(__file__), "projections.csv")
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
