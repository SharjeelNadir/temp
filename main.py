from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import FileResponse

import requests
import json
import mysql.connector
from dateutil.parser import parse as parse_date
import re
import os 
import shutil
import glob
from typing import List
from datetime import datetime, timedelta, date
import httpx



app = FastAPI()

def connect_to_database():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Sharjeel0302",
        database="cv_database"  # Make sure to specify your database name here
    )

templates = Jinja2Templates(directory="templates")  # Specify the directory where your HTML templates are stored
app.mount("/static", StaticFiles(directory="static"), name="static")

EXTERNAL_API_URL = "http://192.168.10.145:8000/generate"

stored_json_data = None  # Variable to store the JSON data from /upload-to-external
uploaded_campaign_number = 1  # Global variable to store campaign number
file_name=""
UPLOAD_FOLDER = "cvs"
# Create the upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def validate_email(email):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise ValueError("Invalid email format")
def parse_and_convert_date(date_str):
    # Check if the input matches the format "Dec/2001" or "December/2001"
    match = re.match(r"(\w{3,})/(\d{4})", date_str)
    if match:
        month_str = match.group(1)
        year_str = match.group(2)

        # Convert month string to numerical month
        month_lookup = {
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 
            'may': '05', 'jun': '06', 'jul': '07', 'aug': '08', 
            'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
            'january': '01', 'february': '02', 'march': '03', 
            'april': '04', 'june': '06', 'july': '07', 'august': '08', 
            'september': '09', 'october': '10', 'november': '11', 'december': '12'
        }

        month_num = month_lookup.get(month_str.lower()[:3])
        if not month_num:
            return None  # Invalid month string

        return f"{month_num}/{year_str}"

    try:
        # Attempt to parse with dateutil.parser
        parsed_date = parse_date(date_str, fuzzy=True).date().isoformat()
        return parsed_date
    except ValueError:
        return None  # Handle any other specific cases or formats as needed

