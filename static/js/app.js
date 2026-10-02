// app.js - Direct Link Bypasser Frontend

const state = {
    mode: 'single',
    history: JSON.parse(localStorage.getItem('bypass_history') || '[]'),
    batchResults: [],
    timerInterval: null
};

// --- Multi-Platform Sound, Notification & Haptic Engine ---
let audioCtx = null;
let fallbackAudioEl = null;
let titleFlashInterval = null;
let originalPageTitle = document.title;

// Generate pure WAV Data URI for universal Android/iOS/Desktop audio playback
function createChimeBlobUrl() {
    try {
        const sampleRate = 22050;
        const duration = 0.8;
        const numSamples = Math.floor(sampleRate * duration);
        const buffer = new ArrayBuffer(44 + numSamples * 2);
        const view = new DataView(buffer);

        function writeString(offset, string) {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        }

        writeString(0, 'RIFF');
        view.setUint32(4, 36 + numSamples * 2, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true); // PCM
        view.setUint16(22, 1, true); // Mono
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeString(36, 'data');
        view.setUint32(40, numSamples * 2, true);

        // Synthesize Celebratory Chime: C5 -> E5 -> G5 -> C6
        for (let i = 0; i < numSamples; i++) {
            const t = i / sampleRate;
            let sample = 0;
            if (t >= 0.0 && t < 0.25) sample += Math.sin(2 * Math.PI * 523.25 * t) * Math.exp(-9 * t);
            if (t >= 0.15 && t < 0.40) sample += Math.sin(2 * Math.PI * 659.25 * t) * Math.exp(-9 * (t - 0.15));
            if (t >= 0.30 && t < 0.55) sample += Math.sin(2 * Math.PI * 783.99 * t) * Math.exp(-8 * (t - 0.30));
            if (t >= 0.45) sample += Math.sin(2 * Math.PI * 1046.50 * t) * Math.exp(-5 * (t - 0.45));

            const clamped = Math.max(-1, Math.min(1, sample * 0.75));
            view.setInt16(44 + i * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7FFF, true);
        }

        const blob = new Blob([view], { type: 'audio/wav' });
        return URL.createObjectURL(blob);
    } catch (e) {
        return null;
    }
}

