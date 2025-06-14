window.onload = () => {
    const video = document.getElementById("video");
    const canvas = document.getElementById("canvas");
    const faceInput = document.getElementById("face_image");
    const captureBtn = document.getElementById("capture");
    const alertBlock = document.getElementById("alert")

    alertBlock.style.display="none";

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
        const message = document.getElementById("message")
        message.innerHTML = "Face captured successfully!"
        alertBlock.style.display="block"
    });

    // Handle form submission
    document.getElementById("signupForm").addEventListener("submit", function (e) {
        e.preventDefault();
        const formData = new FormData(this);
        // Ensure role is included (in case browser autofill or JS changes)
        const role = document.getElementById("role").value;
        formData.set("role", role);

        fetch("/signup", {
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
                window.location.href = data.redirect_url;
            } else {
                alert(data.error || "Signup failed.");
            }
        })
        .catch(error => {
            alert("Error: " + error);
            console.error("Error:", error);
        });
    });
};