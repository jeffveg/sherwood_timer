#!/usr/bin/env python

# Import stuff
import threading
import sys 
from time import sleep, strftime, gmtime
from datetime import datetime,timedelta
from os.path import join
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
from SyncWithSherwood import *
import SyncWithSherwood
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO, emit
import logging

DeBug = False

if len(sys.argv) == 2:
    arg = sys.argv[1]
    if arg == "-D":
        DeBug = True

# Stuff to pull from config
SongList            = "SongList/EDM"
DefaultGameRunTime  = 5
SanctionGameRunTime = 8

path = join("SherwoodTimer", os.getcwd() )
if DeBug: print("Program Root " + path + " | SongList " + SongList )

# --- Logging Setup ---
def setup_logging():
    log_dir = join(path, 'Gamerecordings')
    os.makedirs(log_dir, exist_ok=True)
    _logger = logging.getLogger('sherwood')
    _logger.setLevel(logging.DEBUG)
    log_filename = join(log_dir, 'error_' + datetime.now().strftime('%Y-%m-%d') + '.log')
    fh = logging.FileHandler(log_filename)
    fh.setLevel(logging.ERROR)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                       datefmt='%Y-%m-%d %H:%M:%S'))
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                       datefmt='%Y-%m-%d %H:%M:%S'))
    _logger.addHandler(fh)
    _logger.addHandler(ch)
    return _logger

logger = setup_logging()

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
OutdoorMode      = False
AutoInst         = False 
APIIitegration   = False
AnnouncedOvertime = False

NormalScoreValues = {
"Hit"       : 1,
"Catch"     : 2,
"Spot"      : 1,
"Penalty"   : -1,
"ExtraPoint": 1
}

TournamentScoreValues = {
"Hit"       : 1,
"Catch"     : 3,
"Spot"      : 0,
"Penalty"   : -2,
"ExtraPoint": 0
}

ScoreValues = dict(NormalScoreValues)

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

# Reference resolution — all hardcoded coordinates were designed for 1920x1080.
# ScaleX/ScaleY let us place everything proportionally on ANY screen size.
REF_W = 1920.0
REF_H = 1080.0
ScaleX = SWidth / REF_W
ScaleY = SHeight / REF_H

DefaultBack = pygame.transform.scale(
    pygame.image.load(join(path,"Images/DefaultBack.jpg")), (SWidth, SHeight))
TimerBack = pygame.transform.scale(
    pygame.image.load(join(path,"Images/TimerBack2.bmp")), (SWidth, SHeight))
BlackTimerBack = pygame.transform.scale(
    pygame.image.load(join(path,"Images/BlackTimerBack.jpg")), (SWidth, SHeight))
Logo = pygame.image.load(join(path,"Images/logo.png"))
screen.blit(pygame.transform.scale(Logo, (SWidth, SHeight)), (0, 0))
pygame.display.flip()

# --- Pre-load fonts (scaled to actual screen, loaded ONCE not every frame) ---
FONT_TIMER    = pygame.freetype.Font("Fonts/Moby-Bold.ttf", int(450 * ScaleY))
FONT_SCORES   = pygame.freetype.Font("Fonts/monofonto-rg.otf", int(75 * ScaleY))
FONT_BIG      = pygame.freetype.Font("Fonts/BAUHS93.TTF", int(105 * ScaleY))
FONT_GAME     = pygame.freetype.Font("Fonts/ERASDEMI.TTF", int(75 * ScaleY))
FONT_SONG     = pygame.freetype.Font("Fonts/ERASDEMI.TTF", int(30 * ScaleY))

# --- Color constants ---
CLR_YELLOW = (253, 214, 48)
CLR_BLACK  = (0, 0, 0)
CLR_PURPLE = (95, 0, 160)
CLR_RED    = (255, 0, 0)

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
        try:
            tts_engine = pyttsx3.init()
            tts_engine.startLoop(False)
            voices = tts_engine.getProperty("voices")
            if len(voices) > 1:
                tts_engine.setProperty("voice", voices[1].id)
            elif len(voices) > 0:
                tts_engine.setProperty("voice", voices[0].id)
            tts_engine.setProperty("rate", 150)

            # Volume ducking callbacks — lower music when TTS speaks
            def on_start(name):
                try:
                    pygame.mixer.music.set_volume(0.15)
                except Exception:
                    pass

            def on_end(name, completed):
                try:
                    if GameRunning == "Playing":
                        pygame.mixer.music.set_volume(1.0)
                    else:
                        pygame.mixer.music.set_volume(BackgroundVol)
                except Exception:
                    pass

            tts_engine.connect('started-utterance', on_start)
            tts_engine.connect('finished-utterance', on_end)

            t_running = True
            while t_running:
                try:
                    if self.queue.empty():
                        tts_engine.iterate()
                    else:
                        data = self.queue.get()
                        if data == "exit":
                            t_running = False
                        else:
                            tts_engine.say(data)
                except Exception as error:
                    logger.error("TTS iteration error: %s", error)
            tts_engine.endLoop()
        except Exception as error:
            logger.error("TTS engine initialization failed: %s", error)


