CREATE DATABASE IF NOT EXISTS cv_database;
USE cv_database;

CREATE TABLE if not exists candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(255),
    address VARCHAR(255),
    campaign_number INT, -- New column for campaign number
    candidate_score int,
    file_name varchar(255)
);

CREATE TABLE if not exists campaignnumber (
    id INT AUTO_INCREMENT PRIMARY KEY,
    campaign_number INT NOT NULL,
    status VARCHAR(255) NOT NULL,
    expiration_date DATE  -- Ensure the column name is correct here
);

CREATE TABLE if not exists experiences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    organization_name VARCHAR(255),
    designation VARCHAR(255),
    start_date DATE,
    end_date VARCHAR(225),
    summary TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE TABLE if not exists skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    skill VARCHAR(255),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE TABLE if not exists educations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    institute_name VARCHAR(255),
    degree VARCHAR(255),
    start_date VARCHAR(225),
    end_date VARCHAR(225),
    summary TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE TABLE if not exists certifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    certification VARCHAR(255),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE TABLE if not exists research (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    research_title VARCHAR(255),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE TABLE if not exists scoring (
    id INT AUTO_INCREMENT PRIMARY KEY,
    typee VARCHAR(255),
    skill_name VARCHAR(255),
    score INT,
    campaign_number int 
);

CREATE TABLE IF NOT EXISTS job_descriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_title VARCHAR(255) NOT NULL,
    job_description TEXT NOT NULL,
    campaign_number VARCHAR(50) NOT NULL,
    tags TEXT,  -- Using TEXT to allow for a list of tags as a comma-separated string
    psychology ENUM('yes', 'no') NOT NULL default 'no' , -- Using ENUM to store either 'yes' or 'no'
    experience int
);

CREATE TABLE if not exists position_descriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description longtext NOT NULL
);

CREATE TABLE if not exists question_answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    question_text TEXT NOT NULL, -- Column to store the text of the question
    answer TEXT, -- Column to store the candidate's answer
    is_correct BOOLEAN, -- Column to indicate if the answer is correct or not
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE TABLE if not exists questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_text TEXT NOT NULL
);

CREATE TABLE if not exists options (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT,
    option_text TEXT NOT NULL,
    is_correct TINYINT(1) DEFAULT 0,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE TABLE if not exists candidate_questions (
	id INT AUTO_INCREMENT PRIMARY KEY,
	candidate_id INT,
	question_id INT,
	selected_option_id INT,
	correct_or_not TINYINT(1) DEFAULT 0,
	LLM_marks VARCHAR(255) default 0,
	FOREIGN KEY (candidate_id) REFERENCES candidates(id),
	FOREIGN KEY (question_id) REFERENCES questions(id),
	FOREIGN KEY (selected_option_id) REFERENCES options(id)
	);

CREATE TABLE if not exists user_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    mcq_score INT,
    total_mcq INT,
    llm_score VARCHAR(255) DEFAULT 'Not Generated yet (Error)',
    manual_score INT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);
create table if not exists login(
id int auto_increment primary key,
username varchar(255),
password varchar(255),
campaign_number int 
)

