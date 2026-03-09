#!/usr/bin/env python

import requests
import sqlite3
import threading
from os.path import join
from time import sleep
import os
import logging

logger = logging.getLogger('sherwood')

path = join("SherwoodTimer", os.getcwd())
database = join(path, 'stdata.db')

API_BASE = "https://app.sherwoodadventure.com/api/scoring.php"
SMS_API_BASE = "https://app.sherwoodadventure.com/api/sms-notify.php"
API_KEY = "jawvoj-nikwyV-4zawfu"

# Set when operator picks a tournament from the list
selected_tournament_number = None
selected_tournament_name = None
game_type_override = None

# Track which tournaments have already had their first sync processed
_first_sync_done = {}

# Queue of game numbers whose final scores still need uploading
_pending_uploads = []
_pending_lock = threading.Lock()

# DB migration flag — ensure BracketType / MatchNum columns exist
_db_migrated = False


# SQL fragment for bracket ordering: round_robin first, then winners, losers, grand_final
BRACKET_ORDER_SQL = (
    "CASE BracketType"
    " WHEN 'round_robin' THEN 0"
    " WHEN 'winners' THEN 1"
    " WHEN 'losers' THEN 2"
    " WHEN 'grand_final' THEN 3"
    " ELSE 0 END"
)

# Full sort order used everywhere
GAME_SORT_SQL = BRACKET_ORDER_SQL + ", GroupNum ASC, RoundNum ASC, MatchNum ASC, GameNumber ASC"

# Track the latest live scores that need pushing (set by ChangeScore, consumed by sync thread)
_live_score_dirty = False
_live_score_data = {}  # {"game_number": int, "green": int, "yellow": int}
_live_lock = threading.Lock()


