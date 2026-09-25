// app.js - Direct Link Bypasser Frontend

const state = {
    mode: 'single',
    history: JSON.parse(localStorage.getItem('bypass_history') || '[]'),
    batchResults: [],
    timerInterval: null
};

// --- Sound & Notification Alert Engine ---
let audioCtx = null;
let titleFlashInterval = null;
let originalPageTitle = document.title;

function initAudioContext() {
    if (!audioCtx) {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (AudioContextClass) {
            audioCtx = new AudioContextClass();
        }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}

// Pre-unlock AudioContext on first user interaction
document.addEventListener('click', initAudioContext, { once: false });
document.addEventListener('keydown', initAudioContext, { once: false });

function playCompletionChime() {
    if (localStorage.getItem('bypass_sound') === 'false') return;

    try {
        initAudioContext();
        if (audioCtx) {
            const now = audioCtx.currentTime;
            
            // Celebratory 4-stage Chime: C5 -> E5 -> G5 -> C6 with smooth exponential decay
            const notes = [
                { freq: 523.25, time: 0.0, duration: 0.15 },
                { freq: 659.25, time: 0.12, duration: 0.15 },
                { freq: 783.99, time: 0.24, duration: 0.18 },
                { freq: 1046.50, time: 0.38, duration: 0.50 }
            ];

            notes.forEach(n => {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();

                osc.type = 'sine';
                osc.frequency.setValueAtTime(n.freq, now + n.time);

                gain.gain.setValueAtTime(0.001, now + n.time);
                gain.gain.exponentialRampToValueAtTime(0.4, now + n.time + 0.02);
                gain.gain.exponentialRampToValueAtTime(0.0001, now + n.time + n.duration);

                osc.connect(gain);
                gain.connect(audioCtx.destination);

                osc.start(now + n.time);
                osc.stop(now + n.time + n.duration);
            });
        }
    } catch (e) {
        console.warn('Audio synthesis fallback:', e);
    }
}

function flashTabTitle() {
    clearInterval(titleFlashInterval);
    let toggle = false;
    titleFlashInterval = setInterval(() => {
        document.title = toggle ? "⚡ (1) DIRECT LINK READY!" : "🔔 Check Your Link — BypassDirect";
        toggle = !toggle;
    }, 700);

    const onFocus = () => {
        clearInterval(titleFlashInterval);
        document.title = originalPageTitle;
        window.removeEventListener('focus', onFocus);
    };
    window.addEventListener('focus', onFocus);
}

function triggerCompletionAlert(finalUrl) {
    // 1. Play crystal clear audio tone (works in background & minimized tabs)
    playCompletionChime();

    // 2. Flash browser tab title (triggers OS Taskbar flash on Windows)
    flashTabTitle();

    // 3. Desktop Native Push Notification
    if ("Notification" in window) {
        if (Notification.permission === "granted") {
            const notif = new Notification("⚡ Link Bypassed Successfully!", {
                body: "Your direct destination link is ready. Click to open.",
                icon: "https://api.iconify.design/solar:bolt-bold.svg?color=%236366f1",
                requireInteraction: true
            });
            notif.onclick = () => {
                window.focus();
                const openBtn = document.getElementById('openLinkBtn');
                if (openBtn && openBtn.href) {
                    window.open(openBtn.href, '_blank');
                }
            };
        } else if (Notification.permission === "default") {
            Notification.requestPermission();
        }
    }
}

function toggleSoundAlert() {
    const isMuted = localStorage.getItem('bypass_sound') === 'false';
    const newStatus = isMuted ? 'true' : 'false';
    localStorage.setItem('bypass_sound', newStatus);
    updateSoundButtonUI();
    if (newStatus === 'true') {
        playCompletionChime();
        showToast('Sound alert enabled (test chime played)!');
    } else {
        showToast('Sound alert muted.');
    }
}

function testCompletionAlert() {
    initAudioContext();
    triggerCompletionAlert('https://example.com/direct-link-unlocked');
    showToast('Testing alert tone & notification!');
}

function updateSoundButtonUI() {
    const btn = document.getElementById('soundToggleBtn');
    const icon = document.getElementById('soundToggleIcon');
    const statusText = document.getElementById('soundToggleStatus');
    const isMuted = localStorage.getItem('bypass_sound') === 'false';

    if (!btn || !icon || !statusText) return;

    if (isMuted) {
        btn.classList.remove('active');
        icon.className = 'fa-solid fa-volume-xmark';
        statusText.innerText = 'Sound: OFF';
    } else {
        btn.classList.add('active');
        icon.className = 'fa-solid fa-volume-high';
        statusText.innerText = 'Sound: ON';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    renderHistory();
    updateSoundButtonUI();

    // Request notification permissions proactively
    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
    }

    // Dynamically set bookmarklet URL to current site origin
    const bookmarkletEl = document.getElementById('bookmarkletLink');
    if (bookmarkletEl) {
        const origin = window.location.origin;
        bookmarkletEl.href = `javascript:(function(){window.open('${origin}/?url='+encodeURIComponent(location.href),'_blank');})();`;
    }

    // Check if ?url= query parameter is passed (e.g. from bookmarklet)
    const urlParams = new URLSearchParams(window.location.search);
    const paramUrl = urlParams.get('url');
    if (paramUrl) {
        document.getElementById('urlInput').value = paramUrl;
        handleBypass();
    }

    // Enter key triggers bypass in single mode
    document.getElementById('urlInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleBypass();
    });

    // Batch input link counter
    document.getElementById('batchInput').addEventListener('input', (e) => {
        const lines = e.target.value.split('\n').filter(l => l.trim().length > 0);
        document.getElementById('batchCount').innerText = `${lines.length} links detected`;
    });
});

