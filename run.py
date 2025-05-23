#!/usr/bin/env python

# Import stuff
import threading
import sys 
from array import*
from time import sleep, localtime, strftime, gmtime, strptime
from datetime import datetime,timedelta
from os import listdir
from os.path import isfile, join
import os
import random
import pygame
import pygame.freetype
from pyvidplayer2 import Video
import queue
import pyttsx3
from tinytag import TinyTag 
import sqlite3
import ctypes
import requests
from SyncWithChallonge import * 
import justpy as jp
import asyncio

DeBug = False

if len(sys.argv) == 2:
    arg = sys.argv[1]
    if arg == "-D":
        DeBug = True

# Stuff to pull from config
ValueHit            = 1
ValueCatch          = 2
ValueSpot           = 2
ValuePenalty        = 1
ValueExtraPoint     = 1
SongList            = "SongList/EDM"
DefaultGameRunTime  = 5
SanctionGameRunTime = 8

path = join("SherwoodTimer", os.getcwd() )
if DeBug: print("Program Root " + path + " | SongList " + SongList )

# Defaults
HoldIt           = datetime.now()
DelayScreen      = datetime.now() - timedelta(seconds = 20)
GameRunning      = "No"
GameStart        = datetime.now()
GameEnd          = datetime.now()
GameRunTime      = DefaultGameRunTime
SecondsLeft      = 0
LastCountSec     = 0
SecondsPaused    = 0
CurrentVid       = "Startup"
CurrentGameType  = "Elimination"
BackgroundMusic  = True
BackgroundVol    = .25
AutoInst         = False 
APIIitegration   = False
AnnouncedOvertime = False

ScoreValues = {
"Hit"       : 1,
"Catch"     : 2,
"Spot"      : 1,
"Penalty"   : -1,
"ExtraPoint": 1
}

#Define score buckets
GreenScores = {
    "Total"     : 0,
    "Hit"       : 0, 
    "Catch"     : 0,
    "Spot"      : 0,
    "Penalty"   : 0,
    "ExtraPoint": 0
}

YellowScores = {
    "Total"     : 0,
    "Hit"       : 0, 
    "Catch"     : 0,
    "Spot"      : 0,
    "Penalty"   : 0,
    "ExtraPoint": 0
}

CurrentGame = {
    "GameNumber"         : 0,
    "AltGameNum"         : 0,
    "AltTournmentSystem" : "",
    "GreenTeamName"      : "",
    "GreenTeamNum"       : 0,
    "GreenTotalScore"    : 0,
    "AltGreenTeamNum"    : 0,
    "YellowTeamName"     : "",
    "YellowTeamNum"      : 0,
    "AltYellowTeamNum"   : 0,
    "YellowTotalScore"   : 0,
    "GameType"           : "Elimination",
    "ScheduledStartTime" : "",
    "ActualStartTime"    : "",
    "ActualEndTime"      : "",
    "SongPlayed"         : "",
    "ArtistPlayed"       : "",
    "GameWinner"         : "",
    "GameStatus"         : "Not Started",
    "GameEarlyStopReason": ""
    }

NextGame = {
    "GameNumber"         : 0,
    "AltGameNum"         : 0,
    "AltTournmentSystem" : "",
    "GreenTeamName"      : "",
    "GreenTeamNum"       : 0,
    "GreenTotalScore"    : 0,
    "AltGreenTeamNum"    : 0,
    "YellowTeamName"     : "",
    "YellowTeamNum"      : 0,
    "AltYellowTeamNum"   : 0,
    "YellowTotalScore"   : 0,
    "GameType"           : "",
    "ScheduledStartTime" : "",
    }

database = join(path,"stdata.db")

played = {}
pygame.mixer.init()

pygame.mixer.music.load(join(path,"SoundFX/large-bell.mp3"))
SongData = TinyTag.get(join(path,"SoundFX/large-bell.mp3")) 

pygame.init()
pygame.event.set_allowed([pygame.KEYDOWN,pygame.KEYUP])
#Setup Screen
if DeBug: print(str(datetime.now()) + " Start" )
if DeBug: 
    pygame.mouse.set_visible(True)
    ScreenScale = 0.4
    os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (0,0)
else:
    ScreenScale = 1
    pygame.mouse.set_visible(False)

infoObject = pygame.display.Info()
SWidth = infoObject.current_w * ScreenScale
SHeight = infoObject.current_h * ScreenScale
clock = pygame.time.Clock()
flags = pygame.NOFRAME
screen = pygame.display.set_mode((SWidth, SHeight),flags)

#Adjust screen scale from windows settings 
scaleFactor = (ctypes.windll.shcore.GetScaleFactorForDevice(0) ) /100 
ScreenScale = ScreenScale / scaleFactor

SWidth, SHeight = screen.get_size()
DefaultBack = pygame.image.load(join(path,"Images/DefaultBack.jpg"))

TimerBack = pygame.image.load(join(path,"Images/TimerBack2.bmp"))
BlackTimerBack = pygame.image.load(join(path,"Images/BlackTimerBack.jpg"))
Logo = pygame.image.load(join(path,"Images/logo.png"))
screen.blit(pygame.transform.scale(Logo, (SWidth, SHeight)), (0, 0))
pygame.display.flip()

if DeBug: print(str(datetime.now()) + " Screen Done" )
vCountdown = Video(join(path,"Video/Countdown.mp4"))
vEliminationInst = Video(join(path,"Video/EliminationInst.mp4"))
vNormalInst = Video(join(path,"Video/NormalInst.mp4"))
vPromo = Video(join(path,"Video/Promo.mp4"))
vSanctionInst = Video(join(path,"Video/SanctionInst.mp4"))
vShootInst = Video(join(path,"Video/ShootInst.mp4"))

vCountdown.resize((SWidth, SHeight))
vEliminationInst.resize((SWidth, SHeight))
vNormalInst.resize((SWidth,SHeight))
vPromo.resize((SWidth, SHeight))
vSanctionInst.resize((SWidth, SHeight))
vShootInst.resize((SWidth, SHeight))

vCountdown.stop()
vEliminationInst.stop()
vNormalInst.stop()
vPromo.stop()
vSanctionInst.stop()
vShootInst.stop()

if DeBug: print(str(datetime.now()) + " Video Loaded" )

#LoadSounds
Bell = pygame.mixer.Sound(join(path,"SoundFX/large-bell.mp3"))
Buzzer = pygame.mixer.Sound(join(path,"SoundFX/buzzer.wav"))
Reset = pygame.mixer.Sound(join(path,"SoundFX/reset.wav"))
Ding = pygame.mixer.Sound(join(path,"SoundFX/Ding.wav"))
EarlyWin = pygame.mixer.Sound(join(path,"SoundFX/EarlyWin.wav"))
Close = pygame.mixer.Sound(join(path,"SoundFX/Close.ogg"))
if DeBug:
    EndGame = pygame.mixer.Sound(join(path,"SoundFX/reset.wav"))
else:
    EndGame = pygame.mixer.Sound(join(path,"SoundFX/EndGameCount.ogg"))
pygame.mixer.Sound.play(Ding)

if DeBug: print(str(datetime.now()) + " Sounds Loaded" )

def PrintDeBug():
    threading.Timer.daemon = True
    threading.Timer(10.0, PrintDeBug).start()
    print( "Current Time " + datetime.now().strftime("%H:%M:%S")  \
           + " Countdown " + str(SecondsLeft) )
    print("CurrentGameType " + CurrentGameType + " | CurrentVid " + CurrentVid \
          + " | GameRunning " + GameRunning )
   # print(CurrentGame)