# functions for uploading and storing in database 
@app.post("/upload-to-external/")
async def upload_to_external(files: List[UploadFile] = File(...), campaign_number: int = Form(...)):
    global stored_json_data, uploaded_campaign_number
    uploaded_campaign_number = campaign_number
    #stored_json_data = []  # Reset the stored JSON data for each new upload
    global file_name
    for file in files:
        try:
            # Save the file temporarily
            file_location = os.path.join(UPLOAD_FOLDER, file.filename)
            with open(file_location, "wb") as f:
                f.write(file.file.read())

       
            # Prepare the file for the external API
            with open(file_location, "rb") as f:
                print("------------------------------------------------------------------------------------------------------------------")
                print(f"Sending file: {file.filename}, Content-Type: {file.content_type}")
                file_name=file.filename
                response = requests.post(EXTERNAL_API_URL, files={'resumes': (file.filename, f, file.content_type)})
                response.raise_for_status()  # Raise an error for bad status codes
                print(response.json())
                result = response.json()  # Store the JSON response
                stored_json_data=result
                store()
            # Optionally remove the file after processing
            #os.remove(file_location)

        except requests.exceptions.RequestException as e:
            print(f"RequestException: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            print(f"General Exception: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return HTMLResponse(content="""
        <html>
        <head>
            <title>Resume Uploaded</title>
        </head>
        <body style="background-color: black; color: white; font-family: Arial, sans-serif; text-align: center; padding: 20px;">
            <h2>Success!</h2>
            <p>Resume Uploaded Successfully</p>
            <p><a href="/">Back to Main Menu </a></p>
        </body>
        </html>
    """)


@app.get("/store_to_database")
def store():
    global stored_json_data
    global file_name
    print("*******************************************************")
    #print(stored_json_data)
    print(uploaded_campaign_number)
    if not stored_json_data:
        return {"message": "No JSON data available"}

    try:
        # print("HELLOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO")
        json_data = stored_json_data[0]  # Assuming stored_json_data is a list with a single string element
        data = json.loads(json_data)
        # print(uploaded_campaign_number)
        # Extract variables from JSON data
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        address = data.get('address')
        experiences = data.get('experiences', [])
        skills = data.get('skills', [])
        educations = data.get('educations', [])
        certifications = data.get('certifications', [])
        research = data.get('research', [])
        
        # Validate name and email
        if not name:
            raise HTTPException(status_code=400, detail="Name cannot be empty")

        # Connect to MySQL database
        db_connection = connect_to_database()
        cursor = db_connection.cursor()
        
        try:
            
            # Insert candidate information into 'candidates' table
            insert_candidate_query = """
                 INSERT INTO candidates (name, email, phone, address, campaign_number,file_name)
                    VALUES (%s, %s, %s, %s, %s,%s)
                """

            candidate_data = (name, email, phone, address, uploaded_campaign_number,file_name)
            cursor.execute(insert_candidate_query, candidate_data)
            candidate_id = cursor.lastrowid

            # Function to parse and convert dates
            def parse_and_convert_date(date_str):
                try:
                    if date_str:
                        return parse_date(date_str).date()
                except ValueError:
                    return None

            # Insert experiences into 'experiences' table
            for experience in experiences:
                start_date = parse_and_convert_date(experience.get('Start Date', ''))
                end_date = parse_and_convert_date(experience.get('End Date', ''))
                if start_date == end_date:
                    end_date = None
                insert_experience_query = """
                    INSERT INTO experiences (candidate_id, organization_name, designation, start_date, end_date, summary)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                experience_data = (
                    candidate_id,
                    experience.get('Organization Name', ''),
                    experience.get('Designation', ''),
                    start_date,
                    end_date,
                    experience.get('Summary', '')
                )
                cursor.execute(insert_experience_query, experience_data)

            # Insert skills into 'skills' table
            for skill in skills:
                insert_skill_query = """
                    INSERT INTO skills (candidate_id, skill)
                    VALUES (%s, %s)
                """
                skill_data = (candidate_id, skill)
                cursor.execute(insert_skill_query, skill_data)

            # Insert educations into 'educations' table
            for education in educations:
                start_date = parse_and_convert_date(education.get('Start Date', ''))
                end_date = parse_and_convert_date(education.get('End Date', ''))
                if start_date == end_date:
                    end_date = None
                insert_education_query = """
                    INSERT INTO educations (candidate_id, institute_name, degree, start_date, end_date, summary)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                education_data = (
                    candidate_id,
                    education.get('Institute Name', ''),
                    education.get('Degree', ''),
                    start_date,
                    end_date,
                    education.get('Summary', '')
                )
                cursor.execute(insert_education_query, education_data)

            # Insert certifications into 'certifications' table
            for certification in certifications:
                insert_certification_query = """
                    INSERT INTO certifications (candidate_id, certification)
                    VALUES (%s, %s)
                """
                certification_data = (candidate_id, certification)
                cursor.execute(insert_certification_query, certification_data)

            # Insert research into 'research' table
            for research_item in research:
                insert_research_query = """
                    INSERT INTO research (candidate_id, research_title)
                    VALUES (%s, %s)
                """
                research_data = (candidate_id, research_item)
                cursor.execute(insert_research_query, research_data)

            # Commit changes and close cursor and connection
            db_connection.commit()
            cursor.close()
            db_connection.close()

            return {"message": "Data saved to database successfully"}

        except mysql.connector.Error as e:
            return {"error": f"MySQL Error: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to insert data into database: {str(e)}"}

    except IndexError:
        return {"error": "No JSON data found in the stored data"}
    except json.JSONDecodeError as e:
        return {"error": "Failed to parse stored JSON data: " + str(e)}



#setting score 
def get_skills():
    db_connection = connect_to_database()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT skill FROM skills")
    skills = [row["skill"] for row in cursor.fetchall()]
    cursor.close()
    db_connection.close()
    return skills

@app.get("/set-score", response_class=HTMLResponse)
async def set_score(request: Request):
    skills = get_skills()
    return templates.TemplateResponse("set_score.html", {"request": request, "skills": skills})

@app.post("/apply-scoring/", response_class=HTMLResponse)
async def apply_scoring(
    
    score: int = Form(...), 
    experience_years: int = Form(None), 
    skills: str = Form(None), 
    education_type: str = Form(None), 
    certification: str = Form(None), 
    research_years: str = Form(None),
    campaign_number: int = Form(...),  # Assuming campaign number is always provided
):
    try:
        db_connection = connect_to_database()
        cursor = db_connection.cursor()

       
        fields = [
            ("experience", experience_years, f"{experience_years} "),
            ("skills", skills, skills),
            ("education", education_type, education_type),
            ("certifications", certification, certification),
            ("research", research_years, f"{research_years} ")
        ]

        for field, value, skill_name in fields:
            if value is not None:
                cursor.execute("SELECT id FROM scoring WHERE typee=%s AND skill_name=%s AND campaign_number=%s", (field, skill_name, campaign_number))
                result = cursor.fetchone()

                if result:
                    cursor.execute("UPDATE scoring SET score=%s WHERE id=%s", (score, result[0]))
                else:
                    cursor.execute("INSERT INTO scoring (typee, skill_name, score, campaign_number) VALUES (%s, %s, %s, %s)", (field, skill_name, score, campaign_number))

        db_connection.commit()
        cursor.close()
        db_connection.close()

        return """
        <html>
        <head>
            <title>Scoring Rules</title>
        </head>
        <body style="background-color: black; color: white; font-family: Arial, sans-serif; text-align: center; padding: 20px;">
            <h2>Success!</h2>
            <p>Scoring rules updated successfully</p>
            <p><a href="/set-score">Back to Scoring Page </a></p>
        </body>
        </html>
        """

    except mysql.connector.Error as e:
        print(f"MySQL Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"MySQL Error: {str(e)}")
    except Exception as e:
        print(f"Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to apply scoring: {str(e)}")










#resume ko score karny waly functions 

# Function to calculate skill scores
def skills_calculate(cursor, candidate_id, campaign_number):
    skill_score = 0
    cursor.execute("SELECT skill_name, score FROM scoring WHERE typee = 'skills' AND campaign_number = %s", (campaign_number,))
    scoring_results = cursor.fetchall()
    for scoring_row in scoring_results:
        skill_name = scoring_row['skill_name']
        score = scoring_row['score']
        cursor.execute("SELECT COUNT(*) AS skill_count FROM skills WHERE candidate_id = %s AND skill = %s", (candidate_id, skill_name))
        skill_count_result = cursor.fetchone()
        skill_count = skill_count_result['skill_count']
        skill_score += score * skill_count
    return skill_score

# Function to calculate experience scores
def experience_calculate(cursor, candidate_id, campaign_number):
    highest_experience_score = 0
    cursor.execute("SELECT skill_name, score FROM scoring WHERE typee = 'experience' AND campaign_number = %s ORDER BY skill_name DESC", (campaign_number,))
    scoring_results = cursor.fetchall()
    cursor.execute("SELECT start_date, end_date FROM experiences WHERE candidate_id = %s", (candidate_id,))
    experiences = cursor.fetchall()
    total_experience = 0
    for experience in experiences:
        start_date = experience['start_date']
        end_date = experience['end_date']
        if start_date is None:
            continue
        if end_date is None:
            end_date = date.today()
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        experience_years = (end_date - start_date).days / 365.25
        total_experience += experience_years
    for scoring_row in scoring_results:
        experience_criteria = int(scoring_row['skill_name'])
        score = scoring_row['score']
        if total_experience >= experience_criteria:
            highest_experience_score = max(highest_experience_score, score)
    return highest_experience_score

# Function to calculate research scores
def research_calculate(cursor, candidate_id, campaign_number):
    research_score = 0
    cursor.execute("SELECT skill_name, score FROM scoring WHERE typee = 'research' AND campaign_number = %s", (campaign_number,))
    scoring_results = cursor.fetchall()
    cursor.execute("SELECT research_title FROM research WHERE candidate_id = %s", (candidate_id,))
    candidate_researches = cursor.fetchall()
    for scoring_row in scoring_results:
        research_name = scoring_row['skill_name']
        score = scoring_row['score']
        cursor.execute("SELECT COUNT(*) AS research_count FROM research WHERE candidate_id = %s AND research_title = %s", (candidate_id, research_name))
        research_count_result = cursor.fetchone()
        research_count = research_count_result['research_count']
        research_score += score * research_count
    return research_score

# Function to calculate education scores
def education_calculate(cursor, candidate_id, campaign_number):
    highest_education_score = 0
    cursor.execute("SELECT skill_name, score FROM scoring WHERE typee = 'education' AND campaign_number = %s", (campaign_number,))
    scoring_results = cursor.fetchall()
    cursor.execute("SELECT institute_name, degree FROM educations WHERE candidate_id = %s", (candidate_id,))
    candidate_educations = cursor.fetchall()
    for scoring_row in scoring_results:
        education_name = scoring_row['skill_name'].strip().lower()
        score = scoring_row['score']
        for education in candidate_educations:
            institute_name = (education['institute_name'] or '').strip().lower()
            degree = (education['degree'] or '').strip().lower()
            if education_name in institute_name or education_name in degree:
                if score > highest_education_score:
                    highest_education_score = score
    return highest_education_score

# Function to calculate certification scores
def certification_calculate(cursor, candidate_id, campaign_number):
    highest_certification_score = 0
    cursor.execute("SELECT skill_name, score FROM scoring WHERE typee = 'certification' AND campaign_number = %s", (campaign_number,))
    scoring_results = cursor.fetchall()
    cursor.execute("SELECT certification FROM certifications WHERE candidate_id = %s", (candidate_id,))
    candidate_certifications = cursor.fetchall()
    for scoring_row in scoring_results:
        certification_name = scoring_row['skill_name'].strip().lower()
        score = scoring_row['score']
        for certification in candidate_certifications:
            certification_entry = (certification['certification'] or '').strip().lower()
            if certification_name in certification_entry:
                if score > highest_certification_score:
                    highest_certification_score = score
    return highest_certification_score

# Master function to calculate all scores
def calculate_all_scores():
    db_connection = None
    try:
        db_connection = connect_to_database()
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute("SELECT id, campaign_number FROM candidates")
        candidates = cursor.fetchall()
        
        for candidate in candidates:
            candidate_id = candidate['id']
            campaign_number = candidate['campaign_number']
            
            total_score = (
                skills_calculate(cursor, candidate_id, campaign_number) +
                experience_calculate(cursor, candidate_id, campaign_number) +
                research_calculate(cursor, candidate_id, campaign_number) +
                education_calculate(cursor, candidate_id, campaign_number) +
                certification_calculate(cursor, candidate_id, campaign_number)
            )
            
            cursor.execute("UPDATE candidates SET candidate_score = %s WHERE id = %s", (total_score, candidate_id))
        
        db_connection.commit()
    except mysql.connector.Error as e:
        print(f"Error calculating all scores: {e}")
    finally:
        if db_connection and db_connection.is_connected():
            cursor.close()
            db_connection.close()

@app.get("/get-scores", response_class=HTMLResponse)
async def list_score(request: Request, campaign_number: int = None, sort: str = None):
    try:
        calculate_all_scores()
        db_connection = connect_to_database()
        cursor = db_connection.cursor(dictionary=True)
        if campaign_number:
            cursor.execute("SELECT id, name, candidate_score FROM candidates WHERE campaign_number = %s", (campaign_number,))
        else:
            cursor.execute("SELECT id, name, candidate_score FROM candidates")
        candidates = cursor.fetchall()
        db_connection.close()
        return templates.TemplateResponse("display_scores.html", {
            "request": request,
            "candidates": candidates
        })
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"MySQL Error: {str(e)}")







@app.get("/view-candidate/{candidate_id}", response_class=HTMLResponse)
async def view_candidate(request: Request, candidate_id: int):
    try:
        db_connection = connect_to_database()
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute("SELECT id, name, candidate_score FROM candidates WHERE id = %s", (candidate_id,))
        candidate = cursor.fetchone()
        db_connection.close()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        return templates.TemplateResponse("view_candidate.html", {
            "request": request,
            "candidate": candidate
        })
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"MySQL Error: {str(e)}")











