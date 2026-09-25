// app.js - Direct Link Bypasser Frontend

const state = {
    mode: 'single',
    history: JSON.parse(localStorage.getItem('bypass_history') || '[]'),
    batchResults: [],
    timerInterval: null
};

document.addEventListener('DOMContentLoaded', () => {
    renderHistory();

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
    const url = input.value.trim();

    if (!url) {
        showToast('Please enter a valid URL.');
        return;
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
    
    let seconds = 0;
    progressText.innerText = 'Traversing ad shortener layers & solving tokens (0s)...';
    stepList.innerHTML = `
        <div class="step-item"><i class="fa-solid fa-bolt fa-spin"></i> Initiating automated token handshake & multi-stage bypass...</div>
    `;

    clearInterval(state.timerInterval);
    state.timerInterval = setInterval(() => {
        seconds++;
        if (seconds < 25) {
            progressText.innerText = `Solving Layer 1 Shortener & Skipping Ad Timers (${seconds}s)...`;
        } else if (seconds < 55) {
            progressText.innerText = `Solving Layer 2 Nested Shortener & Redeeming Target (${seconds}s)...`;
        } else {
            progressText.innerText = `Finalizing Direct Link Retrieval (${seconds}s)...`;
        }
    }, 1000);

    try {
        const response = await fetch(`/api/bypass?url=${encodeURIComponent(url)}`);
        const data = await response.json();
        clearInterval(state.timerInterval);

        if (data.success && data.final_url && data.final_url !== url) {
            displaySingleResult(data);
            saveToHistory(url, data.final_url, data.method);
            showToast('Direct destination link unlocked!');
        } else {
            showToast(data.error || 'Could not find a direct destination link.');
        }
    } catch (err) {
        clearInterval(state.timerInterval);
        showToast('Network timeout or error while solving link.');
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
