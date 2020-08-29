# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 09:56:27 2020

@author: Thibault
"""

import socket, json

HOST = '127.0.0.1'
PORT = 20000

def parse(message):
    b=message.decode().find('(')
    res=dict()
    if b==-1:
        res['type']='command'
        res['command']=message.decode()
    else:
        res['type']='class'
        first_part=message[:b].decode()
        res['class']=first_part
        last_part=message[b:].decode()
        assert last_part.endswith(')') and last_part.startswith('(')
        last_part=last_part[1:-1]
        assert last_part.find('(')==-1 and last_part.find(')')==-1
        data=last_part.split(',')
        args=[]
        kwargs=dict()
        for i in range(len(data)):
            data[i]=data[i].lstrip('"').rstrip('"')
            if data[i].find('=')!=-1:
                k,v=data[i].split('=')
                kwargs[k]=v
            else:
                args.append(data[i])
        res['args']=args
        res['kwargs']=kwargs
    msg=json.dumps(res).encode()
    return msg


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.send(parse(b'Material("left_IDT", "#AC3333")'))
                      
                      
                      
            