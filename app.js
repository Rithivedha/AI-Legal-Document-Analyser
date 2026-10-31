// Base API configuration (supports GitHub Pages, localtunnel, file://, or local dev)
const defaultApi = (window.location.protocol === 'file:' || window.location.port === '5500' || window.location.port === '3000') 
    ? 'http://localhost:8000' 
    : (window.location.hostname.includes('github.io') ? (localStorage.getItem('API_BASE') || 'https://seven-doors-run.loca.lt') : '');
let API_BASE = localStorage.getItem('API_BASE') || defaultApi;

// State Management
let currentLang = 'en';
let analysisData = null;
let isVoiceQuery = false;
let isListening = false;
let recognition = null;
let currentDocId = null; // identifier returned from /analyze

// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadStatus = document.getElementById('upload-status');
const uploadedFilename = document.getElementById('uploaded-filename');
const loadingSection = document.getElementById('loading-section');
const loadingProgress = document.getElementById('loading-progress');
const uploadSection = document.getElementById('upload-section');
const dashboardSection = document.getElementById('dashboard-section');

// Engine Settings DOM Elements
const engineStatus = document.getElementById('engine-status');
const btnOpenSettings = document.getElementById('btn-open-settings');
const btnCloseSettings = document.getElementById('btn-close-settings');
const settingsModal = document.getElementById('settings-modal');
const settingsProvider = document.getElementById('settings-provider');
const settingsKeyInput = document.getElementById('settings-key-input');
const btnSaveKey = document.getElementById('btn-save-key');

const btnLangEn = document.getElementById('lang-en');
const btnLangTa = document.getElementById('lang-ta');

const summaryText = document.getElementById('summary-text');
const btnVoiceSummary = document.getElementById('btn-voice-summary');
const voiceSummaryLabel = btnVoiceSummary.querySelector('span');

const riskScoreValue = document.getElementById('risk-score-value');
const riskLevelBadge = document.getElementById('risk-level-badge');
const gaugeFill = document.getElementById('gauge-fill');
const riskExplanation = document.getElementById('risk-explanation-text');

const alertsList = document.getElementById('alerts-list');
const termsGrid = document.getElementById('terms-grid');

const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const btnSend = document.getElementById('btn-send');
const btnMic = document.getElementById('btn-mic');
const listeningIndicator = document.getElementById('listening-indicator');
const listeningText = document.getElementById('listening-text');
const chips = document.querySelectorAll('.chat-suggestions .chip');

// Translations
const T = {
    en: {
        voiceSummaryLabel: '🔊 Voice Summary (Tamil)',
        noAlerts: '✅ No major alerts found.',
        noAlertsDesc: 'This document does not contain any obvious high‑risk clauses or penalties.',
        chatWelcome: 'Hello! Ask me anything about your uploaded document. Type a question, click a suggestion, or use the microphone to speak in English or Tamil.',
        placeholder: 'Ask a question about the document…',
        analyzing: 'Analyzing Document...',
        searching: 'Searching Document...'
    },
    ta: {
        voiceSummaryLabel: '🔊 குரல் சுருக்கம்',
        noAlerts: '✅ குறிப்பிடத்தக்க ஆபத்துகள் எதுவும் இல்லை.',
        noAlertsDesc: 'இந்த ஒப்பந்தத்தில் அபராதம் அல்லது கடுமையான ஆபத்துக்கள் எதுவும் கண்டறியப்படவில்லை.',
        chatWelcome: 'வணக்கம்! பதிவேற்றப்பட்ட ஆவணத்தைப் பற்றி ஏதேனும் கேள்விகளை கேளுங்கள். தட்டச்சு செய்யலாம், பரிந்துரைகளை கிளிக் செய்யலாம் அல்லது மைக்ரோஃபோனைப் பயன்படுத்தி ஆங்கிலம் அல்லது தமிழில் பேசலாம்.',
        placeholder: 'ஆவணம் பற்றி ஒரு கேள்வி கேட்கவும்…',
        analyzing: 'ஆவணம் பகுப்பாய்வு... ',
        searching: 'ஆவணத்தைத் தேடுகிறது...'
    }
};