# Thread for Text to Speech Engine
class TTSThread(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue
        self.daemon = True
        self.start()

    def run(self):
        tts_engine = pyttsx3.init()
        tts_engine.startLoop(False)
        voices = tts_engine.getProperty("voices")
        tts_engine.setProperty("voice", voices[1].id)
        rate = tts_engine.getProperty("rate")   # getting details of current speaking rate
        tts_engine.setProperty("rate", 125)  
        t_running = True
        while t_running:
            if self.queue.empty():
                tts_engine.iterate()
            else:
                data = self.queue.get()
                if data == "exit":
                    t_running = False
                else:
                    tts_engine.say(data)
        tts_engine.endLoop()


# Thread for score Web
class WebGameThread(threading.Thread):
    
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()

    def ButtonHit(self, msg):
        if GameRunning == "Playing":
            if self.ButtonName == "GHU": Green_Hit_Up()
            elif self.ButtonName == "GSU": Green_Spot_Up()
            elif self.ButtonName == "GCU": Green_Catch_Up()
            elif self.ButtonName == "GPU": Green_Penalty_Up()
            elif self.ButtonName == "YHU": Yellow_Hit_Up()
            elif self.ButtonName == "YSU": Yellow_Spot_Up()
            elif self.ButtonName == "YCU": Yellow_Catch_Up()
            elif self.ButtonName == "YPU": Yellow_Penalty_Up()
            elif self.ButtonName == "GHD": Green_Hit_Down()
            elif self.ButtonName == "GSD": Green_Spot_Down()
            elif self.ButtonName == "GCD": Green_Catch_Down()
            elif self.ButtonName == "GPD": Green_Penalty_Down()
            elif self.ButtonName == "YHD": Yellow_Hit_Down()
            elif self.ButtonName == "YSD": Yellow_Spot_Down()
            elif self.ButtonName == "YCD": Yellow_Catch_Down()
            elif self.ButtonName == "YPD": Yellow_Penalty_Down()
        else:
            if self.ButtonName == "GT": ButtonPressed(pygame.K_5) # Game Type
            elif self.ButtonName == "NG": ButtonPressed(pygame.K_RIGHT) # Pull Next Game
            elif self.ButtonName == "FG": ButtonPressed(pygame.K_UP) # Pull First Game
            elif self.ButtonName == "RD": ButtonPressed(pygame.K_DOWN) # Pull Data from Challonge
            elif self.ButtonName == "AI": ButtonPressed(pygame.K_BACKSPACE) # Toggle Auto Instructions
            elif self.ButtonName == "TT": ButtonPressed(pygame.K_3) # Toggle API integration
            elif self.ButtonName == "TM": ButtonPressed(pygame.K_7) # Toggle Between Game Music
            elif self.ButtonName == "MV": ButtonPressed(pygame.K_9) # Toggle Between Game Music Volumn  
    
    @jp.SetRoute('/ctl')
    def sawebctl():
        wp = jp.WebPage()
        wp.title = "Sherwood Adventure Timer Control"
        jp.Space(num=3,a=wp)
        wp.head_html = '<meta http-equiv="refresh" content="5" >'
        if GameRunning == 'No':
            button_grid = jp.Div(classes='grid grid-cols-2 gap-4', a=wp)
            Button = 'w-dvw text-7xl m-4 p-1 bg-green-700 text-yellow-500 text-center'
            Display = 'w-dvw text-7xl m-4 p-1 bg-white text-black text-center'
            
            GT = jp.Div(text="Game Type", a=button_grid, classes=Button)
            GT.ButtonName = "GT"
            GT.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            Text = CurrentGameType
            jp.Div(text=Text, a=button_grid, classes=Display)

            AI = jp.Div(text="Auto Instructions", a=button_grid, classes=Button)
            AI.ButtonName = "AI"
            AI.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            if AutoInst:
                Text = "ON"
            else:
                Text = "OFF"
            jp.Div(text=Text, a=button_grid, classes=Display)
            
            TT = jp.Div(text="Tourn Integration", a=button_grid, classes=Button)
            TT.ButtonName = "TT"
            TT.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            if APIIitegration:
                Text = "ON"
            else:
                Text = "OFF"
            jp.Div(text=Text, a=button_grid, classes=Display)
            
            NG = jp.Div(text="Next Game", a=button_grid, classes=Button)
            NG.ButtonName = "NG"
            NG.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
     
            FG = jp.Div(text="First Game", a=button_grid, classes=Button)
            FG.ButtonName = "FG"
            FG.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            
            jp.P(text="Green:", a=button_grid, classes="text-7xl")
            jp.P(text="Yellow:", a=button_grid, classes="text-7xl")
            Text = NextGame.get("GreenTeamName")
            jp.P(text=Text, a=button_grid, classes="text-7xl")
            
            Text =  "  " + NextGame.get("YellowTeamName")
            jp.P(text=Text, a=button_grid, classes="text-7xl")          
            
            
            
            TM = jp.Div(text="Music", a=button_grid, classes=Button)
            TM.ButtonName = "TM"
            TM.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            if BackgroundMusic:
                Text = "ON"
            else:
                Text = "OFF"
            jp.Div(text=Text, a=button_grid, classes=Display)
            
            MV = jp.Div(text="Music Volume", a=button_grid, classes=Button)
            MV.ButtonName = "MV"
            MV.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            Text = str(int(BackgroundVol * 100) )
            jp.Div(text=Text, a=button_grid, classes=Display)
        
        else:
            wp.head_html = '<meta http-equiv="refresh" content="10" >'
            jp.P(text="Game Running", a=wp, classes="text-7xl")
                

        return wp


    @jp.SetRoute('/')
    def saweb():
        wp = jp.WebPage()
        wp.title = "Sherwood Adventure Timer Control"
        jp.Space(num=3,a=wp)
        if GameRunning == 'No':
            wp.head_html = '<meta http-equiv="refresh" content="10" >'
            jp.P(text="No Game Running", a=wp, classes="text-7xl")
            jp.Space(num=3,a=wp)
            jp.P(text="Next Game", a=wp, classes="text-7xl")
            jp.P(text="Green:", a=wp, classes="text-7xl")
            Text = "  " + NextGame.get("GreenTeamName")
            jp.P(text=Text, a=wp, classes="text-7xl")
            jp.Space(num=3,a=wp)
            jp.P(text="Yellow:", a=wp, classes="text-7xl")
            Text =  "  " + NextGame.get("YellowTeamName")
            jp.P(text=Text, a=wp, classes="text-7xl")

        elif GameRunning == 'Countdown':
            wp.head_html = '<meta http-equiv="refresh" content="10" >'
            jp.P(text="Countdown Running", a=wp, classes="text-7xl")  
        else:
            wp.head_html = '<meta http-equiv="refresh" content="30" >'
            button_grid = jp.Div(classes='grid grid-cols-2 gap-4', a=wp)
            GreenButton = 'w-dvw text-7xl m-4 p-1 bg-green-700 text-white text-center'
            YellowButton = 'w-dvw text-7xl m-4 p-1 bg-yellow-500 text-black text-center'
            
            ghu = jp.Div(text="Green Hit Up", a=button_grid, classes=GreenButton)
            ghu.ButtonName = "GHU"
            ghu.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )

            yhu = jp.Div(text="Yellow Hit Up", a=button_grid, classes=YellowButton)
            yhu.ButtonName = "YHU"
            yhu.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            
            if CurrentGameType == "Elimination":
                gsu = jp.Div(text="Green Spot Up", a=button_grid, classes=GreenButton)
                gsu.ButtonName = "GSU"
                gsu.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            
            if CurrentGameType == "Elimination":
                ysu = jp.Div(text="Yellow Spot Up", a=button_grid, classes=YellowButton)
                ysu.ButtonName = "YSU"
                ysu.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            
            if CurrentGameType in ("Elimination","Sanction"):
                gcu = jp.Div(text="Green Catch Up", a=button_grid, classes=GreenButton)
                gcu.ButtonName = "GCU"
                gcu.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            
            if CurrentGameType in ("Elimination","Sanction"):
                ycu = jp.Div(text="Yellow Catch Up", a=button_grid, classes=YellowButton)
                ycu.ButtonName = "YCU"
                ycu.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            
            if CurrentGameType in ("Elimination","Sanction"):
                gpu = jp.Div(text="Green Penalty Up", a=button_grid, classes=GreenButton)
                gpu.ButtonName = "GPU"
                gpu.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            
            if CurrentGameType in ("Elimination","Sanction"):
                ypu = jp.Div(text="Yellow Penalty Up", a=button_grid, classes=YellowButton)
                ypu.ButtonName = "YPU"
                ypu.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )


            if CurrentGameType in ("Normal","Sanction"):
                jp.Div(text=" ----- ", a=button_grid, classes=GreenButton)
                jp.Div(text=" ----- ", a=button_grid, classes=YellowButton)

            ghd = jp.Div(text="Green Hit Down", a=button_grid, classes=GreenButton)
            ghd.ButtonName = "GHD"
            ghd.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )

            yhd = jp.Div(text="Yellow Hit Down", a=button_grid, classes=YellowButton)
            yhd.ButtonName = "YHD"
            yhd.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            
            if CurrentGameType == "Elimination":
                gsd = jp.Div(text="Green Spot Down", a=button_grid, classes=GreenButton)
                gsd.ButtonName = "GSD"
                gsd.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            
            if CurrentGameType == "Elimination":
                ysd = jp.Div(text="Yellow Spot Down", a=button_grid, classes=YellowButton)
                ysd.ButtonName = "YSD"
                ysd.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            
            if CurrentGameType in ("Elimination","Sanction"):
                gcd = jp.Div(text="Green Catch Down", a=button_grid, classes=GreenButton)
                gcd.ButtonName = "GCD"
                gcd.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            
            if CurrentGameType in ("Elimination","Sanction"):
                ycd = jp.Div(text="Yellow Catch Down", a=button_grid, classes=YellowButton)
                ycd.ButtonName = "YCD"
                ycd.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            
            if CurrentGameType in ("Elimination","Sanction"):
                gpd = jp.Div(text="Green Penalty Down", a=button_grid, classes=GreenButton)
                gpd.ButtonName = "GPD"
                gpd.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )
            
            if CurrentGameType in ("Elimination","Sanction"):
                ypd = jp.Div(text="Yellow Penalty Down", a=button_grid, classes=YellowButton)
                ypd.ButtonName = "YPD"
                ypd.on('click', WebGameThread.ButtonHit, debounce=500, immediate=False )

        return wp
        
    def run(self):   
        while 1 == 1: 
            jp.justpy(port=80,host='0.0.0.0')


