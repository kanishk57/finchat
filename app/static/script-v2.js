const STORAGE_KEY = 'finchat_sessions_v6';
const UI_STORAGE_KEY = 'finchat_ui_v1';

const chatForm = document.getElementById('chatForm');
const queryInput = document.getElementById('queryInput');
const chatContainer = document.getElementById('chatContainer');
const chatContainerWrapper = document.getElementById('chatContainerWrapper');
const submitBtn = document.getElementById('submitBtn');
const welcomeScreen = document.getElementById('welcomeScreen');
const mainCanvas = document.getElementById('mainCanvas');
const mainDropOverlay = document.getElementById('mainDropOverlay');

const sidebar = document.getElementById('sidebar');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');
const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
const sidebarToggleIcon = document.getElementById('sidebarToggleIcon');
const mobileSidebarToggle = document.getElementById('mobileSidebarToggle');
const mobileSidebarClose = document.getElementById('mobileSidebarClose');
const sidebarSessionSearch = document.getElementById('sidebarSessionSearch');
const sidebarSessionList = document.getElementById('sidebarSessionList');
const sidebarChatSummary = document.getElementById('sidebarChatSummary');

const historyModal = document.getElementById('historyModal');
const historyList = document.getElementById('historyList');

const mentionDropdown = document.getElementById('mentionDropdown');
const mentionList = document.getElementById('mentionList');

const fileUpload = document.getElementById('fileUpload');
const globalFileUpload = document.getElementById('globalFileUpload');

const sidebarDocCount = document.getElementById('sidebarDocCount');
const sidebarStorageValue = document.getElementById('sidebarStorageValue');
const sidebarEntityCount = document.getElementById('sidebarEntityCount');
const sidebarIndexStatus = document.getElementById('sidebarIndexStatus');
const sidebarModelStatus = document.getElementById('sidebarModelStatus');
const sidebarHealthText = document.getElementById('sidebarHealthText');
const sidebarSessionCountBadge = document.getElementById('sidebarSessionCountBadge');
const sidebarActiveSessionBadge = document.getElementById('sidebarActiveSessionBadge');

const activeAnalysisTitle = document.getElementById('activeAnalysisTitle');
const headerSessionStatus = document.getElementById('headerSessionStatus');
const headerVaultStatus = document.getElementById('headerVaultStatus');

const statsModal = document.getElementById('statsModal');
const statsDocumentCount = document.getElementById('statsDocumentCount');
const statsStorageValue = document.getElementById('statsStorageValue');
const statsUpdatedValue = document.getElementById('statsUpdatedValue');
const statsEntitiesList = document.getElementById('statsEntitiesList');

let isSidebarCollapsed = false;
let isMobileSidebarOpen = false;
let progressPollInterval = null;
let latestPortfolioStats = null;
let latestDocuments = [];
let sidebarSearchTerm = '';
let serverReachable = false;

const messageCitationsMap = new Map();

let chatSessions = [];
let currentSessionId = null;

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatBytes(value) {
    const size = Number(value || 0);
    if (!size) return '0 MB';
    const mb = size / (1024 * 1024);
    if (mb >= 1024) return `${(mb / 1024).toFixed(2)} GB`;
    return `${mb.toFixed(2)} MB`;
}

function formatRelativeTime(timestamp) {
    if (!timestamp) return 'Just now';
    const diff = Date.now() - timestamp;
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    return new Date(timestamp).toLocaleDateString();
}

function generateId() {
    return Math.random().toString(36).slice(2, 11);
}

function sortSessions(sessions) {
    return [...sessions].sort((a, b) => {
        if (Boolean(a.pinned) !== Boolean(b.pinned)) {
            return Number(Boolean(b.pinned)) - Number(Boolean(a.pinned));
        }
        return (b.updatedAt || 0) - (a.updatedAt || 0);
    });
}

function normalizeSession(session) {
    const messages = Array.isArray(session?.messages) ? session.messages : [];
    const updatedAt = session?.updatedAt || session?.createdAt || Date.now();
    const normalizedMessages = messages.map((message) => ({
        id: message.id || generateId(),
        role: message.role === 'assistant' ? 'assistant' : 'user',
        html: message.html || '',
        citations: Array.isArray(message.citations) ? message.citations : []
    }));

    return {
        id: session?.id || generateId(),
        title: session?.title || 'New Analysis',
        pinned: Boolean(session?.pinned),
        createdAt: session?.createdAt || updatedAt,
        updatedAt,
        messages: normalizedMessages
    };
}

function createSession(overrides = {}) {
    return normalizeSession({
        id: generateId(),
        title: 'New Analysis',
        pinned: false,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messages: [],
        ...overrides
    });
}

function loadPersistedState() {
    try {
        const rawSessions = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        chatSessions = rawSessions.map(normalizeSession);
    } catch (error) {
        console.error('Failed to parse saved sessions', error);
        chatSessions = [];
    }

    try {
        const uiState = JSON.parse(localStorage.getItem(UI_STORAGE_KEY) || '{}');
        isSidebarCollapsed = Boolean(uiState.sidebarCollapsed);
    } catch (error) {
        console.error('Failed to parse UI state', error);
    }

    if (chatSessions.length === 0) {
        chatSessions.push(createSession());
    }

    chatSessions = sortSessions(chatSessions);
    currentSessionId = chatSessions[0].id;
}

function persistUiState() {
    localStorage.setItem(UI_STORAGE_KEY, JSON.stringify({ sidebarCollapsed: isSidebarCollapsed }));
}

function persistSessions() {
    chatSessions = sortSessions(chatSessions);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chatSessions));
}

