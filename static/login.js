window.onload = () => {
    const video = document.getElementById("video");
    const canvas = document.getElementById("canvas");
    const faceInput = document.getElementById("face_image");
    const captureBtn = document.getElementById("capture");

    // Access the user's webcam
    navigator.mediaDevices.getUserMedia({ video: true })
        .then((stream) => {
            video.srcObject = stream;
        });

    // Capture the face image when the button is clicked
    captureBtn.addEventListener("click", () => {
        const context = canvas.getContext("2d");
        canvas.width = 320;
        canvas.height = 240;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const imageData = canvas.toDataURL("image/png");
        faceInput.value = imageData;
        // Show preview
        let preview = document.getElementById("facePreview");
        if (!preview) {
            preview = document.createElement("img");
            preview.id = "facePreview";
            preview.style.marginTop = "10px";
            captureBtn.parentNode.insertBefore(preview, canvas.nextSibling);
        }
        preview.src = imageData;
        alert("Face captured successfully!");
    });

    // Handle form submission
    document.getElementById("loginForm").addEventListener("submit", function (e) {
        e.preventDefault();
        const formData = new FormData(this);
        // Ensure role is included
        const role = document.getElementById("role").value;
        formData.set("role", role);

        fetch("/login", {
            method: "POST",
            body: formData,
        })
        .then(async response => {
            let data;
            try {
                data = await response.json();
            } catch {
                data = { success: false, error: "Invalid server response." };
            }
            if (data.success && data.redirect_url) {
                // Store id_card in localStorage for both student and professor
                const idCard = document.getElementById('id_card').value;
                if (role === 'professor') {
                    localStorage.setItem('professor_id_card', idCard);
                } else {
                    localStorage.setItem('student_id_card', idCard);
                }
                window.location.href = data.redirect_url;
            } else {
                alert(data.error || "Login failed.");
            }
        })
        .catch(error => {
            alert("Error: " + error);
            console.error("Error:", error);
        });
    });
};
