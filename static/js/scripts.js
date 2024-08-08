// Add JavaScript for handling advanced voice commands and interactions
document.addEventListener('DOMContentLoaded', () => {
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'en-US';
    recognition.continuous = true;
    recognition.onresult = (event) => {
        const command = event.results[event.results.length - 1][0].transcript;
        fetch('/voice-command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Voice Command Response:', data);
        });
    };
    recognition.start();
});
