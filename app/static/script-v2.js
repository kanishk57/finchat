const chatForm = document.getElementById('chatForm');
const queryInput = document.getElementById('queryInput');
const chatContainer = document.getElementById('chatContainer');
const chatContainerWrapper = document.getElementById('chatContainerWrapper');
const submitBtn = document.getElementById('submitBtn');
const welcomeScreen = document.getElementById('welcomeScreen');

// Sidebar/Drawer logic
const metadataSidebar = document.getElementById('metadataSidebar');
const toggleMetadataBtn = document.getElementById('toggleMetadataBtn');
const closeMetadataBtn = document.getElementById('closeMetadataBtn');

toggleMetadataBtn?.addEventListener('click', () => {
    metadataSidebar.classList.toggle('drawer-hidden');
    metadataSidebar.classList.toggle('drawer-visible');
});

closeMetadataBtn?.addEventListener('click', () => {
    metadataSidebar.classList.add('drawer-hidden');
    metadataSidebar.classList.remove('drawer-visible');
});

function openDrawer() {
    metadataSidebar.classList.remove('drawer-hidden');
    metadataSidebar.classList.add('drawer-visible');
}

// Toast Notification
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-24 left-1/2 -translate-x-1/2 bg-[#3c3d3e] text-[#e3e3e3] px-6 py-3 rounded-full shadow-2xl z-[150] font-medium text-[13px] animate-in fade-in slide-in-from-bottom-4 duration-300';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => { toast.classList.add('opacity-0'); setTimeout(() => toast.remove(), 300); }, 3000);
}

// Message Rendering
function createMessageElement(role) {
    const messageDiv = document.createElement('div');
    // Normalize role: default to user if missing or unexpected
    const normalizedRole = (role === 'assistant' || role === 'ai' || role === 'bot') ? 'assistant' : 'user';
    messageDiv.setAttribute('data-role', normalizedRole);
    
    const isAssistant = normalizedRole === 'assistant';
    
    // Base classes that are always present
    const baseClasses = 'w-full flex gap-5 p-6 mb-2 text-[#e3e3e3] animate-in fade-in transition-colors rounded-3xl';
    
    // Use full, non-concatenated strings for Tailwind JIT/Purging compatibility
    if (isAssistant) {
        messageDiv.className = `${baseClasses} bg-[#1e1f20] border border-[#28292a]`;
    } else {
        messageDiv.className = `${baseClasses} bg-transparent`;
    }
    
    const icon = isAssistant ? 'terminal' : 'account_circle';
    const iconColor = isAssistant ? 'text-primary' : 'text-[#768390]';
    const label = isAssistant ? 'FinChat' : 'YOU';

    messageDiv.innerHTML = `
        <div class="flex-shrink-0">
            <div class="w-9 h-9 rounded-xl bg-[#28292a] flex items-center justify-center border border-[#333537]">
                <span class="material-symbols-outlined ${iconColor} text-[22px]">${icon}</span>
            </div>
        </div>
        <div class="flex-1 min-w-0 pt-1">
            <div class="text-[10px] font-bold uppercase tracking-widest text-[#768390] mb-3 flex items-center gap-2">
                ${label}
            </div>
            <div class="content text-[15px] leading-relaxed text-[#e3e3e3]"></div>
            <div class="source-list"></div>
        </div>
    `;
    
    return { 
        messageDiv, 
        content: messageDiv.querySelector('.content'), 
        sourceList: messageDiv.querySelector('.source-list') 
    };
}

function renderMarkdownLinks(text) {
    text = text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
    text = text.replace(/(\$[\d,]+(\.\d+)?([MBK])?)/g, '<b>$1</b>');
    text = text.replace(/(\d+[\/\-]\d+[\/\-]\d+)/g, '<b>$1</b>');
    text = text.replace(/(\d+(\.\d+)?%)/g, '<b>$1</b>');
    return text.replace(/\[Source (\d+)\]/g, '');
}

const messageCitationsMap = new Map();

