window.onload = () => {
    // Load and display available quizzes
    async function loadQuizzes() {
        const quizListDiv = document.getElementById('quizList');
        quizListDiv.innerHTML = '<div>Loading quizzes...</div>';
        try {
            const res = await fetch('/student/quizzes');
            const data = await res.json();
            if (!data.quizzes || data.quizzes.length === 0) {
                quizListDiv.innerHTML = '<div class="alert alert-warning">No quizzes available at the moment.</div>';
                return;
            }
            let html = '<h4>Available Quizzes</h4><ul class="list-group">';
            data.quizzes.forEach(q => {
                html += `<li class="list-group-item d-flex justify-content-between align-items-center">
                    <span>${q.title}</span>
                    <button class="btn btn-outline-primary btn-sm" onclick="takeQuiz(${q.id})">Take Quiz</button>
                </li>`;
            });
            html += '</ul>';
            quizListDiv.innerHTML = html;
        } catch (err) {
            quizListDiv.innerHTML = '<div class="alert alert-danger">Failed to load quizzes.</div>';
        }
    }

    // Expose loadQuizzes globally for use after quiz submission
    window.loadQuizzes = loadQuizzes;
    loadQuizzes();
    // UI: Webcam and face capture (like signup)
    const video = document.createElement('video');
    video.id = 'video';
    video.width = 320;
    video.height = 240;
    video.autoplay = true;
    video.className = 'rounded';
    const canvas = document.createElement('canvas');
    canvas.id = 'canvas';
    canvas.style.display = 'none';
    const faceInput = document.createElement('input');
    faceInput.type = 'hidden';
    faceInput.id = 'face_image';
    faceInput.name = 'face_image';
    const captureBtn = document.createElement('button');
    captureBtn.type = 'button';
    captureBtn.id = 'capture';
    captureBtn.className = 'btn btn-primary mx-auto';
    captureBtn.innerText = 'Capture Face';
    const alertBlock = document.createElement('div');
    alertBlock.className = 'alert alert-info';
    alertBlock.role = 'alert';
    alertBlock.id = 'alert';
    alertBlock.style.display = 'none';
    const message = document.createElement('p');
    message.id = 'message';
    alertBlock.appendChild(message);

    // Insert webcam UI at the top of the dashboard
    const container = document.querySelector('.container');
    const webcamDiv = document.createElement('div');
    webcamDiv.className = 'mb-4';
    webcamDiv.appendChild(video);
    webcamDiv.appendChild(document.createElement('br'));
    webcamDiv.appendChild(captureBtn);
    webcamDiv.appendChild(canvas);
    webcamDiv.appendChild(alertBlock);
    webcamDiv.appendChild(faceInput);
    container.insertBefore(webcamDiv, container.firstChild.nextSibling);

    // Access the user's webcam
    navigator.mediaDevices.getUserMedia({ video: true })
        .then((stream) => {
            video.srcObject = stream;
        });

    // Capture the face image when the button is clicked
    captureBtn.addEventListener('click', () => {
        const context = canvas.getContext('2d');
        canvas.width = 320;
        canvas.height = 240;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const imageData = canvas.toDataURL('image/png');
        faceInput.value = imageData;
        message.innerHTML = 'Face captured successfully!';
        alertBlock.style.display = 'block';
    });

    // Patch quiz submission to require face capture
    window.takeQuiz = async function(quizId) {
        const res = await fetch(`/student/quiz/${quizId}`);
        const data = await res.json();
        if (!data.success) {
            alert(data.error || 'Failed to load quiz.');
            return;
        }
        const quiz = data.quiz;
        let html = `<h4>${quiz.title}</h4><form id="studentQuizForm">`;
        quiz.questions.forEach((q, idx) => {
            html += `<div class="mb-3"><b>Q${idx + 1}:</b> ${q.question || ''}</div>`;
            if (q.answers) {
                const isMulti = q.multiple_correct_answers === 'true';
                const inputType = isMulti ? 'checkbox' : 'radio';
                Object.entries(q.answers).forEach(([key, val]) => {
                    if (val) {
                        html += `<div class="form-check ms-3">
                            <input class="form-check-input" type="${inputType}" name="q${idx}${isMulti ? '[]' : ''}" value="${key}" id="q${idx}_${key}">
                            <label class="form-check-label" for="q${idx}_${key}">${val}</label>
                        </div>`;
                    }
                });
            }
            html += '<hr>';
        });
        html += `<button type="submit" class="btn btn-success">Submit Quiz</button></form>`;
        document.getElementById('takeQuiz').innerHTML = html;
        document.getElementById('studentQuizForm').onsubmit = async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            // Add quiz_id and student_id to submission
            formData.append('quiz_id', quizId);
            const studentId = localStorage.getItem('student_id_card');
            if (!studentId) {
                alert('Student ID not found. Please log in again.');
                return;
            }
            formData.append('student_id', studentId);
            // Add face image
            formData.append('face_image', faceInput.value);
            const res = await fetch('/student/submit_quiz', {
                method: 'POST',
                body: formData
            });
            const result = await res.json();
            if (result.success) {
                document.getElementById('takeQuiz').innerHTML = `<div class='alert alert-info'><b>Your grade: ${result.grade} / ${quiz.questions.length}</b></div>`;
                loadQuizzes();
            } else {
                alert(result.error || 'Failed to submit quiz.');
            }
        };
    };
};
