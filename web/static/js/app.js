/* ==========================================
   Sherwood Adventure Timer - Web Controller
   Socket.IO client + UI logic
   ========================================== */

// Connect to the SocketIO server (same host)
const socket = io();

// Current state from the server
let state = {};

// Debounce tracking
const cooldowns = {};
const DEBOUNCE_MS = 500;

// Confirmation modal state
let pendingConfirmAction = null;

// ==========================================
// DOM Element Cache
// ==========================================
const el = {};

function cacheElements() {
    // Views
    el.gameHeader = document.getElementById('game-header');
    el.scoringView = document.getElementById('scoring-view');
    el.waitingView = document.getElementById('waiting-view');
    el.managementView = document.getElementById('management-view');
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

    // Game control buttons
    el.pauseBtn = document.getElementById('pause-btn');
    el.pauseIcon = document.getElementById('pause-icon');
    el.pauseLabel = document.getElementById('pause-label');

    // Waiting
    el.waitingMessage = document.getElementById('waiting-message');

    // Management
    el.nextGreenName = document.getElementById('next-green-name');
    el.nextYellowName = document.getElementById('next-yellow-name');
    el.gameTypeVal = document.getElementById('game-type-val');
    el.autoInstVal = document.getElementById('auto-inst-val');
    el.apiIntVal = document.getElementById('api-int-val');
    el.musicVal = document.getElementById('music-val');
    el.volVal = document.getElementById('vol-val');

    // Confirmation modal
    el.confirmOverlay = document.getElementById('confirm-overlay');
    el.confirmMessage = document.getElementById('confirm-message');
    el.confirmYes = document.getElementById('confirm-yes');
    el.confirmNo = document.getElementById('confirm-no');
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

    var isPlaying = state.gameRunning === 'Playing' || state.gameRunning === 'Pause';
    var isTransition = ['Countdown', 'Ready', 'AutoInst', 'Stop'].indexOf(state.gameRunning) !== -1;
    var isIdle = state.gameRunning === 'No' || state.gameRunning === 'Finished';

    // Show/hide views
    toggleEl(el.gameHeader, isPlaying || isTransition);
    toggleEl(el.scoringView, isPlaying);
    toggleEl(el.waitingView, isTransition);
    toggleEl(el.managementView, isIdle);

    if (isPlaying) {
        renderScoringView();
    }
    if (isTransition) {
        renderWaitingView();
    }
    if (isIdle) {
        renderManagementView();
    }

    // Always update header when visible
    if (isPlaying || isTransition) {
        renderHeader();
    }
}

function renderHeader() {
    // Timer
    var secs = state.secondsLeft || 0;
    var negative = secs < 0;
    var absSecs = Math.abs(secs);
    var min = Math.floor(absSecs / 60);
    var sec = absSecs % 60;
    var timerStr = (negative ? '-' : '') + min + ':' + String(sec).padStart(2, '0');
    el.timerDisplay.textContent = timerStr;

    // Timer styling
    el.timerDisplay.classList.toggle('overtime', negative);
    el.timerDisplay.classList.toggle('paused', state.gameRunning === 'Pause');

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
    var showCatchPenalty = gt === 'Elimination' || gt === 'Sanction';

    toggleButtons('.spot-btn', showSpot);
    toggleButtons('.catch-btn', showCatchPenalty);
    toggleButtons('.penalty-btn', showCatchPenalty);

    // Update pause button to reflect current state
    if (el.pauseBtn) {
        var isPaused = state.gameRunning === 'Pause';
        el.pauseBtn.classList.toggle('is-paused', isPaused);
        if (el.pauseIcon) el.pauseIcon.innerHTML = isPaused ? '&#9654;' : '&#9208;';
        if (el.pauseLabel) el.pauseLabel.textContent = isPaused ? 'Resume' : 'Pause';
    }
}

