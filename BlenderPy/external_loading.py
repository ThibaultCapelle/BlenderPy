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
                                 p.y*dbu*self.scaling,
                                 0.])
            holes=[[] for i in range(s.holes())]
            print('total:{:}, hull:{:}, number of holes:{:}'\
                  .format(s.num_points(),
                          s.num_points_hull(),
                          s.holes()))
            for i in range(s.holes()):
                for p in s.each_point_hole(i):
                    holes[i].append([p.x*dbu*self.scaling,
                                     p.y*dbu*self.scaling,
                                     0.])
                print('hole nr {:} has {:} points'.format(i, len(holes[i])))
            shape[1]=holes
            res.append(shape)
        self.polygons=res    
        self.kwargs=kwargs
        
    def polygon_area(self, xs, ys):
        """https://en.wikipedia.org/wiki/Centroid#Of_a_polygon"""
        # https://stackoverflow.com/a/30408825/7128154
        return 0.5 * (np.dot(xs, np.roll(ys, 1)) - np.dot(ys, np.roll(xs, 1)))

    def polygon_centroid(self, points):
        """https://en.wikipedia.org/wiki/Centroid#Of_a_polygon"""
        xs, ys=[p[0] for p in points], [p[1] for p in points]
        xy = np.array([xs, ys])
        c = np.dot(xy + np.roll(xy, 1, axis=1),
                   xs * np.roll(ys, 1) - np.roll(xs, 1) * ys
                   ) / (6 * self.polygon_area(xs, ys))
        return c
        
    def load(self):
        res=[]
        for shape in self.polygons:
            plane_geom=Plane_Geom(**self.kwargs)
            plane_geom.generate_triangulation_from_shapely_LineString\
            (plane_geom.generate_shapely_polygon_from_points(shape))
            plane_geom.send_to_blender(from_external_loading=True)
            '''plane_geom.generate_triangulation_from_point_list(shape)
            plane_geom.send_to_blender(from_external_loading=True)'''
            res.append(plane_geom)
        return res

if __name__=='__main__':
    from BlenderPy.meshing import Box
    from BlenderPy.sending_data import delete_all
    import numpy as np
    delete_all()
    loader=GDSLoader(filename=r'C:\Users\Thibault\Documents\postdoc\Masks\trenches.gds',
                     layer=3,xmin=-1000, xmax=3500,
                     ymin=-2000, ymax=2000,
                     cell_name='TOP', thickness=0.15)
    trenches=loader.load()
    silicon=Box(Lx=10, Ly=10, Lz=0.1)
    for trench in trenches:
        trench.z-=0.025
        silicon.subtract(trench)
    loader=GDSLoader(filename=r'C:\Users\Thibault\Documents\postdoc\Masks\trenches.gds',
                     layer=9,xmin=-1000, xmax=3500,
                     ymin=-2000, ymax=2000,
                     cell_name='TOP', thickness=0.1)
    recesses=loader.load()
    for recess in recesses:
        recess.zmin=silicon.zmax
    loader=GDSLoader(filename=r'C:\Users\Thibault\Documents\postdoc\Masks\trenches.gds',
                     layer=8,xmin=-1000, xmax=3500,
                     ymin=-2000, ymax=2000,
                     cell_name='TOP', thickness=0.02)
    circuits=loader.load()
    for circuit in circuits:
        circuit.zmin=recess.zmax
    '''verts=silicon.vertices
    xmin, xmax, ymin, ymax=(np.min([trench.xmin for trench in trenches]),
                            np.max([trench.xmax for trench in trenches]),
                            np.min([trench.ymin for trench in trenches]),
                            np.max([trench.ymax for trench in trenches]))
                            
    for i, p in enumerate(verts):
        if p[0]<xmax and p[0]>xmin and p[1]>ymin and p[1]<ymax:
            verts[i][2]+=xmax-p[0]
    silicon.vertices=verts'''

        