function buildCitationsHTML(citations, msgId, container) {
    if (!citations || citations.length === 0) return;
    messageCitationsMap.set(msgId, citations);
    
    container.innerHTML = `
        <div class="mt-4 pt-3 border-t border-[#28292a] flex flex-col gap-2">
            <div class="text-[10px] uppercase tracking-widest text-[#768390] font-bold">Sources</div>
            <div class="flex flex-wrap gap-2 items-center"></div>
        </div>
    `;
    const chipGroup = container.querySelector('.flex-wrap');
    
    citations.forEach(c => {
        const chip = document.createElement('div');
        chip.className = 'flex items-center gap-2 bg-[#1e1f20] border border-[#28292a] px-3 py-1 rounded-full text-xs text-[#e3e3e3] hover:border-[#F43F5E] hover:bg-[#28292a] cursor-pointer transition-all';
        chip.innerHTML = `
            <span class="material-symbols-outlined text-[#F43F5E] w-3 h-3 text-[14px]">description</span>
            <span class="max-w-[150px] truncate">${c.doc_name}</span>
        `;
        chip.onclick = () => showVerification(c.ref, msgId);
        chipGroup.appendChild(chip);
    });
}

window.showVerification = function(ref, msgId) {
    const citation = messageCitationsMap.get(msgId)?.find(c => c.ref === ref);
    if (!citation) return;

    const meta = document.getElementById('metadataDisplay');
    meta.innerHTML = `
        <div class="py-2 border-b border-[#28292a]"><div class="text-[10px] text-[#c4c7c5] font-bold uppercase">Asset</div><div class="text-xs font-mono">${citation.doc_name}</div></div>
        <div class="py-2 border-b border-[#28292a]"><div class="text-[10px] text-[#c4c7c5] font-bold uppercase">Page</div><div class="text-xs font-mono">${citation.page}</div></div>
    `;
    document.getElementById('contextExcerpt').textContent = citation.text || 'Document segment.';
    
    const preview = document.getElementById('sourcePreview');
    preview.src = `/pdfs/${encodeURIComponent(citation.doc_name)}#page=${citation.page}`;
    
    document.getElementById('verificationPanel').classList.remove('hidden');
};

// State Management
const STORAGE_KEY = 'finchat_sessions_v6';
let chatSessions = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
let currentSessionId = chatSessions.length > 0 ? chatSessions[0].id : null;

function saveCurrentChat() {
    let session = chatSessions.find(s => s.id === currentSessionId);
    if(!session) return;
    session.messages = Array.from(chatContainer.querySelectorAll('[data-message-id]')).map(msgDiv => {
        // Fallback for role identification if data-role is somehow missing or corrupted
        let role = msgDiv.getAttribute('data-role');
        if (!role) {
            // Check for the assistant's distinctive background color
            role = msgDiv.classList.contains('bg-[#1e1f20]') ? 'assistant' : 'user';
        }
        
        return {
            id: msgDiv.getAttribute('data-message-id'),
            role: role,
            html: msgDiv.querySelector('.content').innerHTML,
            citations: messageCitationsMap.get(msgDiv.getAttribute('data-message-id'))
        };
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chatSessions));
}

function renderChatArea() {
    chatContainer.innerHTML = '';
    let session = chatSessions.find(s => s.id === currentSessionId);
    if (!session) return;
    
    document.getElementById('activeAnalysisTitle').textContent = session.title;
    session.messages.forEach(item => {
        // Robust role detection for old/broken localStorage data
        let role = item.role;
        if (!role) {
            // Infer: Assistant messages usually have citations
            role = (item.citations && item.citations.length > 0) ? 'assistant' : 'user';
        }
        
        const { messageDiv, content, sourceList } = createMessageElement(role);
        messageDiv.setAttribute('data-message-id', item.id);
        content.innerHTML = item.html;
        if(item.citations) buildCitationsHTML(item.citations, item.id, sourceList);
        chatContainer.appendChild(messageDiv);
    });
    welcomeScreen.classList.toggle('hidden', session.messages.length > 0);
}

// Event Listeners
document.getElementById('newChatBtn')?.addEventListener('click', () => { 
    if (chatSessions.length > 0 && chatSessions[0].messages.length === 0) {
        currentSessionId = chatSessions[0].id;
    } else {
        chatSessions.unshift({ id: Math.random().toString(36).substr(2, 9), title: 'New Analysis', messages: [] });
        currentSessionId = chatSessions[0].id;
    }
    renderChatArea();
});
document.getElementById('newChatMobileBtn')?.addEventListener('click', () => document.getElementById('newChatBtn')?.click());

