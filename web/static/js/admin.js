/* ==========================================
   Sherwood Adventure Timer - Admin Settings
   ========================================== */

(function () {
    'use strict';

    // ---- Socket.IO connection ----
    var socket = io({ reconnection: true, reconnectionDelay: 1000 });

    // ---- DOM references ----
    var els = {
        scoreHit:        document.getElementById('val-scoreHit'),
        scoreCatch:      document.getElementById('val-scoreCatch'),
        scoreSpot:       document.getElementById('val-scoreSpot'),
        scorePenalty:    document.getElementById('val-scorePenalty'),
        scoreExtra:      document.getElementById('val-scoreExtra'),
        songListSelect:  document.getElementById('songlist-select'),
        defaultRunTime:  document.getElementById('val-defaultRunTime'),
        sanctionRunTime: document.getElementById('val-sanctionRunTime'),
        gameType:        document.getElementById('info-gameType'),
        gameState:       document.getElementById('info-gameState'),
        connectionStatus: document.getElementById('connection-status'),
    };

    // Current values (for stepper logic)
    var currentValues = {
        scoreHit: 1,
        scoreCatch: 2,
        scoreSpot: 1,
        scorePenalty: -1,
        scoreExtra: 1,
        defaultRunTime: 5,
        sanctionRunTime: 8,
    };

    // ---- Connection status ----
    socket.on('connect', function () {
        els.connectionStatus.textContent = 'Connected';
        els.connectionStatus.classList.remove('disconnected');
    });

    socket.on('disconnect', function () {
        els.connectionStatus.textContent = 'Disconnected';
        els.connectionStatus.classList.add('disconnected');
    });

    // ---- State update handler ----
    socket.on('state_update', function (state) {
        updateDisplay(state);
    });

    // ---- Ack handler ----
    socket.on('admin_ack', function (data) {
        if (data.success) {
            // Flash the value element green
            var el = els[data.setting];
            if (el) {
                el.classList.remove('flash-success');
                void el.offsetWidth; // Force reflow to restart animation
                el.classList.add('flash-success');
            }
        }
    });

    // ---- Theme toggle ----
    var themeSwitch = document.getElementById('theme-switch');

    function applyTheme(outdoor) {
        if (outdoor) {
            document.body.setAttribute('data-theme', 'light');
        } else {
            document.body.removeAttribute('data-theme');
        }
        if (themeSwitch) {
            themeSwitch.checked = outdoor;
        }
    }

    if (themeSwitch) {
        themeSwitch.addEventListener('change', function () {
            var isOutdoor = themeSwitch.checked;
            applyTheme(isOutdoor);
            socket.emit('admin_update', { setting: 'outdoorMode', value: isOutdoor });
        });
    }

    // ---- Update display from state ----
    function updateDisplay(state) {
        // Score values
        if (state.scoreValues) {
            var sv = state.scoreValues;
            currentValues.scoreHit = sv.Hit || 0;
            currentValues.scoreCatch = sv.Catch || 0;
            currentValues.scoreSpot = sv.Spot || 0;
            currentValues.scorePenalty = sv.Penalty || 0;
            currentValues.scoreExtra = sv.ExtraPoint || 0;

            els.scoreHit.textContent = currentValues.scoreHit;
            els.scoreCatch.textContent = currentValues.scoreCatch;
            els.scoreSpot.textContent = currentValues.scoreSpot;
            els.scorePenalty.textContent = currentValues.scorePenalty;
            els.scoreExtra.textContent = currentValues.scoreExtra;
        }

        // Song list dropdown
        if (state.songListOptions) {
            var currentSongDir = (state.songList || '').replace('SongList/', '');
            var select = els.songListSelect;
            // Only rebuild options if they changed
            var optionValues = [];
            for (var i = 0; i < select.options.length; i++) {
                optionValues.push(select.options[i].value);
            }
            var newOptions = state.songListOptions;
            if (optionValues.join(',') !== newOptions.join(',')) {
                select.innerHTML = '';
                for (var j = 0; j < newOptions.length; j++) {
                    var opt = document.createElement('option');
                    opt.value = newOptions[j];
                    opt.textContent = newOptions[j];
                    select.appendChild(opt);
                }
            }
            select.value = currentSongDir;
        }

        // Timer values
        if (state.defaultGameRunTime !== undefined) {
            currentValues.defaultRunTime = state.defaultGameRunTime;
            els.defaultRunTime.textContent = currentValues.defaultRunTime;
        }
        if (state.sanctionGameRunTime !== undefined) {
            currentValues.sanctionRunTime = state.sanctionGameRunTime;
            els.sanctionRunTime.textContent = currentValues.sanctionRunTime;
        }

        // Info
        els.gameType.textContent = state.currentGameType || '---';
        els.gameState.textContent = state.gameRunning || '---';

        // Theme
        applyTheme(!!state.outdoorMode);
    }

    // ---- Stepper button handling ----
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.step-btn');
        if (!btn) return;

        var setting = btn.getAttribute('data-setting');
        var dir = btn.getAttribute('data-dir');
        if (!setting || !dir) return;

        var current = currentValues[setting];
        if (current === undefined) return;

        var newVal;
        if (dir === 'up') {
            newVal = current + 1;
        } else {
            newVal = current - 1;
        }

        // Timer values must be positive integers
        if ((setting === 'defaultRunTime' || setting === 'sanctionRunTime') && newVal < 1) {
            return; // Don't allow zero or negative
        }

        // Optimistically update display
        currentValues[setting] = newVal;
        els[setting].textContent = newVal;

        // Send to server
        socket.emit('admin_update', { setting: setting, value: newVal });
    });

    // ---- Song list dropdown handling ----
    els.songListSelect.addEventListener('change', function () {
        var value = els.songListSelect.value;
        socket.emit('admin_update', { setting: 'songList', value: value });
    });

    // ---- Collapsible score values section ----
    var scoreToggle = document.getElementById('score-values-toggle');
    var scoreBody = document.getElementById('score-values-body');

    if (scoreToggle && scoreBody) {
        scoreToggle.addEventListener('click', function () {
            var arrow = scoreToggle.querySelector('.toggle-arrow');
            scoreBody.classList.toggle('hidden');
            if (arrow) {
                arrow.classList.toggle('expanded');
            }
        });
    }

})();