# Thread for score Web (Flask + SocketIO)
class WebGameThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True

        # Suppress Flask/Werkzeug request logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        self.app = Flask(__name__,
                         template_folder=join(path, 'web', 'templates'),
                         static_folder=join(path, 'web', 'static'))
        self.app.config['SECRET_KEY'] = 'sherwood-timer-secret'
        self.socketio = SocketIO(self.app,
                                  async_mode='threading',
                                  cors_allowed_origins='*')
        self._setup_routes()
        self._setup_socketio_events()
        self.start()

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html')

        @self.app.route('/scoreboard')
        def scoreboard():
            return render_template('scoreboard.html')

        @self.app.route('/admin')
        def admin():
            return render_template('admin.html')

        @self.app.route('/games')
        def games():
            return render_template('games.html')

        @self.app.route('/favicon.ico')
        def favicon():
            return send_from_directory(join(path, 'web'), 'favicon.ico', mimetype='image/x-icon')

    def _setup_socketio_events(self):
        @self.socketio.on('connect')
        def handle_connect():
            emit('state_update', self._get_full_state())

        @self.socketio.on('score_action')
        def handle_score(data):
            action = data.get('action', '')
            success = False
            # Game control actions (pause/stop work during play, start when idle)
            if action == 'PAUSE' and GameRunning in ("Playing", "Pause"):
                PauseVid()
                success = True
            elif action == 'STOP' and GameRunning in ("Playing", "Pause"):
                StopVid()
                pygame.mixer.Sound.play(Close)
                success = True
            elif action == 'START' and GameRunning in ("No", "Finished"):
                StartGame()
                success = True
            elif action == 'EARLYWIN' and GameRunning == "Playing" and CurrentGameType == "Elimination":
                pygame.mixer.Sound.play(EarlyWin)
                EarlyWinGameEnd()
                success = True
            elif GameRunning == "Playing":
                score_map = {
                    'GHU': Green_Hit_Up,    'GHD': Green_Hit_Down,
                    'GSU': Green_Spot_Up,   'GSD': Green_Spot_Down,
                    'GCU': Green_Catch_Up,  'GCD': Green_Catch_Down,
                    'GPU': Green_Penalty_Up,'GPD': Green_Penalty_Down,
                    'YHU': Yellow_Hit_Up,   'YHD': Yellow_Hit_Down,
                    'YSU': Yellow_Spot_Up,  'YSD': Yellow_Spot_Down,
                    'YCU': Yellow_Catch_Up, 'YCD': Yellow_Catch_Down,
                    'YPU': Yellow_Penalty_Up,'YPD': Yellow_Penalty_Down,
                }
                func = score_map.get(action)
                if func:
                    func()
                    success = True
            elif action == 'TT':
                global APIIitegration
                if APIIitegration:
                    APIIitegration = False
                    SyncWithSherwood.selected_tournament_number = None
                    SpeakIt.put("Tournament integration off")
                    success = True
                else:
                    tournaments = ListTournaments()
                    if tournaments:
                        emit('tournament_list', {'tournaments': tournaments})
                        success = True
                    else:
                        SpeakIt.put("No active tournaments found")
            else:
                ctrl_map = {
                    'GT': pygame.K_5,       'NG': pygame.K_RIGHT,
                    'FG': pygame.K_UP,      'RD': pygame.K_DOWN,
                    'AI': pygame.K_BACKSPACE,
                    'TM': pygame.K_7,       'MV': pygame.K_9,
                }
                key = ctrl_map.get(action)
                if key:
                    ButtonPressed(key)
                    success = True
            emit('score_ack', {'action': action, 'success': success})
            # Broadcast updated state to ALL clients immediately
            self.socketio.emit('state_update', self._get_full_state())

        @self.socketio.on('request_state')
        def handle_request_state():
            emit('state_update', self._get_full_state())

        @self.socketio.on('select_tournament')
        def handle_select_tournament(data):
            global APIIitegration
            tournament_number = data.get('tournament_number', '')
            game_type_override = data.get('game_type_override', '')
            if tournament_number:
                SyncWithSherwood.selected_tournament_number = tournament_number
                APIIitegration = True
                SpeakIt.put("Tournament integration on")
                GetOrUpdateGames()
                if game_type_override:
                    _apply_game_type_override(tournament_number, game_type_override)
                # Skip past any default placeholder games to the first tournament game
                _skip_default_games()
                GetNextGame()
            else:
                APIIitegration = False
                SyncWithSherwood.selected_tournament_number = None
            self.socketio.emit('state_update', self._get_full_state())

        @self.socketio.on('request_games_list')
        def handle_request_games_list():
            """Return all games from the database for the games picker page."""
            games_list = _get_games_list()
            emit('games_list', {
                'games': games_list,
                'nextGameNumber': NextGame.get('GameNumber', 0)
            })

        @self.socketio.on('set_next_game')
        def handle_set_next_game(data):
            """Set a specific game as the next game by its GameNumber."""
            game_number = data.get('game_number', 0)
            if game_number > 0:
                _set_specific_next_game(game_number)
                self.socketio.emit('state_update', self._get_full_state())
                # Also refresh the games list for all clients on the games page
                games_list = _get_games_list()
                self.socketio.emit('games_list', {
                    'games': games_list,
                    'nextGameNumber': NextGame.get('GameNumber', 0)
                })

        @self.socketio.on('admin_update')
        def handle_admin_update(data):
            global ScoreValues, SongList, DefaultGameRunTime, SanctionGameRunTime, GameRunTime, OutdoorMode
            setting = data.get('setting', '')
            value = data.get('value')
            success = False
            try:
                if setting == 'scoreHit':
                    ScoreValues['Hit'] = int(value)
                    success = True
                elif setting == 'scoreCatch':
                    ScoreValues['Catch'] = int(value)
                    success = True
                elif setting == 'scoreSpot':
                    ScoreValues['Spot'] = int(value)
                    success = True
                elif setting == 'scorePenalty':
                    ScoreValues['Penalty'] = int(value)
                    success = True
                elif setting == 'scoreExtra':
                    ScoreValues['ExtraPoint'] = int(value)
                    success = True
                elif setting == 'songList':
                    songDir = join(path, 'SongList', str(value))
                    if os.path.isdir(songDir):
                        SongList = 'SongList/' + str(value)
                        success = True
                elif setting == 'defaultRunTime':
                    val = int(value)
                    if val > 0:
                        DefaultGameRunTime = val
                        # Update current GameRunTime if applicable
                        if CurrentGameType in ("Normal", "Tournament", "Elimination"):
                            GameRunTime = DefaultGameRunTime
                        success = True
                elif setting == 'sanctionRunTime':
                    val = int(value)
                    if val > 0:
                        SanctionGameRunTime = val
                        if CurrentGameType == "Sanction":
                            GameRunTime = SanctionGameRunTime
                        success = True
                elif setting == 'outdoorMode':
                    OutdoorMode = bool(value)
                    success = True
            except (ValueError, TypeError):
                success = False
            emit('admin_ack', {'setting': setting, 'success': success})
            self.socketio.emit('state_update', self._get_full_state())

    def broadcast_state(self):
        """Called from main loop to push state to all connected clients."""
        self.socketio.emit('state_update', self._get_full_state())

    def _get_full_state(self):
        """Snapshot all global state into a dict for the client."""
        return {
            'gameRunning': GameRunning,
            'currentGameType': CurrentGameType,
            'secondsLeft': SecondsLeft,
            'greenScores': dict(GreenScores),
            'yellowScores': dict(YellowScores),
            'currentGame': {
                'GameNumber': CurrentGame.get('GameNumber', 0),
                'GreenTeamName': CurrentGame.get('GreenTeamName', ''),
                'YellowTeamName': CurrentGame.get('YellowTeamName', ''),
                'GameType': CurrentGame.get('GameType', ''),
                'GameStatus': CurrentGame.get('GameStatus', ''),
                'GameWinner': CurrentGame.get('GameWinner', ''),
                'GameEarlyStopReason': CurrentGame.get('GameEarlyStopReason', ''),
            },
            'nextGame': {
                'GameNumber': NextGame.get('GameNumber', 0),
                'GreenTeamName': NextGame.get('GreenTeamName', ''),
                'YellowTeamName': NextGame.get('YellowTeamName', ''),
            },
            'backgroundMusic': BackgroundMusic,
            'backgroundVol': int(BackgroundVol * 100),
            'autoInst': AutoInst,
            'apiIntegration': APIIitegration,
            'selectedTournament': SyncWithSherwood.selected_tournament_number or '',
            'scoreValues': dict(ScoreValues),
            'songList': SongList,
            'defaultGameRunTime': DefaultGameRunTime,
            'sanctionGameRunTime': SanctionGameRunTime,
            'songListOptions': sorted([d for d in os.listdir(join(path, 'SongList'))
                                       if os.path.isdir(join(path, 'SongList', d))]),
            'outdoorMode': OutdoorMode,
        }

    def run(self):
        self.socketio.run(self.app, host='0.0.0.0', port=80,
                          allow_unsafe_werkzeug=True)