def GetNextGame(MinGameNumber=-1):
    global CurrentGame
    global NextGame
    global CurrentGameType
    global GameRunTime
    try:
        conn = sqlite3.connect(database)
    
        cur = conn.cursor()
        cur.execute("Select min(GameNumber) from Games where GameStatus = 'Not Started' and GameNumber > ?;",(MinGameNumber,) )
        row = cur.fetchone()
        if row[0] == None:
            cur.execute("INSERT INTO Games (GameStatus) VALUES ('Not Started');")
            conn.commit()
            cur.execute( "Select min(GameNumber) from Games where GameStatus = 'Not Started';")
            row = cur.fetchone()
        GameNum = row[0]
        if DeBug: print("GameNumber => " + str(GameNum))
        cur.execute("Select  GameNumber" \
                        + ", AltGameNum" \
                        + ", AltTournmentSystem" \
                        + ", GreenTeamName" \
                        + ", GreenTeamNum" \
                        + ", AltGreenTeamNum" \
                        + ", YellowTeamName" \
                        + ", YellowTeamNum" \
                        + ", AltYellowTeamNum" \
                        + ", GameType" \
                        + ", ScheduledStartTime" \
                    + " from Games where GameNumber = ?;", (GameNum,) )
        row = cur.fetchone()
    except Exception as error:
        print("Database Error: Could not get game - ",error)
        GameNum = -1
        NextGame["GameNumber"] = -1        
        NextGame["GreenTeamName"] = "Green"
        NextGame["YellowTeamName"] = "Yellow"
        NextGame["GameType"] = "Normal"
    else:
        NextGame["GameNumber"] = row[0]        
        NextGame["AltGameNum"] = row[1]
        NextGame["AltTournmentSystem"] = row[2] 
        NextGame["GreenTeamName"] = row[3]
        NextGame["GreenTeamNum"] = row[4]
        NextGame["AltGreenTeamNum"] = row[5]
        NextGame["YellowTeamName"] = row[6]
        NextGame["YellowTeamNum"] = row[7]
        NextGame["AltYellowTeamNum"] = row[8]
        NextGame["GameType"] = row[9]
        NextGame["ScheduledStartTime"] = row[10] 
        
    try:
        cur.execute("Select count(*) from Scores where Side = 'Yellow' and GameNumber = ?;", (GameNum,))
        row = cur.fetchone()
        if row[0] == 0:
            cur.execute("INSERT INTO Scores (GameNumber,Side) VALUES (?,'Yellow');", (GameNum,))
            conn.commit()
        cur.execute("Select count(*) from Scores where Side = 'Green' and GameNumber = ?;", (GameNum,))
        row = cur.fetchone()
        if row[0] == 0:
            cur.execute("INSERT INTO Scores (GameNumber,Side) VALUES (?,'Green');", (GameNum,))
            conn.commit()
    except Exception as error:
        print("Database Error: Checking Score Record exists - ", error)

    conn.close()
    if DeBug: 
        print("Next Game:")
        print(NextGame)
        print("---------------------------------")
    CurrentGameType = NextGame.get("GameType")
    if CurrentGameType == "Normal":
        GameRunTime = DefaultGameRunTime

    elif CurrentGameType == "Elimination":
        GameRunTime = DefaultGameRunTime

    elif CurrentGameType == "Sanction":
        GameRunTime = SanctionGameRunTime
    else:
        GameRunTime = DefaultGameRunTime     

