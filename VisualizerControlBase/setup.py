#!/usr/bin/env python

#from distutils.core import setup, Extension
from distutils.core import setup
from dsextras import PkgConfigExtension

visualizercontrolbase = PkgConfigExtension(name='VisualizerControlBase',
	pkc_name = 'gstreamer-0.10',
	pkc_version = '',
	sources = ['visualizercontrolbase.c'])

setup(name = 'visualizercontrolbase',
	version = '1.0',
	description = 'Module containing VisualizerControl base class',
	ext_modules = [visualizercontrolbase])
