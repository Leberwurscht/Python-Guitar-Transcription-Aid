#!/usr/bin/env python

#from distutils.core import setup, Extension
from distutils.core import setup
from dsextras import PkgConfigExtension

spectrumdata = PkgConfigExtension(name='SpectrumData',
	pkc_name = 'gstreamer-0.10',
	pkc_version = '',
	sources = ['spectrumdata.c'])

setup(name = 'spectrumdata',
	version = '1.0',
	description = 'Module containing SpectrumData base class',
	ext_modules = [spectrumdata])