function renderWaitingView() {
    var messages = {
        'Countdown': 'Countdown in Progress...',
        'Ready': 'Get Ready!',
        'AutoInst': 'Playing Instructions...',
        'Stop': 'Game Over!'
    };
    el.waitingMessage.textContent = messages[state.gameRunning] || 'Please Wait...';
}

function renderManagementView() {
    var ng = state.nextGame || {};
    el.nextGreenName.textContent = ng.GreenTeamName || '---';
    el.nextYellowName.textContent = ng.YellowTeamName || '---';
    el.gameTypeVal.textContent = state.currentGameType || 'Normal';
    el.autoInstVal.textContent = state.autoInst ? 'ON' : 'OFF';
    el.apiIntVal.textContent = state.apiIntegration ? 'ON' : 'OFF';
    el.musicVal.textContent = state.backgroundMusic ? 'ON' : 'OFF';
    el.volVal.textContent = state.backgroundVol || 0;
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
    if (!btn) btn = document.querySelector('[data-confirm="' + action + '"]');
    if (!btn) return;
    btn.classList.remove('flash');
    // Trigger reflow to restart animation
    void btn.offsetWidth;
    btn.classList.add('flash');
    // Haptic feedback on mobile
    if (navigator.vibrate) {
        navigator.vibrate(30);
    }
}

// ==========================================
// Confirmation Modal
// ==========================================
function showConfirm(action) {
    var messages = {
        'PAUSE': state.gameRunning === 'Pause' ? 'Resume the game?' : 'Pause the game?',
        'STOP': 'Stop the game? This cannot be undone.',
        'START': 'Start the game?'
    };

    pendingConfirmAction = action;
    el.confirmMessage.textContent = messages[action] || 'Are you sure?';

    // Use green color for start, red for others
    el.confirmYes.classList.toggle('confirm-start', action === 'START');
    el.confirmYes.textContent = action === 'STOP' ? 'Stop Game' : 'Yes';

    el.confirmOverlay.classList.remove('hidden');
}

function hideConfirm() {
    el.confirmOverlay.classList.add('hidden');
    pendingConfirmAction = null;
}

function confirmAction() {
    if (pendingConfirmAction) {
        socket.emit('score_action', { action: pendingConfirmAction });
    }
    hideConfirm();
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

function handleConfirmButtonClick(e) {
    var btn = e.currentTarget;
    var action = btn.dataset.confirm;
    if (!action) return;

    // Show confirmation dialog instead of sending directly
    showConfirm(action);
}

// ==========================================
// Initialization
// ==========================================
document.addEventListener('DOMContentLoaded', function() {
    cacheElements();

    // Attach click handlers to regular action buttons (data-action)
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

    // Attach click handlers to confirm buttons (data-confirm) — these show modal first
    var confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(function(btn) {
        btn.addEventListener('touchend', function(e) {
            e.preventDefault();
            handleConfirmButtonClick(e);
        });
        btn.addEventListener('click', function(e) {
            if (e.sourceCapabilities && e.sourceCapabilities.firesTouchEvents) return;
            handleConfirmButtonClick(e);
        });
    });

    // Modal: Yes button
    el.confirmYes.addEventListener('touchend', function(e) {
        e.preventDefault();
        confirmAction();
    });
    el.confirmYes.addEventListener('click', function(e) {
        if (e.sourceCapabilities && e.sourceCapabilities.firesTouchEvents) return;
        confirmAction();
    });

    // Modal: Cancel button
    el.confirmNo.addEventListener('touchend', function(e) {
        e.preventDefault();
        hideConfirm();
    });
    el.confirmNo.addEventListener('click', function(e) {
        if (e.sourceCapabilities && e.sourceCapabilities.firesTouchEvents) return;
        hideConfirm();
    });

    // Modal: Click overlay backdrop to cancel
    el.confirmOverlay.addEventListener('click', function(e) {
        if (e.target === el.confirmOverlay) {
            hideConfirm();
        }
    });

    // Request full state on load
    socket.emit('request_state');
});
