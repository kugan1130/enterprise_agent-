// State Management
let authToken = localStorage.getItem("nexa_token") || "";
let currentUser = JSON.parse(localStorage.getItem("nexa_user") || "null");
let sessionId = "session_" + Math.floor(Math.random() * 1000000);
let activeChartInstance = null;

// DOM Initialization
document.addEventListener("DOMContentLoaded", () => {
    if (authToken && currentUser) {
        showAppScreen();
    } else {
        showAuthModal();
    }
});

// AUTH UI TOGGLE
function switchAuthTab(tab) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".auth-form").forEach(f => f.classList.remove("active"));
    
    if (tab === 'login') {
        document.getElementById("tab-login").classList.add("active");
        document.getElementById("form-login").classList.add("active");
    } else {
        document.getElementById("tab-register").classList.add("active");
        document.getElementById("form-register").classList.add("active");
    }
}

function showAuthModal() {
    document.getElementById("auth-modal").classList.remove("hidden");
    document.getElementById("app-container").classList.add("hidden");
}

function showAppScreen() {
    document.getElementById("auth-modal").classList.add("hidden");
    document.getElementById("app-container").classList.remove("hidden");
    
    document.getElementById("user-name-display").textContent = currentUser.username;
    document.getElementById("user-role-display").textContent = currentUser.role.toUpperCase();
    document.getElementById("active-session-id").textContent = sessionId;

    fetchUploadedDocuments();
}

// LOGIN / REGISTER / LOGOUT
async function handleLogin(event) {
    event.preventDefault();
    const u = document.getElementById("login-username").value;
    const p = document.getElementById("login-password").value;
    const errDiv = document.getElementById("login-error");
    errDiv.classList.add("hidden");

    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: u, password: p }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error?.message || data.detail || "Login failed");

        authToken = data.access_token;
        currentUser = data.user;
        localStorage.setItem("nexa_token", authToken);
        localStorage.setItem("nexa_user", JSON.stringify(currentUser));
        showAppScreen();
    } catch (err) {
        errDiv.textContent = err.message;
        errDiv.classList.remove("hidden");
    }
}

async function handleRegister(event) {
    event.preventDefault();
    const u = document.getElementById("reg-username").value;
    const e = document.getElementById("reg-email").value;
    const p = document.getElementById("reg-password").value;
    const r = document.getElementById("reg-role").value;
    const errDiv = document.getElementById("reg-error");
    errDiv.classList.add("hidden");

    try {
        const res = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: u, email: e, password: p, role: r }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error?.message || data.detail || "Registration failed");

        authToken = data.access_token;
        currentUser = data.user;
        localStorage.setItem("nexa_token", authToken);
        localStorage.setItem("nexa_user", JSON.stringify(currentUser));
        showAppScreen();
    } catch (err) {
        errDiv.textContent = err.message;
        errDiv.classList.remove("hidden");
    }
}

function handleLogout() {
    localStorage.removeItem("nexa_token");
    localStorage.removeItem("nexa_user");
    authToken = "";
    currentUser = null;
    showAuthModal();
}

function startNewSession() {
    sessionId = "session_" + Math.floor(Math.random() * 1000000);
    document.getElementById("active-session-id").textContent = sessionId;
    document.getElementById("chat-messages").innerHTML = `
        <div class="welcome-card">
            <div class="welcome-icon"><i class="fa-solid fa-robot"></i></div>
            <h2>New Chat Session Initialized</h2>
            <p>Session ID: ${sessionId}</p>
        </div>
    `;
    hideActivityPanel();
}

// PDF DOCUMENT UPLOAD
function triggerFileInput() {
    document.getElementById("pdf-file-input").click();
}

function handleFileSelected(event) {
    const file = event.target.files[0];
    if (file) uploadPDF(file);
}

function handleDragOver(event) {
    event.preventDefault();
}

function handleDrop(event) {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file && file.type === "application/pdf") uploadPDF(file);
}

async function uploadPDF(file) {
    const statusDiv = document.getElementById("upload-status");
    const statusText = document.getElementById("upload-status-text");
    statusDiv.classList.remove("hidden");
    statusText.textContent = `Ingesting ${file.name}...`;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/documents/upload", {
            method: "POST",
            headers: { Authorization: `Bearer ${authToken}` },
            body: formData,
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error?.message || data.detail || "Upload failed");

        statusText.textContent = `Success: Ingested ${data.chunks_ingested} text chunks!`;
        setTimeout(() => statusDiv.classList.add("hidden"), 3000);
        fetchUploadedDocuments();
    } catch (err) {
        statusText.textContent = `Upload Error: ${err.message}`;
        setTimeout(() => statusDiv.classList.add("hidden"), 4000);
    }
}