def _ensure_db_columns():
    """Add BracketType and MatchNum columns if they don't exist yet."""
    global _db_migrated
    if _db_migrated:
        return
    conn = None
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        # Check existing columns
        cur.execute("PRAGMA table_info(Games);")
        columns = [row[1] for row in cur.fetchall()]
        if "BracketType" not in columns:
            cur.execute("ALTER TABLE Games ADD COLUMN BracketType TEXT DEFAULT 'round_robin';")
            conn.commit()
            logger.info("DB migration: Added BracketType column")
        if "MatchNum" not in columns:
            cur.execute("ALTER TABLE Games ADD COLUMN MatchNum INT DEFAULT 0;")
            conn.commit()
            logger.info("DB migration: Added MatchNum column")
        _db_migrated = True
    except Exception as error:
        logger.error("DB migration error: %s", error)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _api_get(action, **params):
    params["action"] = action
    params["api_key"] = API_KEY
    try:
        r = requests.get(API_BASE, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error("API GET %s error: %s", action, e)
        return {"success": False, "error": str(e)}


def _api_post(action, data):
    try:
        r = requests.post(
            API_BASE,
            params={"action": action, "api_key": API_KEY},
            json=data,
            timeout=10
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error("API POST %s error: %s", action, e)
        return {"success": False, "error": str(e)}


def ListTournaments():
    result = _api_get("list_tournaments")
    if result.get("success"):
        return result.get("tournaments", [])
    else:
        logger.error("ListTournaments failed: %s", result.get("error"))
        return []


def GetOrUpdateGames():
    if not selected_tournament_number:
        logger.error("No tournament selected")
        return 0

    _ensure_db_columns()

    result = _api_get("get_tournament", tournament_number=selected_tournament_number)
    if not result.get("success"):
        logger.error("GetOrUpdateGames API error: %s", result.get("error"))
        return 0

    conn = None
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()

        tournament = result.get("tournament", {})
        matches = result.get("matches", [])
        last_game_type = "Normal"

        for m in matches:
            # Skip matches without both teams assigned
            if not m.get("team1_name") or not m.get("team2_name"):
                continue

            AltGameNum = m.get("match_id")
            GroupNum = m.get("group_id") or 0
            RoundNum = m.get("round") or 0
            MatchNum = m.get("match_number") or 0
            BracketType = m.get("bracket_type") or "round_robin"
            # API mapping: team1 = Green, team2 = Yellow
            GTeamName = m.get("team1_name", "Green")
            GTeamNum = m.get("team1_id") or 0
            YTeamName = m.get("team2_name", "Yellow")
            YTeamNum = m.get("team2_id") or 0
            GameType = m.get("game_type", "Normal")
            ScheduledStartTime = m.get("scheduled_time") or ""
            ApiStatus = m.get("status", "pending")        # pending/in_progress/completed/bye
            last_game_type = GameType

            try:
                cur.execute(
                    "INSERT INTO Games(AltGameNum, AltTournmentNum, AltTournmentSystem,"
                    " GroupNum, RoundNum, MatchNum, BracketType,"
                    " GreenTeamName, AltGreenTeamNum,"
                    " YellowTeamName, AltYellowTeamNum, GameType, ScheduledStartTime)"
                    " VALUES(?, ?, 'Sherwood', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                    " ON CONFLICT(AltGameNum) DO UPDATE SET"
                    " GreenTeamName = excluded.GreenTeamName,"
                    " YellowTeamName = excluded.YellowTeamName,"
                    " GameType = excluded.GameType,"
                    " BracketType = excluded.BracketType,"
                    " MatchNum = excluded.MatchNum;",
                    (str(AltGameNum), selected_tournament_number,
                     GroupNum, RoundNum, MatchNum, BracketType,
                     GTeamName, GTeamNum,
                     YTeamName, YTeamNum, GameType, ScheduledStartTime)
                )
                conn.commit()
            except Exception as error:
                logger.error("Database Error: Could not save/update game - %s", error)

            # Handle forfeits / completed-on-server: if the API says a match is
            # completed or a bye but we still have it as 'Not Started', skip it
            if ApiStatus in ("completed", "bye"):
                try:
                    cur.execute(
                        "UPDATE Games SET GameStatus = 'Skipped'"
                        " WHERE AltGameNum = ? AND GameStatus = 'Not Started';",
                        (str(AltGameNum),)
                    )
                    if cur.rowcount > 0:
                        conn.commit()
                        logger.info("Sync: Skipped game (AltGameNum %s) — API status '%s'", AltGameNum, ApiStatus)
                except Exception as error:
                    logger.error("Database Error: Could not skip forfeited game - %s", error)

        # Skip default-named games on first sync for Tournament type
        if last_game_type == "Tournament" and selected_tournament_number not in _first_sync_done:
            _first_sync_done[selected_tournament_number] = True
            try:
                cur.execute(
                    "SELECT GameNumber, GreenTeamName, YellowTeamName FROM Games"
                    " WHERE GameStatus = 'Not Started' AND AltTournmentNum = ?"
                    " ORDER BY " + GAME_SORT_SQL + ";",
                    (selected_tournament_number,)
                )
                rows = cur.fetchall()
                for row in rows:
                    gNum, gName, yName = row[0], row[1], row[2]
                    if gName == "Green" or yName == "Yellow":
                        cur.execute("UPDATE Games SET GameStatus = 'Skipped' WHERE GameNumber = ?;", (gNum,))
                        conn.commit()
                        logger.info("Tournament: Skipped default game #%s (%s vs %s)", gNum, gName, yName)
                    else:
                        break

            except Exception as error:
                logger.error("Database Error: Could not skip default games - %s", error)

        return 1
    except Exception as error:
        logger.error("GetOrUpdateGames error: %s", error)
        return 0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def MarkLiveScoreDirty(gameNum, greenScore, yellowScore):
    """Flag that live scores need pushing. Called from ChangeScore in run.py."""
    global _live_score_dirty, _live_score_data
    with _live_lock:
        _live_score_dirty = True
        _live_score_data = {"game_number": gameNum, "green": greenScore, "yellow": yellowScore}


def _push_live_scores():
    """Push the latest live scores if dirty. Returns True on success or nothing to do."""
    global _live_score_dirty
    with _live_lock:
        if not _live_score_dirty:
            return True
        data = dict(_live_score_data)

    conn = None
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute("SELECT AltGameNum FROM Games WHERE GameNumber = ?;", (data["game_number"],))
        row = cur.fetchone()
        if row is None:
            return True  # nothing to push

        match_id = row[0]
        result = _api_post("update_score", {
            "match_id": int(match_id),
            "team1_score": data["green"],     # team1 = Green
            "team2_score": data["yellow"]     # team2 = Yellow
        })

        if result.get("success"):
            with _live_lock:
                _live_score_dirty = False
            return True
        else:
            logger.error("_push_live_scores API error: %s", result.get("error"))
            return False
    except Exception as error:
        logger.error("_push_live_scores error: %s", error)
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def QueueUpload(gameNum):
    """Add a game to the pending uploads queue for retry."""
    with _pending_lock:
        if gameNum not in _pending_uploads:
            _pending_uploads.append(gameNum)
            logger.info("Queued game #%s for upload retry", gameNum)


def RetryPendingUploads():
    """Attempt to upload scores for any games in the pending queue. Returns count remaining."""
    with _pending_lock:
        pending = list(_pending_uploads)

    if not pending:
        return 0

    still_pending = []
    for gameNum in pending:
        result = UploadScores(gameNum)
        if result == 1:
            logger.info("Retry upload succeeded for game #%s", gameNum)
        else:
            still_pending.append(gameNum)

    with _pending_lock:
        # Remove successfully uploaded, keep failures + any newly added
        for gameNum in pending:
            if gameNum not in still_pending and gameNum in _pending_uploads:
                _pending_uploads.remove(gameNum)

    return len(still_pending)


def StartMatch(GameNum):
    conn = None
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute("SELECT AltGameNum FROM Games WHERE GameNumber = ?;", (GameNum,))
        row = cur.fetchone()
        if row is None:
            logger.error("StartMatch: No game found for GameNumber %s", GameNum)
            return 0

        match_id = row[0]
        result = _api_post("start_match", {"match_id": int(match_id)})

        if result.get("success"):
            return 1
        else:
            logger.error("StartMatch API error: %s", result.get("error"))
            return 0
    except Exception as error:
        logger.error("StartMatch error: %s", error)
        return 0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def EndMatch(GameNum):
    conn = None
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute("SELECT AltGameNum FROM Games WHERE GameNumber = ?;", (GameNum,))
        row = cur.fetchone()
        if row is None:
            logger.error("EndMatch: No game found for GameNumber %s", GameNum)
            return 0

        match_id = row[0]
        result = _api_post("end_match", {"match_id": int(match_id)})

        if result.get("success"):
            return 1
        else:
            logger.error("EndMatch API error: %s", result.get("error"))
            return 0
    except Exception as error:
        logger.error("EndMatch error: %s", error)
        return 0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def UploadScores(GameNum):
    conn = None
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute(
            "SELECT AltGameNum, AltYellowTeamNum, YellowTotalScore,"
            " AltGreenTeamNum, GreenTotalScore, GameStatus, GameWinner"
            " FROM Games WHERE GameNumber = ?;",
            (GameNum,)
        )
        row = cur.fetchone()
        if row is None:
            logger.error("UploadScores: No game found for GameNumber %s", GameNum)
            return 0

        match_id = row[0]
        yellow_team_id = row[1]    # team2 in API
        yellow_score = row[2]      # team2_score
        green_team_id = row[3]     # team1 in API
        green_score = row[4]       # team1_score
        game_status = row[5]
        game_winner = row[6]

        if game_status == "Finished":
            if game_winner == "Yellow":
                winner_id = yellow_team_id
            else:
                winner_id = green_team_id

            result = _api_post("submit_score", {
                "match_id": int(match_id),
                "team1_score": green_score,    # team1 = Green
                "team2_score": yellow_score,   # team2 = Yellow
                "winner_id": int(winner_id)
            })

            if not result.get("success"):
                logger.error("UploadScores API error: %s", result.get("error"))
                return 0
        return 1
    except Exception as error:
        logger.error("UploadScores error: %s", error)
        return 0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


# ============================================================
# SMS Notification Functions
# Called by run.py after games end to notify team captains via
# the PHP sms-notify.php endpoint, which sends texts via QUO API.
# ============================================================

def _sms_api_post(action, data):
    """POST to the SMS notification endpoint (sms-notify.php)."""
    try:
        r = requests.post(
            SMS_API_BASE,
            params={"action": action, "api_key": API_KEY},
            json=data,
            timeout=10
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error("SMS API POST %s error: %s", action, e)
        return {"success": False, "error": str(e)}


def NotifyUpcoming(match_id, games_away=2):
    """
    Notify team captains about an upcoming match.
    Called after a game ends — the timer looks ahead in the queue
    and notifies teams that are N games out.

    Args:
        match_id:   The AltGameNum (PHP match ID) of the upcoming match
        games_away: 1 = "on deck / next up", 2+ = "~N games away"
    """
    if not selected_tournament_number:
        return

    result = _sms_api_post("notify_upcoming", {
        "match_id": int(match_id),
        "games_away": int(games_away),
    })

    if result.get("success"):
        sent = result.get("sent", 0)
        skipped = result.get("skipped", 0)
        if sent > 0:
            logger.info("SMS notify_upcoming: sent=%d skipped=%d match_id=%s games_away=%d",
                        sent, skipped, match_id, games_away)
    else:
        logger.error("SMS notify_upcoming error: %s", result.get("error"))


def NotifyScore(match_id):
    """
    Notify opted-in captains about a completed match score.
    Called after UploadScores() succeeds.

    Args:
        match_id: The AltGameNum (PHP match ID) of the completed match
    """
    if not selected_tournament_number:
        return

    result = _sms_api_post("notify_score", {
        "match_id": int(match_id),
    })

    if result.get("success"):
        sent = result.get("sent", 0)
        if sent > 0:
            logger.info("SMS notify_score: sent=%d match_id=%s", sent, match_id)
    else:
        logger.error("SMS notify_score error: %s", result.get("error"))


def GetUpcomingMatchIds(games_ahead=2):
    """
    Look ahead in the local SQLite games queue and return the match IDs
    for the next N 'Not Started' games. Used to determine which teams
    to notify about upcoming matches.

    Args:
        games_ahead: How many games to look ahead (default 2)

    Returns:
        List of (AltGameNum, position) tuples where position is 1-based
        (1 = next game / on deck, 2 = two games away, etc.)
    """
    conn = None
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute(
            "SELECT AltGameNum FROM Games"
            " WHERE GameStatus = 'Not Started'"
            " AND AltGameNum IS NOT NULL AND AltGameNum != '0'"
            " AND AltTournmentNum = ?"
            " ORDER BY " + GAME_SORT_SQL
            + " LIMIT ?;",
            (selected_tournament_number, games_ahead)
        )
        rows = cur.fetchall()
        result = []
        for i, row in enumerate(rows):
            result.append((row[0], i + 1))  # (match_id, position: 1-based)
        return result
    except Exception as error:
        logger.error("GetUpcomingMatchIds error: %s", error)
        return []
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
