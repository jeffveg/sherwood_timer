/* ==========================================
   Sherwood Adventure Timer - Spectator Scoreboard
   Display-only client — no controls, no interaction
   ========================================== */

(function () {
    'use strict';

    // ---- Socket.IO connection ----
    const socket = io({ reconnection: true, reconnectionDelay: 1000 });

    // ---- DOM references ----
    const views = {
        playing: document.getElementById('playing-view'),
        finished: document.getElementById('finished-view'),
        idle: document.getElementById('idle-view'),
        transition: document.getElementById('transition-view'),
    };

    const els = {
        // Game type badge
        gameTypeBadge: document.getElementById('game-type-badge'),

        // Timer
        timerDisplay: document.getElementById('timer-display'),

        // Green scores
        greenName: document.getElementById('green-team-name'),
        greenTotal: document.getElementById('green-total'),
        greenHit: document.getElementById('green-hit'),
        greenSpot: document.getElementById('green-spot'),
        greenCatch: document.getElementById('green-catch'),
        greenPenalty: document.getElementById('green-penalty'),
        greenHitRow: document.getElementById('green-hit-row'),
        greenSpotRow: document.getElementById('green-spot-row'),
        greenCatchRow: document.getElementById('green-catch-row'),
        greenPenaltyRow: document.getElementById('green-penalty-row'),

        // Yellow scores
        yellowName: document.getElementById('yellow-team-name'),
        yellowTotal: document.getElementById('yellow-total'),
        yellowHit: document.getElementById('yellow-hit'),
        yellowSpot: document.getElementById('yellow-spot'),
        yellowCatch: document.getElementById('yellow-catch'),
        yellowPenalty: document.getElementById('yellow-penalty'),
        yellowHitRow: document.getElementById('yellow-hit-row'),
        yellowSpotRow: document.getElementById('yellow-spot-row'),
        yellowCatchRow: document.getElementById('yellow-catch-row'),
        yellowPenaltyRow: document.getElementById('yellow-penalty-row'),

        // Playing next game
        playingNextGame: document.getElementById('playing-next-game'),
        playingNextGreen: document.getElementById('playing-next-green'),
        playingNextYellow: document.getElementById('playing-next-yellow'),

        // Finished view
        winnerIcon: document.getElementById('winner-icon'),
        winnerTitle: document.getElementById('winner-title'),
        winnerName: document.getElementById('winner-name'),
        finalScore: document.getElementById('final-score'),
        winnerBreakdown: document.getElementById('winner-breakdown'),
        finishedNextGame: document.getElementById('finished-next-game'),
        finishedNextGreen: document.getElementById('finished-next-green'),
        finishedNextYellow: document.getElementById('finished-next-yellow'),

        // Idle view
        idleNextGreen: document.getElementById('idle-next-green'),
        idleNextYellow: document.getElementById('idle-next-yellow'),
        idleGameType: document.getElementById('idle-game-type'),

        // Transition view
        transitionMessage: document.getElementById('transition-message'),
        transitionGreenName: document.getElementById('transition-green-name'),
        transitionYellowName: document.getElementById('transition-yellow-name'),

        // Connection
        connectionStatus: document.getElementById('connection-status'),
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
        // Apply outdoor/light theme from server state
        if (state.outdoorMode) {
            document.body.setAttribute('data-theme', 'light');
        } else {
            document.body.removeAttribute('data-theme');
        }
        render(state);
    });

    // ---- Helper: format seconds to M:SS or -M:SS ----
    function formatTime(seconds) {
        if (seconds === undefined || seconds === null) return '0:00';
        var negative = seconds < 0;
        var abs = Math.abs(seconds);
        var m = Math.floor(abs / 60);
        var s = abs % 60;
        return (negative ? '-' : '') + m + ':' + (s < 10 ? '0' : '') + s;
    }

    // ---- Helper: calculate total score ----
    function calcTotal(scores) {
        return (scores.Hit || 0) + (scores.Catch || 0) +
               (scores.Spot || 0) - (scores.Penalty || 0) +
               (scores.ExtraPoint || 0);
    }

    // ---- Show one view, hide others ----
    function showView(name) {
        Object.keys(views).forEach(function (key) {
            if (key === name) {
                views[key].classList.remove('hidden');
            } else {
                views[key].classList.add('hidden');
            }
        });
    }

    // ---- Main render function ----
    function render(state) {
        var gameRunning = state.gameRunning;
        var gameType = state.currentGameType || '';
        var isPlaying = (gameRunning === 'Playing' || gameRunning === 'Paused');
        var isFinished = (gameRunning === 'Finished' || gameRunning === 'Stop');
        var isTransition = (gameRunning === 'Countdown' || gameRunning === 'Ready' ||
                            gameRunning === 'Instructions' || gameRunning === 'Instruction');

        // Game type badge
        if (gameType && (isPlaying || isTransition)) {
            els.gameTypeBadge.textContent = gameType;
            els.gameTypeBadge.classList.remove('hidden');
        } else {
            els.gameTypeBadge.classList.add('hidden');
        }

        if (isPlaying) {
            renderPlaying(state);
            showView('playing');
        } else if (isFinished) {
            renderFinished(state);
            showView('finished');
        } else if (isTransition) {
            renderTransition(state);
            showView('transition');
        } else {
            renderIdle(state);
            showView('idle');
        }
    }

    // ---- Render: Playing / Paused ----
    function renderPlaying(state) {
        var seconds = state.secondsLeft;
        var gameType = state.currentGameType || '';
        var green = state.greenScores || {};
        var yellow = state.yellowScores || {};

        // Timer
        els.timerDisplay.textContent = formatTime(seconds);
        els.timerDisplay.classList.toggle('overtime', seconds < 0);
        els.timerDisplay.classList.toggle('paused', state.gameRunning === 'Paused');

        // Team names
        els.greenName.textContent = state.currentGame.GreenTeamName || 'Green';
        els.yellowName.textContent = state.currentGame.YellowTeamName || 'Yellow';

        // Totals
        els.greenTotal.textContent = calcTotal(green);
        els.yellowTotal.textContent = calcTotal(yellow);

        // Score breakdown visibility based on game type
        var showBreakdown = (gameType !== 'Normal');
        var showSpot = (gameType === 'Elimination');

        // Green breakdown
        setBreakdownVisibility('green', showBreakdown, showSpot);
        if (showBreakdown) {
            els.greenHit.textContent = green.Hit || 0;
            els.greenSpot.textContent = green.Spot || 0;
            els.greenCatch.textContent = green.Catch || 0;
            els.greenPenalty.textContent = green.Penalty || 0;
        }

        // Yellow breakdown
        setBreakdownVisibility('yellow', showBreakdown, showSpot);
        if (showBreakdown) {
            els.yellowHit.textContent = yellow.Hit || 0;
            els.yellowSpot.textContent = yellow.Spot || 0;
            els.yellowCatch.textContent = yellow.Catch || 0;
            els.yellowPenalty.textContent = yellow.Penalty || 0;
        }

        // Next game preview
        var next = state.nextGame || {};
        if (next.GreenTeamName || next.YellowTeamName) {
            els.playingNextGreen.textContent = next.GreenTeamName || '---';
            els.playingNextYellow.textContent = next.YellowTeamName || '---';
            els.playingNextGame.classList.remove('hidden');
        } else {
            els.playingNextGame.classList.add('hidden');
        }
    }

    // ---- Helper: show/hide breakdown rows ----
    function setBreakdownVisibility(side, showBreakdown, showSpot) {
        var hitRow = els[side + 'HitRow'];
        var spotRow = els[side + 'SpotRow'];
        var catchRow = els[side + 'CatchRow'];
        var penaltyRow = els[side + 'PenaltyRow'];

        if (showBreakdown) {
            hitRow.classList.remove('hidden');
            catchRow.classList.remove('hidden');
            penaltyRow.classList.remove('hidden');
            if (showSpot) {
                spotRow.classList.remove('hidden');
            } else {
                spotRow.classList.add('hidden');
            }
        } else {
            hitRow.classList.add('hidden');
            spotRow.classList.add('hidden');
            catchRow.classList.add('hidden');
            penaltyRow.classList.add('hidden');
        }
    }

    // ---- Render: Finished / Stop ----
    function renderFinished(state) {
        var green = state.greenScores || {};
        var yellow = state.yellowScores || {};
        var greenTotal = calcTotal(green);
        var yellowTotal = calcTotal(yellow);
        var gameType = state.currentGameType || '';
        var currentGame = state.currentGame || {};
        var gameWinner = currentGame.GameWinner || '';
        var earlyStop = currentGame.GameEarlyStopReason || '';

        var greenName = currentGame.GreenTeamName || 'Green';
        var yellowName = currentGame.YellowTeamName || 'Yellow';

        // Determine winner
        var winnerTeam = '';
        var winnerLabel = '';
        if (gameWinner === 'Green') {
            winnerTeam = 'green';
            winnerLabel = greenName;
        } else if (gameWinner === 'Yellow') {
            winnerTeam = 'yellow';
            winnerLabel = yellowName;
        } else if (greenTotal > yellowTotal) {
            winnerTeam = 'green';
            winnerLabel = greenName;
        } else if (yellowTotal > greenTotal) {
            winnerTeam = 'yellow';
            winnerLabel = yellowName;
        } else {
            winnerTeam = 'draw';
            winnerLabel = 'Draw!';
        }

        // Winner display
        if (winnerTeam === 'draw') {
            els.winnerIcon.textContent = '\u{1F91D}'; // handshake
            els.winnerTitle.textContent = 'Game Over';
        } else {
            els.winnerIcon.textContent = '\u{1F3C6}'; // trophy
            els.winnerTitle.textContent = earlyStop ? 'Early Win!' : 'Winner!';
        }

        els.winnerName.textContent = winnerLabel;
        els.winnerName.className = 'winner-name';
        if (winnerTeam === 'green') els.winnerName.classList.add('green-winner');
        else if (winnerTeam === 'yellow') els.winnerName.classList.add('yellow-winner');
        else els.winnerName.classList.add('draw-result');

        // Final score
        els.finalScore.textContent = greenTotal + ' - ' + yellowTotal;

        // Breakdown for winner
        var breakdownHTML = '';
        if (gameType !== 'Normal') {
            var scores = winnerTeam === 'yellow' ? yellow : green;
            breakdownHTML += '<span class="wb-item">Hit: ' + (scores.Hit || 0) + '</span>';
            if (gameType === 'Elimination') {
                breakdownHTML += '<span class="wb-item">Spot: ' + (scores.Spot || 0) + '</span>';
            }
            breakdownHTML += '<span class="wb-item">Catch: ' + (scores.Catch || 0) + '</span>';
            breakdownHTML += '<span class="wb-item">Penalty: ' + (scores.Penalty || 0) + '</span>';
            if (scores.ExtraPoint) {
                breakdownHTML += '<span class="wb-item">Bonus: ' + scores.ExtraPoint + '</span>';
            }
        }
        els.winnerBreakdown.innerHTML = breakdownHTML;

        // Next game preview
        var next = state.nextGame || {};
        if (next.GreenTeamName || next.YellowTeamName) {
            els.finishedNextGreen.textContent = next.GreenTeamName || '---';
            els.finishedNextYellow.textContent = next.YellowTeamName || '---';
            els.finishedNextGame.classList.remove('hidden');
        } else {
            els.finishedNextGame.classList.add('hidden');
        }
    }

    // ---- Render: Transition (Countdown / Instructions / Ready) ----
    function renderTransition(state) {
        var gameRunning = state.gameRunning;
        var currentGame = state.currentGame || {};

        if (gameRunning === 'Countdown') {
            els.transitionMessage.textContent = 'Count Down in Progress';
        } else if (gameRunning === 'Ready') {
            els.transitionMessage.textContent = 'Get Ready!';
        } else {
            els.transitionMessage.textContent = 'Instructions Playing...';
        }

        els.transitionGreenName.textContent = currentGame.GreenTeamName || 'Green';
        els.transitionYellowName.textContent = currentGame.YellowTeamName || 'Yellow';
    }

    // ---- Render: Idle ----
    function renderIdle(state) {
        var next = state.nextGame || {};
        var gameType = state.currentGameType || '';

        els.idleNextGreen.textContent = next.GreenTeamName || '---';
        els.idleNextYellow.textContent = next.YellowTeamName || '---';

        if (gameType) {
            els.idleGameType.textContent = gameType + ' Mode';
        } else {
            els.idleGameType.textContent = '';
        }
    }

})();
