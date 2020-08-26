# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 10:05:13 2020

@author: Thibault
"""

import socket, threading

HOST = '127.0.0.1'
PORT = 20000

def Server(host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
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
server_thread = threading.Thread(target=Server)
server_thread.start()