// Loading stages (used for upload analysis)
const STAGES = [
    'Uploading PDF to secure processing server…',
    'Extracting PDF text layers…',
    'Running risk metrics and calculating safety scores…',
    'Identifying warnings and translating legal terminology…',
    'Finalizing analysis report in English and Tamil…'
];

// Speech Synthesis helper
if (window.speechSynthesis) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}
function speakText(text, langCode) {
    if (!window.speechSynthesis || !text) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = langCode;
    const voices = window.speechSynthesis.getVoices();
    const voice = voices.find(v => v.lang.toLowerCase().startsWith(langCode.toLowerCase().slice(0,5)));
    if (voice) utter.voice = voice;
    utter.onstart = () => { if (langCode.startsWith('ta')) btnVoiceSummary.classList.add('playing'); };
    utter.onend = utter.onerror = () => btnVoiceSummary.classList.remove('playing');
    window.speechSynthesis.speak(utter);
}
function isTamil(text) { return /[\u0B80-\u0BFF]/.test(text); }

// Speech Recognition setup
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onstart = () => {
        isListening = true;
        btnMic.classList.add('listening');
        listeningIndicator.classList.remove('hidden');
    };
    recognition.onend = () => {
        isListening = false;
        btnMic.classList.remove('listening');
        listeningIndicator.classList.add('hidden');
    };
    recognition.onerror = (e) => {
        console.error('Speech recognition error:', e);
        isListening = false;
        btnMic.classList.remove('listening');
        listeningIndicator.classList.add('hidden');
    };
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript.trim();
        if (transcript) {
            chatInput.value = transcript;
            isVoiceQuery = true;
            sendMessage();
        }
    };
} else {
    btnMic.style.display = 'none';
    console.warn('SpeechRecognition API not supported');
}

// File upload handling
function initUploadHandlers() {
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => {
        if (fileInput.files[0]) handleFile(fileInput.files[0]);
    });
}

async function handleFile(file) {
    if (file.type !== 'application/pdf') { alert('Please upload a PDF document only.'); return; }
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    uploadedFilename.textContent = file.name;
    uploadStatus.classList.remove('hidden');
    uploadSection.classList.add('hidden');
    dashboardSection.classList.add('hidden');
    loadingSection.classList.remove('hidden');
    // loading stage animation
    let idx = 0;
    loadingProgress.textContent = STAGES[idx];
    const ticker = setInterval(() => { idx = (idx + 1) % STAGES.length; loadingProgress.textContent = STAGES[idx]; }, 2500);
    const form = new FormData();
    form.append('file', file);
    try {
        const resp = await fetch(`${API_BASE}/analyze`, { method: 'POST', body: form });
        if (!resp.ok) {
            let detail = 'Status ' + resp.status;
            try { 
                const errBody = await resp.json(); 
                detail = errBody.detail || detail; 
            } catch (_) {}
            throw new Error(detail);
        }
        const { doc_id } = await resp.json();
        currentDocId = doc_id;
        // fetch cached analysis
        const analysisResp = await fetch(`${API_BASE}/analysis/${doc_id}`);
        if (!analysisResp.ok) {
            let detail = 'Status ' + analysisResp.status;
            try { 
                const errBody = await analysisResp.json(); 
                detail = errBody.detail || detail; 
            } catch (_) {}
            throw new Error('Failed to fetch analysis: ' + detail);
        }
        const { analysis } = await analysisResp.json();
        analysisData = analysis;
        renderDashboard();
        dashboardSection.classList.remove('hidden');
    } catch (err) {
        console.error(err);
        const msg = err.message || 'Unknown error occurred.';
        const displayMsg = msg.toLowerCase().startsWith('analysis failed') ? msg : 'Analysis failed: ' + msg;
        alert(displayMsg);
        uploadSection.classList.remove('hidden');
    } finally {
        clearInterval(ticker);
        loadingSection.classList.add('hidden');
    }
}

