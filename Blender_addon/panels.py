# -*- coding: utf-8 -*-
"""
Created on Thu Aug 27 17:54:45 2020

@author: Thibault
"""

import bpy 

from .printing import printing_stuff, printing_other_stuff
from .receiving_data import Server

'''class Launch_server(bpy.types.Operator):
    bl_idname = "button.1"
    bl_label = "Simple operator"
    
    def execute(self, context):
        Test_Panel.server.connect()
        return {'FINISHED'}

class Stop_server(bpy.types.Operator):
    bl_idname = "button.2"
    bl_label = "Simple operator"
    
    def execute(self, context):
        Test_Panel.server.disconnect()
        return {'FINISHED'}

class Test_Panel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI" 
    bl_category = "Python Server" 
    bl_label = "Call Simple Operator"
    server=Server()
    
    def __init__(self):
        super().__init__()
        
    def draw(self, context):
        layout=self.layout
        row=layout.row()
        row.operator(Launch_server.bl_idname, text="start server", icon="SPHERE")
        row=layout.row()
        row.operator(Stop_server.bl_idname, text="stop server", icon="SPHERE")'''
      
def register() :
    server=Server()
    server.connect()
'''bpy.utils.register_class(Launch_server)
bpy.utils.register_class(Stop_server)
bpy.utils.register_class(Test_Panel)'''
 
def unregister() :
    pass
'''bpy.utils.unregister_class(Launch_server)
bpy.utils.unregister_class(Stop_server)
bpy.utils.unregister_class(Test_Panel)'''