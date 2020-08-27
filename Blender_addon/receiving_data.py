# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 10:05:13 2020

@author: Thibault
"""

import socket, threading

HOST = '127.0.0.1'
PORT = 20000

class Server:
    
    def __init__(self, host=HOST, port=PORT):
        self.host=host
        self.port=port
        self.connected=False
        
    def connect(self):
        if not self.connected:
            self.server_thread=threading.Thread(target=self.listen)
            self.server_thread.start()
            self.connected=True
    
    def listen(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            while True:
                conn, addr = s.accept()
                with conn:
                    print('Connected by', addr)
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break
                        else:
                            print(data)
    
    def disconnect(self):
        if self.connected:
            self.server_thread.stop()
            self.connected=False
        