// Language toggle
function setLanguage(lang) {
    if (currentLang === lang) return;
    currentLang = lang;
    btnLangEn.classList.toggle('active', lang === 'en');
    btnLangTa.classList.toggle('active', lang === 'ta');
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    renderLanguageElements();
}
btnLangEn.addEventListener('click', () => setLanguage('en'));
btnLangTa.addEventListener('click', () => setLanguage('ta'));

// Rendering functions
function renderDashboard() {
    if (!analysisData) return;
    // Risk gauge
    const score = Math.min(Math.max(Number(analysisData.risk_score) || 0, 0), 100);
    riskScoreValue.textContent = score;
    const ARC = 125.66;
    gaugeFill.style.strokeDasharray = ARC;
    gaugeFill.style.strokeDashoffset = ARC * (1 - score / 100);
    let riskLabel = 'Low Risk', riskCls = 'low';
    if (score > 35 && score <= 70) { riskLabel = 'Medium Risk'; riskCls = 'medium'; }
    else if (score > 70) { riskLabel = 'High Risk'; riskCls = 'high'; }
    riskLevelBadge.textContent = riskLabel;
    riskLevelBadge.className = `risk-level ${riskCls}`;
    // Reset chat welcome
    chatMessages.innerHTML = `<div class="message system-message"><div class="message-bubble">${T[currentLang].chatWelcome}</div></div>`;
    renderLanguageElements();
}

function renderLanguageElements() {
    if (!analysisData) return;
    // Summary
    summaryText.textContent = currentLang === 'ta' ? analysisData.tamil_summary : analysisData.english_summary;
    if (currentLang === 'ta') {
        btnVoiceSummary.classList.remove('hidden');
        voiceSummaryLabel.textContent = T.ta.voiceSummaryLabel;
    } else {
        btnVoiceSummary.classList.add('hidden');
        if (window.speechSynthesis) window.speechSynthesis.cancel();
    }
    // Risk explanation
    riskExplanation.textContent = currentLang === 'ta' ? analysisData.risk_explanation_tamil : analysisData.risk_explanation_english;
    // Alerts
    alertsList.innerHTML = '';
    const alerts = analysisData.beware_alerts || [];
    if (alerts.length === 0) {
        alertsList.innerHTML = `<div class="no-alerts"><svg class="no-alerts-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg><div class="alert-content"><span class="alert-title">${T[currentLang].noAlerts}</span><span class="alert-desc">${T[currentLang].noAlertsDesc}</span></div></div>`;
    } else {
        alerts.forEach(a => {
            const title = currentLang === 'ta' ? a.alert_title_tamil : a.alert_title_english;
            const desc = currentLang === 'ta' ? a.alert_explanation_tamil : a.alert_explanation_english;
            const div = document.createElement('div');
            div.className = 'alert-item';
            div.innerHTML = `<svg class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg><div class="alert-content"><span class="alert-title">⚠ ${title}</span><span class="alert-desc">${desc}</span></div>`;
            alertsList.appendChild(div);
        });
    }
    // Legal terms
    termsGrid.innerHTML = '';
    const terms = analysisData.legal_terms_explained || [];
    terms.forEach(t => {
        const exp = currentLang === 'ta' ? t.explanation_tamil : t.explanation_english;
        const card = document.createElement('div');
        card.className = 'term-card';
        card.innerHTML = `<div class="term-name">${t.term}</div><div class="term-desc">${exp}</div>`;
        termsGrid.appendChild(card);
    });
    // Chat placeholder
    chatInput.placeholder = T[currentLang].placeholder;
}