function initAudioContext() {
    try {
        if (!audioCtx) {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (AudioContextClass) {
                audioCtx = new AudioContextClass();
            }
        }
        if (audioCtx && audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
        if (!fallbackAudioEl) {
            const wavUrl = createChimeBlobUrl();
            if (wavUrl) {
                fallbackAudioEl = new Audio(wavUrl);
                fallbackAudioEl.load();
            }
        }
    } catch (e) {
        console.warn('Audio init error:', e);
    }
}

// Unlock audio context on any user interaction across Android, iOS & Desktop
['click', 'touchstart', 'touchend', 'pointerdown', 'keydown'].forEach(evt => {
    document.addEventListener(evt, initAudioContext, { once: false, passive: true });
});

function playCompletionChime() {
    if (localStorage.getItem('bypass_sound') === 'false') return;

    initAudioContext();

    // 1. Primary Engine: Web Audio API Oscillator
    let playedWebAudio = false;
    try {
        if (audioCtx) {
            if (audioCtx.state === 'suspended') audioCtx.resume();
            const now = audioCtx.currentTime;
            
            const notes = [
                { freq: 523.25, time: 0.0, duration: 0.16 },
                { freq: 659.25, time: 0.12, duration: 0.16 },
                { freq: 783.99, time: 0.24, duration: 0.20 },
                { freq: 1046.50, time: 0.38, duration: 0.50 }
            ];

            notes.forEach(n => {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();

                osc.type = 'sine';
                osc.frequency.setValueAtTime(n.freq, now + n.time);

                gain.gain.setValueAtTime(0.001, now + n.time);
                gain.gain.exponentialRampToValueAtTime(0.45, now + n.time + 0.02);
                gain.gain.exponentialRampToValueAtTime(0.0001, now + n.time + n.duration);

                osc.connect(gain);
                gain.connect(audioCtx.destination);

                osc.start(now + n.time);
                osc.stop(now + n.time + n.duration);
            });
            playedWebAudio = true;
        }
    } catch (e) {
        console.warn('Web Audio synthesis error:', e);
    }

    // 2. Secondary Engine: HTML5 Audio Fallback (reliable for backgrounded Android tabs)
    try {
        if (!playedWebAudio || fallbackAudioEl) {
            if (!fallbackAudioEl) {
                const wavUrl = createChimeBlobUrl();
                if (wavUrl) fallbackAudioEl = new Audio(wavUrl);
            }
            if (fallbackAudioEl) {
                fallbackAudioEl.currentTime = 0;
                fallbackAudioEl.play().catch(() => {});
            }
        }
    } catch (e) {
        console.warn('Fallback audio playback error:', e);
    }

    // 3. Physical Haptic Vibration on Android
    try {
        if ("vibrate" in navigator) {
            navigator.vibrate([250, 100, 250, 100, 400]);
        }
    } catch (e) {}
}

function flashTabTitle() {
    clearInterval(titleFlashInterval);
    let toggle = false;
    titleFlashInterval = setInterval(() => {
        document.title = toggle ? "⚡ (1) DIRECT LINK READY!" : "🔔 Direct Link Unlocked — BypassDirect";
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
    // 1. Play audio tone + Haptic vibration
    playCompletionChime();

    // 2. Flash browser tab title (OS taskbar alert on Windows / title on mobile)
    flashTabTitle();

    // 3. Desktop / Mobile Native Push Notification
    if ("Notification" in window) {
        if (Notification.permission === "granted") {
            const notif = new Notification("⚡ Link Bypassed Successfully!", {
                body: "Your direct destination link is ready. Tap to open.",
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
        showToast('Sound & Vibration Alert ON');
    } else {
        showToast('Sound Alert Muted');
    }
}

function testCompletionAlert() {
    initAudioContext();
    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission().then(() => {
            triggerCompletionAlert('https://example.com/direct-link-unlocked');
        });
    } else {
        triggerCompletionAlert('https://example.com/direct-link-unlocked');
    }
    showToast('Playing test chime & vibration...');
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

    // Proactively initialize audio and notification permission on first interaction
    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
    }

    // Dynamically set bookmarklet URL to current site origin
    const bookmarkletEl = document.getElementById('bookmarkletLink');
    if (bookmarkletEl) {
        const origin = window.location.origin;
        bookmarkletEl.href = `javascript:(function(){window.open('${origin}/?url='+encodeURIComponent(location.href),'_blank');})();`;
    }

    // 1. Check if ?url= query parameter is passed
    const urlParams = new URLSearchParams(window.location.search);
    let targetUrl = urlParams.get('url');

    // 2. Check if URL path is passed as a direct shortcut (e.g. /https://shortxlinks.com/... or /shortxlinks.com/...)
    if (!targetUrl) {
        let rawPath = window.location.pathname.replace(/^\/+/, '');
        if (rawPath && rawPath !== 'index.html') {
            // Fix collapsed slashes
            if (rawPath.startsWith('http:/') && !rawPath.startsWith('http://')) {
                rawPath = rawPath.replace('http:/', 'http://');
            } else if (rawPath.startsWith('https:/') && !rawPath.startsWith('https://')) {
                rawPath = rawPath.replace('https:/', 'https://');
            } else if (!rawPath.startsWith('http://') && !rawPath.startsWith('https://')) {
                if (rawPath.includes('.') && !rawPath.startsWith('api') && !rawPath.startsWith('static') && !rawPath.startsWith('docs')) {
                    rawPath = 'https://' + rawPath;
                }
            }

            if (rawPath.startsWith('http://') || rawPath.startsWith('https://')) {
                if (window.location.search && !targetUrl) {
                    rawPath += window.location.search;
                }
                targetUrl = rawPath;
            }
        }
    }

    if (targetUrl) {
        document.getElementById('urlInput').value = targetUrl;
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

// --- Local Storage Instant 0ms Cache ---
function getLocalCachedBypass(url) {
    try {
        const cache = JSON.parse(localStorage.getItem('bypass_local_cache_v2') || '{}');
        const cleanUrl = url.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/\/+$/, '');
        return cache[cleanUrl] || null;
    } catch (e) {
        return null;
    }
}

function setLocalCachedBypass(origUrl, data) {
    try {
        const cache = JSON.parse(localStorage.getItem('bypass_local_cache_v2') || '{}');
        const cleanUrl = origUrl.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/\/+$/, '');
        cache[cleanUrl] = {
            final_url: data.final_url,
            original_url: origUrl,
            hops: data.hops || [],
            stages_bypassed: data.stages_bypassed || 1,
            time_saved_seconds: data.time_saved_seconds || 60,
            method: data.method || '⚡ Instant Browser Cache (0.0s)',
            partial: Boolean(data.partial),
            verified_destination: Boolean(data.verified_destination),
            cached: true,
            timestamp: Date.now()
        };
        const keys = Object.keys(cache);
        if (keys.length > 100) delete cache[keys[0]];
        localStorage.setItem('bypass_local_cache_v2', JSON.stringify(cache));
    } catch (e) {}
}

function clearLocalCachedBypass(url) {
    try {
        const cache = JSON.parse(localStorage.getItem('bypass_local_cache_v2') || '{}');
        const cleanUrl = url.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/\/+$/, '');
        delete cache[cleanUrl];
        localStorage.setItem('bypass_local_cache_v2', JSON.stringify(cache));
    } catch (e) {}
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

async function handleBypass(forceLive = false) {
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

    // 0. Instant Local Browser Cache Check (0.00s Instant Hit)
    if (!forceLive) {
        const localHit = getLocalCachedBypass(originalInputUrl);
        if (localHit && localHit.final_url) {
            localHit.duration_seconds = 0.00;
            displaySingleResult(localHit);
            saveToHistory(originalInputUrl, localHit.final_url, localHit.method);
            showToast('⚡ Instant 0s Cache Hit!');
            triggerCompletionAlert(localHit.final_url);
            return;
        }
    } else {
        clearLocalCachedBypass(originalInputUrl);
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
    progressText.innerText = forceLive 
        ? `Force re-bypassing live shortener (ignoring cache)...` 
        : `Solving Layer ${currentStage} ad-shortener & checking database cache...`;
    stepList.innerHTML = `
        <div class="step-item"><i class="fa-solid fa-bolt fa-spin"></i> ${forceLive ? 'Initiating fresh live bypass handshake...' : 'Checking instant community cache & solving...'}</div>
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

            const apiUrl = `/api/bypass?url=${encodeURIComponent(currentUrl)}${forceLive && round === 1 ? '&force=true' : ''}`;
            const response = await fetch(apiUrl);
            if (!response.ok) {
                throw new Error(`Server returned HTTP ${response.status}`);
            }
            const data = await response.json();

            if (!data.success || !data.final_url || data.final_url === currentUrl) {
                if (round === 1) {
                    showToast(data.error || 'Could not bypass this link.');
                    return;
                } else {
                    // Previous layer succeeded, but subsequent layer is blocked by captcha / verification
                    clearInterval(state.timerInterval);
                    const finalResult = {
                        success: true,
                        partial: true,
                        verified_destination: false,
                        captcha_blocked: data.captcha_blocked || (data.error && data.error.includes('403')),
                        original_url: originalInputUrl,
                        final_url: currentUrl,
                        hops: accumulatedHops,
                        stages_bypassed: stagesBypassed,
                        duration_seconds: totalSeconds,
                        time_saved_seconds: totalTimeSaved,
                        method: `Progressive Multi-Tier Solver (Layer ${round - 1} Bypassed)`
                    };
                    displaySingleResult(finalResult);
                    setLocalCachedBypass(originalInputUrl, finalResult);
                    saveToHistory(originalInputUrl, currentUrl, finalResult.method);
                    showToast(`Layer ${round - 1} bypassed!`);
                    triggerCompletionAlert(currentUrl);
                    return;
                }
            }

            let isCached = Boolean(data.cached);
            if (data.hops && Array.isArray(data.hops)) {
                accumulatedHops = accumulatedHops.concat(data.hops);
            }
            totalTimeSaved += (data.time_saved_seconds || 45);
            stagesBypassed += (data.stages_bypassed || 1);
            currentUrl = data.final_url;

            // If not intermediate or if served from cache, stop loop
            if (!data.intermediate || isCached) {
                clearInterval(state.timerInterval);
                const finalResult = {
                    success: true,
                    cached: isCached,
                    verified_destination: Boolean(data.verified_destination),
                    original_url: originalInputUrl,
                    final_url: currentUrl,
                    hops: accumulatedHops,
                    stages_bypassed: stagesBypassed,
                    duration_seconds: isCached ? (data.duration_seconds || 0.01) : totalSeconds,
                    time_saved_seconds: totalTimeSaved,
                    method: data.method || 'Progressive Multi-Tier AdLinkFly & WPSafeLink Direct Solver'
                };

                displaySingleResult(finalResult);
                setLocalCachedBypass(originalInputUrl, finalResult);
                saveToHistory(originalInputUrl, currentUrl, finalResult.method);
                showToast(isCached ? '⚡ Instant Cache Hit (0s)!' : 'Direct destination link unlocked!');

                // Trigger Audio Chime + Haptic Vibration + Desktop/Mobile Alert
                triggerCompletionAlert(currentUrl);
                return;
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
        setLocalCachedBypass(originalInputUrl, finalResult);
        saveToHistory(originalInputUrl, currentUrl, finalResult.method);
        showToast('Direct destination link unlocked!');

        // Trigger Audio Chime + Haptic Vibration + Desktop/Mobile Alert
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
    const resultBadge = document.getElementById('resultBadge');
    const resultBadgeIcon = document.getElementById('resultBadgeIcon');
    const resultBadgeText = document.getElementById('resultBadgeText');
    const resultNotice = document.getElementById('resultNotice');
    const finalUrlInput = document.getElementById('finalUrlInput');
    const openLinkBtn = document.getElementById('openLinkBtn');
    const communityVerifyCard = document.getElementById('communityVerifyCard');
    const cacheActionsBar = document.getElementById('cacheActionsBar');

    document.getElementById('statTimeSaved').innerText = `${data.time_saved_seconds || 60}s`;
    document.getElementById('statHops').innerText = data.hops_bypassed || data.stages_bypassed || (data.hops ? data.hops.length : 1);
    document.getElementById('statDuration').innerText = `${data.duration_seconds || 0.4}s`;

    finalUrlInput.value = data.final_url;
    openLinkBtn.href = data.final_url;

    if (data.cached) {
        if (resultBadge) {
            resultBadge.className = 'result-badge cache-badge';
            if (resultBadgeIcon) resultBadgeIcon.className = 'fa-solid fa-bolt-lightning';
            if (resultBadgeText) resultBadgeText.innerText = '⚡ Instant Cache Hit (0s)';
        }
        if (resultNotice) {
            resultNotice.innerHTML = `<i class="fa-solid fa-database" style="font-size:1.3rem;flex-shrink:0;"></i> <span><b>Instant Community Cache!</b> This link was previously solved and served directly in <b>${data.duration_seconds || 0.01}s</b>.</span>`;
            resultNotice.classList.remove('hidden');
        }
        if (openLinkBtn) {
            openLinkBtn.innerHTML = `<i class="fa-solid fa-arrow-up-right-from-square"></i> Open Direct`;
        }
        if (communityVerifyCard) communityVerifyCard.classList.add('hidden');
        if (cacheActionsBar) cacheActionsBar.classList.remove('hidden');

    } else if (data.partial || data.captcha_blocked || !data.verified_destination) {
        if (resultBadge) {
            resultBadge.className = 'result-badge warning-badge';
            if (resultBadgeIcon) resultBadgeIcon.className = 'fa-solid fa-shield-halved';
            if (resultBadgeText) resultBadgeText.innerText = '⚡ Layer 1 Bypassed';
        }
        if (resultNotice) {
            let domain = 'destination';
            try {
                domain = new URL(data.final_url).hostname;
            } catch (e) {}
            resultNotice.innerHTML = `<i class="fa-solid fa-circle-info" style="font-size:1.3rem;flex-shrink:0;"></i> <span><b>Layer 1 Bypassed!</b> The destination host (<b>${domain}</b>) has server-side Cloudflare / Bot Verification enabled. Click <b>"Open Link"</b> below to finish.</span>`;
            resultNotice.classList.remove('hidden');
        }
        if (openLinkBtn) {
            openLinkBtn.innerHTML = `<i class="fa-solid fa-arrow-up-right-from-square"></i> Open Link`;
        }
        if (communityVerifyCard) communityVerifyCard.classList.remove('hidden');
        if (cacheActionsBar) cacheActionsBar.classList.remove('hidden');

    } else {
        if (resultBadge) {
            resultBadge.className = 'result-badge success-badge';
            if (resultBadgeIcon) resultBadgeIcon.className = 'fa-solid fa-circle-check';
            if (resultBadgeText) resultBadgeText.innerText = 'Direct Link Ready';
        }
        if (resultNotice) {
            resultNotice.classList.add('hidden');
            resultNotice.innerHTML = '';
        }
        if (openLinkBtn) {
            openLinkBtn.innerHTML = `<i class="fa-solid fa-arrow-up-right-from-square"></i> Open Direct`;
        }
        if (communityVerifyCard) communityVerifyCard.classList.add('hidden');
        if (cacheActionsBar) cacheActionsBar.classList.add('hidden');
    }

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

function forceReBypass() {
    showToast('🔄 Force live re-bypass started...');
    handleBypass(true);
}

async function submitUserVerifiedLink() {
    const origInput = document.getElementById('urlInput');
    const verifiedInput = document.getElementById('verifiedDirectInput');
    const origUrl = origInput.value.trim();
    const verifiedUrl = verifiedInput.value.trim();

    if (!origUrl || !verifiedUrl) {
        showToast('Please paste the final direct destination link.');
        return;
    }

    if (!verifiedUrl.startsWith('http://') && !verifiedUrl.startsWith('https://')) {
        showToast('Please enter a valid URL starting with https://');
        return;
    }

    const btn = document.getElementById('saveVerifiedBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

    try {
        const response = await fetch('/api/cache-submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ original_url: origUrl, final_url: verifiedUrl })
        });
        const resData = await response.json();

        if (resData.success) {
            showToast('✅ Saved to community cache! Future users will get this link in 0s!');
            const finalResult = {
                success: true,
                cached: true,
                verified_destination: true,
                original_url: origUrl,
                final_url: verifiedUrl,
                duration_seconds: 0.01,
                time_saved_seconds: 90,
                method: 'Community Verified Direct Link'
            };
            displaySingleResult(finalResult);
            setLocalCachedBypass(origUrl, finalResult);
            saveToHistory(origUrl, verifiedUrl, finalResult.method);
            verifiedInput.value = '';
        } else {
            showToast('Failed to save to cache.');
        }
    } catch (err) {
        showToast('Error saving verified link.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-check-double"></i> Save Link';
    }
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

        // Trigger Audio Chime + Vibration + Notification
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
