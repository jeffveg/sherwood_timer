/* ==========================================
   Sherwood Adventure Timer - Scorer
   Scoring-only controller — no game management,
   no start/stop/pause, no settings.
   ========================================== */

const socket = io();

// Current state from the server
let state = {};

// Debounce tracking
const cooldowns = {};
const DEBOUNCE_MS = 500;

// ==========================================
// DOM Element Cache
// ==========================================
const el = {};

function cacheElements() {
    // Views
    el.gameHeader = document.getElementById('game-header');
    el.scoringView = document.getElementById('scoring-view');
    el.waitingView = document.getElementById('waiting-view');
    el.connectionStatus = document.getElementById('connection-status');

    // Header
    el.timerDisplay = document.getElementById('timer-display');
    el.headerGreenName = document.getElementById('header-green-name');
    el.headerYellowName = document.getElementById('header-yellow-name');
    el.headerGreenTotal = document.getElementById('header-green-total');
    el.headerYellowTotal = document.getElementById('header-yellow-total');

    // Score values on buttons
    el.greenHitVal = document.getElementById('green-hit-val');
    el.greenSpotVal = document.getElementById('green-spot-val');
    el.greenCatchVal = document.getElementById('green-catch-val');
    el.greenPenaltyVal = document.getElementById('green-penalty-val');
    el.yellowHitVal = document.getElementById('yellow-hit-val');
    el.yellowSpotVal = document.getElementById('yellow-spot-val');
    el.yellowCatchVal = document.getElementById('yellow-catch-val');
    el.yellowPenaltyVal = document.getElementById('yellow-penalty-val');

    // Waiting
    el.waitingMessage = document.getElementById('waiting-message');
}

// ==========================================
// SocketIO Event Handlers
// ==========================================
socket.on('connect', function() {
    updateConnectionStatus(true);
});

socket.on('disconnect', function() {
    updateConnectionStatus(false);
});

socket.on('reconnect', function() {
    updateConnectionStatus(true);
    socket.emit('request_state');
});

socket.on('state_update', function(data) {
    state = data;
    // Apply outdoor/light theme from server state
    if (data.outdoorMode) {
        document.body.setAttribute('data-theme', 'light');
    } else {
        document.body.removeAttribute('data-theme');
    }
    render();
});

socket.on('score_ack', function(data) {
    if (data.success) {
        flashButton(data.action);
    }
});

// ==========================================
// Connection Status
// ==========================================
function updateConnectionStatus(connected) {
    if (!el.connectionStatus) return;
    if (connected) {
        el.connectionStatus.textContent = 'Connected';
        el.connectionStatus.classList.remove('disconnected');
    } else {
        el.connectionStatus.textContent = 'Disconnected';
        el.connectionStatus.classList.add('disconnected');
    }
}

// ==========================================
// Render
// ==========================================
function render() {
    if (!state.gameRunning) return;

    // Scoring is active during Playing, Pause, and Stop (10s grace period)
    var isScoring = state.gameRunning === 'Playing' || state.gameRunning === 'Pause' || state.gameRunning === 'Stop';

    toggleEl(el.gameHeader, isScoring);
    toggleEl(el.scoringView, isScoring);
    toggleEl(el.waitingView, !isScoring);

    if (isScoring) {
        renderHeader();
        renderScoringView();
    } else {
        // Show contextual waiting message
        var messages = {
            'Countdown': 'Countdown in Progress...',
            'Ready': 'Get Ready!',
            'AutoInst': 'Playing Instructions...',
            'No': 'Waiting for game to start...',
            'Finished': 'Game Finished'
        };
        el.waitingMessage.textContent = messages[state.gameRunning] || 'Please Wait...';
    }
}

