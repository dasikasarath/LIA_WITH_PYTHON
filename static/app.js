document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const chatMessages = document.getElementById("chatMessages");
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const sendBtn = document.getElementById("sendBtn");
    const conversationIdInput = document.getElementById("conversationIdInput");
    const activeSessionBadge = document.getElementById("activeSessionBadge");
    const clearMemoryBtn = document.getElementById("clearMemoryBtn");

    // PDF Upload Elements
    const pdfDropzone = document.getElementById("pdfDropzone");
    const pdfFileInput = document.getElementById("pdfFileInput");
    const uploadBtn = document.getElementById("uploadBtn");
    const selectedFileInfo = document.getElementById("selectedFileInfo");
    const selectedFileName = document.getElementById("selectedFileName");
    const selectedFileSize = document.getElementById("selectedFileSize");
    const uploadStatus = document.getElementById("uploadStatus");
    const uploadProgressFill = document.getElementById("uploadProgressFill");
    const uploadStatusMessage = document.getElementById("uploadStatusMessage");

    let selectedFile = null;

    // Synchronize Session ID
    conversationIdInput.addEventListener("input", (e) => {
        const val = e.target.value.trim() || "default-session";
        activeSessionBadge.textContent = `Session: ${val}`;
    });

    // Auto-resize chat textarea
    chatInput.addEventListener("input", function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    chatInput.addEventListener("keydown", function(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event("submit"));
        }
    });

    // Suggestion pills
    document.querySelectorAll(".suggestion-pill").forEach(pill => {
        pill.addEventListener("click", () => {
            const query = pill.getAttribute("data-query");
            chatInput.value = query;
            chatInput.focus();
        });
    });

    // Handle Drag & Drop File Upload
    pdfDropzone.addEventListener("click", () => pdfFileInput.click());

    pdfDropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        pdfDropzone.classList.add("dragover");
    });

    pdfDropzone.addEventListener("dragleave", () => {
        pdfDropzone.classList.remove("dragover");
    });

    pdfDropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        pdfDropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    pdfFileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    function handleFileSelect(file) {
        if (!file.name.toLowerCase().endsWith(".pdf")) {
            alert("Please choose a valid PDF file.");
            return;
        }
        selectedFile = file;
        selectedFileName.textContent = file.name;
        selectedFileSize.textContent = (file.size / (1024 * 1024)).toFixed(2) + " MB";
        selectedFileInfo.style.display = "block";
        uploadBtn.disabled = false;
    }

    // Helper to safely parse responses and prevent JSON parse errors on server errors (e.g. 500)
    async function safeParseResponse(res) {
        const rawText = await res.text();
        let data = null;
        try {
            data = JSON.parse(rawText);
        } catch (_) {
            data = null;
        }

        if (!res.ok) {
            const msg = (data && (data.detail || data.message)) || rawText || `Server error (${res.status})`;
            throw new Error(msg);
        }

        return data !== null ? data : rawText;
    }

    // Health check on initialization to display active model and DB status
    async function checkSystemHealth() {
        try {
            const res = await fetch("/health");
            if (res.ok) {
                const data = await res.json();
                const dbStatusText = document.getElementById("dbStatusText");
                const modelStatusText = document.getElementById("modelStatusText");
                if (dbStatusText) {
                    dbStatusText.textContent = data.database_connected ? "Connected: pgvector" : "DB Disconnected";
                }
                if (modelStatusText) {
                    modelStatusText.textContent = `⚡ ${data.chat_model}`;
                }
            }
        } catch (e) {
            console.warn("Health check error:", e);
        }
    }
    checkSystemHealth();

    // Upload PDF Action
    uploadBtn.addEventListener("click", async () => {
        if (!selectedFile) return;

        uploadBtn.disabled = true;
        uploadStatus.style.display = "block";
        uploadProgressFill.style.width = "40%";
        uploadStatusMessage.textContent = `Uploading and processing '${selectedFile.name}'...`;

        const formData = new FormData();
        formData.append("file", selectedFile);

        try {
            uploadProgressFill.style.width = "75%";
            const res = await fetch("/upload-pdf", {
                method: "POST",
                body: formData
            });

            const data = await safeParseResponse(res);
            uploadProgressFill.style.width = "100%";
            uploadStatusMessage.innerHTML = `<span style="color: #10b981;">✓ Successfully stored ${data.chunks_stored} chunks (${data.pages_processed} pages)!</span>`;
            
            // Append system message to chat
            appendSystemNotice(`📄 Document **${data.filename}** indexed into pgvector with ${data.chunks_stored} chunks.`);
        } catch (err) {
            uploadProgressFill.style.width = "100%";
            uploadProgressFill.style.background = "#ef4444";
            uploadStatusMessage.innerHTML = `<span style="color: #ef4444;">✗ Error: ${err.message}</span>`;
        } finally {
            setTimeout(() => {
                uploadBtn.disabled = false;
            }, 3000);
        }
    });

    // Clear Memory Action
    clearMemoryBtn.addEventListener("click", async () => {
        const convId = conversationIdInput.value.trim() || "default-session";
        if (!confirm(`Clear chat memory for session '${convId}'?`)) return;

        try {
            const res = await fetch("/clear-memory", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ conversation_id: convId })
            });
            const data = await safeParseResponse(res);
            appendSystemNotice(`🗑️ ${data.message}`);
        } catch (e) {
            alert("Failed to clear memory: " + e.message);
        }
    });

    // Chat Form Submit with Real-time Streaming & Fallback
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (!text) return;

        const convId = conversationIdInput.value.trim() || "default-session";

        // Display user message
        appendMessage(text, "user");
        chatInput.value = "";
        chatInput.style.height = "auto";
        sendBtn.disabled = true;

        // Display typing indicator
        const typingElem = appendTypingIndicator();
        chatMessages.scrollTop = chatMessages.scrollHeight;

        let streamingSuccess = false;

        // Attempt Real-time Streaming via SSE for ultra-fast perceived response
        try {
            const streamRes = await fetch("/ask/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question: text,
                    conversation_id: convId
                })
            });

            if (streamRes.ok && streamRes.headers.get("content-type")?.includes("text/event-stream")) {
                if (typingElem.parentNode) typingElem.remove();

                // Create bot message container immediately
                const msgDiv = document.createElement("div");
                msgDiv.className = "message bot";
                const avatar = document.createElement("div");
                avatar.className = "msg-avatar";
                avatar.textContent = "✨";
                const bubble = document.createElement("div");
                bubble.className = "msg-bubble";
                msgDiv.appendChild(avatar);
                msgDiv.appendChild(bubble);
                chatMessages.appendChild(msgDiv);

                let accumulatedAnswer = "";
                let retrievedSources = [];

                const reader = streamRes.body.getReader();
                const decoder = new TextDecoder();
                let buffer = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split("\n");
                    buffer = lines.pop() || "";

                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (!trimmed.startsWith("data:")) continue;
                        const dataStr = trimmed.slice(5).trim();
                        if (!dataStr) continue;

                        try {
                            const parsed = JSON.parse(dataStr);
                            if (parsed.type === "token") {
                                accumulatedAnswer += parsed.data;
                                bubble.innerHTML = marked.parse(accumulatedAnswer);
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            } else if (parsed.type === "meta") {
                                if (parsed.data && parsed.data.sources) {
                                    retrievedSources = parsed.data.sources;
                                }
                            } else if (parsed.type === "error") {
                                accumulatedAnswer += `\n\n*(Notice: ${parsed.data})*`;
                                bubble.innerHTML = marked.parse(accumulatedAnswer);
                            }
                        } catch (parseErr) {
                            console.error("SSE line parse error:", parseErr);
                        }
                    }
                }

                // Append sources if available
                if (retrievedSources && retrievedSources.length > 0) {
                    const sourcesDiv = document.createElement("div");
                    sourcesDiv.className = "msg-sources";
                    sourcesDiv.innerHTML = '<span style="font-size:0.7rem; color:var(--text-muted);">Sources:</span> ' +
                        retrievedSources.map(s => `<span class="source-tag">📌 ${escapeHtml(s)}</span>`).join("");
                    bubble.appendChild(sourcesDiv);
                }

                chatMessages.scrollTop = chatMessages.scrollHeight;
                streamingSuccess = true;
            }
        } catch (streamErr) {
            console.warn("Streaming connection failed, falling back to standard /ask:", streamErr);
            streamingSuccess = false;
        }

        // Fallback to standard /ask if streaming wasn't completed
        if (!streamingSuccess) {
            try {
                const res = await fetch("/ask", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        question: text,
                        conversation_id: convId
                    })
                });

                const data = await safeParseResponse(res);
                if (typingElem.parentNode) typingElem.remove();
                appendMessage(data.answer, "bot", data.sources);
            } catch (err) {
                if (typingElem.parentNode) typingElem.remove();
                appendMessage(`Sorry, an error occurred: ${err.message}`, "bot");
            }
        }

        sendBtn.disabled = false;
        chatInput.focus();
    });

    function appendMessage(text, sender, sources = []) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${sender}`;

        const avatar = document.createElement("div");
        avatar.className = "msg-avatar";
        avatar.textContent = sender === "user" ? "👤" : "✨";

        const bubble = document.createElement("div");
        bubble.className = "msg-bubble";

        if (sender === "bot") {
            bubble.innerHTML = marked.parse(text);
            if (sources && sources.length > 0) {
                const sourcesDiv = document.createElement("div");
                sourcesDiv.className = "msg-sources";
                sourcesDiv.innerHTML = '<span style="font-size:0.7rem; color:var(--text-muted);">Sources:</span> ' +
                    sources.map(s => `<span class="source-tag">📌 ${escapeHtml(s)}</span>`).join("");
                bubble.appendChild(sourcesDiv);
            }
        } else {
            bubble.textContent = text;
        }

        msgDiv.appendChild(avatar);
        msgDiv.appendChild(bubble);
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendTypingIndicator() {
        const div = document.createElement("div");
        div.className = "message bot";
        div.innerHTML = `
            <div class="msg-avatar">✨</div>
            <div class="msg-bubble">
                <div class="typing-dots">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
            </div>
        `;
        chatMessages.appendChild(div);
        return div;
    }

    function appendSystemNotice(html) {
        const div = document.createElement("div");
        div.style.textAlign = "center";
        div.style.margin = "8px 0";
        div.style.fontSize = "0.78rem";
        div.style.color = "var(--text-muted)";
        div.innerHTML = marked.parse(html);
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function escapeHtml(string) {
        return String(string).replace(/[&<>"']/g, function(s) {
            return {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            }[s];
        });
    }
});
