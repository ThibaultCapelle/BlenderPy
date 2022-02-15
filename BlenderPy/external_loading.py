# -*- coding: utf-8 -*-
"""
Created on Sun Dec 26 15:54:46 2021

@author: Thibault
"""

import math
import numpy as np
import struct
from BlenderPy.meshing import PlaneGeom, Polygon, MultiPolygon
from BlenderPy.sending_data import Mesh
from shapely.geometry import LineString, Point

class VTULoader:
    '''Load a VTU file, tipycally exported from COMSOL'''
    
    def __init__(self, filename, **kwargs):
        '''
        Parameters:
            filename: path to the file
            kwargs: PlaneGeom keyword arguments
        '''
        
        self.kwargs=kwargs
        self.filename=filename
        with open(filename, 'r') as f:
            lines=f.readlines()
        reading_points=False
        reading_cells=False
        reading_data=False
        self.data, self.points, self.cells= [], [], []
        for line in lines:
            if line.startswith('<'):
                if line.startswith('<PointData>'):
                    reading_data=True
                elif line.startswith('</PointData>'):
                    reading_data=False
                if line.startswith('<Points>'):
                    reading_points=True
                elif line.startswith('</Points>'):
                    reading_points=False
                if line.startswith('<Cells>'):
                    reading_cells=True
                elif line.startswith('</DataArray>'):
                    reading_cells=False
            else:
                if reading_data:
                    self.data.append(float(line))
                if reading_points:
                    self.points.append([float(x) for x in line.split(' ')])
                if reading_cells:
                    self.cells.append([int(p) for p in line.split(' ')])
        for i in range(len(self.data)):
            self.points[i][2]=self.data[i]
            
    def load(self):
        '''Send the loading to Blender'''
        return Mesh(cells=[['triangle',self.cells]],
                    points=list(self.points), **self.kwargs) 

class STLLoader:
    '''Loader for a STL file'''
    
    def __init__(self, filename, **kwargs):
        '''
        Parameters:
            filename: path to the file
            kwargs: PlaneGeom keyword arguments
        '''
        self.kwargs=kwargs
        self.filename=filename
        with open(self.filename, 'rb') as f:
            self.header=f.read(80).decode()
            self.N_triangles=struct.unpack('I', f.read(4))[0]
            vectors, Ps_s, attrs=[], [], []
            for i in range(self.N_triangles):
                vector=list(struct.unpack('fff', f.read(12)))
                for j in range(3):
                    Ps_s.append(f.read(12))
                attr=struct.unpack('H', f.read(2))[0]
                vectors.append(vector)
                attrs.append(attr)
        dict_points=dict()
        current_index=0
        self.cells=[]
        for i in range(self.N_triangles):
            for j in range(3):
                P=Ps_s[i*3+j]
                if P not in dict_points.keys():
                    dict_points[P]=current_index
                    current_index+=1
            self.cells.append([dict_points[Ps_s[3*i+j]] for j in range(3)])
        self.new_dict_points={v:struct.unpack('fff',k) for k, v in dict_points.items()}
    
    def load(self):
        '''Send the loading to Blender'''
        return Mesh(cells=[['triangle',self.cells]],
          points=list(self.new_dict_points.values()), **self.kwargs) 


