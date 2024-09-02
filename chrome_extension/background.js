chrome.contextMenus.create({
    id: "readText",
    title: "Read this text",
    contexts: ["selection"]
});

// Retrieve settings including color
function getSettings(callback) {
    chrome.storage.local.get(['voice', 'speed', 'color'], (result) => {
        // Provide default values if settings are not found
        const voice = result.voice || 'Hopkins';
        const speed = result.speed || 1.0;
        const color = result.color || '#f9174d'; // Default color
        callback(voice, speed, color);
    });
}

// Highlight text in the active tab
function highlightTextInActiveTab(highlightColor) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        chrome.scripting.executeScript({
            target: { tabId: tabs[0].id },
            func: highlightSelection,
            args: [highlightColor]
        });
    });
}

// Function to highlight the selected text
function highlightSelection(color) {
    const selection = window.getSelection();
    if (selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);

        // Create a new span element with the provided color
        const span = document.createElement('span');
        span.style.backgroundColor = color;
        span.style.color = '#000000';
        span.style.padding = '2px';
        span.style.borderRadius = '2px';
        span.id = "highlight-Narrator-Extension";

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

function removehighlightTextInActiveTab() {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        chrome.scripting.executeScript({
            target: { tabId: tabs[0].id },
            function: removeHighlight
        });
    });
}

function removeHighlight() {
    const highlightedSpans = document.querySelectorAll('span[id^="highlight-Narrator-Extension"]');
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


// Listener for context menu click
chrome.contextMenus.onClicked.addListener(function(info) {
    if (info.menuItemId === "readText") {
        getSettings((voice, speed, color) => {
            highlightTextInActiveTab(color);

            fetch("http://127.0.0.1:5000/tts", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ text: info.selectionText, voice: voice, speed: speed })
            });

            
            
            connectWebSocket()

            
        });
    }
});
