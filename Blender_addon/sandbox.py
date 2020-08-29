# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 17:51:50 2020

@author: Thibault
"""

import json


a=b'Material("left_IDT", "#AC3333", transmission=5)'

b=a.decode().find('(')
first_part=a[:b].decode()
res=dict()
res['type']='class'
res['class']=first_part
last_part=a[b:].decode()
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