# Periodic sync thread — handles live score pushes, pending upload retries,
# and tournament re-sync for forfeits / team name changes
class APISyncThread(threading.Thread):

    LIVE_SCORE_INTERVAL = 10    # seconds between live score pushes
    RESYNC_INTERVAL = 30        # seconds between full tournament re-syncs
    RETRY_INTERVAL = 15         # seconds between pending upload retries

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self._tick = 0
        self.start()

    def run(self):
        while True:
            try:
                sleep(1)
                self._tick += 1

                if not APIIitegration:
                    continue

                # Push live scores every LIVE_SCORE_INTERVAL seconds
                if self._tick % self.LIVE_SCORE_INTERVAL == 0:
                    if GameRunning in ("Playing", "Pause"):
                        SyncWithSherwood._push_live_scores()

                # Retry pending final score uploads
                if self._tick % self.RETRY_INTERVAL == 0:
                    remaining = RetryPendingUploads()
                    if remaining > 0:
                        logger.info("APISyncThread: %d uploads still pending", remaining)

                # Re-sync tournament data to catch forfeits & name changes
                if self._tick % self.RESYNC_INTERVAL == 0:
                    if GameRunning not in ("Playing", "Pause"):
                        old_next = NextGame.get("GameNumber", 0)
                        GetOrUpdateGames()
                        # If current next game was skipped (forfeit), advance
                        _check_next_game_still_valid(old_next)

            except Exception as error:
                logger.error("APISyncThread error: %s", error)


