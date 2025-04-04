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


VERSION = '1.8.1'

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

    def start_writing(self):
        """Start writing to the CSV file."""
        self.file = open(self.filename, mode='w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.file)
        self.writer.writerow(["timestamp", "event", "data"])  # Header row
        self.is_writing = True
        ppi("Started writing to CSV file: " + self.filename)

    def write_row(self, timestamp, event, data):
        """Write a row to the CSV file."""
        if self.is_writing and self.writer:
            self.writer.writerow([timestamp, event, json.dumps(data)])
            ppi(f"Written row to CSV: {timestamp}, {event}, {data}")

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

            if event == 'match-started':
                ppi('Match started')
                match_writer.start_writing()

            elif event == 'match-ended':
                ppi('Match ended')
                match_writer.stop_writing()

            elif match_writer.is_writing:
                # Write other events to the CSV file
                match_writer.write_row(timestamp, event, msg)

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
    



   