document.getElementById('historyToggle')?.addEventListener('click', () => {
    openDrawer();
    document.getElementById('metadataSidebar').innerHTML = `
        <h3 class="text-sm font-bold text-[#e3e3e3] mb-4">Recent Sessions</h3>
        <div class="flex flex-col gap-2">
            ${chatSessions.map(s => `
                <div class="flex items-center justify-between p-2 bg-[#28292a] rounded group">
                    <div class="flex-1 cursor-pointer text-xs truncate mr-2" onclick="currentSessionId='${s.id}'; renderChatArea();">${s.title}</div>
                    <button onclick="deleteSession('${s.id}')" class="opacity-0 group-hover:opacity-100 text-[#768390] hover:text-[#F43F5E] transition-opacity" title="Delete Session">
                        <span class="material-symbols-outlined text-[16px]">delete</span>
                    </button>
                </div>
            `).join('')}
        </div>`;
});

async function deleteSession(id) {
    if (!confirm("Are you sure you want to delete this session?")) return;

    chatSessions = chatSessions.filter(s => s.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chatSessions));

    try {
        await fetch(`/api/v1/chat/session/${id}`, { method: 'DELETE' });
    } catch (e) {
        console.error("Failed to delete session remotely", e);
    }

    if (currentSessionId === id) {
        if (chatSessions.length === 0) {
            chatSessions.push({ id: Math.random().toString(36).substr(2, 9), title: 'New Analysis', messages: [] });
        }
        currentSessionId = chatSessions[0].id;
        renderChatArea();
    }
    
    // Refresh the drawer UI if it's open
    document.getElementById('historyToggle')?.click();
}
document.getElementById('historyToggleMobile')?.addEventListener('click', () => document.getElementById('historyToggle')?.click());

let progressPollInterval = null;

async function checkProgress() {
    try {
        const res = await fetch('/api/v1/documents/progress');
        const data = await res.json();
        
        const container = document.getElementById('kbProgressContainer');
        const text = document.getElementById('kbProgressText');
        const pct = document.getElementById('kbProgressPct');
        const bar = document.getElementById('kbProgressBar');
        
        if (data.status !== 'idle') {
            container.classList.remove('hidden');
            text.textContent = data.message;
            pct.textContent = `${Math.round(data.progress)}%`;
            bar.style.width = `${Math.max(5, data.progress)}%`;
        } else {
            // Once idle, hide progress and refresh the document list if it was active
            if (!container.classList.contains('hidden')) {
                container.classList.add('hidden');
                if (!document.getElementById('kbModal').classList.contains('hidden')) {
                    openKnowledgeVault(); // Refresh list to show new documents
                }
            }
            if (progressPollInterval) {
                clearInterval(progressPollInterval);
                progressPollInterval = null;
            }
        }
    } catch(e) {
        console.error("Failed to check progress", e);
    }
}

function startProgressPolling() {
    if (!progressPollInterval) {
        progressPollInterval = setInterval(checkProgress, 1000);
    }
}

async function openKnowledgeVault() {
    document.getElementById('kbModal').classList.remove('hidden');
    const docList = document.getElementById('docListContainer');
    // Don't show "Loading" text if we're just refreshing during a progress update
    if (docList.innerHTML.trim() === '') {
        docList.innerHTML = '<div class="text-[#c4c7c5] text-sm animate-pulse">Loading documents...</div>';
    }
    
    // Always check progress when opening the vault
    startProgressPolling();
    
    try {
        const res = await fetch('/api/v1/documents');
        const docs = await res.json();
        if (docs.length === 0) {
            docList.innerHTML = '<div class="text-[#768390] text-sm">No documents found.</div>';
            return;
        }
        docList.innerHTML = docs.map(doc => {
            const fileName = doc.name || doc.filename;
            return `
            <div class="flex items-center justify-between p-4 bg-[#131314] rounded-xl border border-[#28292a] group">
                <div class="flex items-center gap-3">
                    <span class="material-symbols-outlined text-[#F43F5E]">description</span>
                    <div>
                        <div class="text-[#e3e3e3] text-sm font-medium">${fileName}</div>
                        <div class="text-[#768390] text-[10px] uppercase mt-1 tracking-wider">${(doc.size / 1024 / 1024).toFixed(2)} MB</div>
                    </div>
                </div>
                <button onclick="deleteDocument('${fileName}')" class="opacity-0 group-hover:opacity-100 p-2 text-[#768390] hover:text-[#F43F5E] transition-all duration-200 focus:outline-none" title="Delete Document">
                    <span class="material-symbols-outlined text-[18px]">delete</span>
                </button>
            </div>
        `}).join('');
    } catch(e) {
        docList.innerHTML = '<div class="text-[#F43F5E] text-sm">Failed to load documents.</div>';
    }
}