def _check_next_game_still_valid(old_next_game_number):
    """If the current NextGame was skipped by a re-sync (forfeit), advance."""
    conn = None
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute("SELECT GameStatus FROM Games WHERE GameNumber = ?;",
                    (old_next_game_number,))
        row = cur.fetchone()
        if row and row[0] in ("Skipped", "Finished"):
            logger.info("Next game #%s was skipped/finished by sync, advancing", old_next_game_number)
            GetNextGame()
    except Exception as error:
        logger.error("_check_next_game_still_valid error: %s", error)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _apply_game_type_override(tournament_number, game_type):
    """Override the GameType for all games in a tournament."""
    conn = None
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute(
            "UPDATE Games SET GameType = ? WHERE AltTournmentNum = ? AND GameStatus = 'Not Started';",
            (game_type, tournament_number)
        )
        conn.commit()
        if DeBug:
            print("Game type override: set %s games to %s" % (cur.rowcount, game_type))
    except Exception as error:
        logger.error("_apply_game_type_override error: %s", error)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _get_games_list():
    """Return all games from the database for the games picker page."""
    conn = None
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute(
            "SELECT GameNumber, AltGameNum, GroupNum, RoundNum,"
            " GreenTeamName, YellowTeamName, GameType, GameStatus,"
            " GreenTotalScore, YellowTotalScore, GameWinner"
            " FROM Games"
            " ORDER BY GroupNum ASC, RoundNum ASC, GameNumber ASC;"
        )
        rows = cur.fetchall()
        games = []
        for row in rows:
            games.append({
                'gameNumber': row[0],
                'altGameNum': row[1] or '',
                'groupNum': row[2] or 0,
                'roundNum': row[3] or 0,
                'greenTeamName': str(row[4] or 'Green'),
                'yellowTeamName': str(row[5] or 'Yellow'),
                'gameType': row[6] or 'Normal',
                'gameStatus': row[7] or 'Not Started',
                'greenScore': row[8] or 0,
                'yellowScore': row[9] or 0,
                'gameWinner': row[10] or ''
            })
        return games
    except Exception as error:
        logger.error("_get_games_list error: %s", error)
        return []
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _set_specific_next_game(game_number):
    """Set a specific game as the next game by directly loading it."""
    global NextGame, CurrentGameType, GameRunTime
    conn = None
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute(
            "SELECT GameNumber, AltGameNum, AltTournmentSystem,"
            " GreenTeamName, GreenTeamNum, AltGreenTeamNum,"
            " YellowTeamName, YellowTeamNum, AltYellowTeamNum,"
            " GameType, ScheduledStartTime"
            " FROM Games WHERE GameNumber = ?;", (game_number,)
        )
        row = cur.fetchone()
        if row is None:
            logger.error("_set_specific_next_game: No game found for GameNumber %s", game_number)
            return

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

        # Ensure score records exist
        try:
            cur.execute("SELECT count(*) FROM Scores WHERE Side = 'Yellow' AND GameNumber = ?;", (game_number,))
            cnt = cur.fetchone()
            if cnt[0] == 0:
                cur.execute("INSERT INTO Scores (GameNumber,Side) VALUES (?,'Yellow');", (game_number,))
                conn.commit()
            cur.execute("SELECT count(*) FROM Scores WHERE Side = 'Green' AND GameNumber = ?;", (game_number,))
            cnt = cur.fetchone()
            if cnt[0] == 0:
                cur.execute("INSERT INTO Scores (GameNumber,Side) VALUES (?,'Green');", (game_number,))
                conn.commit()
        except Exception as error:
            logger.error("_set_specific_next_game: Score record error - %s", error)

    except Exception as error:
        logger.error("_set_specific_next_game error: %s", error)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    # Update game type and score values
    CurrentGameType = NextGame.get("GameType")
    if CurrentGameType == "Normal":
        GameRunTime = DefaultGameRunTime
        ScoreValues.update(NormalScoreValues)
    elif CurrentGameType == "Tournament":
        GameRunTime = DefaultGameRunTime
        ScoreValues.update(TournamentScoreValues)
    elif CurrentGameType == "Elimination":
        GameRunTime = DefaultGameRunTime
        ScoreValues.update(NormalScoreValues)
    elif CurrentGameType == "Sanction":
        GameRunTime = SanctionGameRunTime
        ScoreValues.update(NormalScoreValues)
    else:
        GameRunTime = DefaultGameRunTime
        ScoreValues.update(NormalScoreValues)


