#!/usr/bin/env python

#from distutils.core import setup, Extension
from distutils.core import setup
from dsextras import PkgConfigExtension

module1 = PkgConfigExtension(name='spectrumvisualizer',
	pkc_name = 'gstreamer-0.10',
	pkc_version = '',
	sources = ['spectrumvisualizer.c'])

setup(name = 'spectrumvisualizer',
	version = '1.0',
	description = 'This is a demo package',
	ext_modules = [module1])