def WriteGameToDB():
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()

        #Game info
        #query = "update Games set " 
        #query =  query + "  GreenTotalScore = " + str(CurrentGame.get("GreenTotalScore"))
        #query =  query + ", YellowTotalScore = " + str(CurrentGame.get("YellowTotalScore"))
        #query =  query + ", ActualStartTime  = '" + str(CurrentGame.get("ActualStartTime")) + "'"
        #query =  query + ", ActualEndTime = '" + str(CurrentGame.get("ActualEndTime")) + "'"
        #query =  query + ", SongPlayed =  '" + str(CurrentGame.get("SongPlayed")) + "'"
        #query =  query + ", ArtistPlayed =  '" + str(CurrentGame.get("ArtistPlayed")) + "'"
        #query =  query + ", GameWinner =  '" + str(CurrentGame.get("GameWinner")) + "'"
        #query =  query + ", GameStatus =  '" + str(CurrentGame.get("GameStatus")) + "'"
        #query =  query + ", GameEarlyStopReason = '" + str(CurrentGame.get("GameEarlyStopReason")) + "'"
        #query =  query + " where GameNumber = " + str(CurrentGame.get("GameNumber")) + ";"

        query = "update Games set " 
        query =  query + "  GreenTotalScore = ?" 
        query =  query + ", YellowTotalScore = ?" 
        query =  query + ", ActualStartTime  = ?" 
        query =  query + ", ActualEndTime = ?" 
        query =  query + ", SongPlayed =  ?" 
        query =  query + ", ArtistPlayed =  ?" 
        query =  query + ", GameWinner =  ?" 
        query =  query + ", GameStatus =  ?" 
        query =  query + ", GameEarlyStopReason = ?" 
        query =  query + " where GameNumber = ?;"


        pGreenTotalScore    = CurrentGame.get("GreenTotalScore")
        pYellowTotalScore   = CurrentGame.get("YellowTotalScore")
        pActualStartTime    = CurrentGame.get("ActualStartTime")
        pActualEndTime      = CurrentGame.get("ActualEndTime")
        pSongPlayed         = CurrentGame.get("SongPlayed")
        pArtistPlayed       = CurrentGame.get("ArtistPlayed")
        pGameWinner         = CurrentGame.get("GameWinner")
        pGameStatus         = CurrentGame.get("GameStatus")
        pGameEarlyStopRsn   = CurrentGame.get("GameEarlyStopReason")
        pGameNumber         = CurrentGame.get("GameNumber")

        cur.execute(query
                    ,(
                        pGreenTotalScore 
                        ,pYellowTotalScore 
                        ,pActualStartTime 
                        ,pActualEndTime 
                        ,pSongPlayed 
                        ,pArtistPlayed 
                        ,pGameWinner 
                        ,pGameStatus 
                        ,pGameEarlyStopRsn 
                        ,pGameNumber 
                        )
                    )
        conn.commit()

        #Yellow Scores
        #query = "update Scores set " 
        #query =  query + "  Total = " + str(YellowScores.get("Total"))
        #query =  query + ", Hit = " + str(YellowScores.get("Hit"))
        #query =  query + ", Catch = " + str(YellowScores.get("Catch"))
        #query =  query + ", Spot = " + str(YellowScores.get("Spot"))
        #query =  query + ", Penalty = " + str(YellowScores.get("Penalty"))
        #query =  query + ", ExtraPoint = " + str(YellowScores.get("ExtraPoint"))
        #query =  query + " Where Side = 'Yellow' and GameNumber = " + str(CurrentGame.get("GameNumber")) + ";"

        query = "update Scores set " 
        query =  query + "  Total = ?"
        query =  query + ", Hit = ?" 
        query =  query + ", Catch = ?" 
        query =  query + ", Spot = ?" 
        query =  query + ", Penalty = ?"
        query =  query + ", ExtraPoint = ?" 
        query =  query + " Where Side = ? and GameNumber = ?;"


        pTotal = YellowScores.get("Total")
        pHit = YellowScores.get("Hit")
        pCatch = YellowScores.get("Catch")
        pSpot = YellowScores.get("Spot")
        pPenalty = YellowScores.get("Penalty")
        pExtraPoint = YellowScores.get("ExtraPoint")
        pSide = "Yellow"

        cur.execute(query
                    ,(
                         pTotal 
                        ,pHit 
                        ,pCatch 
                        ,pSpot 
                        ,pPenalty 
                        ,pExtraPoint 
                        ,pSide
                        ) 
                    )
        conn.commit()

        #Green Scores
        #query = "update Scores set " 
        #query =  query + "  Total = " + str(GreenScores.get("Total"))
        #query =  query + ", Hit = " + str(GreenScores.get("Hit"))
        #query =  query + ", Catch = " + str(GreenScores.get("Catch"))
        #query =  query + ", Spot = " + str(GreenScores.get("Spot"))
        #query =  query + ", Penalty = " + str(GreenScores.get("Penalty"))
        #query =  query + ", ExtraPoint = " + str(GreenScores.get("ExtraPoint"))
        #query =  query + " Where Side = 'Green' and GameNumber = " + str(CurrentGame.get("GameNumber")) + ";"
        
        pTotal = GreenScores.get("Total")
        pHit = GreenScores.get("Hit")
        pCatch = GreenScores.get("Catch")
        pSpot = GreenScores.get("Spot")
        pPenalty = GreenScores.get("Penalty")
        pExtraPoint = GreenScores.get("ExtraPoint")
        pSide = "Green"
        
        cur.execute(query
                    ,(
                         pTotal 
                        ,pHit 
                        ,pCatch 
                        ,pSpot 
                        ,pPenalty 
                        ,pExtraPoint 
                        ,pSide
                        ) 
                    )
        conn.commit()
    except Exception as error:
        print("Databse Error: Saving Game - ",error)
        return 0
    conn.close()
    return 1

#Define a get files function
def GetFiles(Path):
    onlyfiles = [f for f in listdir(Path) if isfile(join(Path, f))]
    return onlyfiles

def ChangeScore(Team,ScoreType,Up_Down):
    global ScoreValues
    global GreenScores
    global YellowScores
    global CurrentGame

    CurrentScore = Team[ScoreType]
    if Up_Down == "Down":
        Team[ScoreType] = CurrentScore - 1
    else:    
        Team[ScoreType] = CurrentScore + 1
    
    #Clear Negative values
    for Scores in Team:
        CurrentScore = Team.get(Scores)
        if CurrentScore <= 0:
            Team[Scores] = 0
    
    #Reset Total 
    Total = 0
    Team["Total"] = 0
    for Scores in Team:
        if Scores != "Total":
            Total = Total + (Team.get(Scores) * ScoreValues.get(Scores) )
        
    Team["Total"] = Total
    if DeBug: print(Team)
    CurrentGame["YellowTotalScore"] = YellowScores.get("Total")
    CurrentGame["GreenTotalScore"] = GreenScores.get("Total")

    WriteGameToDB()

def Green_Hit_Up():
    ChangeScore(GreenScores,"Hit","Up")
    pygame.mixer.Sound.play(Buzzer)

def Green_Hit_Down():
    ChangeScore(GreenScores,"Hit","Down")
    pygame.mixer.Sound.play(Ding)  

def Green_Catch_Up():
    if CurrentGameType in ("Elimination","Sanction"):
        ChangeScore(GreenScores,"Catch","Up")
        pygame.mixer.Sound.play(Ding)  

def Green_Catch_Down():
    if CurrentGameType in ("Elimination","Sanction"):
        ChangeScore(GreenScores,"Catch","Down")
        pygame.mixer.Sound.play(Buzzer)

def Green_Spot_Up():
    if CurrentGameType == "Elimination":
        ChangeScore(GreenScores,"Spot","Up")
        pygame.mixer.Sound.play(Ding) 

def Green_Spot_Down():
    if CurrentGameType == "Elimination":
        ChangeScore(GreenScores,"Spot","Down")
        pygame.mixer.Sound.play(Buzzer)

def Green_Penalty_Up():
    if CurrentGameType in ("Elimination","Sanction"):
        ChangeScore(GreenScores,"Penalty","Up")
        pygame.mixer.Sound.play(Buzzer)

def Green_Penalty_Down():
    if CurrentGameType in ("Elimination","Sanction"):
        ChangeScore(GreenScores,"Penalty","Down")
        pygame.mixer.Sound.play(Ding)
    
def Yellow_Hit_Up():
    ChangeScore(YellowScores,"Hit","Up")
    pygame.mixer.Sound.play(Buzzer)

def Yellow_Hit_Down():
    ChangeScore(YellowScores,"Hit","Down")
    pygame.mixer.Sound.play(Ding)

def Yellow_Catch_Up():
    if CurrentGameType in ("Elimination","Sanction"):
        ChangeScore(YellowScores,"Catch","Up")
        pygame.mixer.Sound.play(Ding)

def Yellow_Catch_Down():
    if CurrentGameType in ("Elimination","Sanction"):
        ChangeScore(YellowScores,"Catch","Down")
        pygame.mixer.Sound.play(Buzzer)

def Yellow_Spot_Up():
    if CurrentGameType == "Elimination":
        ChangeScore(YellowScores,"Spot","Up")
        pygame.mixer.Sound.play(Ding)