def _skip_default_games():
    """Mark any 'Not Started' placeholder games (Green vs Yellow) as Skipped
    so GetNextGame() advances to the first real tournament game."""
    conn = None
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        cur.execute(
            "SELECT GameNumber, GreenTeamName, YellowTeamName FROM Games"
            " WHERE GameStatus = 'Not Started'"
            " ORDER BY GroupNum ASC, RoundNum ASC, GameNumber ASC;"
        )
        rows = cur.fetchall()
        for row in rows:
            gNum, gName, yName = row[0], row[1], row[2]
            if gName == "Green" or yName == "Yellow":
                cur.execute("UPDATE Games SET GameStatus = 'Skipped' WHERE GameNumber = ?;", (gNum,))
                conn.commit()
            else:
                break
    except Exception as error:
        logger.error("_skip_default_games error: %s", error)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def GetNextGame(MinGameNumber=-1):
    global CurrentGame
    global NextGame
    global CurrentGameType
    global GameRunTime
    conn = None
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()
        if MinGameNumber > 0:
            # Advancing past a specific game — find the next one in group/round order
            cur.execute("SELECT GroupNum, RoundNum FROM Games WHERE GameNumber = ?;", (MinGameNumber,))
            skip_row = cur.fetchone()
            if skip_row:
                sg = skip_row[0] or 0
                sr = skip_row[1] or 0
                cur.execute(
                    "SELECT GameNumber FROM Games WHERE GameStatus = 'Not Started'"
                    " AND (GroupNum > ? OR (GroupNum = ? AND RoundNum > ?)"
                    " OR (GroupNum = ? AND RoundNum = ? AND GameNumber > ?))"
                    " ORDER BY GroupNum ASC, RoundNum ASC, GameNumber ASC LIMIT 1;",
                    (sg, sg, sr, sg, sr, MinGameNumber)
                )
            else:
                cur.execute(
                    "SELECT GameNumber FROM Games WHERE GameStatus = 'Not Started'"
                    " ORDER BY GroupNum ASC, RoundNum ASC, GameNumber ASC LIMIT 1;"
                )
        else:
            cur.execute(
                "SELECT GameNumber FROM Games WHERE GameStatus = 'Not Started'"
                " ORDER BY GroupNum ASC, RoundNum ASC, GameNumber ASC LIMIT 1;"
            )
        row = cur.fetchone()
        if row is None or row[0] is None:
            cur.execute("INSERT INTO Games (GameStatus) VALUES ('Not Started');")
            conn.commit()
            cur.execute(
                "SELECT GameNumber FROM Games WHERE GameStatus = 'Not Started'"
                " ORDER BY GroupNum ASC, RoundNum ASC, GameNumber ASC LIMIT 1;"
            )
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

        # Ensure score records exist
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
            logger.error("Database Error: Checking Score Record exists - %s", error)

    except Exception as error:
        logger.error("Database Error: Could not get game - %s", error)
        NextGame["GameNumber"] = -1
        NextGame["GreenTeamName"] = "Green"
        NextGame["YellowTeamName"] = "Yellow"
        NextGame["GameType"] = "Normal"
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    if DeBug: 
        print("Next Game:")
        print(NextGame)
        print("---------------------------------")
    CurrentGameType = NextGame.get("GameType")
    if CurrentGameType == "Normal":
        GameRunTime = DefaultGameRunTime
        ScoreValues.update(NormalScoreValues)

    elif CurrentGameType == "Tournament":
        GameRunTime = DefaultGameRunTime
        ScoreValues.update(TournamentScoreValues)

    elif CurrentGameType == "Elimination":
        GameRunTime = DefaultGameRunTime
        ScoreValues.update(NormalScoreValues)

    elif CurrentGameType == "Sanction":
        GameRunTime = SanctionGameRunTime
        ScoreValues.update(NormalScoreValues)
    else:
        GameRunTime = DefaultGameRunTime
        ScoreValues.update(NormalScoreValues)

