/* ==========================================
   Sherwood Adventure Timer - Game Schedule
   SocketIO client + game picker UI
   ========================================== */

const socket = io();

let allGames = [];
let nextGameNumber = 0;
let currentFilter = 'all';

// ==========================================
// DOM Element Cache
// ==========================================
const el = {};

function cacheElements() {
    el.connectionStatus = document.getElementById('connection-status');
    el.gamesList = document.getElementById('games-list');
    el.filterBar = document.getElementById('filter-bar');
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
    socket.emit('request_games_list');
});

socket.on('state_update', function(data) {
    // Apply outdoor/light theme from server state
    if (data.outdoorMode) {
        document.body.setAttribute('data-theme', 'light');
    } else {
        document.body.removeAttribute('data-theme');
    }
    // Track next game number for highlighting
    if (data.nextGame) {
        nextGameNumber = data.nextGame.GameNumber || 0;
        renderGames();
    }
});

socket.on('games_list', function(data) {
    allGames = data.games || [];
    nextGameNumber = data.nextGameNumber || 0;
    renderGames();
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
// Render Games List
// ==========================================
function renderGames() {
    if (!el.gamesList) return;

    // Filter games
    var filtered = allGames;
    if (currentFilter !== 'all') {
        filtered = allGames.filter(function(g) {
            return g.gameStatus === currentFilter;
        });
    }

    if (filtered.length === 0) {
        el.gamesList.innerHTML = '<div class="no-games-msg">No games found</div>';
        return;
    }

    var html = '';
    var lastGroup = -1;

    for (var i = 0; i < filtered.length; i++) {
        var g = filtered[i];
        var isNext = g.gameNumber === nextGameNumber;
        var isFinished = g.gameStatus === 'Finished';
        var isSkipped = g.gameStatus === 'Skipped';
        var isPlaying = g.gameStatus === 'Playing';
        var isNotStarted = g.gameStatus === 'Not Started';

        // Status CSS class
        var cardClass = 'game-card';
        if (isNext && isNotStarted) cardClass += ' is-next';
        if (isFinished) cardClass += ' status-finished';
        if (isSkipped) cardClass += ' status-skipped';
        if (isPlaying) cardClass += ' status-playing';

        // Only allow clicking on Not Started games
        var clickAttr = isNotStarted ? ' data-game="' + g.gameNumber + '"' : '';

        // Group divider label
        if (g.groupNum > 0 && g.groupNum !== lastGroup) {
            html += '<div class="group-divider">Group ' + g.groupNum + '</div>';
            lastGroup = g.groupNum;
        }

        // Status badge
        var badgeClass = 'game-status-badge ';
        var badgeText = g.gameStatus;
        if (isNext && isNotStarted) {
            badgeClass += 'badge-next';
            badgeText = 'Next';
        } else if (isPlaying) {
            badgeClass += 'badge-playing';
            badgeText = 'Playing';
        } else if (isFinished) {
            badgeClass += 'badge-finished';
        } else if (isSkipped) {
            badgeClass += 'badge-skipped';
        } else {
            badgeClass += 'badge-not-started';
        }

        html += '<div class="' + cardClass + '"' + clickAttr + '>';
        html += '  <div class="game-card-header">';
        html += '    <div class="game-card-meta">';
        if (g.groupNum > 0) {
            html += '      <span class="game-group-badge">G' + g.groupNum + '</span>';
        }
        if (g.roundNum > 0) {
            html += '      <span class="game-round-badge">Round ' + g.roundNum + '</span>';
        }
        html += '    </div>';
        html += '    <span class="' + badgeClass + '">' + badgeText + '</span>';
        html += '  </div>';

        html += '  <div class="game-card-teams">';
        html += '    <div class="game-team game-team-green">';
        html += '      <span class="game-team-name">' + escapeHtml(g.greenTeamName) + '</span>';
        if (isFinished || isPlaying) {
            html += '      <span class="game-team-score">' + g.greenScore + '</span>';
        }
        html += '    </div>';
        html += '    <span class="game-vs">vs</span>';
        html += '    <div class="game-team game-team-yellow">';
        html += '      <span class="game-team-name">' + escapeHtml(g.yellowTeamName) + '</span>';
        if (isFinished || isPlaying) {
            html += '      <span class="game-team-score">' + g.yellowScore + '</span>';
        }
        html += '    </div>';
        html += '  </div>';

        if (isFinished && g.gameWinner) {
            html += '  <div class="game-winner">' + escapeHtml(g.gameWinner) + ' wins</div>';
        }

        html += '  <div class="game-type-badge">' + g.gameType + '</div>';
        html += '</div>';
    }

    el.gamesList.innerHTML = html;

    // Attach click handlers to game cards
    var cards = el.gamesList.querySelectorAll('[data-game]');
    cards.forEach(function(card) {
        card.addEventListener('click', function() {
            var gameNum = parseInt(card.dataset.game, 10);
            if (gameNum > 0 && gameNum !== nextGameNumber) {
                socket.emit('set_next_game', { game_number: gameNum });
            }
        });
    });
}

// ==========================================
// Helpers
// ==========================================
function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==========================================
// Filter Handling
// ==========================================
function handleFilterClick(e) {
    var btn = e.target;
    if (!btn.classList.contains('filter-btn')) return;

    // Update active state
    var btns = el.filterBar.querySelectorAll('.filter-btn');
    btns.forEach(function(b) { b.classList.remove('active'); });
    btn.classList.add('active');

    currentFilter = btn.dataset.filter;
    renderGames();
}

// ==========================================
// Initialization
// ==========================================
document.addEventListener('DOMContentLoaded', function() {
    cacheElements();

    // Filter bar click delegation
    el.filterBar.addEventListener('click', handleFilterClick);

    // Request data on load
    socket.emit('request_games_list');
    socket.emit('request_state');
});