def Yellow_Spot_Down():
    if CurrentGameType == "Elimination":
        ChangeScore(YellowScores,"Spot","Down")
        pygame.mixer.Sound.play(Buzzer)

def Yellow_Penalty_Up():
    if CurrentGameType in ("Elimination","Sanction"):
        ChangeScore(YellowScores,"Penalty","Up")
        pygame.mixer.Sound.play(Buzzer)

def Yellow_Penalty_Down():
    if CurrentGameType in ("Elimination","Sanction"):
        ChangeScore(YellowScores,"Penalty","Down")
        pygame.mixer.Sound.play(Ding)

def EarlyWinGameEnd():
    global GreenScores
    global YellowScores
    global CurrentGame
    global GameRunning

    pygame.mixer.music.fadeout(5000)
    if YellowScores.get("Total") > GreenScores.get("Total"):
        CurrentGame["GameEarlyStopReason"] = "Early Win" + str(LastCountSec) 
        CurrentGame["GameWinner"] = "Yellow"
        ChangeScore(YellowScores,"ExtraPoint","UP")
    else:
        CurrentGame["GameEarlyStopReason"] = "Early Win" + str(LastCountSec) 
        CurrentGame["GameWinner"] = "Green"
        ChangeScore(GreenScores,"ExtraPoint","UP")
    GameRunning = "Stop"

def NormalGameEnd():
    global GreenScores
    global YellowScores
    global CurrentGame
    global GameRunning
    global AnnouncedOvertime
    
    AnnouncedOvertime = False
    if CurrentGame.get("GameEarlyStopReason") != "Early Win" :
        if YellowScores.get("Total") > GreenScores.get("Total"):
            CurrentGame["GameWinner"] = "Yellow"
        else:
            CurrentGame["GameWinner"] = "Green"
    text = ""
    if CurrentGame.get("GameWinner") == "Yellow":
        text = text +  CurrentGame.get("YellowTeamName")
    
    else:
        text = text + CurrentGame.get("GreenTeamName")
    text = text + " team is the winner."
    SpeakIt.put(text)
    attempts = 0
    while attempts < 5:
        ret = WriteGameToDB()
        if ret == 0: 
            sleep(1)
            attempts =+ 1
        else:
            break
    if APIIitegration: 
        print("upload to API game ", CurrentGame.get("GameNumber"))
        UploadScores(CurrentGame.get("GameNumber"))
        GetOrUpdateGames()
    GetNextGame()

# Reset the scores
def ResetScore():
    global GreenScores
    global YellowScores
    
    for Score in GreenScores:
        GreenScores[Score] = 0

    for Score in YellowScores:
        YellowScores[Score] = 0
    WriteGameToDB()
    
#Pause un-pause video
def PauseVid():
    global GameRunning

    if GameRunning == "Playing":
        pygame.mixer.music.pause()
        GameRunning = "Pause"
        CurrentGame["GameStatus"] = GameRunning
    elif GameRunning == "Pause":
        pygame.mixer.music.unpause()
        GameRunning = "Playing"
        CurrentGame["GameStatus"] = GameRunning
        SecondsPaused = 0
    WriteGameToDB()
    
# Stop and clear video 
def StopVid():
    global GameRunning
    if GameRunning == "Playing":
        pygame.mixer.music.stop()
        GameRunning = "Stop"
        CurrentGame["GameStatus"] = GameRunning
        
# Get the path of a Song video, returning None on failure
def getRandomSong():
    global path
    global SongList
    global SongData

    fullPath = join(path,SongList)
    # Check if directory actually exists
    if not os.path.exists(fullPath):
        return None
        # Find all videos in top-level of directory
    files = [ os.path.join(fullPath, fn) for fn in next(os.walk(fullPath))[2] ]

    # Return None if we couldn't find any videos
    if len(files) == 0:
        return None

    # Make a new list for played content of this type if it does not exist
    if played.get(SongList) is None:
        played[SongList] = []

    # Remove any videos we might have already played
    unduped = [f for f in files if f not in played[SongList]]
    if len(unduped) == 0:
        played[SongList] = []
        unduped = files

    # Choose a random video from the list of unplayed videos
    choice = random.choice(unduped)

    # Add that choice to the played video list
    played[SongList].append(choice)
    if DeBug: print(choice)
    # Return our video choice
    SongData = TinyTag.get(choice) 
    return choice

def NextToCurrentGame():
    global CurrentGame

    CurrentGame["GameNumber"] = NextGame.get("GameNumber")       
    CurrentGame["AltGameNum"] = NextGame.get("AltGameNum") 
    CurrentGame["AltTournmentSystem"] =  NextGame.get("AltTournmentSystem")  
    CurrentGame["GreenTeamName"] =  NextGame.get("GreenTeamName") 
    CurrentGame["GreenTeamNum"] =  NextGame.get("GreenTeamNum") 
    CurrentGame["AltGreenTeamNum"] = NextGame.get("AltGreenTeamNum") 
    CurrentGame["YellowTeamName"] = NextGame.get("YellowTeamName") 
    CurrentGame["YellowTeamNum"]  = NextGame.get("YellowTeamNum") 
    CurrentGame["AltYellowTeamNum"] =  NextGame.get("AltYellowTeamNum") 
    CurrentGame["ScheduledStartTime"] =  NextGame.get("ScheduledStartTime") 

# Get a random video and play
def StartGame():
    global CurrentVid
    global GameRunning
    global CurrentGame
    global GameStart
    global GameEnd
    global YellowScores
    global GreenScores

    ResetScore()
    if APIIitegration: GetOrUpdateGames()
    NextToCurrentGame()
    if APIIitegration: StartMatch(CurrentGame.get("GameNumber"))
    if pygame.mixer.music.get_busy:
            pygame.mixer.music.fadeout(500)
    if AutoInst:
        GameRunning = "AutoInst"
        CurrentVid = CurrentGameType
        PlayAVideo(CurrentVid)
        SpeakIt.put("Players please proceed to the far end of the field!")
        sleep(10)

    GameRunning = "Countdown"
    CurrentGame["GameStatus"] = GameRunning
    CurrentVid = "vCountdown"
    PlayAVideo(CurrentVid)
    pygame.mixer.Sound.play(Bell) 
    if CurrentGameType != "Sanction":
        GameToPlay = getRandomSong()
        pygame.mixer.music.load(GameToPlay)
        pygame.mixer.music.set_volume(1)
        CurrentGame["SongPlayed"] = SongData.title
        CurrentGame["ArtistPlayed"] = SongData.artist
    else:
        CurrentGame["SongPlayed"] = ""
        CurrentGame["ArtistPlayed"] = ""

    GameRunning = "Ready"
    CurrentGame["GameStatus"] = GameRunning
    GameStart = datetime.now()
    GameEnd = GameStart + timedelta(minutes = GameRunTime)
    CurrentGame["ActualStartTime"] = GameStart
    CurrentGame["ActualEndTime"] = GameEnd
    WriteGameToDB()