def WriteGameToDB():
    conn = None
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()

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
                        ,pGameNumber
                        )
                    )
        conn.commit()

        #Green Scores
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
                        ,pGameNumber
                        )
                    )
        conn.commit()
    except Exception as error:
        logger.error("Database Error: Saving Game - %s", error)
        return 0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return 1

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

    # Flag live scores as dirty so the periodic sync thread pushes them
    if APIIitegration and GameRunning in ("Playing", "Pause"):
        MarkLiveScoreDirty(
            CurrentGame.get("GameNumber"),
            GreenScores.get("Total", 0),
            YellowScores.get("Total", 0)
        )

def Green_Hit_Up():
    ChangeScore(GreenScores,"Hit","Up")
    pygame.mixer.Sound.play(Buzzer)

def Green_Hit_Down():
    ChangeScore(GreenScores,"Hit","Down")
    pygame.mixer.Sound.play(Ding)  

def Green_Catch_Up():
    if CurrentGameType in ("Elimination","Sanction","Tournament"):
        ChangeScore(GreenScores,"Catch","Up")
        pygame.mixer.Sound.play(Ding)  

def Green_Catch_Down():
    if CurrentGameType in ("Elimination","Sanction","Tournament"):
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
    if CurrentGameType in ("Elimination","Sanction","Tournament"):
        ChangeScore(GreenScores,"Penalty","Up")
        pygame.mixer.Sound.play(Buzzer)

def Green_Penalty_Down():
    if CurrentGameType in ("Elimination","Sanction","Tournament"):
        ChangeScore(GreenScores,"Penalty","Down")
        pygame.mixer.Sound.play(Ding)
    
def Yellow_Hit_Up():
    ChangeScore(YellowScores,"Hit","Up")
    pygame.mixer.Sound.play(Buzzer)

def Yellow_Hit_Down():
    ChangeScore(YellowScores,"Hit","Down")
    pygame.mixer.Sound.play(Ding)

def Yellow_Catch_Up():
    if CurrentGameType in ("Elimination","Sanction","Tournament"):
        ChangeScore(YellowScores,"Catch","Up")
        pygame.mixer.Sound.play(Ding)

def Yellow_Catch_Down():
    if CurrentGameType in ("Elimination","Sanction","Tournament"):
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
    if CurrentGameType in ("Elimination","Sanction","Tournament"):
        ChangeScore(YellowScores,"Penalty","Up")
        pygame.mixer.Sound.play(Buzzer)