EXTERNAL_API_URL_CHAT_BOT = "http://192.168.10.145:8000/run_open_query"


import json
import re




def insert_candidate_questions(candidate_id, questions):
    try:
        # Connect to the database
        connection = connect_to_database()
        cursor = connection.cursor()

        # Iterate through each question and insert into the table
        for question in questions:
            question_text = question['question']
            correct_answer = question['options'][question['answer']]['text']
            selected_answer = question.get('selected_answer', '')
            is_correct = 'Yes' if selected_answer == correct_answer else 'No' if selected_answer else 'Not Answered'

            # Insert query
            insert_query = "INSERT INTO candidate_questions (candidate_id, question_text, correct_answer, selected_answer, is_correct) VALUES (%s, %s, %s, %s, %s)"
            data = (candidate_id, question_text, correct_answer, selected_answer, is_correct)
            cursor.execute(insert_query, data)
        
        # Commit changes to the database
        connection.commit()
        print(f"{len(questions)} questions inserted successfully for candidate ID {candidate_id}")

    except mysql.connector.Error as error:
        print(f"Error inserting data into MySQL table: {error}")

    finally:
        if (connection.is_connected()):
            cursor.close()
            connection.close()
            print("MySQL connection is closed")






mcq_data=" "


def extract_json_from_text(text):
    try:
        
        data = json.loads(text)
        return data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None
    except Exception as e:
        print(f"General Exception: {e}")
        return None






