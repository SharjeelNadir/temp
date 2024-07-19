CREATE DATABASE IF NOT EXISTS cv_database;
USE cv_database;

CREATE TABLE candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(255),
    address VARCHAR(255),
    campaign_number INT, -- New column for campaign number
    candidate_score int
);

CREATE TABLE experiences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    organization_name VARCHAR(255),
    designation VARCHAR(255),
    start_date DATE,
    end_date VARCHAR(225),
    summary TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE TABLE skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    skill VARCHAR(255),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE TABLE educations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    institute_name VARCHAR(255),
    degree VARCHAR(255),
    start_date VARCHAR(225),
    end_date VARCHAR(225),
    summary TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE TABLE certifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    certification VARCHAR(255),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE TABLE research (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    research_title VARCHAR(255),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);
CREATE TABLE scoring (
    id INT AUTO_INCREMENT PRIMARY KEY,
    typee VARCHAR(255),
    skill_name VARCHAR(255),
    score INT
);



