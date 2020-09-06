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
    
    def __init__(self, name, color, alpha=1., transmission=0,
                 use_screen_refraction=False, refraction_depth=0.,
                 blend_method='OPAQUE', use_backface_culling=False):
        names = self.get_material_names()
        if name in names:
            self.material_object = self.get_material(name)
        else:
            self.material_object = self.create_material(name)
        self.color=self.convert_color(color)
        params=dict({'name':self.material_object, 'color':self.color,
                     'alpha':alpha, 'transmission':transmission,
                     'use_screen_refraction':use_screen_refraction,
                     'refraction_depth':refraction_depth,
                     'blend_method':blend_method,
                     'use_backface_culling':use_backface_culling})
        send(parse('update_material()', kwargs=params))
    
    def z_dependant_color(self, positions, colors):
        params=dict({'colors':[self.convert_color(color) for color in colors],
                     'name':self.material_object,
                     'positions':positions})
        send(parse('z_dependant_color()', kwargs=params))
    
    def gaussian_laser(self, ZR, W0, I):
        params=dict({'name':self.material_object,
                     'ZR':ZR,
                     'W0':W0,
                     'I':I})
        send(parse('gaussian_laser()', kwargs=params))
        
    def get_material(self, name):
        return ask(parse('get_material({:})'.format(name)))
    
    def create_material(self, name):
        return ask(parse('create_material({:})'.format(name)))
    
    def get_material_names(self):
        return ask(parse('get_material_names()'))
    
    def convert_color(self, color, alpha=1):
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

class Camera:
    
    def __init__(self, name, location, rotation):
        self.add_camera(name, location, rotation)
    
    def add_camera(self, name, location, rotation):
        res=dict()
        kwargs = dict()
        kwargs['location']=location
        kwargs['rotation']=rotation
        kwargs['name']=name
        res['type']='camera'
        res['args']=[]
        res['command']='create_camera'
        res['kwargs']=kwargs
        self.name, self.name_obj=ask(json.dumps(res))
    
    @property
    def position(self):
        res = dict()
        kwargs = dict()
        kwargs['name']=self.name
        kwargs['name_obj']=self.name_obj
        res['command']='get_camera_position'
        res['args']=[]
        res['kwargs']=kwargs
        return ask(json.dumps(res))
    
    @position.setter
    def position(self, val):
        res = dict()
        kwargs = dict()
        kwargs['name']=self.name
        kwargs['name_obj']=self.name_obj
        kwargs['position']=val
        res['command']='set_camera_position'
        res['args']=[]
        res['kwargs']=kwargs
        send(json.dumps(res))
    
    @property
    def rotation(self):
        res = dict()
        kwargs = dict()
        kwargs['name']=self.name
        kwargs['name_obj']=self.name_obj
        res['command']='get_camera_rotation'
        res['args']=[]
        res['kwargs']=kwargs
        return ask(json.dumps(res))
    
    @rotation.setter
    def rotation(self, val):
        res = dict()
        kwargs = dict()
        kwargs['name']=self.name
        kwargs['name_obj']=self.name_obj
        kwargs['rotation']=val
        res['command']='set_camera_rotation'
        res['args']=[]
        res['kwargs']=kwargs
        send(json.dumps(res))
    
class Light:
    
    def __init__(self, name, location, power, radius=0.25):
        self.add_light(name, location, power, radius)
        
    def add_light(self, name, location, power, radius):
        res=dict()
        kwargs = dict()
        kwargs['location']=location
        kwargs['power']=power
        kwargs['radius']=radius
        kwargs['name']=name
        res['type']='light'
        res['args']=[]
        res['command']='create_light'
        res['kwargs']=kwargs
        self.name=ask(json.dumps(res))
        

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
    material=Material('hello', '#F5D15B', alpha=0.5, blend_method='BLEND')
    geom=pygmsh.opencascade.geometry.Geometry(characteristic_length_max=0.25)

    mirror_1=geom.add_cylinder([0,0,0],
                               [0,0,1], 1)
    mesh = pygmsh.generate_mesh(geom)
    mirror_1_mesh=Mesh(mesh, name='mirror_1')
    mirror_1_mesh.assign_material(material)
    '''material.z_dependant_color([0.,0.5,1.],
                               ['#3213CD',
                                '#FFFFFF',
                                '#F60818'])'''
    
    material.gaussian_laser(0.05,0.005, 100)
    cam=Camera('camera', [0,0,0],[0,0,0])
    cam.rotation=[1,0,0]
    print(cam.rotation)
    
                          
                      
                      
            