class GDSLoader:
    '''Loader for a GDS file. It needs to be opened by Klayout'''
    
    DATATYPE = {
        'HEADER': 0x0002,
        'BGNLIB': 0x0102,
        'LIBNAME': 0x0206,
        'UNITS': 0x0305,
        'ENDLIB': 0x0400,
        'BGNSTR': 0x0502,
        'STRNAME': 0x0606,
        'ENDSTR': 0x0700,
        'BOUNDARY': 0x0800,
        'PATH': 0x0900,
        'SREF': 0x0A00,
        'AREF': 0x0B00,
        'TEXT': 0x0C00,
        'LAYER': 0x0D02,
        'DATATYPE': 0x0E02,
        'WIDTH': 0x0F03,
        'XY': 0x1003,
        'ENDEL': 0x1100,
        'SNAME': 0x1206,
        'COLROW': 0x1302,
        'TEXTNODE': 0x1400,
        'NODE': 0x1500,
        'TEXTTYPE': 0x1602,
        'PRESENTATION': 0x1701,
        # SPACING: 0x18??
        'STRING': 0x1906,
        'STRANS': 0x1A01,
        'MAG': 0x1B05,
        'ANGLE': 0x1C05,
        # UINTEGER: 0x1D??
        # USTRING: 0x1E??
        'REFLIBS': 0x1F06,
        'FONTS': 0x2006,
        'PATHTYPE': 0x2102,
        'GENERATIONS': 0x2202,
        'ATTRTABLE': 0x2306,
        'STYPTABLE': 0x2406,
        'STRTYPE': 0x2502,
        'ELFLAGS': 0x2601,
        'ELKEY': 0x2703,
        # LINKTYPE: 0x28??
        # LINKKEYS: 0x29??
        'NODETYPE': 0x2A02,
        'PROPATTR': 0x2B02,
        'PROPVALUE': 0x2C06,
        'BOX': 0x2D00,
        'BOXTYPE': 0x2E02,
        'PLEX': 0x2F03,
        'BGNEXTN': 0x3003,
        'ENDEXTN': 0x3103,
        'TAPENUM': 0x3202,
        'TAPECODE': 0x3302,
        'STRCLASS': 0x3401,
        # RESERVED: 0x3503
        'FORMAT': 0x3602,
        'MASK': 0x3706,
        'ENDMASKS': 0x3800,
        'LIBDIRSIZE': 0x3902,
        'SRFNAME': 0x3A06,
        'LIBSECUR': 0x3B02,
        # Types used only with Custom Plus
        'BORDER': 0x3C00,
        'SOFTFENCE': 0x3D00,
        'HARDFENCE': 0x3E00,
        'SOFTWIRE': 0x3F00,
        'HARDWIRE': 0x4000,
        'PATHPORT': 0x4100,
        'NODEPORT': 0x4200,
        'USERCONSTRAINT': 0x4300,
        'SPACERERROR': 0x4400,
        'CONTACT': 0x4500
    }
    
    REV_DATATYPE = {v: k for k, v in DATATYPE.items()}
    
    DICT_DATAFMT = {
        'NODATA': 0,
        'BITARRAY': 1,
        'INT2': 2,
        'INT4': 3,
        'REAL4': 4, # not used
        'REAL8': 5,
        'ASCII': 6
    }
    
    REV_DATAFMT = {v: k for k, v in DICT_DATAFMT.items()}
    

    def _parse_nodata(self, data):
        """Parse :const:`NODATA` data type. Does nothing."""
    
    def _parse_bitarray(self, data):
        """
        Parse :const:`BITARRAY` data type.
            >>> _parse_bitarray(b'ab') # ok, 2 bytes
            24930
            >>> _parse_bitarray(b'abcd') # too long
            Traceback (most recent call last):
                ...
            IncorrectDataSize: BITARRAY
            >>> _parse_bitarray('') # zero bytes
            Traceback (most recent call last):
                ...
            IncorrectDataSize: BITARRAY
        """
        assert len(data) == 2
        (val,) = struct.unpack('>H', data)
        return val
    
    def _parse_int2(self, data):
        """
        Parse INT2 data type.
            >>> _parse_int2(b'abcd') # ok, even number of bytes
            (24930, 25444)
            >>> _parse_int2(b'abcde') # odd number of bytes
            Traceback (most recent call last):
                ...
            IncorrectDataSize: INT2
            >>> _parse_int2(b'') # zero bytes
            Traceback (most recent call last):
                ...
            IncorrectDataSize: INT2
        """
        data_len = len(data)
        assert data_len and not (data_len % 2)
        return struct.unpack('>%dh' % (data_len//2), data)
    
    def _parse_int4(self, data):
        """
        Parse INT4 data type.
            >>> _parse_int4(b'abcd')
            (1633837924,)
            >>> _parse_int4(b'abcdef') # not divisible by 4
            Traceback (most recent call last):
                ...
            IncorrectDataSize: INT4
            >>> _parse_int4(b'') # zero bytes
            Traceback (most recent call last):
                ...
            IncorrectDataSize: INT4
        """
        data_len = len(data)
        assert data_len and not (data_len % 4)
        return struct.unpack('>%dl' % (data_len//4), data)
    
    def _int_to_real(self, num):
        """
        Convert REAL8 from internal integer representation to Python reals.
        Zeroes:
            >>> print(_int_to_real(0x0))
            0.0
            >>> print(_int_to_real(0x8000000000000000)) # negative
            0.0
            >>> print(_int_to_real(0xff00000000000000)) # denormalized
            0.0
        Others:
            >>> print(_int_to_real(0x4110000000000000))
            1.0
            >>> print(_int_to_real(0xC120000000000000))
            -2.0
        """
        sgn = -1 if 0x8000000000000000 & num else 1
        mant = num & 0x00ffffffffffffff
        exp = (num >> 56) & 0x7f
        return math.ldexp(sgn * mant, 4 * (exp - 64) - 56)
    
    def _parse_real8(self, data):
        """
        Parse REAL8 data type.
            >>> _parse_real8(struct.pack('>3Q', 0x0, 0x4110000000000000, 0xC120000000000000))
            (0.0, 1.0, -2.0)
            >>> _parse_real8(b'') # zero bytes
            Traceback (most recent call last):
                ...
            IncorrectDataSize: REAL8
            >>> _parse_real8(b'abcd') # not divisible by 8
            Traceback (most recent call last):
                ...
            IncorrectDataSize: REAL8
        """
        data_len = len(data)
        assert data_len and not (data_len % 8)
        ints = struct.unpack('>%dQ' % (data_len//8), data)
        return tuple(self._int_to_real(n) for n in ints)
    
    def _parse_ascii(self, data):
        r"""
        Parse ASCII data type.
            >>> _parse_ascii(b'') # zero bytes
            Traceback (most recent call last):
                ...
            IncorrectDataSize: ASCII
            >>> _parse_ascii(b'abcde') == b'abcde'
            True
            >>> _parse_ascii(b'abcde\0') == b'abcde' # strips trailing NUL
            True
        """
        assert len(data)
        # XXX cross-version compatibility
        if data[-1:] == b'\0':
            return data[:-1]
        return data.decode()
    
    def parse(self, tag, data):
        _PARSE_FUNCS = {
            'NODATA': self._parse_nodata,
            'BITARRAY': self._parse_bitarray,
            'INT2': self._parse_int2,
            'INT4': self._parse_int4,
            'REAL8': self._parse_real8,
            'ASCII': self._parse_ascii
        }
        return _PARSE_FUNCS[self.REV_DATAFMT[tag&0xff]](data)
    
    
    def __init__(self, filename=None, xmin=None, 
                 xmax=None, ymin=None,
                 ymax=None, layer=None, scaling=1e-3,
                 cell_name='TOP', centering=None,
                 merged=False, N_per_circle=30, **kwargs):
        '''
        Parameters:
            filename: path to the GDS
            xmin xmax, ymin, ymax: limits of the box to select from
            layer: layer number to select from. Ex: 2 will select the layer 2/0
            scaling: 2D scaling to apply after loading
            cell_name: name of the cell to select from
            centering: desired center of the coordinates,
            merged: if True, merge all the found polygons before sending
            to Blender. If False, send those polygons separately
            kwargs: keyword arguments for PlaneGeom'''
            
        self.scaling=scaling
        self.filename=filename
        self.data=self.read()
        
        
        reading_cell, reading_bound, reading_path=False, False, False
        polygons=[]
        dbu=None
        for datatype, data in self.data:
            if datatype=='UNITS':
                dbu=data[0]
                print(data)
            if datatype=='STRNAME':
                if hasattr(data, 'decode') and data.decode()==cell_name:
                    reading_cell=True
                elif data==cell_name:
                    reading_cell=True
            elif datatype=='ENDSTR':
                reading_cell=False
            elif datatype=='BOUNDARY' or datatype=='BOX':
                reading_bound=True
            elif datatype=='PATH':
                reading_path=True
            elif datatype=='ENDEL':
                reading_bound=False
                reading_path=False
            if reading_cell and reading_bound:
                if datatype=='LAYER' and data[0]!=layer:
                    reading_bound=False
                elif datatype=='XY':
                    data_np=np.array(data)
                    xs, ys = data_np[::2]*dbu, data_np[1::2]*dbu
                    print(np.min(xs))
                    if (np.min(xs)>xmin and np.max(xs)<xmax and
                        np.min(ys)>ymin and np.max(ys)<ymax):
                        polygons.append(list(zip(xs, ys)))
            if reading_cell and reading_path:
                if datatype=='LAYER' and data[0]!=layer:
                    reading_path=False
                elif datatype=='WIDTH':
                    width=data[0]/2
                elif datatype=='PATHTYPE':
                    pathtype=data[0]
                    pathtype_conv=dict({0:2,1:1,2:3})
                    pathtype=pathtype_conv[pathtype]
                elif datatype=='XY':
                    points=[[x,y] for x,y in zip(data[::2], data[1::2])]
                    if len(points)>1:
                        line=LineString(points).buffer(width,
                                    cap_style=pathtype)
                        xs, ys=line.exterior.xy
                        xs, ys = np.array(xs)*dbu, np.array(ys)*dbu
                    elif len(points)==1 and pathtype!=1:
                        line=Point(points[0][0], points[0][1]).buffer(width,
                                        cap_style=pathtype)
                        xs, ys=line.exterior.xy
                        xs, ys = np.array(xs)*dbu, np.array(ys)*dbu
                    else:
                        xs = np.array([data[0]+width*np.cos(theta) for theta
                              in np.linspace(0, 2*np.pi, N_per_circle)])*dbu
                        ys = np.array([data[1]+width*np.sin(theta) for theta
                              in np.linspace(0, 2*np.pi, N_per_circle)])*dbu
                    if (np.min(xs)>xmin and np.max(xs)<xmax and
                        np.min(ys)>ymin and np.max(ys)<ymax):
                        polygons.append(list(zip(xs, ys)))
        self.polygons=MultiPolygon([Polygon(points=p,
                                    holes=[]) for p in polygons])   
        if merged:
            self.polygons=self.polygons.merge()
        if centering is None:
            dx, dy, dz=0.,0.,0.
        else:
            dx, dy, dz=(centering[0]-self.polygons.center[0],
                        centering[1]-self.polygons.center[1],
                        centering[2])
        self.polygons.translate([dx, dy, dz])     
        self.kwargs=kwargs
    
    def read(self):
        res=[]
        with open(self.filename, 'rb') as f:
            f.seek(0, 2)
            eof=f.tell()
            f.seek(0, 0)
            while f.tell()!=eof:
                header=f.read(4)
                data_size, tag=struct.unpack('>HH', header)
                data_size-=4
                datatype=self.REV_DATATYPE[tag]
                data = self.parse(tag, f.read(data_size))
                res.append((datatype, data))
        return res
            
    def load(self):
        '''Send the loading to Blender'''
        return PlaneGeom(polygon=self.polygons, **self.kwargs)

if __name__=='__main__':
    from BlenderPy.meshing import Box
    from BlenderPy.sending_data import delete_all
    delete_all()
    loader=GDSLoader(filename=r'C:\Users\Thibault\Documents\postdoc\Masks\trenches.gds',
                     layer=3,xmin=-1000, xmax=3500,
                     ymin=-2000, ymax=2000,
                     cell_name='TOP', thickness=0.15, name='imported')
    trenches=loader.load()
    trenches.scale=[1e-3, 1e-3, 1e-3]
    
    cyls=GDSLoader(filename=r'C:\Users\Thibault\Documents\postdoc\Blender_scripting_workshop\test.gds', layer=4,
                 cell_name='TOP', xmin=0, xmax=25, merged=False,
                 ymin=-6, ymax=6, thickness=2e-3)
    load=cyls.load()

        