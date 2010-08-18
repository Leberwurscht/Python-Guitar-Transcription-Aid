#!/usr/bin/env python

import Pipeline
import spectrumvisualizer
import gobject
import array
import gtk

gobject.threads_init()

pipeline = Pipeline.Pipeline("/home/maxi/Musik/Audio/jamendo_track_401871.ogg")
bus = pipeline.get_bus()
spectrum = pipeline.spectrum

b = spectrumvisualizer.base(spectrum, pipeline)

def sig(*args):
	print "mag_av:",args
#	print "1.0 " * 4000
	cnt=0
	cpy=[]
#	for i in args[-1]:
#		if cnt%400==0: print i,
#		cpy = args[-1][cnt]
#		args[-1][cnt]+=1.
#		cnt += 1
	pass

b.connect("magnitudes_available", sig)

m=gobject.MainLoop()
gobject.timeout_add(100, pipeline.play)
gobject.timeout_add(1000, m.quit)
m.run()