function getCurrentSession() {
    return chatSessions.find((session) => session.id === currentSessionId) || null;
}

function closeMobileSidebar() {
    isMobileSidebarOpen = false;
    applySidebarState();
}

function openHistoryModal() {
    historyModal.classList.remove('hidden');
    historyModal.classList.add('flex');
    closeMobileSidebar();
}

async function openSettingsModal() {
    await loadSettings();
    document.getElementById('settingsModal').classList.remove('hidden');
    document.getElementById('settingsModal').classList.add('flex');
}

function applySidebarState() {
    const isDesktop = window.innerWidth >= 1024;
    document.body.classList.toggle('sidebar-collapsed', isDesktop && isSidebarCollapsed);
    document.body.classList.toggle('sidebar-mobile-open', !isDesktop && isMobileSidebarOpen);
    sidebarBackdrop.classList.toggle('hidden', !(!isDesktop && isMobileSidebarOpen));

    if (sidebarToggleIcon) {
        sidebarToggleIcon.textContent = isSidebarCollapsed ? 'right_panel_open' : 'left_panel_open';
    }
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-6 left-1/2 z-[170] -translate-x-1/2 rounded-full bg-[#2f3133] px-5 py-3 text-[13px] font-medium text-white shadow-2xl';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 220ms ease';
        setTimeout(() => toast.remove(), 220);
    }, 2600);
}

function scrollChatToBottom(behavior = 'smooth') {
    chatContainerWrapper.scrollTo({ top: chatContainerWrapper.scrollHeight, behavior });
}

function deriveTitleFromQuery(query) {
    return query.replace(/@[\w.-]+/g, '').trim().replace(/\s+/g, ' ').slice(0, 48) || 'New Analysis';
}

function updateSessionMetadata(session, query) {
    if (!session) return;
    if (!session.messages.length && session.title === 'New Analysis') {
        session.title = deriveTitleFromQuery(query);
    }
    session.updatedAt = Date.now();
}

function renderAssistantContent(text) {
    let content = escapeHtml(text);
    content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    content = content.replace(/(\$[\d,]+(\.\d+)?([MBKT])?)/g, '<strong>$1</strong>');
    content = content.replace(/(\d+(\.\d+)?%)/g, '<strong>$1</strong>');
    content = content.replace(/\[Source (\d+)\]/g, '');
    return content
        .split('\n\n')
        .map((paragraph) => `<p class="mb-4">${paragraph.replace(/\n/g, '<br>')}</p>`)
        .join('');
}

function createMessageElement(role) {
    const isAssistant = role === 'assistant';
    const wrapper = document.createElement('div');
    wrapper.setAttribute('data-role', isAssistant ? 'assistant' : 'user');
    wrapper.className = isAssistant
        ? 'w-full rounded-[28px] border border-[#28292a] bg-[#1d1e20] p-5 text-[#e3e3e3] shadow-lg shadow-black/10 sm:p-6'
        : 'w-full rounded-[28px] bg-transparent p-3 text-[#e3e3e3] sm:p-4';

    wrapper.innerHTML = `
        <div class="flex gap-4">
            <div class="flex-shrink-0">
                <div class="flex h-10 w-10 items-center justify-center rounded-2xl border border-[#333537] bg-[#252628]">
                    <span class="material-symbols-outlined text-[20px] ${isAssistant ? 'text-[#F43F5E]' : 'text-[#768390]'}">${isAssistant ? 'finance' : 'account_circle'}</span>
                </div>
            </div>
            <div class="min-w-0 flex-1 pt-1">
                <div class="mb-3 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.18em] text-[#768390]">
                    ${isAssistant ? 'FinChat' : 'You'}
                </div>
                <div class="content text-[15px] leading-relaxed text-[#e3e3e3]"></div>
                <div class="source-list"></div>
            </div>
        </div>
    `;

    return {
        messageDiv: wrapper,
        content: wrapper.querySelector('.content'),
        sourceList: wrapper.querySelector('.source-list')
    };
}

function buildCitationsHTML(citations, msgId, container) {
    messageCitationsMap.set(msgId, citations || []);
    container.innerHTML = '';

    if (!citations || citations.length === 0) return;

    const shell = document.createElement('div');
    shell.className = 'mt-5 border-t border-[#2c2d2f] pt-4';

    const label = document.createElement('div');
    label.className = 'mb-3 text-[10px] font-bold uppercase tracking-[0.18em] text-[#768390]';
    label.textContent = 'Sources';
    shell.appendChild(label);

    const chipGroup = document.createElement('div');
    chipGroup.className = 'flex flex-wrap gap-2';

    citations.forEach((citation) => {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'flex items-center gap-2 rounded-full border border-[#2f3032] bg-[#202123] px-3 py-1.5 text-xs text-[#e3e3e3] transition-colors hover:border-[#F43F5E] hover:bg-[#262729]';
        chip.dataset.ref = String(citation.ref);
        chip.dataset.msgId = msgId;

        const icon = document.createElement('span');
        icon.className = 'material-symbols-outlined text-[14px] text-[#F43F5E]';
        icon.textContent = 'description';

        const name = document.createElement('span');
        name.className = 'max-w-[160px] truncate';
        name.textContent = citation.doc_name;

        chip.appendChild(icon);
        chip.appendChild(name);
        chipGroup.appendChild(chip);
    });

    shell.appendChild(chipGroup);
    container.appendChild(shell);
}