// Voice summary button
btnVoiceSummary.addEventListener('click', () => {
    if (!analysisData) return;
    if (btnVoiceSummary.classList.contains('playing')) {
        window.speechSynthesis && window.speechSynthesis.cancel();
        btnVoiceSummary.classList.remove('playing');
    } else {
        speakText(analysisData.tamil_summary, 'ta-IN');
    }
});

// Chat handling
function addBubble(text, role) {
    const wrap = document.createElement('div');
    wrap.className = `message ${role}-message`;
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = text;
    wrap.appendChild(bubble);
    chatMessages.appendChild(wrap);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
}

async function sendMessage() {
    const q = chatInput.value.trim();
    if (!q) return;
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    addBubble(q, 'user');
    chatInput.value = '';
    // typing indicator
    const thinkBubble = addBubble('', 'system');
    thinkBubble.classList.add('thinking');
    thinkBubble.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    try {
        const payload = { doc_id: currentDocId, question: q };
        const resp = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json();
        const answer = data.answer || 'Error: No answer.';
        thinkBubble.classList.remove('thinking');
        thinkBubble.textContent = answer;
        chatMessages.scrollTop = chatMessages.scrollHeight;
        if (isVoiceQuery) {
            isVoiceQuery = false;
            speakText(answer, isTamil(answer) ? 'ta-IN' : 'en-US');
        }
    } catch (err) {
        console.error(err);
        thinkBubble.classList.remove('thinking');
        thinkBubble.textContent = 'Failed to connect to backend.';
        isVoiceQuery = false;
    }
}

btnSend.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });
chips.forEach(chip => chip.addEventListener('click', () => { chatInput.value = chip.getAttribute('data-query'); sendMessage(); }));

// Microphone button
btnMic.addEventListener('click', () => {
    if (!recognition) return;
    if (isListening) { recognition.stop(); }
    else { recognition.lang = currentLang === 'ta' ? 'ta-IN' : 'en-US'; try { recognition.start(); } catch (e) { console.warn('Recognition start error:', e); } }
});

// Engine Status and Settings Management
async function fetchEngineStatus() {
    if (!engineStatus) return;
    try {
        const resp = await fetch(`${API_BASE}/api/config`);
        if (resp.ok) {
            const data = await resp.json();
            engineStatus.textContent = '⚡ Engine: ' + data.active_engine;
            engineStatus.title = `Groq: ${data.has_groq ? 'Active' : 'Not set'}, Gemini: ${data.has_gemini ? 'Active' : 'Not set'}`;
        }
    } catch (_) {
        engineStatus.textContent = '⚖️ Built-in Legal Intelligence Engine';
    }
}

if (btnOpenSettings) {
    btnOpenSettings.addEventListener('click', () => {
        settingsModal.classList.remove('hidden');
    });
}

if (btnCloseSettings) {
    btnCloseSettings.addEventListener('click', () => {
        settingsModal.classList.add('hidden');
    });
}

if (btnSaveKey) {
    btnSaveKey.addEventListener('click', async () => {
        const provider = settingsProvider.value;
        const key = settingsKeyInput.value.trim();
        if (!key) {
            alert('Please enter a valid API key.');
            return;
        }
        btnSaveKey.textContent = 'Saving...';
        btnSaveKey.disabled = true;
        try {
            const resp = await fetch(`${API_BASE}/api/set-key`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider, api_key: key })
            });
            const data = await resp.json();
            alert(data.message || 'Key saved successfully!');
            settingsKeyInput.value = '';
            settingsModal.classList.add('hidden');
            fetchEngineStatus();
        } catch (e) {
            alert('Failed to save key: ' + e.message);
        } finally {
            btnSaveKey.textContent = 'Save Key';
            btnSaveKey.disabled = false;
        }
    });
}

// Initialise upload handlers and engine status on page load
initUploadHandlers();
fetchEngineStatus();

