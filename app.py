from flask import Flask, render_template, request, redirect, url_for, send_file
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import pdfkit
from io import BytesIO

app = Flask(__name__)

# List of required courses for Google Gen AI Study Jam 2024
required_courses = [
    'The Basics of Google Cloud Compute',
    'Get Started with Cloud Storage',
    'Get Started with API Gateway',
    'Get Started with Looker',
    'Get Started with Dataplex',
    'Get Started with Google Workspace Tools',
    'Cloud Functions: 3 Ways',
    'App Engine: 3 Ways',
    'Cloud Speech API: 3 Ways',
    'Monitoring in Google Cloud',
    'Networking Fundamentals on Google Cloud',
    'Analyze Images with the Cloud Vision API',
    'Prompt Design in Vertex AI',
    'Develop GenAI Apps with Gemini and Streamlit',
    'Get Started with Pub/Sub',
    'Level 3: Google Cloud Adventures'
]

# Function to fetch the HTML content of the profile page
def fetch_profile_data(profile_url):
    response = requests.get(profile_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch the profile page. Status Code: {response.status_code}")
    return response.text

# Function to scrape the completed courses and their completion dates
def get_completed_courses(profile_url):
    page_content = fetch_profile_data(profile_url)
    soup = BeautifulSoup(page_content, 'html.parser')

    completed_courses = []

    # Adjust these selectors based on the actual structure of the Google Skill Boost profile page
    for course in soup.find_all('span', class_='ql-title-medium'):
        completed_courses.append(course.text.strip())

    return completed_courses

# Function to process a single profile
def process_profile(profile_name, profile_url):
    try:
        completed_courses = get_completed_courses(profile_url)

        # Calculate progress
        completed_set = set(completed_courses)
        required_set = set(required_courses)
        missing = required_set - completed_set

        total_required = len(required_courses)
        completed_count = len(completed_set.intersection(required_set))
        missing_count = len(missing)
        progress_percentage = (completed_count / total_required) * 100

        return {
            'profile_name': profile_name,
            'profile_url': profile_url,
            'progress': progress_percentage,
            'missing_count': missing_count
        }
    except Exception as e:
        return {
            'profile_name': profile_name,
            'profile_url': profile_url,
            'error': str(e)
        }

# Route to display the form and handle CSV file upload
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Check if a file is uploaded
        if "csv_file" not in request.files:
            return render_template("index.html", error="No file uploaded")

        csv_file = request.files["csv_file"]
        
        if csv_file.filename == "":
            return render_template("index.html", error="No file selected")

        # Save the uploaded CSV file
        csv_file_path = os.path.join("uploads", csv_file.filename)
        csv_file.save(csv_file_path)

        # Read the CSV file
        try:
            df = pd.read_csv(csv_file_path)
            if 'Profile Name' not in df.columns or 'Profile URL' not in df.columns:
                return render_template("index.html", error="CSV must contain 'Profile Name' and 'Profile URL' columns")

            # Process each profile URL in the CSV file
            results = []
            for _, row in df.iterrows():
                profile_name = row['Profile Name']
                profile_url = row['Profile URL']
                result = process_profile(profile_name, profile_url)
                results.append(result)

            # Generate reports in the form of a table
            return render_template("report.html", results=results)

        except Exception as e:
            return render_template("index.html", error=str(e))

    return render_template("index.html")


@app.route("/export_pdf", methods=["POST"])
def export_pdf():
    # Get the data to export from the form
    results = request.form.get('results_data')
    
    rendered = render_template('report_pdf.html', results=eval(results))
    pdf = pdfkit.from_string(rendered, False)

    response = BytesIO(pdf)
    response.seek(0)

    return send_file(response, as_attachment=True, download_name='progress_report.pdf', mimetype='application/pdf')


@app.route("/export_csv", methods=["POST"])
def export_csv():
    # Get the data to export from the form
    results = eval(request.form.get('results_data'))

    # Create a DataFrame from the results
    df = pd.DataFrame(results)

    # Convert the DataFrame to a CSV and send it as a file
    csv_file = BytesIO()
    df.to_csv(csv_file, index=False)
    csv_file.seek(0)

    return send_file(csv_file, as_attachment=True, download_name='progress_report.csv', mimetype='text/csv')


# Run the Flask app
if __name__ == "__main__":
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)
