# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 09:56:27 2020

@author: Thibault
"""

import socket, json

HOST = '127.0.0.1'
PORT = 20000

def send(message):
    print('len : {:010x}'.format(len(message)))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(('{:010x}'.format(len(message))+message).encode())
    

def send_mesh(mesh, thickness=None):
    points, cells = mesh.points, mesh.cells
    res=dict()
    res['name']='mesh'
    res['type']='mesh'
    res['thickness']=thickness
    res['points']=[[coord for coord in p] for p in points]
    res['cells']=[]
    for celltype in cells:
        if celltype.type=='triangle':
            res['cells']+=[[int(ind) for ind in cell] for cell in celltype.data]
    send(json.dumps(res))

def parse(message):
    b=message.find('(')
    res=dict()
    if b==-1:
        res['type']='command'
        res['command']=message
    else:
        res['type']='class'
        first_part=message[:b]
        res['class']=first_part
        last_part=message[b:]
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
    msg=json.dumps(res)
    return msg

def delete_all():
    send(parse('delete_all'))

if __name__=='__main__':
    send('Material("left_IDT", "#AC3333")')
                          
                      
                      
            