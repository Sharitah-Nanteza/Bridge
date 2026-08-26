document.addEventListener("DOMContentLoaded", () => {
    const sendBtn = document.getElementById("send-btn");
    const userInput = document.getElementById("user-input");
    const responseBox = document.getElementById("response-box");
    const aiReply = document.getElementById("ai-reply");

    sendBtn.addEventListener("click", async () => {
        const question = userInput.value.trim();
        if (!question) return;

        sendBtn.disabled = true;
        sendBtn.innerText = "Analyzing your issue...";
        responseBox.classList.remove("hidden");
        aiReply.innerHTML = "<p>Retrieving legal guidance...</p>";

        try {
            const res = await fetch("/api/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question })
            });

            const data = await res.json();
            if (data.reply) {
                aiReply.innerHTML = data.reply.replace(/\n/g, "<br>");
            } else {
                aiReply.innerText = data.error || "An error occurred. Please try again.";
            }
        } catch (err) {
            aiReply.innerText = "Connection failed. Please check your backend server.";
        } finally {
            sendBtn.disabled = false;
            sendBtn.innerText = "Get Legal Assistance";
        }
    });
});