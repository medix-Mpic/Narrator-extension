document.addEventListener('DOMContentLoaded', () => {
    const statusMessageElement = document.getElementById('statusMessage');
    const statusLightElement = document.getElementById('serverStatus');
    const voiceSelectElement = document.getElementById('voiceSelect');
    const speedSliderElement = document.getElementById('speedSlider');
    const speedValueElement = document.getElementById('speedValue');
    const colorPickerElement = document.getElementById('colorPicker');
    const loadingContainer = document.getElementById('loadingContainer');
    const mainContainer = document.getElementById('mainContainer');

    // Function to show/hide loading screen
    function toggleLoading(show) {
        if (show) {
            loadingContainer.style.display = 'flex';
            mainContainer.style.display = 'none';
        } else {
            loadingContainer.style.display = 'none';
            mainContainer.style.display = 'block';
        }
    }

    // Save settings to local storage
    function saveSettings(voice, speed, color) {
        chrome.storage.local.set({ voice: voice, speed: speed, color: color }, () => {
            console.log('Settings saved');
        });
    }

    // Highlight text in the active tab
    function highlightTextInActiveTab(color) {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            chrome.scripting.executeScript({
                target: { tabId: tabs[0].id },
                function: highlightSelection,
                args: [color]
            });
        });
    }

    function removehighlightTextInActiveTab() {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            chrome.scripting.executeScript({
                target: { tabId: tabs[0].id },
                function: removeHighlight
            });
        });
    }

    function highlightSelection(color) {
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
    
            // Create a new span element with desired styles
            const span = document.createElement('span');
            span.style.backgroundColor = color;
            span.style.color = '#000000';
            span.style.padding = '2px';
            span.style.borderRadius = '2px';
            span.id = "highlight-Narrator-Extension"
    
            try {
                // Attempt to surround contents (works if fully enclosing text nodes)
                range.surroundContents(span);
            } catch (e) {
                // If it fails, wrap the entire range (including elements) with the span
                const contents = range.extractContents();
                span.appendChild(contents);
                range.insertNode(span);
            }
        }
    }

    function removeHighlight() {
        const highlightedSpans = document.querySelectorAll('span[id^="highlight-Narrator-Extension"]')
        highlightedSpans.forEach(span => {
            const parent = span.parentNode;
            parent.replaceChild(document.createTextNode(span.textContent), span);
            parent.normalize(); // Merge adjacent text nodes
        });
    }

    let socket;

    function connectWebSocket() {
        socket = new WebSocket("ws://127.0.0.1:5000/ws");
    
        socket.onopen = function(event) {
            console.log("WebSocket connection opened", event);
        };
    
        socket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.status === "finished") {
                removehighlightTextInActiveTab(); // Remove highlight when playback is finished
                socket.close(); // Close WebSocket connection after receiving the notification
            }
        };
    
        socket.onclose = function(event) {
            console.log("WebSocket connection closed", event);
        };
    
        socket.onerror = function(error) {
            console.error("WebSocket error:", error);
        };
    }
    
    

    // Restore settings from local storage
    function restoreSettings() {
        chrome.storage.local.get(['voice', 'speed', 'color'], (result) => {
            if (result.voice) {
                voiceSelectElement.value = result.voice;
            }
            if (result.speed) {
                speedSliderElement.value = result.speed;
                speedValueElement.textContent = result.speed + "x";
            }
            if (result.color) {
                colorPickerElement.value = result.color;
            }
        });
    }

    // Check server status
    function checkServerStatus() {
        fetch("http://localhost:5000/healthcheck")
            .then(response => response.json())
            .then(data => {
                if (data.status === "ok") {
                    statusLightElement.classList.add('status-green');
                    statusLightElement.classList.remove('status-red');
                    statusMessageElement.textContent = "Server is running";

                    checkModelStatus();
                } else {
                    throw new Error('Unexpected server status');
                }
            })
            .catch(() => {
                statusLightElement.classList.add('status-red');
                statusLightElement.classList.remove('status-green');
                statusMessageElement.textContent = "Server is not running.";
                toggleLoading(false);
            });
    }

    // Check model status
    function checkModelStatus() {
        fetch("http://localhost:5000/modelCheck")
            .then(response => response.json())
            .then(data => {
                if (data.status === "ready") {
                    toggleLoading(false);
                } else if (data.status === "preloading") {
                    statusMessageElement.textContent = "Model is preloading, please wait...";
                    setTimeout(checkModelStatus, 1000);
                } else {
                    throw new Error('Unexpected model status');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                statusMessageElement.textContent = "Error checking model status.";
                toggleLoading(false);
            });
    }

    // Initial server status check
    toggleLoading(true);
    checkServerStatus();
    restoreSettings();

    // Update speed value display and save settings when slider changes
    speedSliderElement.addEventListener('input', () => {
        const speed = speedSliderElement.value;
        speedValueElement.textContent = speed + "x";
        saveSettings(voiceSelectElement.value, speed, colorPickerElement.value);
    });

    // Save settings when voice changes
    voiceSelectElement.addEventListener('change', () => {
        saveSettings(voiceSelectElement.value, speedSliderElement.value, colorPickerElement.value);
    });

    // Save settings when color changes
    colorPickerElement.addEventListener('input', () => {
        saveSettings(voiceSelectElement.value, speedSliderElement.value, colorPickerElement.value);
    });
    
    // Update server status and send TTS request on button click
    document.getElementById('runTTS').addEventListener('click', () => {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            chrome.scripting.executeScript({
                target: { tabId: tabs[0].id },
                function: () => window.getSelection().toString()
            }, (selection) => {
                const selectedText = selection[0].result.trim();
                const selectedVoice = voiceSelectElement.value;
                const selectedSpeed = speedSliderElement.value;
                const selectedColor = colorPickerElement.value;

                const textToSend = selectedText.length > 0 ? selectedText : "Please select text to read.";
                console.log("highlighting text");
                highlightTextInActiveTab(selectedColor);

                fetch("http://localhost:5000/tts", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ text: textToSend, voice: selectedVoice, speed: selectedSpeed })
                });


                connectWebSocket()
                
            });
        })
    });

    document.getElementById('stopTTS').addEventListener('click', () => {
        fetch("http://localhost:5000/stop", {
            method: "POST",
        })
        .then(response => response.json())
        .then(data => console.log(data.message))
        .then(removehighlightTextInActiveTab())
        .then(console.log("audio ended"))
        .catch(error => console.error('Error:', error));
    });
});
