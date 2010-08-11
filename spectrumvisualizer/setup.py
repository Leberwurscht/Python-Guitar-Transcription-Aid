#!/usr/bin/env python

#from distutils.core import setup, Extension
from distutils.core import setup
from dsextras import PkgConfigExtension

module1 = PkgConfigExtension(name='spectrumvisualizer',
	pkc_name = 'gobject-2.0',
	pkc_version = '2.2.0',
	sources = ['spectrumvisualizer.c'])

setup(name = 'spectrumvisualizer',
	version = '1.0',
	description = 'This is a demo package',
	ext_modules = [module1])
