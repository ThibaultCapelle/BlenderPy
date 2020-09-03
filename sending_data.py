# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 09:56:27 2020

@author: Thibault
"""

import socket, json, time

HOST = '127.0.0.1'
PORT = 20000

def send(message):
    print('len : {:010x}'.format(len(message)))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(('{:010x}'.format(len(message))+message).encode())

def receive_all(sock, n):
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
    
def ask(message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(('{:010x}'.format(len(message))+message).encode())
        raw_msglen = s.recv(10)
        msglen = int(raw_msglen.decode(),16)
        print(msglen)
        data=receive_all(s, msglen)
        return data

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
    
class Material:
    
    def __init__(self, name, color, alpha=None, transmission=0,
                 use_screen_refraction=False, refraction_depth=0.):
        print(self.get_material_names())
        '''[item.name for item in bpy.data.materials]
        if name in names:
            self.material=bdy.data.materials.get(name)
        else:
            self.material=self.new_material(name)
        self.color=self.convert_color(color, alpha)
        #self.material.diffuse_color=self.color
        self.material.node_tree.nodes["Principled BSDF"].inputs[0].default_value=self.color
        self.material.node_tree.nodes["Principled BSDF"].inputs[15].default_value=transmission
        self.material.node_tree.nodes["Principled BSDF"].inputs[16].default_value=use_screen_refraction
        self.material.use_screen_refraction=use_screen_refraction
        if use_screen_refraction:
            bpy.context.scene.eevee.use_ssr = True
            bpy.context.scene.eevee.use_ssr_refraction = True
            #bpy.context.object.active_material.refraction_depth = refraction_depth
'''
    def get_material_names(self):
        return ask(parse('get_material_names'))

        
'''    def new_material(self, name):
        mat=bpy.data.materials.new(name)
        mat.use_nodes = True
        self.nodes = mat.node_tree.nodes
        print([node for node in self.nodes])
        #node = self.nodes.new("Principled BSDF")
        return mat
    
    def convert_color(self, color, alpha):
        if len(color)==3:
            if alpha is None:
                alpha=1.0
            return color+[alpha]
        elif len(color)==4:
            return color
        elif color[0]=='#':
            if len(color)==7:
                if alpha is None:
                    alpha=1.0
            else:
                alpha=int(color[7:9], 16)/256.
            return [int(color[i:i+2], 16)/256. for i in [1,3,5]] +[alpha]'''

if __name__=='__main__':
    m=Material('material', 'b')
                          
                      
                      
            