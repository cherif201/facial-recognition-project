CREATE TABLE IF NOT EXISTS students (
    id_card INT PRIMARY KEY  UNIQUE Not NULL,
    first_name TEXT,
    last_name TEXT,
    age INT,
    level TEXT,
    email TEXT UNIQUE Not NULL,
    password TEXT UNIQUE Not NULL,
    face_encoding BYTEA  NOT NULL, -- stores face encoding
    face_height INT,
    face_width INT,
    role TEXT DEFAULT 'student' -- 'student' or 'professor'
);
-- Table for quizzes created by professors
CREATE TABLE IF NOT EXISTS quizzes (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    questions JSONB NOT NULL,
    created_by INT REFERENCES students(id_card),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posted BOOLEAN DEFAULT FALSE
);

-- Table for quiz results submitted by students
CREATE TABLE IF NOT EXISTS quiz_results (
    id SERIAL PRIMARY KEY,
    student_id INT REFERENCES students(id_card),
    quiz_id INT REFERENCES quizzes(id),
    grade FLOAT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS access_logs (
    id SERIAL PRIMARY KEY,
    student_id INT REFERENCES students(id_card),
    login_time TIMESTAMP,
    logout_time TIMESTAMP,
    session_duration INTERVAL,
    FOREIGN KEY (student_id) REFERENCES students(id_card) ON DELETE CASCADE
);
