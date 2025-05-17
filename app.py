
import psycopg2
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import base64
import cv2
import numpy as np
import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Flask app initialization
app = Flask(__name__)

# Dictionary to track user sessions
user_sessions = {}

# Database connection details loaded from environment variables
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

# Load Haar cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Helper function to get a database connection
def get_database_connection():
    return psycopg2.connect(**DB_CONFIG)

# Database initialization is now manual to prevent data loss.
# To initialize the database, run the schema in database.sql manually when needed.
# The app will no longer drop or recreate tables on every start.

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

@app.route('/')
def index():
    return render_template('index.html')


# Route: Signup (with role selection)
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
    role = request.form.get('role', 'student')
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
        INSERT INTO students (first_name, last_name, age, level, id_card, email, password, face_encoding, face_height, face_width, role)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (first_name, last_name, age, level, id_card, email, password, face_encoding, face_height, face_width, role))
    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({"success": True, "redirect_url": "/login"})
# Professor dashboard: Quiz creation and listing
import requests
from flask import jsonify

@app.route('/professor/dashboard')
def professor_dashboard():
    return render_template('professor_dashboard.html')

# API endpoint to generate a quiz using QuizAPI and save to DB
@app.route('/professor/generate_quiz', methods=['POST'])
def generate_quiz():
    data = request.get_json()
    title = data.get('title')
    category = data.get('category')
    difficulty = data.get('difficulty', '').lower()
    num_questions = data.get('num_questions', 5)
    created_by = data.get('created_by')
    if not created_by:
        return jsonify({'success': False, 'error': 'Professor ID (created_by) is required.'}), 400
    api_key = os.getenv('QUIZAPI_KEY')
    # Call QuizAPI
    url = f'https://quizapi.io/api/v1/questions'
    headers = {'X-Api-Key': api_key}
    params = {
        'limit': num_questions,
        'category': category,
        'difficulty': difficulty
    }
    print(f"[QuizAPI DEBUG] URL: {url}")
    print(f"[QuizAPI DEBUG] Headers: {headers}")
    print(f"[QuizAPI DEBUG] Params: {params}")
    try:
        resp = requests.get(url, headers=headers, params=params)
        print(f"[QuizAPI DEBUG] Status code: {resp.status_code}")
        print(f"[QuizAPI DEBUG] Response text: {resp.text}")
        resp.raise_for_status()
        questions = resp.json()
    except Exception as e:
        # If 404, show the response text for debugging
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f" | Response: {e.response.text}"
        return jsonify({'success': False, 'error': error_msg}), 500
    # Save quiz to DB with correct professor id
    conn = get_database_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO quizzes (title, questions, created_by) VALUES (%s, %s, %s) RETURNING id, created_at", (title, json.dumps(questions), int(created_by)))
    quiz_id, created_at = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True, 'quiz': questions, 'quiz_id': quiz_id, 'created_at': str(created_at)})

# List all quizzes
@app.route('/professor/quizzes')
def professor_quizzes():
    conn = get_database_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, created_at FROM quizzes ORDER BY created_at DESC")
    quizzes = [
        {"id": row[0], "title": row[1], "created_at": row[2].strftime('%Y-%m-%d %H:%M')} for row in cur.fetchall()
    ]
    cur.close()
    conn.close()
    return jsonify({'quizzes': quizzes})

# API endpoint to post a quiz (mark as posted)
@app.route('/professor/post_quiz', methods=['POST'])
def post_quiz():
    data = request.get_json()
    quiz_id = data.get('quiz_id')
    if not quiz_id:
        return jsonify({'success': False, 'error': 'Quiz ID required'}), 400
    conn = get_database_connection()
    cur = conn.cursor()
    cur.execute("UPDATE quizzes SET posted = TRUE WHERE id = %s", (quiz_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True})