function switchTab(mode) {
    state.mode = mode;
    const singleTab = document.getElementById('singleTabBtn');
    const batchTab = document.getElementById('batchTabBtn');
    const singleMode = document.getElementById('singleMode');
    const batchMode = document.getElementById('batchMode');

    if (mode === 'single') {
        singleTab.classList.add('active');
        batchTab.classList.remove('active');
        singleMode.classList.remove('hidden');
        batchMode.classList.add('hidden');
    } else {
        batchTab.classList.add('active');
        singleTab.classList.remove('active');
        batchMode.classList.remove('hidden');
        singleMode.classList.add('hidden');
    }
}

function fillSample(url) {
    document.getElementById('urlInput').value = url;
    handleBypass();
}

async function pasteClipboard() {
    try {
        const text = await navigator.clipboard.readText();
        if (text) {
            document.getElementById('urlInput').value = text;
            showToast('Pasted from clipboard!');
        }
    } catch (err) {
        showToast('Clipboard access denied.');
    }
}

async function handleBypass() {
    const input = document.getElementById('urlInput');
    const originalInputUrl = input.value.trim();

    if (!originalInputUrl) {
        showToast('Please enter a valid URL.');
        return;
    }

    initAudioContext();
    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
    }

    const btn = document.getElementById('bypassBtn');
    const spinner = document.getElementById('spinner');
    const progressBox = document.getElementById('progressBox');
    const progressText = document.getElementById('progressStatusText');
    const stepList = document.getElementById('stepList');
    const resultCard = document.getElementById('resultCard');

    // UI Loading State
    btn.disabled = true;
    spinner.classList.remove('hidden');
    resultCard.classList.add('hidden');
    progressBox.classList.remove('hidden');
    
    let totalSeconds = 0;
    let currentStage = 1;
    progressText.innerText = `Solving Layer ${currentStage} ad-shortener & bypassing countdowns (0s)...`;
    stepList.innerHTML = `
        <div class="step-item"><i class="fa-solid fa-bolt fa-spin"></i> Initiating automated token handshake for Layer 1...</div>
    `;

    clearInterval(state.timerInterval);
    state.timerInterval = setInterval(() => {
        totalSeconds++;
        progressText.innerText = `Solving Layer ${currentStage} ad-shortener (${totalSeconds}s)...`;
    }, 1000);

    let currentUrl = originalInputUrl;
    let accumulatedHops = [];
    let totalTimeSaved = 0;
    let stagesBypassed = 0;

    try {
        for (let round = 1; round <= 4; round++) {
            currentStage = round;
            if (round > 1) {
                stepList.innerHTML += `
                    <div class="step-item"><i class="fa-solid fa-check" style="color:var(--success)"></i> Layer ${round - 1} Bypassed! Resolving Layer ${round} nested shortener...</div>
                `;
            }

            const response = await fetch(`/api/bypass?url=${encodeURIComponent(currentUrl)}`);
            if (!response.ok) {
                throw new Error(`Server returned HTTP ${response.status}`);
            }
            const data = await response.json();

            if (!data.success || !data.final_url || data.final_url === currentUrl) {
                if (round === 1) {
                    showToast(data.error || 'Could not bypass this link.');
                    return;
                } else {
                    break;
                }
            }

            if (data.hops && Array.isArray(data.hops)) {
                accumulatedHops = accumulatedHops.concat(data.hops);
            }
            totalTimeSaved += (data.time_saved_seconds || 45);
            stagesBypassed += (data.stages_bypassed || 1);
            currentUrl = data.final_url;

            // If not intermediate, we have reached the final destination!
            if (!data.intermediate) {
                break;
            }
        }

        clearInterval(state.timerInterval);

        const finalResult = {
            success: true,
            original_url: originalInputUrl,
            final_url: currentUrl,
            hops: accumulatedHops,
            stages_bypassed: stagesBypassed,
            duration_seconds: totalSeconds,
            time_saved_seconds: totalTimeSaved,
            method: 'Progressive Multi-Tier AdLinkFly & WPSafeLink Direct Solver'
        };

        displaySingleResult(finalResult);
        saveToHistory(originalInputUrl, currentUrl, finalResult.method);
        showToast('Direct destination link unlocked!');

        // Trigger Audio Chime + Desktop Notification + Tab Flash!
        triggerCompletionAlert(currentUrl);

    } catch (err) {
        clearInterval(state.timerInterval);
        showToast(err.message || 'Network timeout or error while solving link.');
    } finally {
        clearInterval(state.timerInterval);
        btn.disabled = false;
        spinner.classList.add('hidden');
        progressBox.classList.add('hidden');
    }
}