@app.post("/generate-mcq/", response_class=HTMLResponse)
async def generate_mcq(request: Request, field_of_expertise: str = Form(...), difficulty_level: int = Form(...)):
    global mcq_data
    try:
        # Prepare the text to pass to the external API
        text_to_pass = f"Generate me 5 random mcqs related to {field_of_expertise} with level {difficulty_level} difficulty only provide json along with answer and the response should not have anything else apart from json"

        # Make a POST request to the external API
        response = requests.post(EXTERNAL_API_URL_CHAT_BOT, data={"text": text_to_pass})
        response.raise_for_status()  # Raise an error for bad status codes
        
        # Extract JSON from the response text
        print("===================================================")
        print(response.text)
        print("===================================================")

        mcq_data = extract_json_from_text(response.text)
        
        print(mcq_data)
        print(type(mcq_data))
        insert_candidate_questions(1,mcq_data)
        # if not mcq_data or not isinstance(mcq_data, list):
        #     raise HTTPException(status_code=500, detail="Failed to extract MCQ data from response.")

        # Render the template with the MCQ data
        return templates.TemplateResponse("upload_cv.html", {"request": request, "mcq_data": mcq_data})

    except requests.exceptions.RequestException as e:
        print(f"RequestException: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    except Exception as e:
        print(f"General Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))














































@app.get("/upload-cv", response_class=HTMLResponse)
async def upload_cv_page(request: Request):
    return templates.TemplateResponse("upload_cv.html", {"request": request})


@app.get("/check-database", response_class=HTMLResponse)
async def check_database(request: Request, candidate_id: int = 1, campaign_number: int = None):
    try:
        db_connection = connect_to_database()
        cursor = db_connection.cursor(dictionary=True)
        
        # Get candidates based on campaign number
        if campaign_number:
            cursor.execute("SELECT * FROM candidates WHERE campaign_number = %s", (campaign_number,))
        else:
            cursor.execute("SELECT * FROM candidates")
        candidates = cursor.fetchall()
        
        # If no candidates found, return empty response
        if not candidates:
            return templates.TemplateResponse("check_database.html", {
                "request": request,
                "candidate": None,
                "experiences": [],
                "skills": [],
                "educations": [],
                "certifications": [],
                "research": [],
                "prev_id": candidate_id,
                "next_id": candidate_id,
                "campaign_number": campaign_number
            })
        
        # Get candidate data by id
        cursor.execute("SELECT * FROM candidates WHERE id = %s AND campaign_number = %s", (candidate_id, campaign_number))
        candidate = cursor.fetchone()
        
        # If candidate not found with given id, use the first candidate in the list
        if not candidate:
            candidate = candidates[0]
            candidate_id = candidate['id']
        
        # Get related data for the candidate
        cursor.execute("SELECT * FROM experiences WHERE candidate_id = %s", (candidate_id,))
        experiences = cursor.fetchall()
        
        cursor.execute("SELECT * FROM skills WHERE candidate_id = %s", (candidate_id,))
        skills = cursor.fetchall()
        
        cursor.execute("SELECT * FROM educations WHERE candidate_id = %s", (candidate_id,))
        educations = cursor.fetchall()
        
        cursor.execute("SELECT * FROM certifications WHERE candidate_id = %s", (candidate_id,))
        certifications = cursor.fetchall()
        
        cursor.execute("SELECT * FROM research WHERE candidate_id = %s", (candidate_id,))
        research = cursor.fetchall()
        
        # Get the candidate index
        candidate_index = next((index for (index, d) in enumerate(candidates) if d["id"] == candidate_id), 0)
        
        # Determine previous and next candidate IDs
        prev_id = candidates[candidate_index - 1]["id"] if candidate_index > 0 else candidates[-1]["id"]
        next_id = candidates[candidate_index + 1]["id"] if candidate_index < len(candidates) - 1 else candidates[0]["id"]
        
        db_connection.close()
        
        return templates.TemplateResponse("check_database.html", {
            "request": request,
            "candidate": candidate,
            "experiences": experiences,
            "skills": skills,
            "educations": educations,
            "certifications": certifications,
            "research": research,
            "prev_id": prev_id,
            "next_id": next_id,
            "campaign_number": campaign_number
        })
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"MySQL Error: {str(e)}")

@app.get("/view-resume/{file_name}")
async def view_resume(file_name: str):
    resume_path = os.path.join("cvs", file_name)
    if os.path.exists(resume_path):
        return FileResponse(resume_path, media_type="application/pdf")
    else:
        raise HTTPException(status_code=404, detail="Resume not found")

@app.get("/list-candidates", response_class=HTMLResponse)
async def list_candidates(request: Request, campaign_number: int = None, sort: str = None):
    try:
        db_connection = connect_to_database()
        cursor = db_connection.cursor(dictionary=True)
        
        # Get candidates based on campaign number and sorting order
        if campaign_number:
            cursor.execute("SELECT * FROM candidates WHERE campaign_number = %s", (campaign_number,))
        else:
            cursor.execute("SELECT * FROM candidates")
        
        candidates = cursor.fetchall()
        
        if sort == "asc":
            candidates = sorted(candidates, key=lambda x: x["campaign_number"])
        elif sort == "desc":
            candidates = sorted(candidates, key=lambda x: x["campaign_number"], reverse=True)
        
        db_connection.close()
        
        return templates.TemplateResponse("list_candidates.html", {
            "request": request,
            "candidates": candidates
        })
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"MySQL Error: {str(e)}")







