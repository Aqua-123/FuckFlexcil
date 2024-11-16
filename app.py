from flask import (
    Flask,
    request,
    render_template,
    send_file,
)
from PyPDF2 import PdfReader, PdfWriter
import os
import uuid
import time
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
CLEANED_FOLDER = "cleaned"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CLEANED_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["CLEANED_FOLDER"] = CLEANED_FOLDER


@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        # Check if a file was uploaded
        if "file" not in request.files:
            return "No file uploaded", 400

        file = request.files["file"]
        if file.filename == "":
            return "No selected file", 400

        if file:
            unique_id = str(uuid.uuid4())
            input_filename = f"{unique_id}_{file.filename}"
            input_path = os.path.join(UPLOAD_FOLDER, input_filename)
            file.save(input_path)

            output_filename = f"cleaned_{input_filename}"
            output_path = os.path.join(CLEANED_FOLDER, output_filename)
            crop_pdf(input_path, output_path)

            return render_template(
                "download.html",
                cleaned_file=output_filename,
            )

    return render_template("index.html")


def crop_pdf(input_pdf_path, output_pdf_path, crop_height=30):
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        original_media_box = page.mediabox
        page.cropbox.lower_left = (0, crop_height)
        page.cropbox.upper_right = (
            original_media_box.width,
            original_media_box.height - crop_height,
        )
        writer.add_page(page)

    with open(output_pdf_path, "wb") as output_pdf:
        writer.write(output_pdf)


@app.route("/download/<filename>")
def download_file(filename):
    cleaned_path = os.path.join(app.config["CLEANED_FOLDER"], filename)
    return send_file(cleaned_path, as_attachment=True)


def delete_old_files():
    """Deletes files in UPLOAD_FOLDER and CLEANED_FOLDER older than 1 hour."""
    now = time.time()
    folders = [UPLOAD_FOLDER, CLEANED_FOLDER]
    for folder in folders:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                file_age = now - os.path.getmtime(file_path)
                if file_age > 3600:  # 3600 seconds = 1 hour
                    os.remove(file_path)
                    print(f"Deleted old file: {file_path}")


if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(delete_old_files, "interval", minutes=10)  # Run every 10 minutes
    scheduler.start()
    try:
        app.run(debug=True, threaded=True)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