# Route: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    # Extract form data
    id_card = request.form['id_card']
    face_data_url = request.form['face_image']
    role = request.form.get('role', 'student')

    if not face_data_url:
        return jsonify({"success": False, "error": "No face image received."}), 400

    # Process and detect face
    image = process_image(face_data_url)
    face_image, error = detect_face(image)
    if error:
        print(f"Face detection error during login: {error}")  # Debugging line
        return jsonify({"success": False, "error": error}), 400

    # Flatten the detected face for comparison
    input_encoding = face_image.flatten()

    # Fetch stored encoding and shape from the database
    conn = get_database_connection()
    cur = conn.cursor()
    cur.execute("SELECT first_name, id_card, face_encoding, face_height, face_width, role FROM students WHERE id_card = %s", (id_card,))
    row = cur.fetchone()

    if row is None:
        cur.close()
        conn.close()
        return jsonify({"success": False, "error": "Student not found!"}), 404

    first_name, student_id, stored_encoding_bytes, stored_height, stored_width, db_role = row
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
        cur.close()
        conn.close()
        return jsonify({"success": False, "error": "Face does not match our records!"}), 401

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

    # Redirect to dashboard based on role
    if db_role == 'professor':
        redirect_url = '/professor/dashboard'
    else:
        redirect_url = '/student/dashboard'
    return jsonify({"success": True, "redirect_url": redirect_url})

# Student dashboard route
@app.route('/student/dashboard')
def student_dashboard():
    return render_template('student_dashboard.html')

# API: List all posted quizzes
@app.route('/student/quizzes')
def student_quizzes():
    conn = get_database_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM quizzes WHERE posted = TRUE ORDER BY created_at DESC")
    quizzes = [
        {"id": row[0], "title": row[1]} for row in cur.fetchall()
    ]
    cur.close()
    conn.close()
    return jsonify({'quizzes': quizzes})

# API: Get quiz details (questions) for taking
@app.route('/student/quiz/<int:quiz_id>')
def get_quiz(quiz_id):
    conn = get_database_connection()
    cur = conn.cursor()
    cur.execute("SELECT title, questions FROM quizzes WHERE id = %s", (quiz_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return jsonify({'success': False, 'error': 'Quiz not found'})
    title, questions_data = row
    # If questions_data is already a list (not a string), don't decode
    if isinstance(questions_data, str):
        questions = json.loads(questions_data)
    else:
        questions = questions_data
    return jsonify({'success': True, 'quiz': {'id': quiz_id, 'title': title, 'questions': questions}})

# API: Submit quiz answers and grade
@app.route('/student/submit_quiz', methods=['POST'])
def submit_quiz():
    quiz_id = request.form.get('quiz_id')
    # For demo, get student_id from localStorage (should be from session in production)
    student_id = request.form.get('student_id')
    if not student_id:
        return jsonify({'success': False, 'error': 'Student ID required'}), 400
    conn = get_database_connection()
    cur = conn.cursor()
    cur.execute("SELECT questions FROM quizzes WHERE id = %s", (quiz_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return jsonify({'success': False, 'error': 'Quiz not found'})
    questions_data = row[0]
    if isinstance(questions_data, str):
        questions = json.loads(questions_data)
    else:
        questions = questions_data
    # Grade the quiz
    score = 0
    for idx, q in enumerate(questions):
        is_multi = q.get('multiple_correct_answers') == 'true'
        correct_keys = [k for k, v in q.get('correct_answers', {}).items() if v == 'true']
        if is_multi:
            submitted = request.form.getlist(f'q{idx}[]')
            if set(submitted) == set([k.replace('_correct', '') for k in correct_keys]):
                score += 1
        else:
            submitted = request.form.get(f'q{idx}')
            if submitted and f'{submitted}_correct' in correct_keys:
                score += 1
    # Store result
    cur.execute("INSERT INTO quiz_results (student_id, quiz_id, grade) VALUES (%s, %s, %s)", (student_id, quiz_id, score))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True, 'grade': score})

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