# What to do when a button is pressed
def ButtonPressed(channel):
    global CurrentVid
    global CurrentGameType
    global BackgroundMusic
    global BackgroundVol
    global AutoInst
    global APIIitegration
    global GameRunTime

    if DeBug: print("Button Pressed " + str(channel))
    if (GameRunning == "Playing") or ((datetime.now()-DelayScreen).total_seconds() <= 10):
    # if DeBug:
        #Scoring Controls
        if channel ==  pygame.K_q: Green_Hit_Up()
        elif channel ==  pygame.K_a: Green_Hit_Down()
        elif channel ==  pygame.K_e: Green_Catch_Up()
        elif channel ==  pygame.K_d: Green_Catch_Down()
        elif channel ==  pygame.K_w: Green_Spot_Up()
        elif channel ==  pygame.K_s: Green_Spot_Down()
        elif channel ==  pygame.K_r: Green_Penalty_Up()
        elif channel ==  pygame.K_f: Green_Penalty_Down()
        elif channel ==  pygame.K_LEFTBRACKET: Yellow_Hit_Up()
        elif channel ==  pygame.K_QUOTE: Yellow_Hit_Down()
        elif channel ==  pygame.K_o: Yellow_Catch_Up()
        elif channel ==  pygame.K_l: Yellow_Catch_Down()
        elif channel ==  pygame.K_p: Yellow_Spot_Up()
        elif channel ==  pygame.K_COLON: Yellow_Spot_Down()
        elif channel ==  pygame.K_i: Yellow_Penalty_Up()
        elif channel ==  pygame.K_k: Yellow_Penalty_Down()
        #elif channel ==  pygame.K_c: # Clear Scores
        #elif channel ==  pygame.K_f: # EarlyGameWin
        
    elif GameRunning in("No","Finished"):
        #Video Controls
        if channel ==  pygame.K_SPACE:   # Start Game
            StartGame()

        elif channel ==  pygame.K_RSHIFT: # Start Instructions
            CurrentVid = CurrentGameType
            PlayAVideo(CurrentVid)

        elif channel ==  pygame.K_RETURN: # Start Shooting Video
            CurrentVid="vShootInst"
            PlayAVideo(CurrentVid)

        elif channel ==  pygame.K_BACKSLASH: # Start Promo
            CurrentVid="vPromo"
            PlayAVideo(CurrentVid)
        
        #Configuration Controls
        elif channel == pygame.K_5: # Configure Elimination Game
            if CurrentGameType == "Normal":
                CurrentGameType = "Elimination"
                GameRunTime = DefaultGameRunTime

            elif CurrentGameType == "Elimination":
                CurrentGameType = "Sanction"
                GameRunTime = SanctionGameRunTime

            elif CurrentGameType == "Sanction":
                CurrentGameType = "Normal"
                GameRunTime = DefaultGameRunTime
            else:
                CurrentGameType = "Normal"
                GameRunTime = DefaultGameRunTime   
            SpeakIt.put(CurrentGameType)


         #Integration Controls
        elif channel ==  pygame.K_RIGHT: # Pull Next Game
            MinGameNumber = NextGame.get("GameNumber")
            GetNextGame(MinGameNumber)

        elif channel ==  pygame.K_UP: # Pull Previous Game
            GetNextGame(0)

        elif channel ==  pygame.K_DOWN: # Pull Data from Challonge
            if DeBug: print("Pull Data from Challonge")
            if APIIitegration: GetOrUpdateGames()
        #Toggle Controls
        elif channel ==  pygame.K_BACKSPACE: # Toggle Auto Instructions
            if AutoInst:
                AutoInst = False
                SpeakIt.put("Auto instructions off")
            else:
                AutoInst = True
                SpeakIt.put("Auto nstructions on")

        elif channel ==  pygame.K_3: # Toggle API integration

            if DeBug: print("Toggle Tournament integration")
            if APIIitegration:
                APIIitegration = False
                SpeakIt.put("Tournament integration off")
            else:
                APIIitegration = True
                SpeakIt.put("Tournament integration on")
        elif channel ==  pygame.K_7: # Toggle Between Game Music
            if BackgroundMusic:
                BackgroundMusic = False
            else:
                BackgroundMusic = True
        
        elif channel ==  pygame.K_9: # Toggle Between Game Music Volumn
            if BackgroundVol >= 1.0:
                BackgroundVol = .1
            else:
                BackgroundVol = BackgroundVol +.25
    
            pygame.mixer.music.set_volume(BackgroundVol)

    if ("Playing" in CurrentVid) or (not GameRunning in("No","Finished")):
        if channel ==  pygame.K_m: # Pause Game / Video
            PauseVid()
        #elif channel ==  pygame.K_3: # Stop Game / Video
            
    #Other Controls
    if channel ==  pygame.K_INSERT: # Quit System
        pygame.mixer.Sound.play(Close)  

