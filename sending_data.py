# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 09:56:27 2020

@author: Thibault
"""

import socket

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('localhost', 20000))
client_socket.send(b'Hello world !')
client_socket.close()