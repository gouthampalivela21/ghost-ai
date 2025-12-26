console.log("🔥 Superfast streaming client loaded");

/* ----------------------------------------
   MESSAGE BUBBLE HELPERS
------------------------------------------- */
function addBubble(cls, txt) {
    const messages = document.getElementById("messages");

    const el = document.createElement("div");
    el.className = "msg " + (cls === "user" ? "user" : "bot");
    el.textContent = txt;

    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
}

/* ----------------------------------------
   SMALL TYPING BUBBLE
------------------------------------------- */
function showTyping() {
    const messages = document.getElementById("messages");

    const old = document.getElementById("typingBubble");
    if (old) old.remove();

    const el = document.createElement("div");
    el.className = "msg typing-bubble";
    el.id = "typingBubble";

    el.innerHTML = `
        <div class="typing">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
    `;

    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
}

function hideTyping() {
    const t = document.getElementById("typingBubble");
    if (t) t.remove();
}

/* ----------------------------------------
   SUPERFAST STREAMING FUNCTION
------------------------------------------- */
async function sendStreamingMessage(text) {
    const messages = document.getElementById("messages");

    addBubble("user", text);
    showTyping();

    const botEl = document.createElement("div");
    botEl.className = "msg bot";
    botEl.textContent = "";
    messages.appendChild(botEl);
    messages.scrollTop = messages.scrollHeight;

    const res = await fetch("/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, convo: "default" })
    });

    if (!res.ok) {
        hideTyping();
        botEl.textContent = "⚠️ Streaming error";
        return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    let fullText = "";
    let first = true;

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const parts = chunk.split("\n\n");

        for (let part of parts) {
            part = part.trim();
            if (!part.startsWith("data:")) continue;

            try {
                const obj = JSON.parse(part.replace("data:", "").trim());
                if (!obj.chunk) continue;

                if (first) {
                    hideTyping();
                    first = false;
                }

                fullText += obj.chunk;
                botEl.textContent = fullText;
                messages.scrollTop = messages.scrollHeight;

            } catch (e) {
                console.log("JSON parse error", e);
            }
        }
    }

    hideTyping();
}

/* ----------------------------------------
   PAGE LOAD
------------------------------------------- */
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("inputForm");

    if (form) {
        form.addEventListener("submit", (e) => {
            e.preventDefault();
            const input = document.getElementById("messageInput");
            const txt = input.value.trim();
            if (!txt) return;
            input.value = "";
            sendStreamingMessage(txt);
        });
    }

    fetch("/api/history")
        .then(r => r.json())
        .then(arr => {
            const messages = document.getElementById("messages");
            messages.innerHTML = "";
            arr.forEach(m => addBubble(m.sender, m.text));
        })
        .catch(err => console.log("History load error:", err));

    const chatListBox = document.getElementById("chatList");
    if (chatListBox) {
        fetch("/api/history")
            .then(res => res.json())
            .then(chats => {
                chatListBox.innerHTML = "";
                let grouped = {};
                chats.forEach(c => {
                    grouped[c.convo] = grouped[c.convo] || [];
                    grouped[c.convo].push(c);
                });

                Object.keys(grouped).forEach(convo => {
                    let div = document.createElement("div");
                    div.className = "chat-item";
                    div.textContent = grouped[convo][0].text.slice(0, 30) + "...";
                    div.onclick = () => loadConversation(convo);
                    chatListBox.appendChild(div);
                });
            });
    }
});

/* ----------------------------------------
   LOAD CONVERSATION
------------------------------------------- */
function loadConversation(id) {
    fetch("/api/history")
        .then(r => r.json())
        .then(arr => {
            const messages = document.getElementById("messages");
            messages.innerHTML = "";
            arr.filter(m => m.convo === id)
               .forEach(m => addBubble(m.sender, m.text));
        });
}

/* ----------------------------------------
   PROFILE POPUP CLOSE HANDLERS
------------------------------------------- */
document.addEventListener("click", (e) => {
    if (
        profilePopup.classList.contains("active") &&
        !e.target.closest("#profilePopup") &&
        !e.target.closest("#profileTrigger")
    ) {
        closePopup();
    }
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closePopup();
});