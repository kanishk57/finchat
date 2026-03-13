const chatForm = document.getElementById('chatForm');
const queryInput = document.getElementById('queryInput');
const chatContainer = document.getElementById('chatContainer');
const submitBtn = document.getElementById('submitBtn');

// Sidebar logic
const sidebar = document.getElementById('sidebar');
const menuToggle = document.getElementById('menuToggle');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');

if(menuToggle && sidebar) {
    menuToggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });
}
if(mobileMenuBtn && sidebar) {
    mobileMenuBtn.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });
}

function createMessageElement(role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const avatar = document.createElement('div');
    avatar.className = `avatar ${role}`;
    
    if(role === 'assistant') {
        avatar.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
        </svg>`;
    } else {
        avatar.textContent = 'U';
    }
    
    const content = document.createElement('div');
    content.className = 'content';
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    return { messageDiv, content };
}

function renderMarkdownLinks(text) {
    // Basic bold formatting
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Format [Source X] as a cool pill directly inline
    text = text.replace(/\[Source (\d+)\]/g, '<span style="color: var(--coral); font-weight: 800; font-family: var(--font-ui); font-size: 0.9em; background: rgba(255, 135, 67, 0.15); padding: 0 4px; border-radius: 4px;">[S$1]</span>');
    return text;
}

function buildCitationsHTML(citations) {
    // ... logic remains the same ...
    if (!citations || citations.length === 0) return '';
    let html = '<div class="citations-wrapper"><div class="citations-title">Sources Documented</div>';
    citations.forEach(c => {
        // Build the URL to our static /pdfs/ route, adding #page=X
        const url = `/pdfs/${encodeURIComponent(c.doc_name)}#page=${c.page}`;
        html += `<a href="${url}" target="_blank" class="citation-pill" title="Relevance Score: ${c.relevance}"><span>[S${c.ref}]</span> ${c.doc_name} (Pg ${c.page})</a>`;
    });
    html += '</div>';
    return html;
}

// ----------------------------------------------------
// Persistence & Multi-Chat Logic
// ----------------------------------------------------
const STORAGE_KEY = 'finchat_sessions';
let chatSessions = []; // Array of { id, title, messages: [] }
let currentSessionId = null;

function generateId() {
    return Math.random().toString(36).substr(2, 9);
}

function loadSessionsFromStorage() {
    const data = localStorage.getItem(STORAGE_KEY);
    if(data) {
        try {
            chatSessions = JSON.parse(data);
        } catch(e) {
            console.error(e);
            chatSessions = [];
        }
    }
}

function saveSessionsToStorage() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chatSessions));
    renderSidebarHistory();
}

function createNewSession() {
    saveCurrentChat(); // Save the existing chat state first
    currentSessionId = generateId();
    chatSessions.unshift({
        id: currentSessionId,
        title: 'New Chat',
        messages: []
    });
    saveSessionsToStorage();
    renderChatArea();
}

function switchSession(id) {
    if(id === currentSessionId) return;
    saveCurrentChat(); // Save the existing chat state first
    currentSessionId = id;
    renderChatArea();
    if (window.innerWidth <= 768) {
        sidebar.classList.remove('open');
    }
}

function saveCurrentChat() {
    if(!currentSessionId) return;
    
    let currentSession = chatSessions.find(s => s.id === currentSessionId);
    if(!currentSession) return;

    const dynamicMessages = Array.from(chatContainer.querySelectorAll('.message:not(.welcome)'));
    
    // Auto-generate title from first user message if it's still 'New Chat'
    if (currentSession.title === 'New Chat' && dynamicMessages.length > 0) {
        const firstUserMsg = dynamicMessages.find(m => m.classList.contains('user'));
        if (firstUserMsg) {
            const rawText = firstUserMsg.querySelector('.content').textContent.trim();
            currentSession.title = rawText.split(' ').slice(0, 4).join(' ') + '...';
        }
    }

    currentSession.messages = dynamicMessages.map(msgDiv => {
        const isUser = msgDiv.classList.contains('user');
        const role = isUser ? 'user' : 'assistant';
        const rawHTML = msgDiv.querySelector('.content').innerHTML;
        return { role, html: rawHTML };
    });
    
    saveSessionsToStorage();
}

