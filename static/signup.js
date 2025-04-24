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
        console.log("Captured image data:", imageData);  // Debugging line
        alert("Face captured successfully!");
    });

    // Handle form submission
    document.getElementById("signupForm").addEventListener("submit", function (e) {
        e.preventDefault();
        const formData = new FormData(this);

        fetch("/signup", {
            method: "POST",
            body: formData,
        })
        .then(response => response.text())
        .then(data => alert(data))
        .catch(error => console.error("Error:", error));
    });
};