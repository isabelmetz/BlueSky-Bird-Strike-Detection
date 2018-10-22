#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from distutils.core import setup, Extension
import numpy as np

ext_modules = [Extension('cbirds', sources=['CDBirds_Isabel.cpp'])]

setup(name='cbirds', version='1.0', include_dirs=[np.get_include(), '../../../tools/ctools'],
      ext_modules=ext_modules)