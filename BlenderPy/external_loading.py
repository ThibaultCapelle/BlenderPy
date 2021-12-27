# -*- coding: utf-8 -*-
"""
Created on Sun Dec 26 15:54:46 2021

@author: Thibault
"""

import pya

from BlenderPy.meshing import Plane_Geom

class GDSLoader:
    
    def __init__(self, filename=None, xmin=None, 
                 xmax=None, ymin=None,
                 ymax=None, layer=None, scaling=1e-3,
                 cell_name='TOP', **kwargs):
        self.scaling=scaling
        self.filename=filename
        self.layout=pya.Layout()
        self.layout.read(self.filename)
        dbu=self.layout.dbu
        box=pya.Region(pya.Box(xmin/dbu, ymin/dbu, xmax/dbu, ymax/dbu))
        cell = self.layout.cell(self.layout.cell_by_name(cell_name))
        for i, layer_info in enumerate(self.layout.layer_infos()):
            if layer_info.layer==layer:
                layer_ind=i
                break
        shapes=cell.shapes(layer_ind)
        region_all=pya.Region(shapes)
        r=region_all.select_inside(box)
        res=[]
        for s in r.each():
            shape=[[],[]]
            for p in s.each_point_hull():
                shape[0].append([p.x*dbu*self.scaling,
                                 p.y*dbu*self.scaling])
            holes=[[] for i in range(s.holes())]
            for i in range(s.holes()):
                for p in s.each_point_hole(i):
                    holes[i].append([p.x*dbu*self.scaling,
                                     p.y*dbu*self.scaling])
            shape[1]=holes
            res.append(shape)
        self.polygons=res    
        self.kwargs=kwargs
        
    def load(self):
        res=[]
        for shape in self.polygons:
            plane_geom=Plane_Geom(**self.kwargs)
            plane_geom.generate_triangulation_from_point_list(shape)
            plane_geom.send_to_blender(from_external_loading=True)
            res.append(plane_geom)
        return res

if __name__=='__main__':
    from BlenderPy.meshing import Box
    from BlenderPy.sending_data import delete_all
    delete_all()
    loader=GDSLoader(filename=r'C:\Users\Thibault\Documents\postdoc\Masks\trenches.gds',
                     layer=2,xmin=-1000, xmax=3500,
                     ymin=-2000, ymax=2000,
                     cell_name='TOP', thickness=0.15)
    trenches=loader.load()
    silicon=Box(Lx=10, Ly=10, Lz=0.1)
    for trench in trenches:
        trench.z-=0.025
        silicon.subtract(trench)
    '''boolean=silicon.assign_modifier(modifier_type='BOOLEAN')
    boolean.properties['object']=trench
    boolean.apply()'''
        