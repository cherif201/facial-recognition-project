import psycopg2
from flask import Flask, render_template, request, redirect
from datetime import datetime
import base64
import cv2
import numpy as np
import os

# Flask app initialization
app = Flask(__name__)

# Dictionary to track user sessions
user_sessions = {}

# Database connection details
DB_CONFIG = {
    "host": "localhost",
    "dbname": "postgres",
    "user": "postgres",
    "password": "zedmaster2002",
    "port": "5432"
}

# Load Haar cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Helper function to get a database connection
def get_database_connection():
    return psycopg2.connect(**DB_CONFIG)

# Initialize the database (run once at startup)
def initialize_database():
    connection = get_database_connection()
    cursor = connection.cursor()
    with open("database.sql", "r") as sql_file:
        sql_commands = sql_file.read()
    for command in sql_commands.split(";"):
        command = command.strip()
        if command:
            cursor.execute(command)
    connection.commit()
    cursor.close()
    connection.close()
    print("Database setup completed successfully.")

# Initialize the database at startup
initialize_database()

# Helper function to decode and process the image
def process_image(face_data_url):
    header, encoded = face_data_url.split(",", 1)
    image_bytes = base64.b64decode(encoded)
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Save the image for debugging
    cv2.imwrite("login_captured_image.png", image)  # Saves the image to the current directory
    print("Image saved as login_captured_image.png")  # Debugging line

    return image

# Helper function to detect and extract a face
def detect_face(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.05,  # Lower value for more lenient scaling
        minNeighbors=3,    # Lower value for more lenient detection
        minSize=(20, 20)   # Smaller minimum face size
    )
    print(f"Number of faces detected: {len(faces)}")  # Debugging line
    if len(faces) != 1:
        # Save the failed image for debugging
        fail_path = f"failed_face_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        cv2.imwrite(fail_path, image)
        print(f"Saved failed face image as {fail_path}")
        return None, "Please ensure that only one face is present in the image. (A copy of your image was saved for debugging.)"
    x, y, w, h = faces[0]
    face_image = gray[y:y+h, x:x+w]
    return face_image, None

# Route: Home
@app.route('/')
def index():
    return "Welcome to the facial recognition attendance system!"

# Route: Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    # Extract form data
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    age = request.form['age']
    level = request.form['level']
    id_card = request.form['id_card']
    email = request.form['email']
    password = request.form['password']
    face_data_url = request.form['face_image']

    if not face_data_url:
        print("No face image provided")  # Debugging line
        return "No face image provided", 400

    # Process and detect face
    image = process_image(face_data_url)
    face_image, error = detect_face(image)
    if error:
        print(f"Face detection error: {error}")  # Debugging line
        return error, 400

    # Save face encoding (flattened grayscale face image)
    face_encoding = face_image.flatten().tobytes()
    face_height, face_width = face_image.shape

    # Insert data into the database
    connection = get_database_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO students (first_name, last_name, age, level, id_card, email, password, face_encoding, face_height, face_width)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (first_name, last_name, age, level, id_card, email, password, face_encoding, face_height, face_width))
    connection.commit()
    cursor.close()
    connection.close()

    return "Signup successful!"

# Route: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    # Extract form data
    id_card = request.form['id_card']
    face_data_url = request.form['face_image']

    if not face_data_url:
        return "No face image received."

    # Process and detect face
    image = process_image(face_data_url)
    face_image, error = detect_face(image)
    if error:
        print(f"Face detection error during login: {error}")  # Debugging line
        return error, 400

    # Flatten the detected face for comparison
    input_encoding = face_image.flatten()

    # Fetch stored encoding and shape from the database
    conn = get_database_connection()
    cur = conn.cursor()
    cur.execute("SELECT first_name, id_card, face_encoding, face_height, face_width FROM students WHERE id_card = %s", (id_card,))
    row = cur.fetchone()

    if row is None:
        return "Student not found!"

    first_name, student_id, stored_encoding_bytes, stored_height, stored_width = row
    stored_encoding = np.frombuffer(stored_encoding_bytes, dtype=np.uint8)

    # Resize both faces to a fixed size for comparison
    input_face_resized = cv2.resize(face_image, (100, 100)).flatten()
    stored_face_reshaped = stored_encoding.reshape((stored_height, stored_width))
    stored_face_resized = cv2.resize(stored_face_reshaped, (100, 100)).flatten()

    # Use Mean Squared Error (MSE) for comparison
    mse = np.mean((input_face_resized - stored_face_resized) ** 2)
    print(f"MSE between input and stored face: {mse}")
    threshold = 1000  # You may need to tune this value
    match = mse < threshold

    if not match:
        return "Face does not match our records!"

    # Record login time
    login_time = datetime.now()
    user_sessions[student_id] = login_time

    # Store log
    cur.execute("""
        INSERT INTO access_logs (student_id, login_time)
        VALUES (%s, %s)
    """, (student_id, login_time))
    conn.commit()

    cur.close()
    conn.close()

    return f"Login successful! Welcome, {first_name}."

# Route: Logout
@app.route('/logout/<int:student_id>', methods=['POST'])
def logout(student_id):
    logout_time = datetime.now()
    login_time = user_sessions.get(student_id)

    if not login_time:
        return "Session not found."

    duration = logout_time - login_time

    conn = get_database_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE access_logs
        SET logout_time = %s, session_duration = %s
        WHERE student_id = %s AND logout_time IS NULL
        ORDER BY login_time DESC
        LIMIT 1
    """, (logout_time, duration, student_id))

    conn.commit()
    cur.close()
    conn.close()

    return f"Logged out. Duration: {duration}"

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)