function openVerification(ref, msgId) {
    const citation = messageCitationsMap.get(msgId)?.find((item) => item.ref === ref);
    if (!citation) return;

    document.getElementById('citationDocName').textContent = citation.doc_name;
    document.getElementById('contextExcerpt').textContent = citation.text || 'Document segment.';

    const metadataDisplay = document.getElementById('metadataDisplay');
    metadataDisplay.innerHTML = '';

    [
        ['Asset', citation.doc_name],
        ['Page', citation.page],
        ['Relevance', citation.relevance ?? 'N/A']
    ].forEach(([label, value]) => {
        const row = document.createElement('div');
        row.className = 'border-b border-[#28292a] py-2';
        row.innerHTML = `
            <div class="mb-1 text-[10px] font-bold uppercase tracking-[0.18em] text-[#c4c7c5]">${escapeHtml(label)}</div>
            <div class="text-xs font-mono text-[#e3e3e3]">${escapeHtml(value)}</div>
        `;
        metadataDisplay.appendChild(row);
    });

    const sourcePreview = document.getElementById('sourcePreview');
    sourcePreview.src = `/pdfs/${encodeURIComponent(citation.doc_name)}#page=${citation.page}`;
    document.getElementById('verificationPanel').classList.remove('hidden');
    document.getElementById('verificationPanel').classList.add('flex');
}

window.showVerification = openVerification;

function saveCurrentChat() {
    const session = getCurrentSession();
    if (!session) return;

    session.messages = Array.from(chatContainer.querySelectorAll('[data-message-id]')).map((messageNode) => ({
        id: messageNode.getAttribute('data-message-id'),
        role: messageNode.getAttribute('data-role') === 'assistant' ? 'assistant' : 'user',
        html: messageNode.querySelector('.content')?.innerHTML || '',
        citations: messageCitationsMap.get(messageNode.getAttribute('data-message-id')) || []
    }));

    session.updatedAt = Date.now();
    persistSessions();
    renderSidebarSessions();
    updateTopLevelStatus();
}

function renderSidebarSessions() {
    const sessions = sortSessions(chatSessions).filter((session) => {
        if (!sidebarSearchTerm) return true;
        return session.title.toLowerCase().includes(sidebarSearchTerm.toLowerCase());
    });

    const pinnedCount = chatSessions.filter((session) => session.pinned).length;
    sidebarChatSummary.textContent = pinnedCount
        ? `${chatSessions.length} chats • ${pinnedCount} pinned`
        : `${chatSessions.length} chats`;
    sidebarSessionList.innerHTML = '';

    if (sessions.length === 0) {
        sidebarSessionList.innerHTML = '<div class="rounded-[22px] border border-dashed border-[#333537] px-4 py-4 text-sm text-[#8f959b]">No sessions match your search.</div>';
    } else {
        sessions.forEach((session) => {
            const item = document.createElement('div');
            item.className = `session-item ${session.id === currentSessionId ? 'active' : ''} rounded-[22px] border border-[#2f3032] bg-[#171819] p-2.5`;
            item.dataset.sessionId = session.id;
            item.innerHTML = `
                <div class="flex items-start gap-2.5">
                    <button type="button" class="min-w-0 flex-1 text-left" data-action="switch">
                        <div class="flex items-center gap-2">
                            <span class="material-symbols-outlined text-[16px] ${session.pinned ? 'text-amber-300' : 'text-[#768390]'}">${session.pinned ? 'keep' : 'chat_bubble'}</span>
                            <span class="truncate text-sm font-medium text-white">${escapeHtml(session.title)}</span>
                        </div>
                        <div class="mt-1.5 flex items-center gap-2 text-[11px] text-[#8c9197]">
                            <span>${session.messages.length} msgs</span>
                            <span>•</span>
                            <span>${formatRelativeTime(session.updatedAt)}</span>
                        </div>
                    </button>
                    <div class="session-actions flex items-center gap-1">
                        <button type="button" data-action="pin" class="rounded-xl p-1.5 text-[#9ca3af] transition-colors hover:text-white" title="Pin session">
                            <span class="material-symbols-outlined text-[16px]">${session.pinned ? 'keep_off' : 'keep'}</span>
                        </button>
                        <button type="button" data-action="rename" class="rounded-xl p-1.5 text-[#9ca3af] transition-colors hover:text-white" title="Rename session">
                            <span class="material-symbols-outlined text-[16px]">edit</span>
                        </button>
                        <button type="button" data-action="delete" class="rounded-xl p-1.5 text-[#9ca3af] transition-colors hover:text-[#F43F5E]" title="Delete session">
                            <span class="material-symbols-outlined text-[16px]">delete</span>
                        </button>
                    </div>
                </div>
            `;
            sidebarSessionList.appendChild(item);
        });
    }

    historyList.innerHTML = sortSessions(chatSessions).map((session) => `
        <div class="rounded-[26px] border border-[#2f3032] bg-[#171819] p-3.5 ${session.id === currentSessionId ? 'border-[#F43F5E]/50' : ''}" data-session-id="${escapeHtml(session.id)}">
            <div class="flex items-start justify-between gap-4">
                <button type="button" class="min-w-0 flex-1 text-left" data-action="switch">
                    <div class="flex items-center gap-2">
                        <span class="material-symbols-outlined text-[16px] ${session.pinned ? 'text-amber-300' : 'text-[#768390]'}">${session.pinned ? 'keep' : 'chat_bubble'}</span>
                        <div class="truncate text-sm font-medium text-white">${escapeHtml(session.title)}</div>
                    </div>
                    <div class="mt-1.5 text-xs text-[#8c9197]">${session.messages.length} messages • ${formatRelativeTime(session.updatedAt)}</div>
                </button>
                <div class="flex items-center gap-1">
                    <button type="button" data-action="pin" class="rounded-xl p-1.5 text-[#9ca3af] transition-colors hover:text-white" title="Pin session"><span class="material-symbols-outlined text-[16px]">${session.pinned ? 'keep_off' : 'keep'}</span></button>
                    <button type="button" data-action="rename" class="rounded-xl p-1.5 text-[#9ca3af] transition-colors hover:text-white" title="Rename session"><span class="material-symbols-outlined text-[16px]">edit</span></button>
                    <button type="button" data-action="delete" class="rounded-xl p-1.5 text-[#9ca3af] transition-colors hover:text-[#F43F5E]" title="Delete session"><span class="material-symbols-outlined text-[16px]">delete</span></button>
                </div>
            </div>
        </div>
    `).join('');
}