def DrawScoreBoard():

    def DrawTeamScore(TeamColor,HStart,VStart,FontColor): 
        TeamName = TeamColor + "TeamName"
        if TeamColor == "Yellow":
            Team = YellowScores
            TeamLable = " Yellow:" 
            Text = CurrentGame.get("YellowTeamName")
        else:
            Team = GreenScores
            TeamLable =  "  Green:"
            Text = CurrentGame.get("GreenTeamName")

        indent = int(435 * ScreenScale)
        ls = int(68 * ScreenScale)
        x = int(HStart * ScreenScale)
        y = int(VStart * ScreenScale)
        
        Scores.render_to(screen,(x,y), TeamLable + Text, (FontColor))
        if CurrentGameType == "Normal":
            y = y + ls
            BigScore.render_to(screen,(x + indent * .5 , y+ (ls * 1.3) - ls), "Total", (FontColor))
            y = y + ls
            Text = str(Team.get("Total"))
            BigScore.render_to(screen,(x + indent * .5, y + (ls * 1.6) - ls ), "  " + Text, (FontColor))
        else:
            y = y + ls
            Text = str(Team.get("Hit"))
            Scores.render_to(screen,(x,y), "    Hit:" + Text, (FontColor))
            BigScore.render_to(screen,(x + indent , y+ (ls * 1.3) - ls), "Total", (FontColor))
            y = y + ls
            if CurrentGameType in ("Elimination"):
                Text = str(Team.get("Spot"))
                Scores.render_to(screen,(x,y), "   Spot:" + Text, (FontColor))
                y = y + ls
                Text = str(Team.get("Catch"))
                Scores.render_to(screen,(x,y), "  Catch:" + Text, (FontColor))
            else:
                Text = str(Team.get("Catch"))
                Scores.render_to(screen,(x,y), "  Catch:" + Text, (FontColor))
            Text = str(Team.get("Total"))
            BigScore.render_to(screen,(x + indent , y + (ls * 1.6) - ls ), "  " + Text, (FontColor))
            y = y + ls
            Text = str(Team.get("Penalty"))
            Scores.render_to(screen,(x,y), "Penalty:" + Text, (FontColor))

    Yellow = (253,214,48)
    Black = (0,0,0)
    Purple = (95,0,160)
    Red = (255,0,0)
    Timer = pygame.freetype.Font("Fonts/Moby-Bold.ttf", int(450 * ScreenScale))
    Scores = pygame.freetype.Font("Fonts/monofonto-rg.otf", int(75 * ScreenScale))
    BigScore = pygame.freetype.Font("Fonts/BAUHS93.TTF", int(105 * ScreenScale))
    GameInfo = pygame.freetype.Font("Fonts/ERASDEMI.TTF", int(75 * ScreenScale))
    SongInfo = pygame.freetype.Font("Fonts/ERASDEMI.TTF", int(30 * ScreenScale))
    
    if GameRunning in("No","Finished") and (datetime.now()-DelayScreen).total_seconds() > 10:
        screen.blit(pygame.transform.scale(DefaultBack, (SWidth, SHeight)), (0, 0))
        #Winner Box
        x = int(100 * ScreenScale)
        y = int(90 * ScreenScale)
        ls = int(68 * ScreenScale)
        FontColor = Yellow
        indent = int(45 * ScreenScale)
        if CurrentGame.get("GameStatus") == "Finished":
            GameInfo.render_to(screen,(x,y), "Winner:", (FontColor))
            y = y + ls
            if CurrentGame.get("GameWinner") == "Yellow":
                Text = CurrentGame.get("YellowTeamName")
            else:
                Text = CurrentGame.get("GreenTeamName")
            GameInfo.render_to(screen,(x + indent,y), Text, (FontColor))
            y = y + ls
            if CurrentGame.get("GameWinner") == "Yellow":
                Text = str(YellowScores.get("Total")) + " to " + str(GreenScores.get("Total"))
            else:
                Text = str(GreenScores.get("Total")) + " to " +  str(YellowScores.get("Total"))
            GameInfo.render_to(screen,(x + indent,y), "Total " + Text, (FontColor))
            y = y + ls
            if CurrentGameType in ("Elimination","Sanction"):
                Text = ""
                if CurrentGame.get("GameWinner") == "Yellow":
                    if CurrentGameType in ("Elimination"):
                        Text = Text + str(YellowScores.get("Hit")) + " Hits - "
                        Text = Text + str(YellowScores.get("Spot")) + " Spots - "
                        Text = Text + str(YellowScores.get("Catch")) + " Catches - "
                        Text = Text + str(YellowScores.get("Penalty")) + " Penalties - "
                        Text = Text + str(YellowScores.get("ExtraPoint")) + " Extra Point"
                    else:
                        Text = Text + str(YellowScores.get("Hit")) + " Hits - "
                        Text = Text + str(YellowScores.get("Catch")) + " Catches - "
                        Text = Text + str(YellowScores.get("Penalty")) + " Penalties"
                else:
                    if CurrentGameType in ("Elimination"):
                       Text = Text + str(GreenScores.get("Hit")) + " Hits - "
                       Text = Text + str(GreenScores.get("Spot")) + " Spots - "
                       Text = Text + str(GreenScores.get("Catch")) + " Catches - "
                       Text = Text + str(GreenScores.get("Penalty")) + " Penalties - "
                       Text = Text + str(GreenScores.get("ExtraPoint")) + " Extra Point"
                    else:
                       Text = Text + str(GreenScores.get("Hit")) + " Hits - "
                       Text = Text + str(GreenScores.get("Catch")) + " Catches - "
                       Text = Text + str(GreenScores.get("Penalty")) + " Penalties"
                SongInfo.render_to(screen,(x + indent,y), Text, (FontColor))

        else:
            y = y * 3

        #Next Game Info
        if NextGame.get("GameNumber") >= 0 \
            and NextGame.get("GreenTeamName") != "Green" \
            and NextGame.get("YellowTeamName") != "Yellow":
            
            y = y + ls * 2
            GameInfo.render_to(screen,(x,y), "Next Game:", (FontColor))
            y = y + ls * 1.2
            GameInfo.render_to(screen,(x,y), "Green:", (FontColor))
            y = y + ls
            Text = NextGame.get("GreenTeamName")
            GameInfo.render_to(screen,(x + indent,y), Text, (FontColor))
            y = y + ls * 1.2
            GameInfo.render_to(screen,(x,y), "Yellow:", (FontColor))
            y = y + ls
            Text = NextGame.get("YellowTeamName")
            GameInfo.render_to(screen,(x + indent,y), Text, (FontColor))

        x = int(800 * ScreenScale)
        y = int(1030 * ScreenScale)
        Text = CurrentGameType 
        SongInfo.render_to(screen,(x,y), Text, (Purple))
        if AutoInst:
            x = int(1100 * ScreenScale)
            SongInfo.render_to(screen,(x,y), "Auto Instructions", (Purple))
        if APIIitegration:
            x = int(1500 * ScreenScale)
            SongInfo.render_to(screen,(x,y), "Tournament Integration", (Purple))
    else:
        screen.blit(pygame.transform.scale(TimerBack, (SWidth, SHeight)), (0, 0))
        FontColor = Black
        if SecondsLeft < 0:
            FontColor = Red
            Ctr = strftime("%#M:%S", gmtime(SecondsLeft * -1))
        elif SecondsLeft <= 59:
            Ctr = "  " + strftime("%S", gmtime(SecondsLeft))
        else:
            Ctr = strftime("%#M:%S", gmtime(SecondsLeft))
        x = int(262 * ScreenScale)
        y = int(450 * ScreenScale)
        
        if SecondsLeft in (1,3,5,7,9):
            screen.blit(pygame.transform.scale(BlackTimerBack, (SWidth, SHeight)), (0, 0))
            FontColor = Yellow
        if GameRunning == "Pause":    
            Timer.render_to(screen, (x,y), Ctr, (Red))
        else:
            Timer.render_to(screen, (x,y), Ctr, (FontColor))
        
        DrawTeamScore("Yellow",60,40,FontColor)
        DrawTeamScore("Green",960,40,FontColor)

    #Song Info
    if pygame.mixer.music.get_busy():
        x = int(60 * ScreenScale)
        y = int(990 * ScreenScale)
        ls = int(30 * ScreenScale)
        Text = SongData.title
        SongInfo.render_to(screen,(x,y), "Song: " + Text, (FontColor))
        y = y + ls
        Text = SongData.artist
        SongInfo.render_to(screen,(x,y), "By: " + Text, (FontColor))

    pygame.display.flip()

def PlayAVideo(Video):
    global CurrentVid
    global HoldIt

    if pygame.mixer.music.get_busy():
        pygame.mixer.music.fadeout(5000)
    if Video == "vCountdown":
        if not vCountdown.active:
            vCountdown.resize((SWidth, SHeight))
            vCountdown.restart()
            vCountdown.play()
            CurrentVid = "Playing vCountdown"
        while vCountdown.active:
            vCountdown.draw(screen,(0,0))
            pygame.display.update()
            for event in pygame.event.get(): 
                if event.type == pygame.KEYDOWN: 
                    HoldIt = datetime.now()
                    if event.key ==  pygame.K_m: # Pause  Video
                        vCountdown.toggle_pause() 
                elif event.type == pygame.KEYUP: 
                    if  (datetime.now()-HoldIt).total_seconds() > 2:
                        if event.key == pygame.K_v:
                            vCountdown.stop()
                            pygame.mixer.Sound.play(Close)
        
    if Video == "Elimination":
        if not vEliminationInst.active:
            vEliminationInst.resize((SWidth, SHeight))
            vEliminationInst.restart()
            vEliminationInst.play()
            CurrentVid = "Playing Elimination"
        while vEliminationInst.active:
            vEliminationInst.draw(screen,(0,0))
            pygame.display.update()
            for event in pygame.event.get(): 
                if event.type == pygame.KEYDOWN: 
                    HoldIt = datetime.now()
                    if event.key ==  pygame.K_m: # Pause  Video
                        vEliminationInst.toggle_pause() 
                elif event.type == pygame.KEYUP: 
                    if  (datetime.now()-HoldIt).total_seconds() > 2:
                        if event.key == pygame.K_v:
                            vEliminationInst.stop()
                            pygame.mixer.Sound.play(Close)
        
    if Video == "Normal":
        if not vNormalInst.active:
            vNormalInst.resize((SWidth, SHeight))
            vNormalInst.restart()
            vNormalInst.play()
            CurrentVid = "Playing Normal"
        while vNormalInst.active:
            vNormalInst.draw(screen,(0,0))
            pygame.display.update()
            for event in pygame.event.get(): 
                if event.type == pygame.KEYDOWN: 
                    HoldIt = datetime.now()
                    if event.key ==  pygame.K_m: # Pause  Video
                        vNormalInst.toggle_pause() 
                elif event.type == pygame.KEYUP: 
                    if  (datetime.now()-HoldIt).total_seconds() > 2:
                        if event.key == pygame.K_v:
                            vNormalInst.stop()
                            pygame.mixer.Sound.play(Close)        
            
    if Video == "vPromo":
        if not vCountdown.active:
            vPromo.resize((SWidth, SHeight))
            vPromo.restart()
            vPromo.play()
            CurrentVid = "Playing vPromo"
        while vPromo.active:
            vPromo.draw(screen,(0,0))
            pygame.display.update()
            for event in pygame.event.get(): 
                if event.type == pygame.KEYDOWN: 
                    HoldIt = datetime.now()
                    if event.key ==  pygame.K_m: # Pause  Video
                        vPromo.toggle_pause() 
                elif event.type == pygame.KEYUP: 
                    if  (datetime.now()-HoldIt).total_seconds() > 2:
                        if event.key == pygame.K_v:
                            vPromo.stop()
                            pygame.mixer.Sound.play(Close)   

    if Video == "Sanction":
        if not vSanctionInst.active:
            vSanctionInst.resize((SWidth, SHeight))
            vSanctionInst.restart()
            vSanctionInst.play()
            CurrentVid = "Playing Sanction"
        while vSanctionInst.active:
            vSanctionInst.draw(screen,(0,0))
            pygame.display.update()
            for event in pygame.event.get(): 
                if event.type == pygame.KEYDOWN: 
                    HoldIt = datetime.now()
                    if event.key ==  pygame.K_m: # Pause  Video
                        vSanctionInst.toggle_pause() 
                elif event.type == pygame.KEYUP: 
                    if  (datetime.now()-HoldIt).total_seconds() > 2:
                        if event.key == pygame.K_v:
                            vSanctionInst.stop()
                            pygame.mixer.Sound.play(Close)   
        
    if Video == "vShootInst":
        if not vShootInst.active:
            vShootInst.resize((SWidth, SHeight))
            vShootInst.restart()
            vShootInst.play()
            CurrentVid = "Playing vShootInst"
        while vShootInst.active:
            vShootInst.draw(screen,(0,0))
            pygame.display.update()
            for event in pygame.event.get(): 
                if event.type == pygame.KEYDOWN: 
                    HoldIt = datetime.now()
                    if event.key ==  pygame.K_m: # Pause  Video
                        vShootInst.toggle_pause() 
                elif event.type == pygame.KEYUP: 
                    if  (datetime.now()-HoldIt).total_seconds() > 2:
                        if event.key == pygame.K_v:
                            vShootInst.stop()
                            pygame.mixer.Sound.play(Close) 

    vCountdown.resize((0,0))
    vEliminationInst.resize((0, 0))
    vNormalInst.resize((0,0))
    vPromo.resize((0, 0))
    vSanctionInst.resize((0, 0))
    vShootInst.resize((0, 0))
    CurrentVid = "None"
    DrawScoreBoard() 