async function fetchUploadedDocuments() {
    if (currentUser?.role !== "admin") return;
    try {
        const res = await fetch("/api/documents", {
            headers: { Authorization: `Bearer ${authToken}` },
        });
        if (!res.ok) return;
        const docs = await res.json();
        const listDiv = document.getElementById("doc-list");
        listDiv.innerHTML = docs.map(d => `
            <div class="doc-item">
                <i class="fa-solid fa-file-pdf" style="color: #ef4444;"></i>
                <span style="flex: 1; overflow: hidden; text-overflow: ellipsis;">${d.filename}</span>
            </div>
        `).join("");
    } catch (err) {
        console.error("Fetch docs error:", err);
    }
}

// CHAT & STREAMING MESSAGES
function handleKeyPress(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleSendMessage(event);
    }
}

async function handleSendMessage(event) {
    event.preventDefault();
    const input = document.getElementById("chat-input");
    const message = input.value.trim();
    if (!message) return;

    input.value = "";

    // Hide welcome card if present
    const welcomeCard = document.querySelector(".welcome-card");
    if (welcomeCard) welcomeCard.remove();

    // 1. Append User Message Bubble
    appendMessage("user", message);

    // 2. Prepare Assistant Message Bubble
    const assistantBubble = appendMessage("assistant", "");
    showActivityPanel();
    addActivityStep("Initializing Multi-Agent Workflow...");

    try {
        const response = await fetch("/api/chat/stream", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${authToken}`,
            },
            body: JSON.stringify({ message: message, session_id: sessionId }),
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.error?.message || errData.detail || "Request failed");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunkStr = decoder.decode(value);
            const lines = chunkStr.split("\n");

            for (const line of lines) {
                if (line.startswith?.("data: ") || line.indexOf("data: ") === 0) {
                    try {
                        const payload = JSON.parse(line.replace("data: ", ""));

                        if (payload.event === "status") {
                            addActivityStep(payload.message);
                        } else if (payload.event === "route_selected") {
                            addActivityStep(`Supervisor Routed to: '${payload.route.toUpperCase()}' Agent`);
                            setRouteBadge(assistantBubble, payload.route);
                        } else if (payload.event === "token") {
                            fullResponse += payload.chunk;
                            renderAssistantContent(assistantBubble, fullResponse);
                        } else if (payload.event === "completed") {
                            addActivityStep("Workflow Execution Completed.");
                            renderAssistantContent(assistantBubble, payload.response);
                        }
                    } catch (e) {
                        // ignore JSON parse error for partial lines
                    }
                }
            }
        }
    } catch (err) {
        addActivityStep(`Execution Error: ${err.message}`);
        assistantBubble.innerHTML = `<span style="color: #ef4444;"><i class="fa-solid fa-triangle-exclamation"></i> Error: ${err.message}</span>`;
    }
}

// APPEND MESSAGES TO DOM
function appendMessage(role, content) {
    const chatCanvas = document.getElementById("chat-messages");
    const row = document.createElement("div");
    row.className = `message-row ${role}-row`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.innerHTML = role === "user" ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-bot"></i>';

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = content;

    row.appendChild(avatar);
    row.appendChild(bubble);
    chatCanvas.appendChild(row);
    chatCanvas.scrollTop = chatCanvas.scrollHeight;

    return bubble;
}

function setRouteBadge(bubble, route) {
    let badge = bubble.querySelector(".route-badge");
    if (!badge) {
        badge = document.createElement("div");
        badge.className = "route-badge";
        bubble.prepend(badge);
    }
    badge.textContent = `Route: ${route.toUpperCase()}`;
}

function renderAssistantContent(bubble, text) {
    // Preserve route badge if present
    const badge = bubble.querySelector(".route-badge");
    const badgeHtml = badge ? badge.outerHTML : "";
    
    // Parse Markdown using Marked.js
    const parsedMd = typeof marked !== "undefined" ? marked.parse(text) : text;
    bubble.innerHTML = badgeHtml + parsedMd;

    const chatCanvas = document.getElementById("chat-messages");
    chatCanvas.scrollTop = chatCanvas.scrollHeight;
}

// AGENT ACTIVITY PANEL
function showActivityPanel() {
    const panel = document.getElementById("agent-activity-panel");
    panel.classList.remove("hidden");
    document.getElementById("activity-steps").innerHTML = "";
}

function hideActivityPanel() {
    document.getElementById("agent-activity-panel").classList.add("hidden");
}

function addActivityStep(stepText) {
    const stepsDiv = document.getElementById("activity-steps");
    const chip = document.createElement("div");
    chip.className = "step-chip active";
    chip.innerHTML = `<i class="fa-solid fa-check"></i> ${stepText}`;
    stepsDiv.appendChild(chip);
    stepsDiv.scrollLeft = stepsDiv.scrollWidth;
}