function renderHeader() {
    // Timer
    var isStopped = state.gameRunning === 'Stop';
    if (isStopped) {
        el.timerDisplay.textContent = 'Final Scores';
    } else {
        var secs = state.secondsLeft || 0;
        var negative = secs < 0;
        var absSecs = Math.abs(secs);
        var min = Math.floor(absSecs / 60);
        var sec = absSecs % 60;
        var timerStr = (negative ? '-' : '') + min + ':' + String(sec).padStart(2, '0');
        el.timerDisplay.textContent = timerStr;
    }

    // Timer styling
    el.timerDisplay.classList.toggle('overtime', !isStopped && (state.secondsLeft || 0) < 0);
    el.timerDisplay.classList.toggle('paused', state.gameRunning === 'Pause');
    el.timerDisplay.classList.toggle('finalizing', isStopped);

    // Scores
    var gs = state.greenScores || {};
    var ys = state.yellowScores || {};
    el.headerGreenTotal.textContent = gs.Total || 0;
    el.headerYellowTotal.textContent = ys.Total || 0;

    // Team names
    var cg = state.currentGame || {};
    el.headerGreenName.textContent = cg.GreenTeamName || 'Green';
    el.headerYellowName.textContent = cg.YellowTeamName || 'Yellow';
}

function renderScoringView() {
    var gs = state.greenScores || {};
    var ys = state.yellowScores || {};
    var gt = state.currentGameType || 'Normal';

    // Update score values on buttons
    if (el.greenHitVal) el.greenHitVal.textContent = gs.Hit || 0;
    if (el.greenSpotVal) el.greenSpotVal.textContent = gs.Spot || 0;
    if (el.greenCatchVal) el.greenCatchVal.textContent = gs.Catch || 0;
    if (el.greenPenaltyVal) el.greenPenaltyVal.textContent = gs.Penalty || 0;
    if (el.yellowHitVal) el.yellowHitVal.textContent = ys.Hit || 0;
    if (el.yellowSpotVal) el.yellowSpotVal.textContent = ys.Spot || 0;
    if (el.yellowCatchVal) el.yellowCatchVal.textContent = ys.Catch || 0;
    if (el.yellowPenaltyVal) el.yellowPenaltyVal.textContent = ys.Penalty || 0;

    // Button visibility based on game type
    var showSpot = gt === 'Elimination';
    var showCatchPenalty = gt === 'Elimination' || gt === 'Sanction' || gt === 'Tournament';

    toggleButtons('.spot-btn', showSpot);
    toggleButtons('.catch-btn', showCatchPenalty);
    toggleButtons('.penalty-btn', showCatchPenalty);
}

// ==========================================
// Helpers
// ==========================================
function toggleEl(element, show) {
    if (!element) return;
    if (show) {
        element.classList.remove('hidden');
    } else {
        element.classList.add('hidden');
    }
}

function toggleButtons(selector, show) {
    var btns = document.querySelectorAll(selector);
    btns.forEach(function(btn) {
        if (show) {
            btn.classList.remove('hidden');
        } else {
            btn.classList.add('hidden');
        }
    });
}

function flashButton(action) {
    var btn = document.querySelector('[data-action="' + action + '"]');
    if (!btn) return;
    btn.classList.remove('flash');
    // Trigger reflow to restart animation
    void btn.offsetWidth;
    btn.classList.add('flash');
    if (navigator.vibrate) {
        navigator.vibrate(30);
    }
}

// ==========================================
// Button Click Handling
// ==========================================
function handleButtonClick(e) {
    var btn = e.currentTarget;
    var action = btn.dataset.action;
    if (!action) return;

    // Debounce
    if (cooldowns[action]) return;
    cooldowns[action] = true;
    btn.classList.add('cooldown');
    setTimeout(function() {
        delete cooldowns[action];
        btn.classList.remove('cooldown');
    }, DEBOUNCE_MS);

    // Send to server
    socket.emit('score_action', { action: action });
}

// ==========================================
// Initialization
// ==========================================
document.addEventListener('DOMContentLoaded', function() {
    cacheElements();

    // Attach click handlers to score buttons (data-action)
    var actionButtons = document.querySelectorAll('[data-action]');
    actionButtons.forEach(function(btn) {
        btn.addEventListener('touchend', function(e) {
            e.preventDefault();
            handleButtonClick(e);
        });
        btn.addEventListener('click', function(e) {
            if (e.sourceCapabilities && e.sourceCapabilities.firesTouchEvents) return;
            handleButtonClick(e);
        });
    });

    // Request full state on load
    socket.emit('request_state');
});