function renderSidebarHistory() {
    const listContainer = document.querySelector('.history-list');
    if(!listContainer) return;
    
    listContainer.innerHTML = '';
    chatSessions.forEach(session => {
        const item = document.createElement('div');
        item.className = 'history-item';
        // Add active class if it's the current session
        if(session.id === currentSessionId) item.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
        
        item.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
            <span>${session.title || 'Chat'}</span>
        `;
        item.addEventListener('click', () => switchSession(session.id));
        listContainer.appendChild(item);
    });
}

function renderChatArea() {
    // Clear current chat
    const dynamicMessages = Array.from(chatContainer.querySelectorAll('.message:not(.welcome)'));
    dynamicMessages.forEach(msg => msg.remove());
    
    const welcomeMsg = chatContainer.querySelector('.welcome');
    
    if(!currentSessionId) {
        if(welcomeMsg) welcomeMsg.style.display = 'flex';
        return;
    }
    
    let currentSession = chatSessions.find(s => s.id === currentSessionId);
    if(currentSession && currentSession.messages.length > 0) {
        if(welcomeMsg) welcomeMsg.style.display = 'none';
        
        currentSession.messages.forEach(item => {
            const { messageDiv, content } = createMessageElement(item.role);
            content.innerHTML = item.html;
            chatContainer.appendChild(messageDiv);
        });
        scrollToBottom();
    } else {
        if(welcomeMsg) welcomeMsg.style.display = 'flex';
    }
    
    renderSidebarHistory();
}

// Clear chat logic / New Chat Button
document.querySelector('.new-chat-btn').addEventListener('click', () => {
    createNewSession();
    if (window.innerWidth <= 768) {
        sidebar.classList.remove('open');
    }
});

// Load history on startup
document.addEventListener('DOMContentLoaded', () => {
    loadSessionsFromStorage();
    if(chatSessions.length > 0) {
        currentSessionId = chatSessions[0].id;
    } else {
        createNewSession();
    }
    renderChatArea();
});

function scrollToBottom() {
    chatContainer.scrollTo({
        top: chatContainer.scrollHeight,
        behavior: 'smooth'
    });
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query) return;

    // Hide welcome message
    const welcomeMsg = chatContainer.querySelector('.welcome');
    if(welcomeMsg) welcomeMsg.style.display = 'none';

    // 1. Add user message
    const { messageDiv: userMsg } = createMessageElement('user');
    userMsg.querySelector('.content').innerHTML = `<p>${query}</p>`;
    chatContainer.appendChild(userMsg);
    
    queryInput.value = '';
    submitBtn.disabled = true;
    scrollToBottom();

    // 2. Add AI placeholder message with typing indicator
    const { messageDiv: aiMsg, content: aiContent } = createMessageElement('assistant');
    const loadingHtml = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    aiContent.innerHTML = loadingHtml;
    chatContainer.appendChild(aiMsg);
    scrollToBottom();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });

        if (!response.ok) throw new Error('API Request Failed');

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let fullText = '';
        let citationsHtml = '';
        let isFirstToken = true;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (let line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.replace('data: ', '').trim();
                    if (!dataStr) continue;

                    try {
                        const data = JSON.parse(dataStr);
                        
                        if (data.type === 'citations') {
                            citationsHtml = buildCitationsHTML(data.citations);
                        } else if (data.type === 'chunk' || data.content) {
                            if (isFirstToken) {
                                aiContent.innerHTML = '';
                                isFirstToken = false;
                            }
                            
                            fullText += data.content || data.chunk || '';
                            
                            // Parse markdown blocks on the fly
                            let formattedText = renderMarkdownLinks(fullText);
                            formattedText = formattedText.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
                            
                            aiContent.innerHTML = `<p>${formattedText}</p>` + citationsHtml;
                            
                            // Only scroll to bottom if we are already near it to not annoy the user
                            const isNearBottom = chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight < 100;
                            if (isNearBottom) {
                                chatContainer.scrollTop = chatContainer.scrollHeight;
                            }
                        } else if (data.type === 'done') {
                            // Stream completed, save history!
                            saveCurrentChat();
                        }
                    } catch (e) {
                         // Some data string might not parse cleanly in chunks, log and ignore
                    }
                }
            }
        }
    } catch (error) {
        console.error('Error in chat:', error);
        aiContent.innerHTML = `<p style="color: #ff6b6b;">Error: Unable to connect to FinChat Intelligence Engine.</p>`;
    } finally {
        submitBtn.disabled = false;
        queryInput.focus();
        scrollToBottom();
        // Fallback save in case stream parsing missed the 'done' type
        saveCurrentChat();
    }
});
