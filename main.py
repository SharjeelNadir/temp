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
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import List, Dict
import json
import re
import time



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
EXTERNAL_API_URL_CHAT_BOT = "http://192.168.10.145:8000/run_open_query"

stored_json_data = None  # Variable to store the JSON data from /upload-to-external
uploaded_campaign_number = 1  # Global variable to store campaign number
file_name=""
current_candidate_id=None
UPLOAD_FOLDER = "cvs"



# Create the upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)



def validate_email(email):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise ValueError("Invalid email format")

def parse_and_convert_date(date_str):
    if isinstance(date_str, int):
        date_str = str(date_str)

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



@app.get("/get-campaign-numbers")
async def get_campaign_numbers():
    try:
        db_connection = connect_to_database()
        cursor = db_connection.cursor(dictionary=True)

        # Fetch campaigns and their statuses
        cursor.execute("""
            SELECT campaign_number, status, expiration_date
            FROM campaignnumber
        """)
        campaigns = cursor.fetchall()

        # Update the status of expired campaigns
        now = datetime.now().date()  # Get the current date (ignoring time)
        for campaign in campaigns:
            exp_date = campaign['expiration_date']
            if isinstance(exp_date, datetime):
                exp_date = exp_date.date()  # Convert to date if it is a datetime object
            print(exp_date)
            print(now)
            if(exp_date<now):
                print("1")
            if campaign['status'] == 'Ongoing' and exp_date < now:
                print("Hi",exp_date)
                cursor.execute("""
                    UPDATE campaignnumber
                    SET status = 'Expired'
                    WHERE campaign_number = %s
                """, (campaign['campaign_number'],))
                db_connection.commit()

        # Fetch the updated list of ongoing campaigns
        cursor.execute("""
            SELECT campaign_number
            FROM campaignnumber
            WHERE status = 'Ongoing'
        """)
        ongoing_campaigns = cursor.fetchall()

        db_connection.close()
        return JSONResponse(content=ongoing_campaigns)
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")