async function deleteDocument(filename) {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) return;
    
    showToast(`Deleting ${filename}...`);
    try {
        const response = await fetch(`/api/v1/documents/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast(`${filename} deleted. Reindexing in background.`);
            // Refresh list and start polling to wait for index rebuild
            openKnowledgeVault();
        } else {
            showToast("Failed to delete document.");
        }
    } catch (e) {
        console.error("Error deleting document:", e);
        showToast("Error deleting document.");
    }
}

document.getElementById('kbOpenBtn')?.addEventListener('click', openKnowledgeVault);
document.getElementById('kbOpenMobileBtn')?.addEventListener('click', openKnowledgeVault);
document.getElementById('kbCloseBtn')?.addEventListener('click', () => document.getElementById('kbModal').classList.add('hidden'));

// Settings Logic
async function loadSettings() {
    try {
        const res = await fetch('/api/v1/settings');
        const settings = await res.json();
        
        document.getElementById('topKRange').value = settings.top_k;
        document.getElementById('topKValue').textContent = settings.top_k;
        
        document.getElementById('thresholdRange').value = settings.threshold;
        document.getElementById('thresholdValue').textContent = settings.threshold;
        
        document.getElementById('tempRange').value = settings.temperature;
        document.getElementById('tempValue').textContent = settings.temperature;
    } catch (e) {
        console.error("Failed to load settings:", e);
    }
}

async function saveSettings() {
    const settings = {
        top_k: parseInt(document.getElementById('topKRange').value),
        threshold: parseFloat(document.getElementById('thresholdRange').value),
        temperature: parseFloat(document.getElementById('tempRange').value)
    };
    
    try {
        const res = await fetch('/api/v1/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        if (res.ok) {
            showToast("Protocol parameters updated.");
            document.getElementById('settingsModal').classList.add('hidden');
        } else {
            showToast("Failed to update settings.");
        }
    } catch (e) {
        console.error("Failed to save settings:", e);
        showToast("Error saving settings.");
    }
}

document.getElementById('topKRange')?.addEventListener('input', (e) => {
    document.getElementById('topKValue').textContent = e.target.value;
});
document.getElementById('thresholdRange')?.addEventListener('input', (e) => {
    document.getElementById('thresholdValue').textContent = e.target.value;
});
document.getElementById('tempRange')?.addEventListener('input', (e) => {
    document.getElementById('tempValue').textContent = e.target.value;
});

document.getElementById('headerSettingsBtn')?.addEventListener('click', () => {
    loadSettings();
    document.getElementById('settingsModal').classList.remove('hidden');
});
document.getElementById('headerSettingsMobileBtn')?.addEventListener('click', () => {
    loadSettings();
    document.getElementById('settingsModal').classList.remove('hidden');
});
document.getElementById('settingsCloseBtn')?.addEventListener('click', () => document.getElementById('settingsModal').classList.add('hidden'));
document.getElementById('saveSettingsBtn')?.addEventListener('click', saveSettings);

document.getElementById('closeVerificationBtn')?.addEventListener('click', () => {
    document.getElementById('verificationPanel').classList.add('hidden');
    document.getElementById('sourcePreview').src = 'about:blank';
});

document.getElementById('uploadBtn')?.addEventListener('click', () => document.getElementById('fileUpload').click());
async function uploadSessionDocument(file) {
    showToast("Uploading document...");
    const formData = new FormData();
    formData.append('file', file);
    try {
        let uploadUrl = '/api/v1/documents/upload';
        if (currentSessionId) uploadUrl += `?session_id=${currentSessionId}`;
        const response = await fetch(uploadUrl, { method: 'POST', body: formData });
        if (response.ok) showToast("Document uploaded successfully.");
        else showToast("Failed to upload document.");
    } catch (error) {
        showToast("Error uploading document.");
    }
}

async function uploadGlobalDocument(file) {
    showToast("Uploading global document...");
    const formData = new FormData();
    formData.append('file', file);
    try {
        const response = await fetch('/api/v1/documents/upload', { method: 'POST', body: formData });
        if (response.ok) {
            showToast("Global document uploaded successfully. Indexing may take a moment.");
            openKnowledgeVault();
        } else showToast("Failed to upload global document.");
    } catch (error) {
        showToast("Error uploading global document.");
    }
}

document.getElementById('fileUpload')?.addEventListener('change', async (e) => {
    if (e.target.files.length > 0) {
        await uploadSessionDocument(e.target.files[0]);
        e.target.value = '';
    }
});

document.getElementById('globalUploadBtn')?.addEventListener('click', () => document.getElementById('globalFileUpload').click());
document.getElementById('globalFileUpload')?.addEventListener('change', async (e) => {
    if (e.target.files.length > 0) {
        await uploadGlobalDocument(e.target.files[0]);
        e.target.value = '';
    }
});

const mainCanvas = document.getElementById('mainCanvas');
const mainDropOverlay = document.getElementById('mainDropOverlay');
if (mainCanvas && mainDropOverlay) {
    mainCanvas.addEventListener('dragover', (e) => {
        e.preventDefault();
        mainDropOverlay.classList.remove('hidden');
        mainDropOverlay.classList.add('flex');
    });
    mainCanvas.addEventListener('dragleave', (e) => {
        if (e.relatedTarget && mainCanvas.contains(e.relatedTarget)) return;
        mainDropOverlay.classList.add('hidden');
        mainDropOverlay.classList.remove('flex');
    });
    mainCanvas.addEventListener('drop', async (e) => {
        e.preventDefault();
        mainDropOverlay.classList.add('hidden');
        mainDropOverlay.classList.remove('flex');
        if (e.dataTransfer.files.length > 0) {
            await uploadSessionDocument(e.dataTransfer.files[0]);
        }
    });
}

const kbModal = document.getElementById('kbModal');
const kbDropOverlay = document.getElementById('kbDropOverlay');
if (kbModal && kbDropOverlay) {
    kbModal.addEventListener('dragover', (e) => {
        e.preventDefault();
        kbDropOverlay.classList.remove('hidden');
        kbDropOverlay.classList.add('flex');
    });
    kbModal.addEventListener('dragleave', (e) => {
        if (e.relatedTarget && kbModal.contains(e.relatedTarget)) return;
        kbDropOverlay.classList.add('hidden');
        kbDropOverlay.classList.remove('flex');
    });
    kbModal.addEventListener('drop', async (e) => {
        e.preventDefault();
        kbDropOverlay.classList.add('hidden');
        kbDropOverlay.classList.remove('flex');
        if (e.dataTransfer.files.length > 0) {
            await uploadGlobalDocument(e.dataTransfer.files[0]);
        }
    });
}

document.querySelectorAll('.welcome-card').forEach(card => {
    card.addEventListener('click', () => {
        const query = card.getAttribute('data-query');
        if (query) {
            queryInput.value = query;
            submitBtn.click();
        }
    });
});

// @ Mentions Logic
const mentionDropdown = document.getElementById('mentionDropdown');
const mentionList = document.getElementById('mentionList');

async function updateMentionDropdown() {
    const value = queryInput.value;
    const cursorPosition = queryInput.selectionStart;
    const textBeforeCursor = value.substring(0, cursorPosition);
    const words = textBeforeCursor.split(/\s+/);
    const lastWord = words[words.length - 1];

    if (lastWord.startsWith('@')) {
        const query = lastWord.substring(1).toLowerCase();
        try {
            const res = await fetch(`/api/v1/documents?session_id=${currentSessionId}`);
            const docs = await res.json();
            
            const filteredDocs = docs.filter(doc => 
                (doc.name || doc.filename).toLowerCase().includes(query)
            );

            if (filteredDocs.length > 0) {
                mentionList.innerHTML = filteredDocs.map(doc => `
                    <div class="px-4 py-2 hover:bg-[#28292a] cursor-pointer text-xs text-[#e3e3e3] flex items-center gap-3 transition-colors mention-item" data-name="${doc.name || doc.filename}">
                        <span class="material-symbols-outlined text-[16px] text-[#F43F5E]">description</span>
                        <span class="truncate">${doc.name || doc.filename}</span>
                    </div>
                `).join('');

                mentionDropdown.classList.remove('hidden');
                setTimeout(() => { mentionDropdown.classList.remove('opacity-0'); mentionDropdown.classList.add('opacity-100'); }, 10);

                // Add click events to items
                document.querySelectorAll('.mention-item').forEach(item => {
                    item.onclick = () => {
                        const name = item.getAttribute('data-name');
                        const beforeMention = textBeforeCursor.substring(0, textBeforeCursor.lastIndexOf('@'));
                        const afterMention = value.substring(cursorPosition);
                        queryInput.value = beforeMention + '@' + name + ' ' + afterMention;
                        hideMentionDropdown();
                        queryInput.focus();
                    };
                });
            } else {
                hideMentionDropdown();
            }
        } catch (e) { console.error("Mention fetch error", e); hideMentionDropdown(); }
    } else {
        hideMentionDropdown();
    }
}

function hideMentionDropdown() {
    mentionDropdown.classList.add('opacity-0');
    mentionDropdown.classList.remove('opacity-100');
    setTimeout(() => mentionDropdown.classList.add('hidden'), 200);
}

function autoResizeTextarea() {
    queryInput.style.height = 'auto';
    queryInput.style.height = (queryInput.scrollHeight) + 'px';
}

queryInput.addEventListener('input', () => {
    updateMentionDropdown();
    autoResizeTextarea();
});

queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        hideMentionDropdown();
    } else if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
    }
});

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query) return;
    
    welcomeScreen.classList.add('hidden');
    const userMsgId = Math.random().toString(36).substr(2, 9);
    const { messageDiv: userMsg } = createMessageElement('user');
    userMsg.setAttribute('data-message-id', userMsgId);
    userMsg.querySelector('.content').innerHTML = `<p>${query}</p>`;
    chatContainer.appendChild(userMsg);
    
    // Save current user message into history BEFORE sending the request
    saveCurrentChat();
    
    queryInput.value = '';
    autoResizeTextarea();
    const aiMsgId = Math.random().toString(36).substr(2, 9);
    const { messageDiv: aiMsg, content: aiContent, sourceList: aiSources } = createMessageElement('assistant');
    aiMsg.setAttribute('data-message-id', aiMsgId);
    chatContainer.appendChild(aiMsg);
    
    // Fetch previous messages for context
    const currentSession = chatSessions.find(s => s.id === currentSessionId);
    const history = currentSession ? currentSession.messages.filter(m => m.id !== userMsgId).map(m => ({
        role: m.role,
        content: m.html
    })) : [];
    
    try {
        const payload = { 
            query, 
            session_id: currentSessionId,
            history: history
        };
        const response = await fetch('/api/v1/chat', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(payload) 
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Server error: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let fullText = '';
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep the last incomplete line

            for (const line of lines) {
                const trimmedLine = line.trim();
                if (!trimmedLine || !trimmedLine.startsWith('data: ')) continue;
                
                try {
                    const data = JSON.parse(trimmedLine.substring(6));
                    if (data.type === 'citations') { 
                        buildCitationsHTML(data.citations, aiMsgId, aiSources); 
                        openDrawer(); 
                    } else if (data.content) {
                        fullText += data.content;
                        aiContent.innerHTML = renderMarkdownLinks(fullText, aiMsgId).split('\n\n').map(p => `<p class="mb-4">${p.replace(/\n/g, '<br>')}</p>`).join('');
                    } else if (data.type === 'done') {
                        // All good
                    }
                } catch (parseError) {
                    console.error("Error parsing JSON chunk:", parseError, trimmedLine);
                }
            }
        }
        saveCurrentChat();
    } catch (e) { 
        console.error("Chat Error:", e);
        aiContent.innerHTML = `
            <div class="flex items-center gap-2 p-3 bg-[#3d1313] border border-[#ff4b4b44] rounded-xl text-[#ff8b8b] text-[13px]">
                <span class="material-symbols-outlined text-[18px]">error</span>
                <span><b>Execution Error:</b> ${e.message || "Unknown error occurred."}</span>
            </div>
        `;
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const data = localStorage.getItem(STORAGE_KEY);
    if(data) {
        try {
            chatSessions = JSON.parse(data);
            
            // Data Migration: Ensure every message has a role to prevent UI breaks on reload
            chatSessions.forEach(session => {
                if (session.messages) {
                    session.messages.forEach(msg => {
                        if (!msg.role) {
                            msg.role = (msg.citations && msg.citations.length > 0) ? 'assistant' : 'user';
                        }
                    });
                }
            });
            // Re-save corrected data
            localStorage.setItem(STORAGE_KEY, JSON.stringify(chatSessions));
        } catch (e) {
            console.error("Failed to parse or migrate localStorage data", e);
        }
    }
    
    if(chatSessions.length === 0) chatSessions.push({ id: Math.random().toString(36).substr(2, 9), title: 'New Analysis', messages: [] });
    currentSessionId = chatSessions[0].id;
    renderChatArea();
    
    // Check if there is an ongoing background task
    startProgressPolling();
});