def Yellow_Penalty_Down():
    if CurrentGameType in ("Elimination","Sanction","Tournament"):
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
            attempts += 1
        else:
            break
    if APIIitegration:
        gameNum = CurrentGame.get("GameNumber")
        logger.info("Upload to API game %s", gameNum)
        result = UploadScores(gameNum)
        if result != 1:
            # Connection failed — queue for retry by the sync thread
            QueueUpload(gameNum)
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

    try:
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
    except Exception as error:
        logger.error("getRandomSong error: %s", error)
        return None

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
        elif channel == pygame.K_5: # Configure Game Type
            if CurrentGameType == "Normal":
                CurrentGameType = "Tournament"
                GameRunTime = DefaultGameRunTime
                ScoreValues.update(TournamentScoreValues)

            elif CurrentGameType == "Tournament":
                CurrentGameType = "Elimination"
                GameRunTime = DefaultGameRunTime
                ScoreValues.update(NormalScoreValues)

            elif CurrentGameType == "Elimination":
                CurrentGameType = "Sanction"
                GameRunTime = SanctionGameRunTime

            elif CurrentGameType == "Sanction":
                CurrentGameType = "Normal"
                GameRunTime = DefaultGameRunTime
            else:
                CurrentGameType = "Normal"
                GameRunTime = DefaultGameRunTime
                ScoreValues.update(NormalScoreValues)
            SpeakIt.put(CurrentGameType)


         #Integration Controls
        elif channel ==  pygame.K_RIGHT: # Pull Next Game
            MinGameNumber = NextGame.get("GameNumber")
            GetNextGame(MinGameNumber)

        elif channel ==  pygame.K_UP: # Pull Previous Game
            GetNextGame(0)

        elif channel ==  pygame.K_DOWN: # Pull Data from Sherwood
            if DeBug: print("Pull Data from Sherwood")
            if APIIitegration: GetOrUpdateGames()
        #Toggle Controls
        elif channel ==  pygame.K_BACKSPACE: # Toggle Auto Instructions
            if AutoInst:
                AutoInst = False
                SpeakIt.put("Auto instructions off")
            else:
                AutoInst = True
                SpeakIt.put("Auto Instructions on")

        elif channel ==  pygame.K_3: # Toggle API integration
            if DeBug: print("Toggle Tournament integration")
            if APIIitegration:
                APIIitegration = False
                SyncWithSherwood.selected_tournament_number = None
                SpeakIt.put("Tournament integration off")
            else:
                tournaments = ListTournaments()
                if tournaments:
                    if len(tournaments) == 1:
                        SyncWithSherwood.selected_tournament_number = tournaments[0]['tournament_number']
                        APIIitegration = True
                        SpeakIt.put("Tournament integration on. " + tournaments[0].get('name', ''))
                        GetOrUpdateGames()
                        _skip_default_games()
                        GetNextGame()
                    else:
                        web_thread.socketio.emit('tournament_list', {'tournaments': tournaments})
                        SpeakIt.put("Select a tournament")
                else:
                    SpeakIt.put("No active tournaments found")
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
    # All coordinates below are in 1920x1080 "reference" space.
    # ScaleX/ScaleY convert them to the actual screen resolution.

    def DrawTeamScore(TeamColor, HStart, VStart, FontColor):
        if TeamColor == "Yellow":
            Team = YellowScores
            TeamLable = " Yellow:"
            Text = str(CurrentGame.get("YellowTeamName") or "Yellow")
        else:
            Team = GreenScores
            TeamLable =  "  Green:"
            Text = str(CurrentGame.get("GreenTeamName") or "Green")

        indent = int(435 * ScaleX)
        ls = int(68 * ScaleY)
        x = int(HStart * ScaleX)
        y = int(VStart * ScaleY)

        FONT_SCORES.render_to(screen, (x, y), TeamLable + Text, FontColor)
        if CurrentGameType == "Normal":
            y = y + ls
            FONT_BIG.render_to(screen, (x + indent * .5, y + (ls * 1.3) - ls), "Total", FontColor)
            y = y + ls
            Text = str(Team.get("Total"))
            FONT_BIG.render_to(screen, (x + indent * .5, y + (ls * 1.6) - ls), "  " + Text, FontColor)
        else:
            y = y + ls
            Text = str(Team.get("Hit"))
            FONT_SCORES.render_to(screen, (x, y), "    Hit:" + Text, FontColor)
            FONT_BIG.render_to(screen, (x + indent, y + (ls * 1.3) - ls), "Total", FontColor)
            y = y + ls
            if CurrentGameType in ("Elimination"):
                Text = str(Team.get("Spot"))
                FONT_SCORES.render_to(screen, (x, y), "   Spot:" + Text, FontColor)
                y = y + ls
                Text = str(Team.get("Catch"))
                FONT_SCORES.render_to(screen, (x, y), "  Catch:" + Text, FontColor)
            else:
                Text = str(Team.get("Catch"))
                FONT_SCORES.render_to(screen, (x, y), "  Catch:" + Text, FontColor)
            Text = str(Team.get("Total"))
            FONT_BIG.render_to(screen, (x + indent, y + (ls * 1.6) - ls), "  " + Text, FontColor)
            y = y + ls
            Text = str(Team.get("Penalty"))
            FONT_SCORES.render_to(screen, (x, y), "Penalty:" + Text, FontColor)

    if GameRunning in("No","Finished") and (datetime.now()-DelayScreen).total_seconds() > 10:
        screen.blit(DefaultBack, (0, 0))
        #Winner Box
        x = int(100 * ScaleX)
        y = int(90 * ScaleY)
        ls = int(68 * ScaleY)
        FontColor = CLR_YELLOW
        indent = int(45 * ScaleX)
        if CurrentGame.get("GameStatus") == "Finished":
            FONT_GAME.render_to(screen, (x, y), "Winner:", FontColor)
            y = y + ls
            if CurrentGame.get("GameWinner") == "Yellow":
                Text = str(CurrentGame.get("YellowTeamName") or "Yellow")
            else:
                Text = str(CurrentGame.get("GreenTeamName") or "Green")
            FONT_GAME.render_to(screen, (x + indent, y), Text, FontColor)
            y = y + ls
            if CurrentGame.get("GameWinner") == "Yellow":
                Text = str(YellowScores.get("Total")) + " to " + str(GreenScores.get("Total"))
            else:
                Text = str(GreenScores.get("Total")) + " to " +  str(YellowScores.get("Total"))
            FONT_GAME.render_to(screen, (x + indent, y), "Total " + Text, FontColor)
            y = y + ls
            if CurrentGameType in ("Elimination","Sanction","Tournament"):
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
                FONT_SONG.render_to(screen, (x + indent, y), Text, FontColor)

        else:
            y = y * 3

        #Next Game Info
        if NextGame.get("GameNumber") >= 0 \
            and NextGame.get("GreenTeamName") != "Green" \
            and NextGame.get("YellowTeamName") != "Yellow":

            y = y + ls * 2
            FONT_GAME.render_to(screen, (x, y), "Next Game:", FontColor)
            y = y + ls * 1.2
            FONT_GAME.render_to(screen, (x, y), "Green:", FontColor)
            y = y + ls
            Text = str(NextGame.get("GreenTeamName") or "")
            FONT_GAME.render_to(screen, (x + indent, y), Text, FontColor)
            y = y + ls * 1.2
            FONT_GAME.render_to(screen, (x, y), "Yellow:", FontColor)
            y = y + ls
            Text = str(NextGame.get("YellowTeamName") or "")
            FONT_GAME.render_to(screen, (x + indent, y), Text, FontColor)

        x = int(800 * ScaleX)
        y = int(1030 * ScaleY)
        Text = CurrentGameType
        FONT_SONG.render_to(screen, (x, y), Text, CLR_PURPLE)
        if AutoInst:
            x = int(1100 * ScaleX)
            FONT_SONG.render_to(screen, (x, y), "Auto Instructions", CLR_PURPLE)
        if APIIitegration:
            x = int(1500 * ScaleX)
            FONT_SONG.render_to(screen, (x, y), "Tournament Integration", CLR_PURPLE)
    else:
        screen.blit(TimerBack, (0, 0))
        FontColor = CLR_BLACK
        if SecondsLeft < 0:
            FontColor = CLR_RED
            Ctr = strftime("%#M:%S", gmtime(SecondsLeft * -1))
        elif SecondsLeft <= 59:
            Ctr = "  " + strftime("%S", gmtime(SecondsLeft))
        else:
            Ctr = strftime("%#M:%S", gmtime(SecondsLeft))
        x = int(262 * ScaleX)
        y = int(450 * ScaleY)

        if SecondsLeft in (1,3,5,7,9):
            screen.blit(BlackTimerBack, (0, 0))
            FontColor = CLR_YELLOW
        if GameRunning == "Pause":
            FONT_TIMER.render_to(screen, (x, y), Ctr, CLR_RED)
        else:
            FONT_TIMER.render_to(screen, (x, y), Ctr, FontColor)

        DrawTeamScore("Yellow", 60, 40, FontColor)
        DrawTeamScore("Green", 960, 40, FontColor)

    #Song Info
    if pygame.mixer.music.get_busy():
        x = int(60 * ScaleX)
        y = int(990 * ScaleY)
        ls = int(30 * ScaleY)
        Text = SongData.title
        FONT_SONG.render_to(screen, (x, y), "Song: " + Text, FontColor)
        y = y + ls
        Text = SongData.artist
        FONT_SONG.render_to(screen, (x, y), "By: " + Text, FontColor)

    pygame.display.flip()