function updateTopLevelStatus() {
    const session = getCurrentSession();
    const sessionCount = chatSessions.length;

    activeAnalysisTitle.textContent = session?.title || 'Analysis';
    headerSessionStatus.textContent = session?.messages.length ? `${session.messages.length} messages` : 'Fresh session';
    sidebarSessionCountBadge.textContent = `${sessionCount} ${sessionCount === 1 ? 'session' : 'sessions'}`;
    sidebarActiveSessionBadge.textContent = session ? session.title : 'No active chat';
}

function renderChatArea() {
    const session = getCurrentSession();
    chatContainer.innerHTML = '';
    chatContainer.appendChild(welcomeScreen);

    if (!session) return;

    session.messages.forEach((item) => {
        const { messageDiv, content, sourceList } = createMessageElement(item.role);
        messageDiv.setAttribute('data-message-id', item.id);
        content.innerHTML = item.html;
        buildCitationsHTML(item.citations || [], item.id, sourceList);
        chatContainer.appendChild(messageDiv);
    });

    welcomeScreen.classList.toggle('hidden', session.messages.length > 0);
    updateTopLevelStatus();
    renderSidebarSessions();
    requestAnimationFrame(() => scrollChatToBottom('auto'));
}

function setCurrentSession(sessionId) {
    currentSessionId = sessionId;
    renderChatArea();
    closeMobileSidebar();
}

function createNewSession() {
    const current = sortSessions(chatSessions)[0];
    if (current && current.messages.length === 0 && current.title === 'New Analysis') {
        setCurrentSession(current.id);
        return;
    }

    const session = createSession();
    chatSessions.unshift(session);
    persistSessions();
    setCurrentSession(session.id);
}

async function deleteSession(sessionId) {
    const session = chatSessions.find((item) => item.id === sessionId);
    if (!session) return;
    if (!window.confirm(`Delete session "${session.title}"?`)) return;

    chatSessions = chatSessions.filter((item) => item.id !== sessionId);
    if (chatSessions.length === 0) {
        chatSessions.push(createSession());
    }

    currentSessionId = chatSessions[0].id;
    persistSessions();
    renderChatArea();

    try {
        await fetch(`/api/v1/chat/session/${sessionId}`, { method: 'DELETE' });
        serverReachable = true;
    } catch (error) {
        console.error('Failed to delete session remotely', error);
    }

    showToast('Session deleted.');
}

function renameSession(sessionId) {
    const session = chatSessions.find((item) => item.id === sessionId);
    if (!session) return;

    const nextTitle = window.prompt('Rename session', session.title)?.trim();
    if (!nextTitle) return;

    session.title = nextTitle.slice(0, 80);
    session.updatedAt = Date.now();
    persistSessions();
    renderChatArea();
}

function togglePinnedSession(sessionId) {
    const session = chatSessions.find((item) => item.id === sessionId);
    if (!session) return;
    session.pinned = !session.pinned;
    session.updatedAt = Date.now();
    persistSessions();
    renderSidebarSessions();
}

function handleSessionAction(target) {
    const sessionNode = target.closest('[data-session-id]');
    if (!sessionNode) return;

    const sessionId = sessionNode.dataset.sessionId;
    const action = target.closest('[data-action]')?.dataset.action || 'switch';

    if (action === 'switch') {
        setCurrentSession(sessionId);
        historyModal.classList.add('hidden');
        historyModal.classList.remove('flex');
    }
    if (action === 'rename') renameSession(sessionId);
    if (action === 'pin') togglePinnedSession(sessionId);
    if (action === 'delete') deleteSession(sessionId);
}

function updateSystemHealthText(message) {
    sidebarHealthText.textContent = message;
}

function setModelStatus(text, tone = 'ok') {
    sidebarModelStatus.textContent = text;
    if (tone === 'ok') {
        sidebarModelStatus.style.color = '#86efac';
        sidebarModelStatus.style.borderColor = 'rgba(34,197,94,0.2)';
        sidebarModelStatus.style.background = 'rgba(34,197,94,0.12)';
    } else {
        sidebarModelStatus.style.color = '#fda4af';
        sidebarModelStatus.style.borderColor = 'rgba(244,63,94,0.2)';
        sidebarModelStatus.style.background = 'rgba(244,63,94,0.12)';
    }
}

function updateSidebarStats() {
    const docCount = latestPortfolioStats?.document_count || latestDocuments.length || 0;
    const totalSize = latestPortfolioStats?.total_size_mb ? `${latestPortfolioStats.total_size_mb.toFixed(2)} MB` : formatBytes(latestDocuments.reduce((sum, doc) => sum + Number(doc.size || 0), 0));
    const entityCount = latestPortfolioStats?.unique_entities?.length || 0;

    sidebarDocCount.textContent = String(docCount);
    sidebarStorageValue.textContent = totalSize;
    sidebarEntityCount.textContent = `${entityCount} tracked ${entityCount === 1 ? 'entity' : 'entities'}`;
}