function displaySingleResult(data) {
    const resultCard = document.getElementById('resultCard');
    const finalUrlInput = document.getElementById('finalUrlInput');
    const openLinkBtn = document.getElementById('openLinkBtn');

    document.getElementById('statTimeSaved').innerText = `${data.time_saved_seconds || 60}s`;
    document.getElementById('statHops').innerText = data.hops_bypassed || data.stages_bypassed || (data.hops ? data.hops.length : 1);
    document.getElementById('statDuration').innerText = `${data.duration_seconds || 0.4}s`;

    finalUrlInput.value = data.final_url;
    openLinkBtn.href = data.final_url;

    // Render hops timeline
    const timeline = document.getElementById('hopsTimeline');
    timeline.innerHTML = '';
    if (data.hops && Array.isArray(data.hops)) {
        data.hops.forEach((h, idx) => {
            const node = document.createElement('div');
            node.className = 'hop-node';
            const stageText = h.stage || (h.type ? `Redirect (${h.type})` : `Step ${idx+1}`);
            node.innerHTML = `<b>[Hop ${idx + 1}]</b> ${stageText} &rarr; <span style="color:var(--accent)">${h.url || h}</span>`;
            timeline.appendChild(node);
        });
    }

    resultCard.classList.remove('hidden');
}

