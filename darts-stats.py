import os
import json
import platform
import random
import argparse
import threading
import logging
import time
import requests
import socketio
import websocket
import csv


sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
sh.setFormatter(formatter)
logger=logging.getLogger()
logger.handlers.clear()
logger.setLevel(logging.INFO)
logger.addHandler(sh)



http_session = requests.Session()
http_session.verify = False
sio = socketio.Client(http_session=http_session, logger=True, engineio_logger=True)


VERSION = '0.0.1'

def ppi(message, info_object = None, prefix = '\r\n'):
    logger.info(prefix + str(message))
    if info_object is not None:
        logger.info(str(info_object))
    
def ppe(message, error_object):
    ppi(message)
    if DEBUG:
        logger.exception("\r\n" + str(error_object))

class MatchStatsWriter:
    def __init__(self, filename="match_stats.csv"):
        self.filename = filename
        self.file = None
        self.writer = None
        self.is_writing = False

    def start_writing(self, matchId, matchHost, matchPlayers, gameMode, gamePointsStart):
        """Start writing to the CSV file."""
        self.file = open(self.filename, mode='w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.file)
        self.writer.writerow(["matchId: "+ matchId+ " matchHost: "+ str(matchHost) + " gameMode: "+ gameMode + " gamePointsStart: "+ gamePointsStart])  # Header row
        self.writer.writerow(["timestamp", "event", "player", "playerIsBot", "mode", "pointsLeft", "dartNumber", "dartValue", "dartsTrown", "dartsThrownValue", "busted","fieldName", "fieldNumber", "fieldMultiplier", "coordsX", "coordsY"])  # Header row
        self.is_writing = True
        ppi("Started writing to CSV file: " + self.filename)

    def write_row(self, timestamp, event, player, playerIsBot, mode, pointsLeft, dartNumber, dartValue, dartsTrown, dartsThrownValue, busted, fieldName, fieldNumber, fieldMultiplier, coordsX, coordsY):
        """Write a row to the CSV file."""
        if self.is_writing and self.writer:
            self.writer.writerow([timestamp, event, player, playerIsBot, mode, pointsLeft, dartNumber, dartValue, dartsTrown, dartsThrownValue, busted, fieldName, fieldNumber, fieldMultiplier, coordsX, coordsY])
            # ppi(f"Written row to CSV: {timestamp}, {event}, {player}, {playerIsBot}, {mode}, {pointsLeft}, {dartNumber}, {dartValue}")

    def stop_writing(self):
        """Stop writing and close the CSV file."""
        if self.file:
            self.file.close()
            self.file = None
            self.writer = None
            self.is_writing = False
            ppi("Stopped writing to CSV file: " + self.filename)


# Instantiate the MatchStatsWriter
match_writer = MatchStatsWriter()






def broadcast_intern(endpoint, data):
    try:
        endpoint.send(json.dumps(data))
    except:  
        return

@sio.event
def connect():
    ppi('CONNECTED TO DATA-FEEDER ' + sio.connection_url)
    STATS_Info ={
        'status': 'STATS connected',
        'version': VERSION
    }
    sio.emit('message', STATS_Info)   

@sio.event
def connect_error(data):
    if DEBUG:
        ppe("CONNECTION TO DATA-FEEDER FAILED! " + sio.connection_url, data)

@sio.event
def message(msg):
    try:
        m = msg
        ppi(json.dumps(m, indent = 4, sort_keys = True))
        ppi('Message recived')

        if 'event' in msg:
            event = msg['event']
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            timestampFile = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())

            if event == 'match-started':
                ppi('Match started')
                # "event": "match-started",
                #     "id": currentMatch,
                #     "me": AUTODART_USER_BOARD_ID,
                #     "meHost": currentMatchHost,
                #     "players": currentMatchPlayers,
                #     "player": currentPlayerName,
                #     "game": {
                #         "mode": mode,
                #         "pointsStart": str(m['settings'][base]),
                #         # TODO: fix
                #         "special": "TODO"
                #         }  
                matchId = msg['id']
                if 'meHost' in msg:
                    matchHost = msg['meHost']
                else:
                    matchHost = 'Turnament' 
                matchPlayers = msg['player']
                gameMode = msg['game']['mode']
                gamePointsStart = msg['game']['pointsStart']   
                match_writer.filename =timestampFile+'_'+ msg['game']['mode'] + '_' + msg['id'] + '.csv'
                match_writer.start_writing(matchId,matchHost,matchPlayers,gameMode,gamePointsStart)

            elif event == 'match-ended':
                ppi('Match ended')
                match_writer.stop_writing()

            elif match_writer.is_writing:
                # {""event"": ""dart1-thrown"", ""player"": ""i3ull3t"", ""playerIndex"": ""0"", ""playerIsBot"": ""False"", ""game"": {""mode"": ""X01"", ""pointsLeft"": ""481"", ""dartNumber"": ""1"", ""dartValue"": ""20""}}
                if msg['event'] == 'dart1-thrown' or msg['event'] == 'dart2-thrown' or msg['event'] == 'dart3-thrown':
                    player = msg['player']
                    playerIsBot = msg['playerIsBot']
                    mode = msg['game']['mode']
                    pointsLeft = msg['game']['pointsLeft']
                    dartNumber = msg['game']['dartNumber']
                    dartValue = msg['game']['dartValue']
                    fieldName = msg['game']['fieldName']
                    fieldNumber = msg['game']['fieldNumber']
                    fieldMultiplier = msg['game']['fieldMultiplier']
                    coordsX = msg['game']['coords']['x']
                    coordsY = msg['game']['coords']['y']

                    match_writer.write_row(timestamp, event, player, playerIsBot, mode, pointsLeft, dartNumber, dartValue,"", "","",fieldName, fieldNumber, fieldMultiplier, coordsX, coordsY)
                    lastMessageEvent = msg['event']
                
                # Write other events to the CSV file
                # match_writer.write_row(timestamp, event, msg)
                # {""event"": ""darts-pulled"", ""player"": ""i3ull3t"", ""playerIndex"": ""0"", ""game"": {""mode"": ""X01"", ""pointsLeft"": ""321"", ""dartsThrown"": ""3"", ""dartsThrownValue"": ""60"", ""busted"": ""False""}}"
                elif msg['event'] == 'darts-pulled':
                    player = msg['player']
                    mode = msg['game']['mode']
                    pointsLeft = msg['game']['pointsLeft']
                    dartsTrown = msg['game']['dartsThrown']
                    dartsThrownValue = msg['game']['dartsThrownValue']
                    busted = msg['game']['busted']
                    match_writer.write_row(timestamp, event, player, "", mode, pointsLeft, "", "", dartsTrown, dartsThrownValue, busted,"", "", "", "", "")
                # {""event"": ""match-won"", ""player"": ""i3ull3t"", ""playerIndex"": ""0"", ""game"": {""mode"": ""X01"", ""dartsThrownValue"": ""40""}}"
                elif msg['event'] == 'match-won':
                    player = msg['player']
                    mode = msg['game']['mode']
                    dartsThrownValue = msg['game']['dartsThrownValue']

                    ppi('Match won')
                    match_writer.write_row(timestamp, event, player, "", mode, "", "", "", "", dartsThrownValue, "", "", "", "", "", "")
                elif msg['event'] == 'busted':
                    player = msg['player']
                    mode = msg['game']['mode']
                    dartsThrownValue = msg['game']['dartsThrownValue']

                    ppi('Match won')
                    match_writer.write_row(timestamp, event, player, "", mode, "", "", "", "", dartsThrownValue, "", "", "", "", "", "") 

    except Exception as e:
        ppe('DATA-FEEDER Message failed: ', e)