async function loadPortfolioStats() {
    try {
        const response = await fetch('/api/v1/documents/portfolio/stats');
        const stats = await response.json();
        latestPortfolioStats = stats;
        serverReachable = true;

        statsDocumentCount.textContent = String(stats.document_count || 0);
        statsStorageValue.textContent = `${Number(stats.total_size_mb || 0).toFixed(2)} MB`;
        statsUpdatedValue.textContent = stats.last_updated || '-';

        statsEntitiesList.innerHTML = '';
        const entities = Array.isArray(stats.unique_entities) ? stats.unique_entities : [];
        if (entities.length === 0) {
            statsEntitiesList.innerHTML = '<span class="text-sm text-[#8f959b]">No entities detected yet.</span>';
        } else {
            entities.forEach((entity) => {
                const chip = document.createElement('span');
                chip.className = 'rounded-full border border-[#333537] px-3 py-1 text-xs text-[#e3e3e3]';
                chip.textContent = entity;
                statsEntitiesList.appendChild(chip);
            });
        }

        updateSidebarStats();
        setModelStatus('Online', 'ok');
    } catch (error) {
        console.error('Failed to load portfolio stats', error);
        serverReachable = false;
        setModelStatus('Offline', 'error');
    }
}

function renderDocumentList(docs) {
    const docListContainer = document.getElementById('docListContainer');
    if (!docs.length) {
        docListContainer.innerHTML = '<div class="rounded-3xl border border-dashed border-[#333537] px-4 py-6 text-sm text-[#8f959b]">No documents found.</div>';
        return;
    }

    docListContainer.innerHTML = docs.map((doc) => {
        const fileName = doc.name || doc.filename;
        return `
            <div class="group flex items-center justify-between gap-4 rounded-3xl border border-[#2f3032] bg-[#161718] p-4">
                <div class="min-w-0 flex items-center gap-3">
                    <span class="material-symbols-outlined text-[#F43F5E]">description</span>
                    <div class="min-w-0">
                        <div class="truncate text-sm font-medium text-[#e3e3e3]">${escapeHtml(fileName)}</div>
                        <div class="mt-1 text-[10px] uppercase tracking-[0.18em] text-[#768390]">${formatBytes(doc.size)} • ${escapeHtml(doc.source || 'global')}</div>
                    </div>
                </div>
                <button type="button" data-filename="${escapeHtml(fileName)}" class="delete-document-btn rounded-2xl p-2 text-[#768390] transition-colors hover:text-[#F43F5E]" title="Delete document">
                    <span class="material-symbols-outlined text-[18px]">delete</span>
                </button>
            </div>
        `;
    }).join('');
}

async function openKnowledgeVault() {
    const kbModal = document.getElementById('kbModal');
    kbModal.classList.remove('hidden');
    kbModal.classList.add('flex');
    startProgressPolling();

    const docListContainer = document.getElementById('docListContainer');
    docListContainer.innerHTML = '<div class="text-sm text-[#c4c7c5] animate-pulse">Loading documents...</div>';

    try {
        const response = await fetch('/api/v1/documents');
        latestDocuments = await response.json();
        serverReachable = true;
        renderDocumentList(latestDocuments);
        updateSidebarStats();
    } catch (error) {
        console.error('Failed to load documents', error);
        docListContainer.innerHTML = '<div class="text-sm text-[#F43F5E]">Failed to load documents.</div>';
        serverReachable = false;
        setModelStatus('Offline', 'error');
    }
}

async function loadDocumentsSummary() {
    try {
        const response = await fetch('/api/v1/documents');
        latestDocuments = await response.json();
        serverReachable = true;
        updateSidebarStats();
        if (!document.getElementById('kbModal').classList.contains('hidden')) {
            renderDocumentList(latestDocuments);
        }
    } catch (error) {
        console.error('Failed to load documents summary', error);
        serverReachable = false;
        setModelStatus('Offline', 'error');
    }
}

