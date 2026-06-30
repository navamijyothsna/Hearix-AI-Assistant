const container = document.getElementById('app-container');
const statusText = document.getElementById('status-text');
const feedbackText = document.getElementById('feedback-text');
const exactNotesToggle = document.getElementById('exact-notes-toggle');

// Speech Recognition Setup
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
} else {
    statusText.innerText = "Speech Recognition not supported in this browser.";
}

// Text to Speech Setup
const synth = window.speechSynthesis;

// Accessibility mandatory auditory cue
const MANDATORY_CUE = "Tap anywhere to speak again.";

function speakOut(text) {
    if (synth.speaking) {
        synth.cancel();
    }
    // Rule #3: Must append mandatory cue
    const finalUtterance = text + " " + MANDATORY_CUE;

    statusText.innerText = "Speaking...";
    const utterance = new SpeechSynthesisUtterance(finalUtterance);

    utterance.onend = () => {
        statusText.innerText = "Tap anywhere to speak";
    };

    synth.speak(utterance);
    feedbackText.innerText = finalUtterance;
}

container.addEventListener('click', () => {
    if (!recognition) return;

    if (synth.speaking) {
        synth.cancel(); // Stop talking if tapped
    }

    statusText.innerText = "Listening...";
    feedbackText.innerText = "";
    container.classList.add('listening');

    try {
        recognition.start();
    } catch (e) {
        // Handle if already started
        console.error(e);
    }
});

if (recognition) {
    recognition.onresult = async (event) => {
        const transcript = event.results[0][0].transcript.toLowerCase();
        container.classList.remove('listening');
        statusText.innerText = "Processing...";
        feedbackText.innerText = `You said: "${transcript}"`;

        await processCommand(transcript);
    };

    recognition.onerror = (event) => {
        container.classList.remove('listening');
        statusText.innerText = "Try again";
        feedbackText.innerText = `Error: ${event.error}`;
        speakOut("I didn't catch that.");
    };

    recognition.onend = () => {
        container.classList.remove('listening');
        if (statusText.innerText === "Listening...") {
            statusText.innerText = "Tap anywhere to speak";
        }
    };
}

async function processCommand(transcript) {
    // String matching as per Rule #2, bypassing Regex.
    // Ensure "about" and "in" are present in that order
    let topic = "";
    let documentName = "";

    if (transcript.includes("about") && transcript.includes("in")) {
        const afterAbout = transcript.split("about")[1]; // gets whatever is after 'about'

        // Ensure "in" is actually after "about"
        if (afterAbout.includes("in")) {
            const beforeIn = afterAbout.split("in")[0];
            const afterIn = afterAbout.split("in")[1];

            topic = beforeIn.trim();
            documentName = afterIn.trim().replace(".", "");
        } else {
            speakOut("Please say 'about' followed by the topic, and 'in' followed by the document name.");
            return;
        }
    } else {
        speakOut("Please format your command like: 'read about topic in document'.");
        return;
    }

    if (!topic || !documentName) {
        speakOut("I couldn't understand the topic or document from your command.");
        return;
    }

    try {
        const response = await fetch('http://localhost:8000/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                document_name: documentName,
                topic: topic,
                exact_notes: exactNotesToggle.checked
            })
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        speakOut(data.response);

    } catch (error) {
        speakOut("Failed to reach the backend server.");
        console.error("Fetch error:", error);
    }
}
