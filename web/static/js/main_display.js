/* ==========================================
   Sherwood Adventure Timer - Main Display
   Full-screen web version of the pygame scoreboard.
   Mirrors the pygame display including scoreboard views
   and video playback.  Click page once to enable audio.
   ========================================== */

(function () {
    'use strict';

    var socket = io({ reconnection: true, reconnectionDelay: 1000 });

    // ---- DOM references ----
    var container = document.getElementById('main-display');

    var views = {
        playing:    document.getElementById('playing-view'),
        idle:       document.getElementById('idle-view'),
        transition: document.getElementById('transition-view')
    };

    var els = {
        // Timer
        timer: document.getElementById('timer-display'),

        // Green scores
        greenName:       document.getElementById('green-name'),
        greenHit:        document.getElementById('green-hit'),
        greenSpot:       document.getElementById('green-spot'),
        greenCatch:      document.getElementById('green-catch'),
        greenTotal:      document.getElementById('green-total'),
        greenPenalty:    document.getElementById('green-penalty'),
        greenHitRow:     document.getElementById('green-hit-row'),
        greenSpotRow:    document.getElementById('green-spot-row'),
        greenCatchRow:   document.getElementById('green-catch-row'),
        greenPenaltyRow: document.getElementById('green-penalty-row'),
        greenSide:       document.getElementById('green-side'),

        // Yellow scores
        yellowName:       document.getElementById('yellow-name'),
        yellowHit:        document.getElementById('yellow-hit'),
        yellowSpot:       document.getElementById('yellow-spot'),
        yellowCatch:      document.getElementById('yellow-catch'),
        yellowTotal:      document.getElementById('yellow-total'),
        yellowPenalty:    document.getElementById('yellow-penalty'),
        yellowHitRow:     document.getElementById('yellow-hit-row'),
        yellowSpotRow:    document.getElementById('yellow-spot-row'),
        yellowCatchRow:   document.getElementById('yellow-catch-row'),
        yellowPenaltyRow: document.getElementById('yellow-penalty-row'),
        yellowSide:       document.getElementById('yellow-side'),

        // Idle view
        winnerSection:    document.getElementById('winner-section'),
        winnerLabel:      document.getElementById('winner-label'),
        winnerName:       document.getElementById('winner-name'),
        winnerScore:      document.getElementById('winner-score'),
        winnerBreakdown:  document.getElementById('winner-breakdown'),
        nextGameSection:  document.getElementById('next-game-section'),
        nextGreenName:    document.getElementById('next-green-name'),
        nextYellowName:   document.getElementById('next-yellow-name'),

        // Transition view
        transitionGreen:   document.getElementById('transition-green'),
        transitionYellow:  document.getElementById('transition-yellow'),
        transitionMessage: document.getElementById('transition-message'),

        // Song info
        songInfo:    document.getElementById('song-info'),
        songTitle:   document.getElementById('song-title'),
        songArtist:  document.getElementById('song-artist'),

        // Video overlay
        videoOverlay: document.getElementById('video-overlay'),
        unmuteHint:   document.getElementById('unmute-hint'),

        // Status bar
        statusGameType:  document.getElementById('status-game-type'),
        statusAutoInst:  document.getElementById('status-auto-inst'),
        statusTournament: document.getElementById('status-tournament')
    };

    // ---- Video state ----
    var videoPlaying = false;
    var lastState = null;  // cached so we can re-render after video ends

    // ---- Socket events ----
    socket.on('state_update', function (state) {
        lastState = state;
        render(state);
    });

    socket.on('connect', function () {
        socket.emit('request_state');
    });

    socket.on('video_start', function (data) {
        var video = els.videoOverlay;
        video.src = '/video/' + data.file;
        video.classList.remove('hidden');
        videoPlaying = true;
        video.play().catch(function (e) {
            console.warn('Video autoplay blocked:', e);
        });
    });

    socket.on('video_stop', function () {
        stopVideo();
    });

    // Handle natural video end (web video finishes before server sends stop)
    els.videoOverlay.addEventListener('ended', function () {
        stopVideo();
    });

    function stopVideo() {
        var video = els.videoOverlay;
        video.pause();
        video.removeAttribute('src');
        video.load();
        video.classList.add('hidden');
        videoPlaying = false;
        // Re-render with last known state so the display updates immediately
        if (lastState) render(lastState);
    }

    // Unmute on first user interaction
    document.addEventListener('click', function unmute() {
        els.videoOverlay.muted = false;
        if (els.unmuteHint) els.unmuteHint.classList.add('hidden');
        document.removeEventListener('click', unmute);
    });

    // ---- Helpers ----
    function formatTime(seconds) {
        if (seconds === undefined || seconds === null) return '0:00';
        var negative = seconds < 0;
        var abs = Math.abs(seconds);
        var m = Math.floor(abs / 60);
        var s = abs % 60;
        return (negative ? '-' : '') + m + ':' + (s < 10 ? '0' : '') + s;
    }

    function showView(name) {
        Object.keys(views).forEach(function (key) {
            if (key === name) {
                views[key].classList.remove('hidden');
            } else {
                views[key].classList.add('hidden');
            }
        });
    }

    function setBackground(bg) {
        container.setAttribute('data-bg', bg);
    }

    function toggleFlashText(on) {
        // Toggle flash-text class on all score text elements for the odd-second flash
        var flashEls = document.querySelectorAll(
            '.team-header, .score-detail, .total-label, .total-value, #song-title, #song-artist'
        );
        flashEls.forEach(function (el) {
            if (on) {
                el.classList.add('flash-text');
            } else {
                el.classList.remove('flash-text');
            }
        });
    }

    // ---- Main render ----
    function render(state) {
        var gameRunning = state.gameRunning;
        if (!gameRunning) return;

        // Skip view updates while a video overlay is active — it covers
        // everything anyway, and we want to avoid background flashes.
        if (videoPlaying) return;

        var isPlaying = (gameRunning === 'Playing' || gameRunning === 'Pause' || gameRunning === 'Stop');
        var isTransition = (gameRunning === 'Countdown' || gameRunning === 'Ready' || gameRunning === 'AutoInst');
        var isIdle = (gameRunning === 'No' || gameRunning === 'Finished');

        // Song info + status bar — always visible regardless of view
        renderSongInfo(state);
        renderStatusBar(state);

        if (isPlaying) {
            renderPlaying(state);
            showView('playing');
        } else if (isTransition) {
            renderTransition(state);
            setBackground('default');
            showView('transition');
        } else {
            renderIdle(state);
            setBackground('default');
            showView('idle');
        }
    }

    // ---- Render: Playing / Pause / Stop ----
    function renderPlaying(state) {
        var seconds = state.secondsLeft || 0;
        var gameType = state.currentGameType || 'Normal';
        var gameRunning = state.gameRunning;
        var green = state.greenScores || {};
        var yellow = state.yellowScores || {};
        var currentGame = state.currentGame || {};

        // Determine background and text flash
        var isOddSecond = (seconds >= 1 && seconds <= 30 && seconds % 2 === 1);
        var isStopped = (gameRunning === 'Stop');
        var isPaused = (gameRunning === 'Pause');
        var isOvertime = (seconds < 0);

        if (isStopped) {
            setBackground('timer');
            toggleFlashText(false);
        } else if (isOddSecond && !isPaused) {
            setBackground('timer-flash');
            toggleFlashText(true);
        } else {
            setBackground('timer');
            toggleFlashText(false);
        }

        // Timer display
        els.timer.classList.remove('overtime', 'paused', 'flash-text', 'finalizing');
        if (isStopped) {
            els.timer.textContent = 'Final Scores';
            els.timer.classList.add('finalizing');
        } else if (isOddSecond && !isPaused) {
            els.timer.textContent = formatTime(seconds);
            els.timer.classList.add('flash-text');
        } else {
            els.timer.textContent = formatTime(seconds);
            if (isOvertime) {
                els.timer.classList.add('overtime');
            }
            if (isPaused) {
                els.timer.classList.add('paused');
            }
        }

        // Team names
        els.greenName.textContent = currentGame.GreenTeamName || 'Green';
        els.yellowName.textContent = currentGame.YellowTeamName || 'Yellow';

        // Totals
        els.greenTotal.textContent = green.Total || 0;
        els.yellowTotal.textContent = yellow.Total || 0;

        // Score breakdown visibility
        var isNormal = (gameType === 'Normal');
        var showSpot = (gameType === 'Elimination');
        var showBreakdown = !isNormal;

        els.greenSide.classList.toggle('normal-mode', isNormal);
        els.yellowSide.classList.toggle('normal-mode', isNormal);

        setRowVisibility(els.greenHitRow, showBreakdown);
        setRowVisibility(els.greenSpotRow, showSpot);
        setRowVisibility(els.greenCatchRow, showBreakdown);
        setRowVisibility(els.greenPenaltyRow, showBreakdown);

        setRowVisibility(els.yellowHitRow, showBreakdown);
        setRowVisibility(els.yellowSpotRow, showSpot);
        setRowVisibility(els.yellowCatchRow, showBreakdown);
        setRowVisibility(els.yellowPenaltyRow, showBreakdown);

        // Score values
        if (showBreakdown) {
            els.greenHit.textContent = green.Hit || 0;
            els.greenSpot.textContent = green.Spot || 0;
            els.greenCatch.textContent = green.Catch || 0;
            els.greenPenalty.textContent = green.Penalty || 0;

            els.yellowHit.textContent = yellow.Hit || 0;
            els.yellowSpot.textContent = yellow.Spot || 0;
            els.yellowCatch.textContent = yellow.Catch || 0;
            els.yellowPenalty.textContent = yellow.Penalty || 0;
        }
    }

    function setRowVisibility(el, show) {
        if (show) {
            el.classList.remove('hidden');
        } else {
            el.classList.add('hidden');
        }
    }

    // ---- Render: Idle / Finished ----
    function renderIdle(state) {
        var currentGame = state.currentGame || {};
        var gameRunning = state.gameRunning;
        var gameType = state.currentGameType || '';
        var green = state.greenScores || {};
        var yellow = state.yellowScores || {};
        var nextGame = state.nextGame || {};

        // Winner section — only if game just finished
        if (gameRunning === 'Finished' && currentGame.GameStatus === 'Finished') {
            var winner = currentGame.GameWinner || '';
            var greenTotal = green.Total || 0;
            var yellowTotal = yellow.Total || 0;

            els.winnerLabel.textContent = 'Winner:';

            if (winner === 'Yellow') {
                els.winnerName.textContent = currentGame.YellowTeamName || 'Yellow';
                els.winnerScore.textContent = 'Total ' + yellowTotal + ' to ' + greenTotal;
            } else {
                els.winnerName.textContent = currentGame.GreenTeamName || 'Green';
                els.winnerScore.textContent = 'Total ' + greenTotal + ' to ' + yellowTotal;
            }

            // Score breakdown for winner
            var scores = (winner === 'Yellow') ? yellow : green;
            var breakdown = '';
            if (gameType !== 'Normal') {
                breakdown += (scores.Hit || 0) + ' Hits - ';
                if (gameType === 'Elimination') {
                    breakdown += (scores.Spot || 0) + ' Spots - ';
                }
                breakdown += (scores.Catch || 0) + ' Catches - ';
                breakdown += (scores.Penalty || 0) + ' Penalties';
                if (scores.ExtraPoint) {
                    breakdown += ' - ' + scores.ExtraPoint + ' Extra Point';
                }
            }
            els.winnerBreakdown.textContent = breakdown;

            els.winnerSection.classList.remove('hidden');
        } else {
            els.winnerSection.classList.add('hidden');
        }

        // Next game preview
        var hasNext = nextGame.GameNumber >= 0 &&
            nextGame.GreenTeamName && nextGame.GreenTeamName !== 'Green' &&
            nextGame.YellowTeamName && nextGame.YellowTeamName !== 'Yellow';

        if (hasNext) {
            els.nextGreenName.textContent = nextGame.GreenTeamName;
            els.nextYellowName.textContent = nextGame.YellowTeamName;
            els.nextGameSection.classList.remove('hidden');
        } else {
            els.nextGameSection.classList.add('hidden');
        }
    }

    // ---- Render: Transition ----
    function renderTransition(state) {
        var gameRunning = state.gameRunning;
        var currentGame = state.currentGame || {};

        if (gameRunning === 'Countdown') {
            els.transitionMessage.textContent = 'Count Down in Progress';
        } else if (gameRunning === 'Ready') {
            els.transitionMessage.textContent = 'Get Ready!';
        } else if (gameRunning === 'AutoInst') {
            els.transitionMessage.textContent = 'Instructions Playing...';
        } else {
            els.transitionMessage.textContent = 'Please Wait...';
        }

        els.transitionGreen.textContent = currentGame.GreenTeamName || 'Green';
        els.transitionYellow.textContent = currentGame.YellowTeamName || 'Yellow';
    }

    // ---- Render: Song info (overlays any view) ----
    function renderSongInfo(state) {
        if (state.musicPlaying && state.songTitle) {
            els.songTitle.textContent = 'Song: ' + state.songTitle;
            els.songArtist.textContent = 'By: ' + state.songArtist;
            els.songInfo.classList.remove('hidden');
        } else {
            els.songInfo.classList.add('hidden');
        }
    }

    // ---- Render: Status bar ----
    function renderStatusBar(state) {
        var gameType = state.currentGameType || '';
        els.statusGameType.textContent = gameType;

        if (state.autoInst) {
            els.statusAutoInst.classList.remove('hidden');
        } else {
            els.statusAutoInst.classList.add('hidden');
        }

        if (state.apiIntegration) {
            els.statusTournament.classList.remove('hidden');
            els.statusTournament.textContent = 'Tournament Integration';
        } else {
            els.statusTournament.classList.add('hidden');
        }
    }

    // Set initial background
    setBackground('default');

})();
