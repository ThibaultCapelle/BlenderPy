# -*- coding: utf-8 -*-
"""
Created on Sat Dec 25 17:25:42 2021

@author: Thibault
"""

from setuptools import setup

setup(name='BlenderPy',
      version='1.0',
      description='Python Blender high level API ',
      author='Thibault CAPELLE',
      author_email='capelle_thibault@riseup.net',
      packages=['BlenderPy'],
	  package_dir={'BlenderPy': 'BlenderPy'}
     )