@app.post("/upload-to-external/")
async def upload_to_external(files: List[UploadFile] = File(...), campaign_number: int = Form(...)):
    global stored_json_data, uploaded_campaign_number
    uploaded_campaign_number = campaign_number
    # stored_json_data = []  # Reset the stored JSON data for each new upload
    stored_json_data=None
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
                print("----------------------------------------------------------------------------------")
                result = response.json()  # Store the JSON response
                response_str = json.dumps(result)
                tokens = response_str.split()
                
                print("Total number of tokens in response.json():", len(tokens))
                
                stored_json_data=result
                print(type(stored_json_data))
                print("*"*50)
                print("Length of stored JSON data:", len(stored_json_data[0]))
                print("*"*50)
                store()
                generate_mcq()
                return RedirectResponse(url='/mcqs')
            # Optionally remove the file after processing
            #os.remove(file_location)

        except requests.exceptions.RequestException as e:
            print(f"RequestException: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            print(f"General Exception: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # return HTMLResponse(content="""
    #     <html>
    #     <head>
    #         <title>Resume Uploaded</title>
    #     </head>
    #     <body style="background-color: black; color: white; font-family: Arial, sans-serif; text-align: center; padding: 20px;">
    #         <h2>Success!</h2>
    #         <p>Resume Uploaded Successfully</p>
    #         <p><a href="/">Back to Main Menu </a></p>
    #     </body>
    #     </html>
    # """)

@app.get("/store_to_database")
def store():
    global stored_json_data, file_name, current_candidate_id
    
    if not stored_json_data:
        return {"message": "No JSON data available"}
    
    try:
        json_data = stored_json_data[0]  # Assuming stored_json_data is a list with a single string element
        
        # Print the JSON data for debugging
        print("Stored JSON data:", json_data)
        
        # Parse JSON data
        data = json.loads(json_data)
        

        # Print the parsed data for debugging
        print("Parsed JSON data:", data)
        
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
        validate_email(email)

        # Connect to MySQL database
        db_connection = connect_to_database()
        cursor = db_connection.cursor()

        try:
            # Check if candidate with the same name and campaign number already exists
            check_candidate_query = """
                SELECT id FROM candidates 
                WHERE name = %s AND campaign_number = %s
            """
            cursor.execute(check_candidate_query, (name, uploaded_campaign_number))
            existing_candidate = cursor.fetchone()
            
            if existing_candidate:
                candidate_id = existing_candidate[0]
            else:
                # Insert candidate information into 'candidates' table
                insert_candidate_query = """
                    INSERT INTO candidates (name, email, phone, address, campaign_number, file_name)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                candidate_data = (name, email, phone, address, uploaded_campaign_number, file_name)
                cursor.execute(insert_candidate_query, candidate_data)
                candidate_id = cursor.lastrowid
                current_candidate_id = candidate_id

            # Function to parse and convert dates
            def parse_and_convert_date(date_str):
                if isinstance(date_str, int):
                    date_str = str(date_str)
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
            db_connection.rollback()
            print(f"MySQL Error: {str(e)}")
            return {"error": f"MySQL Error: {str(e)}"}
        except Exception as e:
            db_connection.rollback()
            print(f"Failed to insert data into database: {str(e)}")
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
        
        # Fetch candidate details
        cursor.execute("SELECT id, name, candidate_score, campaign_number FROM candidates WHERE id = %s", (candidate_id,))
        candidate = cursor.fetchone()
        
        # Check if candidate exists
        if not candidate:
            db_connection.close()
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Calculate MCQ statistics
        cursor.execute("""
            SELECT COUNT(*) AS total_mcqs, 
                   SUM(correct_or_not) AS correct_mcqs
            FROM candidate_questions
            WHERE candidate_id = %s
        """, (candidate_id,))
        mcq_stats = cursor.fetchone()
        
        total_mcqs = mcq_stats['total_mcqs']
        correct_mcqs = mcq_stats['correct_mcqs']
        score_percentage = (correct_mcqs / total_mcqs) * 100 if total_mcqs > 0 else 0

        # Fetch LLM score
        try:
            payload = f"{candidate} This is a candidate selected for post of {post} and {description}. Just rate them out of 10 and don't tell nothing else just a single line answer in format x/10"
            response = requests.post(EXTERNAL_API_URL_CHAT_BOT, data={"text": payload})
            response.raise_for_status()
            llm_score = response.text.strip()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            llm_score = "Error fetching score"
        
        db_connection.close()
        
        return templates.TemplateResponse("view_candidate.html", {
            "request": request,
            "candidate": candidate,
            "total_mcqs": total_mcqs,
            "correct_mcqs": correct_mcqs,
            "score_percentage": score_percentage,
            "llm_score": llm_score
        })
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"MySQL Error: {str(e)}")












mcq_data=" "
post=None
description=None
tags=None
psychology=None
experience=None
MAX_RETRIES = 15    
RETRY_DELAY = 5  # seconds






def extract_post(campaign_number):
    global post, description,tags,experience,psychology
    try:
        connection = connect_to_database()
        cursor = connection.cursor(dictionary=True)

        # SQL query to get job title and description based on campaign_number
        select_query = """
        SELECT job_title, job_description,tags,experience,psychology   
        FROM job_descriptions
        WHERE campaign_number = %s
        """

        cursor.execute(select_query, (campaign_number,))
        result = cursor.fetchone()

        # Check if result is None
        if result:
            post = result.get("job_title")
            description = result.get("job_description")
            tags = result.get("tags")
            experience = result.get("experience")
            psychology=result.get("psychology")
            # print(f"Job Title: {post}")
            # print(f"Job Description: {description}")
            # print(f"tags :{tags}")
            # print(f"experience:{experience}")
            # print(f"psychology:{psychology}")
            return {
                "job_title": post,
                "job_description": description,
                "tags":tags,
                "experience":experience,
                "psychology":psychology
            }
        else:
            # Set global variables to None if no result found
            post = None
            description = None
            print("No job description found for the given campaign number.")
            return {
                "job_title": None,
                "job_description": None
            }

    except mysql.connector.Error as error:
        print(f"Error extracting data: {error}")
        # Set global variables to None on error
        post = None
        description = None
        return {
            "job_title": None,
            "job_description": None
        }
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()





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



def insert_candidate_questions(candidate_id, questions):
    try:
        connection = connect_to_database()
        cursor = connection.cursor()

        all_questions = json.loads(questions)
        print(type(all_questions))
        print("$" * 100)
        print(all_questions)
        print("**************************************")

        for question_info in all_questions:
            question_text = question_info['question']
            options = question_info['options']
            correct_answer_key = question_info['answer']

            # Convert the correct answer from 'a', 'b', 'c', 'd' to 0, 1, 2, 3
            correct_answer_index = ord(correct_answer_key) - ord('a')
            correct_answer = options[correct_answer_index]

            # Insert the question into the 'questions' table
            print("Inserting into questions table...")
            insert_query = "INSERT INTO questions (question_text) VALUES (%s)"
            cursor.execute(insert_query, (question_text,))
            question_id = cursor.lastrowid  # Get the last inserted question ID

            print("Inserting into options table...")
            for index, option in enumerate(options):
                is_correct = 1 if index == correct_answer_index else 0
                insert_query = "INSERT INTO options (question_id, option_text, is_correct) VALUES (%s, %s, %s)"
                cursor.execute(insert_query, (question_id, option, is_correct))

            print("Inserting in candidate_questions")
            insert_query = "INSERT INTO candidate_questions(candidate_id, question_id) VALUES (%s, %s)"
            cursor.execute(insert_query, (candidate_id, question_id))

        # Commit changes to the database
        connection.commit()
        print(f"{len(all_questions)} questions and their options inserted successfully for candidate ID {candidate_id}")

    except mysql.connector.Error as error:
        print(f"Error inserting data into MySQL table: {error}")

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")


def generate_mcq():
    global mcq_data, post, description, tags, experience, psychology, current_candidate_id
    extract_post(uploaded_campaign_number)
    print("="*50)
    print(current_candidate_id)
    print("="*50)
    retries = 0
    while retries < MAX_RETRIES:
        try:
            # Prepare the text to pass to the external API based on the value of psychology
            if psychology == 'yes':
                text_to_pass = (
                    f"(only return JSON) Generate 10 MCQs with their options for post: {post} "
                    f"and the job description: {description} for an experienced person with experience: {experience} "
                    f"and these are the tags: {tags}. The MCQs should be based on these tags, along with 5 psychology question. "
                    f"Only provide JSON in the format "
                    f"[{{\"question\":\"Question text here\",\"options\":[\"a) Option 1\",\"b) Option 2\",\"c) Option 3\",\"d) Option 4\"],\"answer\":\"a\"}},...] "
                    f"Include the answer in a, b, c, d form. The response should only have JSON. Do not write 'Here are 5 MCQs', just return JSON."
                )
            else:
                text_to_pass = (
                    f"Generate me 10 MCQs with their options for post: {post} and the job description: {description} "
                    f"for an experienced person with experience: {experience} and these are the tags: {tags} around which the MCQs should be based. "
                    f"Only provide JSON in the format: "
                    f"[{{\"question\":\"Question text here\",\"options\":[\"a) Option 1\",\"b) Option 2\",\"c) Option 3\",\"d) Option 4\"],\"answer\":\"a\"}},...] "
                    f"along with the answer in a, b, c, d form. The response should only have JSON. Do not write 'Here are 5 MCQs', just return JSON."
                )

            # Make a POST request to the external API
            response = requests.post(EXTERNAL_API_URL_CHAT_BOT, data={"text": text_to_pass})
            response.raise_for_status()  # Raise an error for bad status codes

            # Extract JSON from the response text
            print("===================================================")
            print("Response by Chatbot :")
            print(response.text)
            print("===================================================")

            mcq_data = extract_json_from_text(response.text)
            print("MCQ Extracted are :")
            print(mcq_data)
            print("----------------")
            print(type(mcq_data))

            # Try inserting the questions
            try:
                print("Calling insert in candidate function")
                insert_candidate_questions(current_candidate_id, mcq_data)
                # If insertion is successful, break out of the retry loop
                break
            except Exception as e:
                print(f"Insert candidate questions failed: {e}")
                # Increment retries if insertion fails
                retries += 1
                if retries >= MAX_RETRIES:
                    raise HTTPException(status_code=500, detail="Failed to insert MCQ data into the database after several attempts.")
                # Wait before retrying
                time.sleep(RETRY_DELAY)

        except requests.exceptions.RequestException as e:
            print(f"RequestException: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            print(f"General Exception: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # Render the template with the MCQ data
    return 0

























async def get_mcqs_from_db(candidate_id: int):
    connection = connect_to_database()
    cursor = connection.cursor(dictionary=True)
    
    query = """
    SELECT q.id as question_id, q.question_text, o.id as option_id, o.option_text
    FROM questions q
    JOIN options o ON q.id = o.question_id
    JOIN candidate_questions cq ON q.id = cq.question_id
    WHERE cq.candidate_id = %s
    """
    cursor.execute(query, (candidate_id,))
    rows = cursor.fetchall()
    
    mcqs = {}
    for row in rows:
        question_id = row["question_id"]
        if question_id not in mcqs:
            mcqs[question_id] = {"question_text": row["question_text"], "options": []}
        mcqs[question_id]["options"].append({"option_id": row["option_id"], "option_text": row["option_text"]})
    
    cursor.close()
    connection.close()
    
    return [{"question_id": k, "question_text": v["question_text"], "options": v["options"]} for k, v in mcqs.items()]

@app.post("/mcqs")
async def display_mcqs(request: Request):
    global current_candidate_id
    candidate_id = 1  # Set the candidate_id you want to filter by
    mcqs = await get_mcqs_from_db(current_candidate_id)
    return templates.TemplateResponse("mcq.html", {"request": request, "mcqs": mcqs})

@app.post("/submit_mcqs")
async def submit_mcqs(request: Request):
    global current_candidate_id
    form = await request.form()
    selected_options = {key: value for key, value in form.items() if key.startswith("option_")}
    
    connection = connect_to_database()
    cursor = connection.cursor()
    
    candidateid = 27  # Use the correct candidate ID
    for key, value in selected_options.items():
        question_id = key.split("_")[1]
        selected_option_id = value
        
        # Check if the selected option is correct
        correct_query = """
        SELECT is_correct
        FROM options
        WHERE id = %s
        """
        cursor.execute(correct_query, (selected_option_id,))
        is_correct = cursor.fetchone()[0]  # Fetch the correctness status
        
        print(f"Updating selected_option_id to {selected_option_id} for question_id {question_id} and candidate_id {current_candidate_id}")
        
        insert_query = """
        UPDATE candidate_questions
        SET selected_option_id = %s, correct_or_not = %s
        WHERE candidate_id = %s AND question_id = %s;
        """
        cursor.execute(insert_query, (selected_option_id, is_correct, current_candidate_id, question_id))
        print("Update successful. Rows affected:", cursor.rowcount)
    
    connection.commit()
    cursor.close()
    connection.close()
    
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










display_campaign_number=None

def fetch_candidate_details(candidate_id):
    global display_campaign_number
    connection = None
    cursor = None
    data = None
    try:
        # Connect to the database
        connection = connect_to_database()
        if connection is None:
            print("Failed to connect to the database.")
            return None

        cursor = connection.cursor(dictionary=True)
        
        # Define the SQL query
        query = """
        SELECT
            c.id AS candidate_id,
            c.name,
            c.email,
            c.phone,
            c.address,
            c.campaign_number,
            c.candidate_score,
            c.file_name,
            e.id AS experience_id,
            e.organization_name,
            e.designation,
            e.start_date AS experience_start_date,
            e.end_date AS experience_end_date,
            e.summary AS experience_summary,
            s.id AS skill_id,
            s.skill,
            ed.id AS education_id,
            ed.institute_name,
            ed.degree,
            ed.start_date AS education_start_date,
            ed.end_date AS education_end_date,
            ed.summary AS education_summary,
            cert.id AS certification_id,
            cert.certification,
            r.id AS research_id,
            r.research_title
        FROM candidates c
        LEFT JOIN experiences e ON c.id = e.candidate_id
        LEFT JOIN skills s ON c.id = s.candidate_id
        LEFT JOIN educations ed ON c.id = ed.candidate_id
        LEFT JOIN certifications cert ON c.id = cert.candidate_id
        LEFT JOIN research r ON c.id = r.candidate_id
        WHERE c.id = %s;
        """
        
        # Execute the query
        cursor.execute(query, (candidate_id,))
        data = cursor.fetchall()
        display_campaign_number=data[0]['campaign_number']
        print("campaign number is ")
        print(display_campaign_number)
    except mysql.connector.Error as error:
        print(f"Error fetching data: {error}")
        return None

    finally:
        # Close the cursor and connection
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
    
    return data

# Example usage
# print(details)

def send_text_to_api():
    global post,description
    detials=fetch_candidate_details(current_candidate_id)
    extract_post(display_campaign_number)
    try:
        # Define the payload
        payload = f"{detials} This is a candidate selected for post of {post} and {description} where they need experience of {experience} and these are the main tags:{tags} .  just rate them out of 10 and dont tell nothing else just a single line answer in format x/10"

        # Make a POST request to the API
        response = requests.post(EXTERNAL_API_URL_CHAT_BOT, data={"text":payload})
        
        # Check if the request was successful
        response.raise_for_status()  # Raise an error for bad status codes

        # Print the response
        print("Response from API:")
        print(response.text)  # Assuming the response is in JSON format
        # temp=extract_rating(response.text)
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")



















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





@app.get("/jobdescription", response_class=HTMLResponse)
async def read_job_description(request: Request):
    return templates.TemplateResponse("jobdescription.html", {"request": request})

def extract_keywords(job_title):
    # Convert job title to lowercase and split into words
    words = re.findall(r'\b\w+\b', job_title.lower())
    
    # Define a list of common roles or keywords you are interested in
    keywords = ["intern", "senior", "junior", "manager", "director", "assistant", "analyst", "developer","mto","associate"]
    
    # Extract keywords that are found in the job title
    extracted_keywords = [word for word in words if word in keywords]
    
    return extracted_keywords

@app.get("/get-job-description")
async def get_job_description(jobTitle: str):
    try:
        # Extract keywords from the job title
        keywords = extract_keywords(jobTitle)
        if not keywords:
            return JSONResponse(content={"description": ""}, status_code=404)

        # Connect to the database
        db_connection = connect_to_database()
        cursor = db_connection.cursor(dictionary=True)

        # Build the query based on extracted keywords
        query = " OR ".join(f"title LIKE %s" for _ in keywords)
        query = f"SELECT description FROM position_descriptions WHERE {query}"
        
        # Execute the query
        cursor.execute(query, tuple(f"%{keyword}%" for keyword in keywords))
        result = cursor.fetchone()

        # Close the connection
        cursor.close()
        db_connection.close()

        if result:
            return JSONResponse(content={"description": result['description']})
        else:
            return JSONResponse(content={"description": ""}, status_code=404)

    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(content={"error": "An error occurred while processing your request."}, status_code=500)

# Existing POST endpoint for inserting job description
@app.post("/insert-job-description")
async def insert_job_description(
    jobTitle: str = Form(...),
    jobDescription: str = Form(...),
    campaignNumber: str = Form(...),
    tags: str = Form(...),
    experience: int = Form(...),
    psychology: str = Form(...),
    status: str = Form(...),
    expiration_date: str = Form(...)
):
    try:
        # Connect to the database
        db_connection = connect_to_database()

        # Insert the job description into the database
        insert_query = """
        INSERT INTO job_descriptions (job_title, job_description, campaign_number, tags, experience, psychology)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (jobTitle, jobDescription, campaignNumber, tags, experience, psychology)
        insert_query_campaign = """
        INSERT INTO campaignnumber (campaign_number, status, expiration_date) VALUES (%s, %s, %s)
        """
        values_campaign = (campaignNumber, status, expiration_date)
        with db_connection.cursor() as cursor:
            cursor.execute(insert_query, values)
            cursor.execute(insert_query_campaign, values_campaign)
            db_connection.commit()

        # Close the connection
        db_connection.close()
        return HTMLResponse(content="""
            <html>
            <head>
                <title>Data Stored</title>
            </head>
            <body style="background-color: black; color: white; font-family: Arial, sans-serif; text-align: center; padding: 20px;">
                <h2>Success!</h2>
                <p>Job Description and Campaign Information Uploaded Successfully</p>
                <p><a href="/" style="color: #1ccdaa;">Back to Main Menu</a></p>
            </body>
            </html>
        """, status_code=200)
    except Exception as e:
        print(f"Error: {e}")
        return HTMLResponse(content="""
            <html>
            <head>
                <title>Error</title>
            </head>
            <body style="background-color: black; color: white; font-family: Arial, sans-serif; text-align: center; padding: 20px;">
                <h2>Error!</h2>
                <p>An error occurred while processing your request. Please try again later.</p>
                <p><a href="/" style="color: #1ccdaa;">Back to Main Menu</a></p>
            </body>
            </html>
        """, status_code=500)




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
