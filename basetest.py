#!/usr/bin/env python

import Pipeline
import spectrumvisualizer
import gobject

pipeline = Pipeline.Pipeline("/home/maxi/Musik/Audio/jamendo_track_401871.ogg")
bus = pipeline.get_bus()
spectrum = pipeline.spectrum

b = spectrumvisualizer.base(spectrum, pipeline)

def sig(*args):
	print "mag_av:",args

b.connect("magnitudes_available", sig)

m=gobject.MainLoop()
gobject.timeout_add(100, pipeline.play)
gobject.timeout_add(1000, m.quit)
m.run()