@sio.event
def disconnect():
    ppi('DISCONNECTED FROM DATA-FEEDER ' + sio.connection_url)

def connect_data_feeder():
    try:
        server_host = CON.replace('ws://', '').replace('wss://', '').replace('http://', '').replace('https://', '')
        server_url = 'ws://' + server_host
        sio.connect(server_url, transports=['websocket'])
    except Exception:
        try:
            server_url = 'wss://' + server_host
            sio.connect(server_url, transports=['websocket'], retry=True, wait_timeout=3)
        except Exception:
            pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-CON", "--connection", default="127.0.0.1:8079", required=False, help="Connection to data feeder")
    ap.add_argument("-DEB", "--debug", type=int, choices=range(0, 2), default=False, required=False, help="If '1', the application will output additional information")

    args = vars(ap.parse_args())

    osType = platform.system()
    osName = os.name
    osRelease = platform.release()
    ppi('\r\n', None, '')
    ppi('##########################################', None, '')
    ppi('       WELCOME TO DARTS-STATS', None, '')
    ppi('##########################################', None, '')
    ppi('VERSION: ' + VERSION, None, '')
    ppi('RUNNING OS: ' + osType + ' | ' + osName + ' | ' + osRelease, None, '')
    ppi('\r\n', None, '')

    DEBUG = args['debug']
    CON = args['connection']
    
    try:            
        connect_data_feeder() 

    except Exception as e:
        ppe("Connect failed: ", e)

    
    
sio.wait()
time.sleep(5)
    



   