async function deleteDocument(filename) {
    if (!window.confirm(`Delete ${filename}?`)) return;
    showToast(`Deleting ${filename}...`);

    try {
        const response = await fetch(`/api/v1/documents/${encodeURIComponent(filename)}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Failed to delete document');
        serverReachable = true;
        showToast(`${filename} deleted. Reindexing in background.`);
        await openKnowledgeVault();
    } catch (error) {
        console.error('Error deleting document', error);
        showToast('Error deleting document.');
        serverReachable = false;
        setModelStatus('Offline', 'error');
    }
}

async function uploadSessionDocument(file) {
    showToast('Uploading document...');
    const formData = new FormData();
    formData.append('file', file);

    try {
        let uploadUrl = '/api/v1/documents/upload';
        if (currentSessionId) uploadUrl += `?session_id=${currentSessionId}`;
        const response = await fetch(uploadUrl, { method: 'POST', body: formData });
        if (!response.ok) throw new Error('Upload failed');
        serverReachable = true;
        startProgressPolling();
        showToast('Document uploaded successfully.');
    } catch (error) {
        console.error('Error uploading session document', error);
        showToast('Error uploading document.');
        serverReachable = false;
        setModelStatus('Offline', 'error');
    }
}

async function uploadGlobalDocument(file) {
    showToast('Uploading global document...');
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/v1/documents/upload', { method: 'POST', body: formData });
        if (!response.ok) throw new Error('Upload failed');
        serverReachable = true;
        startProgressPolling();
        showToast('Global document uploaded successfully.');
        await openKnowledgeVault();
    } catch (error) {
        console.error('Error uploading global document', error);
        showToast('Error uploading global document.');
        serverReachable = false;
        setModelStatus('Offline', 'error');
    }
}

async function checkProgress() {
    try {
        const response = await fetch('/api/v1/documents/progress');
        const data = await response.json();
        serverReachable = true;

        const kbProgressContainer = document.getElementById('kbProgressContainer');
        const kbProgressText = document.getElementById('kbProgressText');
        const kbProgressPct = document.getElementById('kbProgressPct');
        const kbProgressBar = document.getElementById('kbProgressBar');

        if (data.status !== 'idle') {
            kbProgressContainer.classList.remove('hidden');
            kbProgressText.textContent = data.message;
            kbProgressPct.textContent = `${Math.round(data.progress)}%`;
            kbProgressBar.style.width = `${Math.max(5, Number(data.progress || 0))}%`;
            sidebarIndexStatus.textContent = data.message;
            headerVaultStatus.textContent = `${Math.round(data.progress)}% indexing`;
            updateSystemHealthText(data.message);
        } else {
            kbProgressContainer.classList.add('hidden');
            sidebarIndexStatus.textContent = 'Idle';
            headerVaultStatus.textContent = 'Vault idle';
            updateSystemHealthText('Index and session status');
            if (progressPollInterval) {
                clearInterval(progressPollInterval);
                progressPollInterval = null;
            }
        }

        setModelStatus('Online', 'ok');
    } catch (error) {
        console.error('Failed to check progress', error);
        serverReachable = false;
        setModelStatus('Offline', 'error');
    }
}

function startProgressPolling() {
    if (!progressPollInterval) {
        progressPollInterval = setInterval(checkProgress, 1000);
    }
    checkProgress();
}

async function loadSettings() {
    try {
        const response = await fetch('/api/v1/settings');
        const settings = await response.json();
        document.getElementById('topKRange').value = settings.top_k;
        document.getElementById('topKValue').textContent = settings.top_k;
        document.getElementById('thresholdRange').value = settings.threshold;
        document.getElementById('thresholdValue').textContent = settings.threshold;
        document.getElementById('tempRange').value = settings.temperature;
        document.getElementById('tempValue').textContent = settings.temperature;
        serverReachable = true;
    } catch (error) {
        console.error('Failed to load settings', error);
        serverReachable = false;
        setModelStatus('Offline', 'error');
    }
}

async function saveSettings() {
    const settings = {
        top_k: Number(document.getElementById('topKRange').value),
        threshold: Number(document.getElementById('thresholdRange').value),
        temperature: Number(document.getElementById('tempRange').value)
    };

    try {
        const response = await fetch('/api/v1/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        if (!response.ok) throw new Error('Failed to save settings');
        showToast('Protocol parameters updated.');
        document.getElementById('settingsModal').classList.add('hidden');
        document.getElementById('settingsModal').classList.remove('flex');
        serverReachable = true;
    } catch (error) {
        console.error('Failed to save settings', error);
        showToast('Error saving settings.');
        serverReachable = false;
        setModelStatus('Offline', 'error');
    }
}

async function exportCurrentSession() {
    saveCurrentChat();
    const session = getCurrentSession();
    if (!session || session.messages.length === 0) {
        showToast('Nothing to export yet.');
        return;
    }

    try {
        const response = await fetch('/api/v1/chat/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: session.title, messages: session.messages })
        });
        if (!response.ok) throw new Error('Export failed');

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${session.title.replace(/[^a-z0-9]+/gi, '_').toLowerCase() || 'analysis'}.md`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        showToast('Report exported.');
        serverReachable = true;
    } catch (error) {
        console.error('Failed to export session', error);
        showToast('Failed to export report.');
        serverReachable = false;
        setModelStatus('Offline', 'error');
    }
}

async function updateMentionDropdown() {
    const value = queryInput.value;
    const cursorPosition = queryInput.selectionStart;
    const textBeforeCursor = value.slice(0, cursorPosition);
    const words = textBeforeCursor.split(/\s+/);
    const lastWord = words[words.length - 1];

    if (!lastWord.startsWith('@')) {
        hideMentionDropdown();
        return;
    }

    const query = lastWord.slice(1).toLowerCase();

    try {
        const response = await fetch(`/api/v1/documents?session_id=${currentSessionId}`);
        const docs = await response.json();
        const filteredDocs = docs.filter((doc) => (doc.name || doc.filename).toLowerCase().includes(query));

        if (!filteredDocs.length) {
            hideMentionDropdown();
            return;
        }

        mentionList.innerHTML = filteredDocs.map((doc) => {
            const name = doc.name || doc.filename;
            return `
                <button type="button" class="mention-item flex items-center gap-3 px-4 py-3 text-left text-xs text-[#e3e3e3] transition-colors hover:bg-[#28292a]" data-name="${escapeHtml(name)}">
                    <span class="material-symbols-outlined text-[16px] text-[#F43F5E]">description</span>
                    <span class="truncate">${escapeHtml(name)}</span>
                </button>
            `;
        }).join('');

        mentionDropdown.classList.remove('hidden');
        mentionDropdown.classList.add('flex');
        requestAnimationFrame(() => {
            mentionDropdown.classList.remove('opacity-0');
            mentionDropdown.classList.add('opacity-100');
        });
    } catch (error) {
        console.error('Mention fetch error', error);
        hideMentionDropdown();
    }
}

function hideMentionDropdown() {
    mentionDropdown.classList.add('opacity-0');
    mentionDropdown.classList.remove('opacity-100');
    setTimeout(() => {
        mentionDropdown.classList.add('hidden');
        mentionDropdown.classList.remove('flex');
    }, 180);
}

function autoResizeTextarea() {
    queryInput.style.height = 'auto';
    queryInput.style.height = `${queryInput.scrollHeight}px`;
}

async function submitChat(event) {
    event.preventDefault();
    const query = queryInput.value.trim();
    if (!query) return;

    const session = getCurrentSession();
    if (!session) return;

    updateSessionMetadata(session, query);

    welcomeScreen.classList.add('hidden');

    const userMsgId = generateId();
    const userMessage = createMessageElement('user');
    userMessage.messageDiv.setAttribute('data-message-id', userMsgId);
    userMessage.content.innerHTML = `<p>${escapeHtml(query)}</p>`;
    chatContainer.appendChild(userMessage.messageDiv);

    saveCurrentChat();
    renderSidebarSessions();
    updateTopLevelStatus();

    queryInput.value = '';
    autoResizeTextarea();
    hideMentionDropdown();

    const aiMsgId = generateId();
    const aiMessage = createMessageElement('assistant');
    aiMessage.messageDiv.setAttribute('data-message-id', aiMsgId);
    chatContainer.appendChild(aiMessage.messageDiv);
    scrollChatToBottom();

    const history = session.messages
        .filter((message) => message.id !== userMsgId)
        .map((message) => ({ role: message.role, content: message.html }));

    try {
        submitBtn.disabled = true;
        const response = await fetch('/api/v1/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, session_id: currentSessionId, history })
        });

        if (!response.ok || !response.body) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Server error: ${response.status}`);
        }

        serverReachable = true;
        setModelStatus('Online', 'ok');

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let fullText = '';
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed.startsWith('data: ')) continue;

                const payload = trimmed.slice(6);
                try {
                    const data = JSON.parse(payload);
                    if (data.type === 'citations') {
                        buildCitationsHTML(data.citations, aiMsgId, aiMessage.sourceList);
                    } else if (data.content) {
                        fullText += data.content;
                        aiMessage.content.innerHTML = renderAssistantContent(fullText);
                        scrollChatToBottom('auto');
                    }
                } catch (error) {
                    console.error('Error parsing stream chunk', error, trimmed);
                }
            }
        }

        saveCurrentChat();
        renderChatArea();
    } catch (error) {
        console.error('Chat Error', error);
        aiMessage.content.innerHTML = `
            <div class="flex items-center gap-2 rounded-2xl border border-[#ff4b4b44] bg-[#3d1313] p-3 text-[13px] text-[#ff8b8b]">
                <span class="material-symbols-outlined text-[18px]">error</span>
                <span><strong>Execution Error:</strong> ${escapeHtml(error.message || 'Unknown error occurred.')}</span>
            </div>
        `;
        serverReachable = false;
        setModelStatus('Offline', 'error');
    } finally {
        submitBtn.disabled = false;
    }
}

function setupDragAndDrop() {
    if (mainCanvas && mainDropOverlay) {
        mainCanvas.addEventListener('dragover', (event) => {
            event.preventDefault();
            mainDropOverlay.classList.remove('hidden');
            mainDropOverlay.classList.add('flex');
        });

        mainCanvas.addEventListener('dragleave', (event) => {
            if (event.relatedTarget && mainCanvas.contains(event.relatedTarget)) return;
            mainDropOverlay.classList.add('hidden');
            mainDropOverlay.classList.remove('flex');
        });

        mainCanvas.addEventListener('drop', async (event) => {
            event.preventDefault();
            mainDropOverlay.classList.add('hidden');
            mainDropOverlay.classList.remove('flex');
            if (event.dataTransfer.files.length > 0) {
                await uploadSessionDocument(event.dataTransfer.files[0]);
            }
        });
    }

    const kbModal = document.getElementById('kbModal');
    const kbDropOverlay = document.getElementById('kbDropOverlay');
    if (kbModal && kbDropOverlay) {
        kbModal.addEventListener('dragover', (event) => {
            event.preventDefault();
            kbDropOverlay.classList.remove('hidden');
            kbDropOverlay.classList.add('flex');
        });

        kbModal.addEventListener('dragleave', (event) => {
            if (event.relatedTarget && kbModal.contains(event.relatedTarget)) return;
            kbDropOverlay.classList.add('hidden');
            kbDropOverlay.classList.remove('flex');
        });

        kbModal.addEventListener('drop', async (event) => {
            event.preventDefault();
            kbDropOverlay.classList.add('hidden');
            kbDropOverlay.classList.remove('flex');
            if (event.dataTransfer.files.length > 0) {
                await uploadGlobalDocument(event.dataTransfer.files[0]);
            }
        });
    }
}

function setupEventListeners() {
    sidebarToggleBtn?.addEventListener('click', () => {
        isSidebarCollapsed = !isSidebarCollapsed;
        persistUiState();
        applySidebarState();
    });

    mobileSidebarToggle?.addEventListener('click', () => {
        isMobileSidebarOpen = true;
        applySidebarState();
    });

    mobileSidebarClose?.addEventListener('click', closeMobileSidebar);
    sidebarBackdrop?.addEventListener('click', closeMobileSidebar);

    window.addEventListener('resize', () => {
        if (window.innerWidth >= 1024) isMobileSidebarOpen = false;
        applySidebarState();
    });

    document.getElementById('newChatBtn')?.addEventListener('click', createNewSession);
    document.getElementById('collapsedHistoryBtn')?.addEventListener('click', openHistoryModal);
    document.getElementById('collapsedVaultBtn')?.addEventListener('click', openKnowledgeVault);
    document.getElementById('collapsedSettingsBtn')?.addEventListener('click', openSettingsModal);
    document.getElementById('collapsedExportBtn')?.addEventListener('click', exportCurrentSession);

    sidebarSessionSearch?.addEventListener('input', (event) => {
        sidebarSearchTerm = event.target.value;
        renderSidebarSessions();
    });

    sidebarSessionList?.addEventListener('click', (event) => handleSessionAction(event.target));
    historyList?.addEventListener('click', (event) => handleSessionAction(event.target));

    document.getElementById('historyCloseBtn')?.addEventListener('click', () => {
        historyModal.classList.add('hidden');
        historyModal.classList.remove('flex');
    });

    document.getElementById('kbOpenBtn')?.addEventListener('click', openKnowledgeVault);
    document.getElementById('kbCloseBtn')?.addEventListener('click', () => {
        document.getElementById('kbModal').classList.add('hidden');
        document.getElementById('kbModal').classList.remove('flex');
    });
    document.getElementById('sidebarUploadBtn')?.addEventListener('click', () => globalFileUpload.click());
    document.getElementById('globalUploadBtn')?.addEventListener('click', () => globalFileUpload.click());
    globalFileUpload?.addEventListener('change', async (event) => {
        if (event.target.files.length > 0) {
            await uploadGlobalDocument(event.target.files[0]);
            event.target.value = '';
        }
    });
    document.getElementById('docListContainer')?.addEventListener('click', (event) => {
        const deleteButton = event.target.closest('.delete-document-btn');
        if (!deleteButton) return;
        deleteDocument(deleteButton.dataset.filename);
    });

    document.getElementById('headerSettingsBtn')?.addEventListener('click', openSettingsModal);
    document.getElementById('settingsCloseBtn')?.addEventListener('click', () => {
        document.getElementById('settingsModal').classList.add('hidden');
        document.getElementById('settingsModal').classList.remove('flex');
    });
    document.getElementById('saveSettingsBtn')?.addEventListener('click', saveSettings);

    document.getElementById('topKRange')?.addEventListener('input', (event) => {
        document.getElementById('topKValue').textContent = event.target.value;
    });
    document.getElementById('thresholdRange')?.addEventListener('input', (event) => {
        document.getElementById('thresholdValue').textContent = event.target.value;
    });
    document.getElementById('tempRange')?.addEventListener('input', (event) => {
        document.getElementById('tempValue').textContent = event.target.value;
    });

    document.getElementById('portfolioStatsBtn')?.addEventListener('click', async () => {
        await loadPortfolioStats();
        statsModal.classList.remove('hidden');
        statsModal.classList.add('flex');
    });
    document.getElementById('statsCloseBtn')?.addEventListener('click', () => {
        statsModal.classList.add('hidden');
        statsModal.classList.remove('flex');
    });
    document.getElementById('statsRefreshBtn')?.addEventListener('click', loadPortfolioStats);

    document.getElementById('exportReportBtn')?.addEventListener('click', exportCurrentSession);

    document.getElementById('closeVerificationBtn')?.addEventListener('click', () => {
        document.getElementById('verificationPanel').classList.add('hidden');
        document.getElementById('verificationPanel').classList.remove('flex');
        document.getElementById('sourcePreview').src = 'about:blank';
    });

    document.getElementById('uploadBtn')?.addEventListener('click', () => fileUpload.click());
    fileUpload?.addEventListener('change', async (event) => {
        if (event.target.files.length > 0) {
            await uploadSessionDocument(event.target.files[0]);
            event.target.value = '';
        }
    });

    mentionList?.addEventListener('click', (event) => {
        const item = event.target.closest('.mention-item');
        if (!item) return;
        const value = queryInput.value;
        const cursorPosition = queryInput.selectionStart;
        const textBeforeCursor = value.slice(0, cursorPosition);
        const beforeMention = textBeforeCursor.slice(0, textBeforeCursor.lastIndexOf('@'));
        const afterMention = value.slice(cursorPosition);
        queryInput.value = `${beforeMention}@${item.dataset.name} ${afterMention}`;
        hideMentionDropdown();
        queryInput.focus();
        autoResizeTextarea();
    });

    queryInput?.addEventListener('input', () => {
        autoResizeTextarea();
        updateMentionDropdown();
    });
    queryInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') hideMentionDropdown();
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    chatForm?.addEventListener('submit', submitChat);

    chatContainer?.addEventListener('click', (event) => {
        const chip = event.target.closest('[data-ref][data-msg-id]');
        if (!chip) return;
        openVerification(Number(chip.dataset.ref), chip.dataset.msgId);
    });

    document.querySelectorAll('.welcome-card').forEach((card) => {
        card.addEventListener('click', () => {
            const query = card.getAttribute('data-query');
            if (!query) return;
            queryInput.value = query;
            autoResizeTextarea();
            submitBtn.click();
        });
    });

    document.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
            event.preventDefault();
            createNewSession();
        }
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    loadPersistedState();
    applySidebarState();
    renderChatArea();
    autoResizeTextarea();
    setupEventListeners();
    setupDragAndDrop();
    startProgressPolling();
    await Promise.allSettled([loadPortfolioStats(), loadDocumentsSummary()]);

    if (serverReachable) {
        setModelStatus('Online', 'ok');
    }
});
