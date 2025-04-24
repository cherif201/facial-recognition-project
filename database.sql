CREATE TABLE IF NOT EXISTS students (
    id_card INT PRIMARY KEY  UNIQUE Not NULL,
    first_name TEXT,
    last_name TEXT,
    age INT,
    level TEXT,
    email TEXT UNIQUE Not NULL,
    password TEXT UNIQUE Not NULL,
    face_encoding BYTEA  NOT NULL -- stores face encoding
);

CREATE TABLE IF NOT EXISTS access_logs (
    id SERIAL PRIMARY KEY,
    student_id INT REFERENCES students(id_card),
    login_time TIMESTAMP,
    logout_time TIMESTAMP,
    session_duration INTERVAL,
    FOREIGN KEY (student_id) REFERENCES students(id_card) ON DELETE CASCADE
);
