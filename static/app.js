document.addEventListener("DOMContentLoaded", () => {
    fetchLegalGuides();
});

async function fetchLegalGuides() {
    const container = document.getElementById("guides-container");

    try {
        const response = await fetch('/api/guides');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        renderGuides(data);
    } catch (error) {
        console.error("Error fetching legal guides:", error);
        container.innerHTML = "<p>Unable to load legal guides. Please try refreshing.</p>";
    }
}

function renderGuides(guides) {
    const container = document.getElementById("guides-container");
    container.innerHTML = "";

    Object.keys(guides).forEach(key => {
        const item = guides[key];
        const card = document.createElement("div");
        card.className = "guide-card";

        card.innerHTML = `
            <h3>${item.category}</h3>
            <div class="act-badge">${item.act}</div>
            <div class="steps-content">${item.sms_details}</div>
        `;

        container.appendChild(card);
    });
}