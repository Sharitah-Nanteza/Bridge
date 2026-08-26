// Localized UI Strings Dictionary
const uiTranslations = {
    en: {
        tagline: "Interactive Legal & Digital Safety Assistant",
        ussdText: "No Internet? Dial <strong>*384*123#</strong> on any phone to access this helpline via USSD!",
        langLabel: "Preferred Language / Londa Olulimi:",
        sectionHeading: "Ask for Help",
        sectionSubheading: "Describe your issue (e.g., mobile money scam, online threats, privacy violation):",
        placeholder: "Describe your issue here...",
        submitBtn: "Get Legal Assistance",
        loadingText: "Analyzing legal and digital safety options...",
        playVoice: "🔊 Play Voice"
    },
    lg: {
        tagline: "Omuyambi Wo Ku By'amateeka n'Obukuumi Ku Mutimbagano",
        ussdText: "Tolina yintaneeti? Kubeera <strong>*384*123#</strong> ku ssimu yonna okufuna obuyambi obwa USSD!",
        langLabel: "Londa Olulimi:",
        sectionHeading: "Saba Obuyambi",
        sectionSubheading: "Nnyonnyola ekizibu kyo (e.g., obufere bw'esimu, okutiisibwatiisibwa, okutyoboola ebyama):",
        placeholder: "Wandika ekizibu kyo wano...",
        submitBtn: "Funa Obuyambi Bw'Amateeka",
        loadingText: "Okukunganya amagezi ku by'amateeka...",
        playVoice: "🔊 Wuliriza Eddoboozi"
    },
    sw: {
        tagline: "Msaidizi Wako wa Sheria na Usalama wa Mtandao",
        ussdText: "Huna intaneti? Piga <strong>*384*123#</strong> kwa simu yoyote kupata huduma hii kupitia USSD!",
        langLabel: "Chagua Lugha:",
        sectionHeading: "Omba Msaada",
        sectionSubheading: "Eleza tatizo lako (mf. utapeli wa pesa kwa simu, vitisho mtandaoni, ukiukaji wa faragha):",
        placeholder: "Andika tatizo lako hapa...",
        submitBtn: "Pata Msaada wa Kisheria",
        loadingText: "Kuangalia hatua za kisheria na usalama...",
        playVoice: "🔊 Sikiliza Sauti"
    },
    nyn: {
        tagline: "Omuhabuzi W'amateeka n'Eby'okwerinda aha Mutimbagano",
        ussdText: "Oteine intaneeti? Teera <strong>*384*123#</strong> aha simu yoona kutunga obuhabuzi via USSD!",
        langLabel: "Toora Oruhanga:",
        sectionHeading: "Shaba Obuhabuzi",
        sectionSubheading: "Shoboorora oburemeezi bwawe (mf. obufuru bwa marwa, okutinisibwa, okusisa ebyama):",
        placeholder: "Handika oburemeezi bwawe aha...",
        submitBtn: "Tunga Obuhabuzi Bw'Amateeka",
        loadingText: "Orikusherura obuhabuzi bw'amateeka...",
        playVoice: "🔊 Hurira Edjoboozi"
    },
    lgg: {
        tagline: "A'di 'Ba E'yo Amani 'Diyi 'Ba Matu Niyia",
        ussdText: "Intaneeti yo? Piga <strong>*384*123#</strong> simu azi 'dii dri a'di ussd ki!",
        langLabel: "A'di Ti 'Diyi:",
        sectionHeading: "Zi Konyi",
        sectionSubheading: "O'du e'yo mi 'dii (e.g., mobile money scam, okpo enikani):",
        placeholder: "O'du e'yo mi 'dii 'fani...",
        submitBtn: "E'do Konyi Matu Niyia",
        loadingText: "E'do e'yo amani 'diyi 'ba...",
        playVoice: "🔊 Ongo Wula"
    },
    ach: {
        tagline: "Lakonii me Chik dok Yub me Bedo maber I Internet",
        ussdText: "Pe tye ki intaneeti? Go <strong>*384*123#</strong> i cimu mo keken me nongo kony pa USSD!",
        langLabel: "Yer Leb:",
        sectionHeading: "Kway Kony",
        sectionSubheading: "Tit peko ni (e.g., goba me lim i cimu, bwola i internet):",
        placeholder: "Coya peko ni kany...",
        submitBtn: "Nong Kony me Chik",
        loadingText: "Nyenyo tic me chik...",
        playVoice: "🔊 Winj Dwono"
    }
};

document.addEventListener("DOMContentLoaded", () => {
    const languageSelect = document.getElementById("languageSelect");
    const queryForm = document.getElementById("queryForm");

    // Initialize UI language on boot
    updateUILanguage(languageSelect.value);

    // Update UI language whenever user changes the dropdown selection
    languageSelect.addEventListener("change", (e) => {
        updateUILanguage(e.target.value);
    });

    if (queryForm) {
        queryForm.addEventListener("submit", submitQuery);
    }
});

function updateUILanguage(langCode) {
    const t = uiTranslations[langCode] || uiTranslations.en;

    document.getElementById("tagline").innerText = t.tagline;
    document.getElementById("ussdText").innerHTML = t.ussdText;
    document.getElementById("langLabel").innerText = t.langLabel;
    document.getElementById("sectionHeading").innerText = t.sectionHeading;
    document.getElementById("sectionSubheading").innerText = t.sectionSubheading;
    document.getElementById("queryInput").placeholder = t.placeholder;
    document.getElementById("submitBtn").innerText = t.submitBtn;
}

async function submitQuery(e) {
    e.preventDefault();

    const queryInput = document.getElementById("queryInput");
    const languageSelect = document.getElementById("languageSelect");
    const submitBtn = document.getElementById("submitBtn");
    const responseBox = document.getElementById("responseBox");

    const query = queryInput.value.trim();
    const language = languageSelect.value;
    const t = uiTranslations[language] || uiTranslations.en;

    if (!query) return;

    submitBtn.disabled = true;
    submitBtn.innerText = t.loadingText;
    responseBox.style.display = "block";
    responseBox.innerHTML = `⏳ ${t.loadingText}`;

    try {
        const res = await fetch("/api/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query, language })
        });

        const data = await res.json();

        if (data.answer) {
            responseBox.innerHTML = `
                <div style="margin-bottom: 12px;">
                    <button id="speakBtn" type="button" style="padding: 8px 16px; background-color: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; display: inline-flex; align-items: center; gap: 6px;">
                        ${t.playVoice}
                    </button>
                </div>
                <div id="answerText">${data.answer.replace(/\n/g, '<br>')}</div>
            `;

            document.getElementById("speakBtn").onclick = () => playVoice(data.answer, language);
        } else {
            responseBox.innerText = data.error || "An error occurred while fetching advice.";
        }
    } catch (err) {
        console.error("Fetch Error:", err);
        responseBox.innerText = "Failed to fetch response. Please check your backend service.";
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerText = t.submitBtn;
    }
}

function playVoice(text, langCode) {
    if (!("speechSynthesis" in window)) {
        alert("Text-to-speech is not supported in this browser.");
        return;
    }

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);

    const voiceLocales = {
        en: "en-US",
        sw: "sw-KE",
        lg: "en-UG",
        nyn: "en-UG",
        lgg: "en-UG",
        ach: "en-UG"
    };

    utterance.lang = voiceLocales[langCode] || "en-US";
    utterance.rate = 0.95;

    window.speechSynthesis.speak(utterance);
}