VIDEO_MAP = {
    "vCountdown":   vCountdown,
    "Elimination":  vEliminationInst,
    "Normal":       vNormalInst,
    "vPromo":       vPromo,
    "Sanction":     vSanctionInst,
    "vShootInst":   vShootInst,
}
ALL_VIDEOS = list(VIDEO_MAP.values())

def ShrinkAllVideos():
    for v in ALL_VIDEOS:
        v.resize((1, 1))

def PlayAVideo(Video):
    global CurrentVid
    global HoldIt
    vid = VIDEO_MAP.get(Video)
    if vid is None:
        return
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.fadeout(5000)
    if not vid.active:
        vid.resize((SWidth, SHeight))
        vid.restart()
        vid.play()
        CurrentVid = "Playing " + Video
    while vid.active:
        vid.draw(screen, (0, 0))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                HoldIt = datetime.now()
                if event.key == pygame.K_m:
                    vid.toggle_pause()
            elif event.type == pygame.KEYUP:
                if (datetime.now() - HoldIt).total_seconds() > 2:
                    if event.key == pygame.K_v:
                        vid.stop()
                        pygame.mixer.Sound.play(Close)
    ShrinkAllVideos()
    CurrentVid = "None"
    DrawScoreBoard()

if DeBug: PrintDeBug()

SpeakIt = queue.Queue()

tts_thread = TTSThread(SpeakIt)
SpeakIt.put("Welcome to Archery Tag by Sherwood Adventure.")

CurrentVid = "None"
ShrinkAllVideos()

GetNextGame()

DrawScoreBoard() 

web_thread = WebGameThread()
sync_thread = APISyncThread()
broadcast_tick = 0

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
    

    # Broadcast state to web clients (~2Hz)
    broadcast_tick += 1
    if broadcast_tick >= 5:
        web_thread.broadcast_state()
        broadcast_tick = 0

    #Leave some CPU for others — clock.tick(10) caps at 10 FPS
    clock.tick(10)
        