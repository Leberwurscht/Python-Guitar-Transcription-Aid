#!/usr/bin/env python

import Pipeline
import spectrumvisualizer
import gobject

pipeline = Pipeline.Pipeline("/home/maxi/Musik/Audio/jamendo_track_401871.ogg")
bus = pipeline.get_bus()
spectrum = pipeline.spectrum

b = spectrumvisualizer.base(spectrum, bus)
pipeline.play()

print b.called
m=gobject.MainLoop()
gobject.timeout_add(1000, m.quit)
m.run()
print b.called
