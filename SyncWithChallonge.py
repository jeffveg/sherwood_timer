#!/usr/bin/env python

import challonge
import json
from datetime import datetime
import sqlite3
from os import listdir
from os.path import isfile, join
import os
import sys

path = join("SherwoodTimer", os.getcwd() )
database = join(path,'stdata.db')
CUser = "SherwoodAdventure"
CAPIKey = "v6fQDM72P88S8LqLPilpTmvPQEOfbHw472q3Ze8I"

def GetOrUpdateGames():
    challonge.set_credentials(CUser, CAPIKey)
    tournament = challonge.tournaments.index()
    ChalGameNumb = -1
    try:
        conn = sqlite3.connect(database)
    except Exception as error:
        print("Database Error: Could not open Database - ",error)
        return 0

    try:
        for t in tournament:
            if t.get("state") == "group_stages_underway": #and t.get("start_at").date() == datetime.today().date():
                ChalGameNumb = t.get("id")
                GameDesc = t.get("description")
                if "Elimination".casefold() in GameDesc.casefold():
                    GameType = "Elimination"
                elif "Sanction".casefold() in GameDesc.casefold():
                    GameType = "Sanction"
                else:
                    GameType = "Normal"
                GameStartTime = t.get("start_at")
        if ChalGameNumb != -1 :

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
                        print("Database Error: Could not save/update game - ",error)
                        print(query)
                conn.close()
        else:
            print("No Active Challong Tournament Found ")
            return 0
        return 1
    except Exception as error:
        print("API Error - ",error)
        return 0


def StartMatch(GameNum):
    challonge.set_credentials(CUser, CAPIKey)
    try:
        conn = sqlite3.connect(database)
    except Exception as error:
        return 0
    cur = conn.cursor()
    cur.execute("Select AltGameNum" \
                + ", AltTournmentNum" \
            + " from Games where GameNumber = ?;", (GameNum,) )
    row = cur.fetchone()
    match_id = row[0]
    tournment_id = row[1]
  
    try:
        challonge.matches.mark_as_underway(tournment_id,match_id)
    except Exception as error:
        print("API Error - ",error)
        return 0

def EndMatch(GameNum):
    challonge.set_credentials(CUser, CAPIKey)
    try:
        conn = sqlite3.connect(database)
    except Exception as error:
        return 0
    cur = conn.cursor()
    cur.execute("Select AltGameNum" \
                + ", AltTournmentNum" \
            + " from Games where GameNumber = ?;", (GameNum,) )
    row = cur.fetchone()
    match_id = row[0]
    tournment_id = row[1]
    
    try:
        challonge.matches.unmark_as_underway(tournment_id,match_id)
    except Exception as error:
        print("API Error - ",error)
        return 0
    
def UploadScores(GameNum):
    challonge.set_credentials(CUser, CAPIKey)
    try:
        conn = sqlite3.connect(database)
    except Exception as error:
        return 0
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
        try:
            challonge.matches.update(tournment_id,match_id, scores_csv=GameScore , winner_id=GameWinner_id, state="Complete" )
        except Exception as error:
            print("API Error - ",error)
            return 0