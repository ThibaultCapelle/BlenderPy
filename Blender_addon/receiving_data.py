# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 10:05:13 2020

@author: Thibault
"""

import socket, threading, json
from . import Interprete

HOST = '127.0.0.1'
PORT = 20000

class Server:
    
    def __init__(self, host=HOST, port=PORT):
        self.host=host
        self.port=port
        self.connected=False
        
    def connect(self):
        if not self.connected:
            self.server_thread=threading.Thread(target=self.listen, daemon=True)
            self.connected=True
            self.server_thread.start()
    
    def listen(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            while self.connected:
                conn, addr = s.accept()
                with conn:
                    print('Connected by', addr)
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break
                        else:
                            print(data)
                            self.interpreter(data)
            s.shutdown(socket.SHUT_RDWR)
            s.close()
    
    def disconnect(self):
        self.connected=False
        if self.connected:
            print('I will disconnect this server')
    
    def interpreter(self, message):
        cmd = json.loads(message.decode())
        if cmd['type']=='command':
            if cmd['command']=='delete_all':
                Interprete.delete_all()
        elif cmd['type']=='class':
            if cmd['class']=='Material':
                Interprete.Material(cmd)
        else:
            print("unknown")
        
        