async function handleBatchBypass() {
    const textarea = document.getElementById('batchInput');
    const rawLines = textarea.value.split('\n').map(l => l.trim()).filter(l => l.length > 0);

    if (rawLines.length === 0) {
        showToast('Please enter at least one URL.');
        return;
    }

    initAudioContext();
    const btn = document.getElementById('batchBypassBtn');
    const spinner = document.getElementById('batchSpinner');
    const batchResultCard = document.getElementById('batchResultCard');
    const tableBody = document.getElementById('batchTableBody');

    btn.disabled = true;
    spinner.classList.remove('hidden');
    tableBody.innerHTML = '';

    try {
        const response = await fetch('/api/batch-bypass', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ urls: rawLines })
        });
        const data = await response.json();
        state.batchResults = data.results || [];

        tableBody.innerHTML = state.batchResults.map((r, i) => `
            <tr>
                <td>${i + 1}</td>
                <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${r.original_url}</td>
                <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--success);font-weight:600;">
                    ${r.final_url || r.error || 'Failed'}
                </td>
                <td>
                    <span class="badge ${r.success ? 'badge-beta' : 'badge-error'}">${r.success ? 'Resolved' : 'Error'}</span>
                </td>
                <td>
                    ${r.success && r.final_url ? `<a href="${r.final_url}" target="_blank" class="btn btn-outline"><i class="fa-solid fa-arrow-up-right-from-square"></i></a>` : '-'}
                </td>
            </tr>
        `).join('');

        batchResultCard.classList.remove('hidden');
        showToast(`Processed ${state.batchResults.length} links!`);

        // Trigger Audio Chime + Desktop Notification + Tab Flash
        triggerCompletionAlert('Batch processing finished');

    } catch (err) {
        showToast('Batch processing failed.');
    } finally {
        btn.disabled = false;
        spinner.classList.add('hidden');
    }
}

function copyFinalUrl() {
    const finalUrl = document.getElementById('finalUrlInput').value;
    if (finalUrl) {
        navigator.clipboard.writeText(finalUrl);
        const copyText = document.getElementById('copyBtnText');
        copyText.innerText = 'Copied!';
        setTimeout(() => { copyText.innerText = 'Copy Link'; }, 2000);
        showToast('Copied direct link to clipboard!');
    }
}

function copyAllBatch() {
    const urls = state.batchResults.filter(r => r.success && r.final_url).map(r => r.final_url).join('\n');
    if (urls) {
        navigator.clipboard.writeText(urls);
        showToast('Copied all direct links to clipboard!');
    }
}

function saveToHistory(orig, dest, method) {
    state.history.unshift({ orig, dest, method, timestamp: new Date().toLocaleTimeString() });
    if (state.history.length > 10) state.history.pop();
    localStorage.setItem('bypass_history', JSON.stringify(state.history));
    renderHistory();
}

function renderHistory() {
    const list = document.getElementById('historyList');
    if (state.history.length === 0) {
        list.innerHTML = '<div class="empty-history">No links bypassed yet in this session.</div>';
        return;
    }

    list.innerHTML = state.history.map(item => `
        <div class="history-item">
            <div class="history-urls">
                <span class="history-dest">${item.dest}</span>
                <span class="history-orig">${item.orig}</span>
            </div>
            <button class="btn btn-paste" onclick="copyText('${item.dest}')" title="Copy URL">
                <i class="fa-regular fa-copy"></i>
            </button>
        </div>
    `).join('');
}

function clearHistory() {
    state.history = [];
    localStorage.removeItem('bypass_history');
    renderHistory();
    showToast('History cleared.');
}

function copyText(text) {
    navigator.clipboard.writeText(text);
    showToast('Copied to clipboard!');
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.innerText = msg;
    toast.classList.remove('hidden');
    setTimeout(() => { toast.classList.add('hidden'); }, 3000);
}