@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})





@app.post("/update-table")
async def update_table_data(request: Request):
    try:
        data = await request.json()
        table_id = data.get('tableId')
        table_data = data.get('data')
        
        if not table_id or not table_data:
            raise HTTPException(status_code=400, detail="Invalid request data")
        
        db_connection = connect_to_database()
        cursor = db_connection.cursor()

        try:
            for row in table_data:
                row_id = row.get('id')
                if table_id == 'candidateTable':
                    candidate_id = row.get('id')
                    cursor.execute("""
                        UPDATE candidates
                        SET name = %s, email = %s, phone = %s, address = %s, campaign_number = %s
                        WHERE id = %s
                    """, (row.get('Name'), row.get('Email'), row.get('Phone'), row.get('Address'), row.get('Campaign Number'), candidate_id))
                elif table_id == 'experiencesTable':
                    cursor.execute("""
                        UPDATE experiences
                        SET organization_name = %s, designation = %s, start_date = %s, end_date = %s, summary = %s
                        WHERE id = %s
                    """, (row.get('Organization Name'), row.get('Designation'), row.get('Start Date'), row.get('End Date'), row.get('Summary'), row_id))
                elif table_id == 'skillsTable':
                    cursor.execute("""
                        UPDATE skills
                        SET skill = %s
                        WHERE id = %s
                    """, (row.get('Skill'), row_id))
                elif table_id == 'educationsTable':
                    cursor.execute("""
                        UPDATE educations
                        SET institute_name = %s, degree = %s, start_date = %s, end_date = %s, summary = %s
                        WHERE id = %s
                    """, (row.get('Institute Name'), row.get('Degree'), row.get('Start Date'), row.get('End Date'), row.get('Summary'), row_id))
                elif table_id == 'certificationsTable':
                    cursor.execute("""
                        UPDATE certifications
                        SET certification = %s
                        WHERE id = %s
                    """, (row.get('Certification'), row_id))
                elif table_id == 'researchTable':
                    cursor.execute("""
                        UPDATE research
                        SET research_title = %s
                        WHERE id = %s
                    """, (row.get('Research Title'), row_id))

            db_connection.commit()
            cursor.close()
            db_connection.close()

            return JSONResponse(content={"message": "Data updated successfully"})
        
        except mysql.connector.Error as e:
            db_connection.rollback()
            cursor.close()
            db_connection.close()
            raise HTTPException(status_code=500, detail=f"MySQL Error: {str(e)}")
        except Exception as e:
            db_connection.rollback()
            cursor.close()
            db_connection.close()
            raise HTTPException(status_code=500, detail=f"Failed to update data: {str(e)}")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
