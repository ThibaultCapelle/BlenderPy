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
        return json.loads(data)['content']

def parse(message, kwargs=None):
    b=message.find('(')
    res=dict()
    if b==-1:
        res['type']='command'
        res['command']=message
    else:
        res['type']='command'
        first_part=message[:b]
        res['command']=first_part
        last_part=message[b:]
        assert last_part.endswith(')') and last_part.startswith('(')
        last_part=last_part[1:-1]
        assert last_part.find('(')==-1 and last_part.find(')')==-1
        data=last_part.split(',')
        args=[]
        if kwargs is None:
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
    print(msg)
    return msg

def delete_all():
    send(parse('delete_all()'))
    
class Material:
    
    def __init__(self, name, color, alpha=None, transmission=0,
                 use_screen_refraction=False, refraction_depth=0.):
        names = self.get_material_names()
        if name in names:
            self.material_object = self.get_material(name)
        else:
            self.material_object = self.create_material(name)
        self.color=self.convert_color(color, alpha)
        params=dict({'name':self.material_object, 'color':self.color,
                     'alpha':alpha, 'transmission':transmission,
                     'use_screen_refraction':use_screen_refraction,
                     'refraction_depth':refraction_depth})
        send(parse('update_material()', kwargs=params))
        '''[item.name for item in bpy.data.materials]
        if name in names:
            self.material=bdy.data.materials.get(name)
        else:
            self.material=self.new_material(name)
        
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
    def get_material(self, name):
        return ask(parse('get_material({:})'.format(name)))
    
    def create_material(self, name):
        return ask(parse('create_material({:})'.format(name)))
    
    def get_material_names(self):
        return ask(parse('get_material_names()'))
    
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
            return [int(color[i:i+2], 16)/256. for i in [1,3,5]] +[alpha]

class Mesh:
    
    def __init__(self, mesh, thickness=None, name='mesh'):
        self.thickness=thickness
        self.mesh=mesh
        self.name_obj, self.name_msh = self.send_mesh(self.mesh,
                                                      thickness=self.thickness,
                                                      name=name)
        
    def send_mesh(self, mesh, thickness=None, name='mesh'):
        points, cells = mesh.points, mesh.cells
        res=dict()
        kwargs = dict()
        kwargs['points']=[[coord for coord in p] for p in points]
        kwargs['cells']=[]
        for celltype in cells:
            if celltype.type=='triangle':
                kwargs['cells']+=[[int(ind) for ind in cell] for cell in celltype.data]
        kwargs['name']=name
        kwargs['thickness']=thickness
        res['type']='mesh'
        res['args']=[]
        res['command']='create_mesh'
        res['kwargs']=kwargs
        return ask(json.dumps(res)) 
    
    def assign_material(self, material):
        kwargs = dict({'name_obj':self.name_obj,
                       'name_mat':material.material_object})
        send(parse('assign_material()', kwargs=kwargs))
        

if __name__=='__main__':
    import pygmsh
    
    delete_all()
    
    geom = pygmsh.opencascade.geometry.Geometry(characteristic_length_max=1)
    geom.add_box([-3,-3,-1],[6,6,1])
    mesh = pygmsh.generate_mesh(geom)
    obj = Mesh(mesh)
    m=Material('material', '#C12828')
    obj.assign_material(m)
    
                          
                      
                      
            