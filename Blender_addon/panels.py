# -*- coding: utf-8 -*-
"""
Created on Thu Aug 27 17:54:45 2020

@author: Thibault
"""

from .receiving_data import Server

      
def register() :
    server=Server()
    server.connect()
 
def unregister() :
    pass
