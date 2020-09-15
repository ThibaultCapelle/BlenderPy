# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 10:05:13 2020

@author: Thibault
"""

import socket, threading, json
from .interprete import Interprete

HOST = '127.0.0.1'
PORT = 20000

class Server:
    
    def __init__(self, host=HOST, port=PORT):
        self.host=host
        self.port=port
        self.connected=False
        self.interprete = Interprete(self)
        
    def connect(self):
        if not self.connected:
            self.server_thread=threading.Thread(target=self.listen, daemon=True)
            self.connected=True
            self.server_thread.start()
            
    def receive_all(self, sock, n):
        # Helper function to recv n bytes or return None if EOF is hit
        data = bytearray()
        i=1
        while len(data) < n:
            print('packet number {:}'.format(i))
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
            i+=1
        return data  
    
    def send(self, message):
        print('len : {:010x}'.format(len(message)))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.sendall(('{:010x}'.format(len(message))+message).encode())
    
    def send_answer(self, conn, message):
        message=json.dumps(dict({'content':message}))
        conn.sendall(('{:010x}'.format(len(message))+message).encode())
        
    def listen(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            while self.connected:
                conn, addr = s.accept()
                with conn:
                    print('Connected by', addr)
                    while True:
                        raw_msglen = conn.recv(10)
                        if not raw_msglen:
                            print("No raw_msglen")
                            break
                        msglen = int(raw_msglen.decode(),16)
                        print('len of packet is {:}'.format(msglen))
                        data=self.receive_all(conn, msglen)
                        if data is not None:
                            self.interpreter(conn, data)
                        elif len(data)!=msglen:
                            print('the length and the data did not match')
            s.shutdown(socket.SHUT_RDWR)
            s.close()
    
    def disconnect(self):
        self.connected=False
        if self.connected:
            print('I will disconnect this server')
    
    def interpreter(self, conn, message):
        cmd = json.loads(message)
        cmd['kwargs']['connection']=conn
        self.interprete.call(cmd)
        
        