if DeBug: PrintDeBug()

SpeakIt = queue.Queue()

tts_thread = TTSThread(SpeakIt)
SpeakIt.put("Welcome to Archery Tag by Sherwood Adventure.")

CurrentVid = "None"
vCountdown.resize((0,0))
vEliminationInst.resize((0, 0))
vNormalInst.resize((0,0))
vPromo.resize((0, 0))
vSanctionInst.resize((0, 0))
vShootInst.resize((0, 0))

GetNextGame()

DrawScoreBoard() 

WebGameThread()

while 1:

    for event in pygame.event.get(): 
        if event.type == pygame.KEYDOWN: 
            HoldIt = datetime.now()
            ButtonPressed(event.key)
        if event.type == pygame.KEYUP: 
           if  (datetime.now()-HoldIt).total_seconds() > 2:
               if event.key == pygame.K_v: #Stop the Game
                  StopVid()
                  pygame.mixer.Sound.play(Close)  
               elif event.key == pygame.K_h: #Early Game Win
                  if CurrentGameType == "Elimination":
                    pygame.mixer.Sound.play(EarlyWin)
                    EarlyWinGameEnd()
               elif event.key == pygame.K_ESCAPE:#Clear Scores
                  ResetScore()
                  pygame.mixer.Sound.play(Reset)                                                                                                       
               elif event.key == pygame.K_INSERT:#Stop it
                  WriteGameToDB()
                  # os.system("systemctl poweroff")
                  pygame.quit()
                  os._exit(1)
                  
    if GameRunning == "Ready": 
        GameRunning = "Playing"
        CurrentGame["GameStatus"] = GameRunning
        if CurrentGameType != "Sanction": 
            pygame.mixer.music.play()
            pygame.mixer.music.set_volume(1)
        WriteGameToDB()

    elif GameRunning == "Playing":
        SecondsLeft = int((GameEnd - datetime.now()).total_seconds())
        if SecondsLeft <= 30:
            if SecondsLeft != LastCountSec:
                if SecondsLeft == 15:
                    pygame.mixer.music.fadeout(10000)
                elif SecondsLeft == 10:
                    pygame.mixer.Sound.play(EndGame)
                elif SecondsLeft <= 0 and not ( CurrentGameType == "Elimination" and YellowScores.get("Total") == GreenScores.get("Total")   ):
                    DelayScreen = datetime.now()
                    pygame.mixer.Sound.play(Bell) 
                    GameRunning = "Stop"
                    CurrentGame["GameStatus"] = GameRunning
            if (SecondsLeft == -1) and (not AnnouncedOvertime):
                SpeakIt.put("Game Tied.")
                SpeakIt.put("Next out wins!")
                AnnouncedOvertime = True
            LastCountSec = SecondsLeft
               
        else:
            #if song was not long enough
            if CurrentGameType != "Sanction":
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                    pygame.mixer.music.set_volume(1)
                    GameToPlay = getRandomSong()
                    pygame.mixer.music.load(GameToPlay)
                    CurrentGame["SongPlayed"] =  CurrentGame.get("SongPlayed") + "|" + SongData.title
                    CurrentGame["ArtistPlayed"] = CurrentGame.get("ArtistPlayed") + "|" + SongData.artist
                    pygame.mixer.music.play()
                    WriteGameToDB()
        DrawScoreBoard() 
    
    elif GameRunning == "Stop":
        if (datetime.now()-DelayScreen).total_seconds() > 10:
            GameRunning = "Finished"
            CurrentGame["GameStatus"] = GameRunning
            NormalGameEnd()
    
    elif GameRunning == "Pause":
        SecondsLeft = int((GameEnd - datetime.now()).total_seconds())
        if SecondsLeft != SecondsPaused:
           GameEnd = GameEnd + timedelta(seconds = 1)
           CurrentGame["ActualEndTime"] = GameEnd
           SecondsPaused = SecondsLeft + 1
   
    if CurrentVid == "None":        
        DrawScoreBoard()

    if (BackgroundMusic) and (CurrentVid == "None") and (GameRunning in("No","Finished")): 
        if not pygame.mixer.music.get_busy():
            BackgroundSong = getRandomSong()
            pygame.mixer.music.load(BackgroundSong)
            pygame.mixer.music.set_volume(BackgroundVol)
            pygame.mixer.music.play()
    elif not BackgroundMusic:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
    

    pygame.display.update() 
    
    #Leave some CPU for others....
    sleep(0.1)           
  
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
 
  
  
  
  


   
  
        
   
        
 
  
  
  
  


   
  
        
    
        
        
        
        
        
        
        
        
 
  
  
  
  


   
  
        
      
        
        
 
  
  
  
  


   
  
        


   
  
        


   


   
  
        


   


   
  
        


      



    
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
 
  
  
  
  


   
  
        
   
        
 
  
  
  
  


   
  
        
    
        
        
        
        
        
        
        
        
 
  
  
  
  


   
  
        
      
        
        
 
  
  
  
  


   
  
        


   
  
        


   


   
  
        


   


   
  
        


      





   
        
        
        
        
 
  
  
  
  


   
  
        
      
        
        
 
  
  
  
  


   
  
        


   
  
        


   


   
  
        


   


   
  
        


      






        


   


   
  
        


      





   
        
        
        
        
 
  
  
  
  


   
  
        
      
        
        
 
  
  
  
  


   
  
        


   
  
        


   


   
  
        


   


   
  
        


      





     


      








 








  


      








 











 

















  


      








 











 











