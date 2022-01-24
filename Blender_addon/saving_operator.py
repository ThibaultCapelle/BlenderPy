# -*- coding: utf-8 -*-
"""
Created on Sat Jan  1 14:40:44 2022

@author: Thibault
"""

import bpy
import json
from bpy_extras.io_utils import ImportHelper
from mathutils import Vector, Euler

class Saving(bpy.types.Operator,ImportHelper):
    
    bl_idname = "object.save_to_dict"
    bl_label = "Saving"
    
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def execute(self, context):        # execute() is called when running the operator.
        # The original script
        for obj in context.selected_objects:
            data=dict()
            keys=[(obj, 'location'),
                  (obj, 'scale'),
                  (obj, 'rotation_euler')]
            if obj.type=='LIGHT':
                son=bpy.data.lights[obj.name]
                keys+=[(son, 'energy'),
                       (son, 'shadow_soft_size')]
            for source, key in keys:
                val=getattr(source, key)
                if isinstance(val, Vector) or isinstance(val, Euler):
                    val=[val.x, val.y, val.z]
                data[key]=val
            
                
            with open(self.filepath, 'w') as f:
                json.dump(data, f)
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.

def menu_func(self, context):
    self.layout.operator(Saving.bl_idname)

addon_keymaps = []

def register():
    bpy.utils.register_class(Saving)
    bpy.types.VIEW3D_MT_object.append(menu_func)  # Adds the new operator to an existing menu.
    wm = bpy.context.window_manager
    # Note that in background mode (no GUI available), keyconfigs are not available either,
    # so we have to check this to avoid nasty errors in background case.
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='Object Mode', space_type='EMPTY')
        kmi = km.keymap_items.new(Saving.bl_idname, 'S', 'PRESS', alt=True)
        addon_keymaps.append((km, kmi))

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    bpy.utils.unregister_class(Saving)
    bpy.types.VIEW3D_MT_object.remove(menu_func)