#!/usr/bin/env python

import challonge
import json
from datetime import datetime
import sqlite3
from os import listdir
from os.path import isfile, join
import os
import sys
import logging

logger = logging.getLogger('sherwood')

path = join("SherwoodTimer", os.getcwd() )
database = join(path,'stdata.db')
CUser = "SherwoodAdventure"
CAPIKey = "v6fQDM72P88S8LqLPilpTmvPQEOfbHw472q3Ze8I"

# Track which tournaments have already had their first sync processed
_first_sync_done = {}

def GetOrUpdateGames():
    conn = None
    try:
        challonge.set_credentials(CUser, CAPIKey)
        tournament = challonge.tournaments.index()
        ChalGameNumb = -1

        conn = sqlite3.connect(database)

        for t in tournament:
            if t.get("state") == "group_stages_underway":
                ChalGameNumb = t.get("id")
                GameDesc = t.get("description")
                if "Elimination".casefold() in GameDesc.casefold():
                    GameType = "Elimination"
                elif "Sanction".casefold() in GameDesc.casefold():
                    GameType = "Sanction"
                elif "league".casefold() in GameDesc.casefold():
                    GameType = "Tournament"
                else:
                    GameType = "Normal"
                GameStartTime = t.get("start_at")

        if ChalGameNumb == -1:
            logger.error("No Active Challonge Tournament Found")
            return 0

        PlayerList = {"TeamNum" : "TeamName"}
        Players = challonge.participants.index(ChalGameNumb)
        for p in Players:
            TeamNum = int(str((p.get("group_player_ids"))).replace('[','').replace(']',''))
            TeamName = p.get("name")
            PlayerList[TeamNum] = TeamName

        matches = challonge.matches.index(ChalGameNumb)

        if t.get("group_stages_enabled"): #This is a round robin

            for m in matches:
                AltGameNum = m.get("id")
                GroupID = m.get("group_id")
                RoundNum = m.get("round")
                YTeamNum = m.get("player1_id")
                YTeamName = PlayerList.get(YTeamNum)
                GTeamNum = m.get("player2_id")
                GTeamName = PlayerList.get(GTeamNum)

                query = "INSERT INTO Games(AltGameNum"  \
                        + ", AltTournmentNum"  \
                        + ", AltTournmentSystem"  \
                        + ", GroupNum"  \
                        + ", RoundNum"  \
                        + ", GreenTeamName"  \
                        + ", AltGreenTeamNum"  \
                        + ", YellowTeamName"  \
                        + ", AltYellowTeamNum"  \
                        + ", GameType" \
                        + ", ScheduledStartTime)"  \
                    + " VALUES(" + str(AltGameNum)  \
                        + ", " + str(ChalGameNumb)  \
                        + ", 'Challonge' " \
                        + ", " + str(GroupID)  \
                        + ", " + str(RoundNum)  \
                        + ", '" + GTeamName  + "'"\
                        + ", " + str(GTeamNum)  \
                        + ", '" + YTeamName  + "'" \
                        + ", " + str(YTeamNum)  \
                        + ", '" + GameType  + "'" \
                        + ", '" + str(GameStartTime)  + "'" \
                        + ") " \
                    + " ON CONFLICT(AltGameNum) " \
                    + " DO UPDATE SET " \
                        + "  GreenTeamName = excluded.GreenTeamName "  \
                        + ", YellowTeamName = excluded.YellowTeamName "  \
                    + ";"
                try:
                    cur = conn.cursor()
                    cur.execute(query)
                    conn.commit()
                except Exception as error:
                    logger.error("Database Error: Could not save/update game - %s", error)
                    logger.error("Failed query: %s", query)

            # Skip default-named games on first sync for Tournament type
            if GameType == "Tournament" and ChalGameNumb not in _first_sync_done:
                _first_sync_done[ChalGameNumb] = True
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT GameNumber, GreenTeamName, YellowTeamName FROM Games "
                                "WHERE GameStatus = 'Not Started' AND AltTournmentNum = ? "
                                "ORDER BY GameNumber ASC;", (ChalGameNumb,))
                    rows = cur.fetchall()
                    for row in rows:
                        gNum, gName, yName = row[0], row[1], row[2]
                        if gName == "Green" or yName == "Yellow":
                            cur.execute("UPDATE Games SET GameStatus = 'Skipped' WHERE GameNumber = ?;", (gNum,))
                            conn.commit()
                            logger.info("Tournament: Skipped default game #%s (%s vs %s)", gNum, gName, yName)
                        else:
                            break  # Stop at first real game
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


def StartMatch(GameNum):
    conn = None
    try:
        challonge.set_credentials(CUser, CAPIKey)
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute("Select AltGameNum, AltTournmentNum"
                    " from Games where GameNumber = ?;", (GameNum,) )
        row = cur.fetchone()
        if row is None:
            logger.error("StartMatch: No game found for GameNumber %s", GameNum)
            return 0
        match_id = row[0]
        tournment_id = row[1]
        challonge.matches.mark_as_underway(tournment_id, match_id)
        return 1
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
        challonge.set_credentials(CUser, CAPIKey)
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute("Select AltGameNum, AltTournmentNum"
                    " from Games where GameNumber = ?;", (GameNum,) )
        row = cur.fetchone()
        if row is None:
            logger.error("EndMatch: No game found for GameNumber %s", GameNum)
            return 0
        match_id = row[0]
        tournment_id = row[1]
        challonge.matches.unmark_as_underway(tournment_id, match_id)
        return 1
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
        challonge.set_credentials(CUser, CAPIKey)
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute("Select AltGameNum" \
                    + ", AltTournmentNum" \
                    + ", AltTournmentSystem" \
                    + ", AltYellowTeamNum" \
                    + ", YellowTotalScore" \
                    + ", AltGreenTeamNum" \
                    + ", GreenTotalScore" \
                    + ", GameStatus" \
                    + ", GameWinner" \
                + " from Games where GameNumber = ?;", (GameNum,) )
        row = cur.fetchone()
        if row is None:
            logger.error("UploadScores: No game found for GameNumber %s", GameNum)
            return 0
        match_id = row[0]
        tournment_id = row[1]
        #AltTournmentSystem = row[2]
        player1_id = row[3]
        player1_Score = row[4]
        player2_id = row[5]
        player2_score = row[6]
        GameStatus = row[7]
        GameWinner = row[8]
        GameScore = str(player1_Score) + "-" + str(player2_score)

        if GameStatus == "Finished":
            if GameWinner == "Yellow":
                GameWinner_id = player1_id
            else:
                GameWinner_id = player2_id
            challonge.matches.update(tournment_id, match_id, scores_csv=GameScore, winner_id=GameWinner_id, state="Complete")
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
