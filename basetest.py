#!/usr/bin/env python

import Pipeline
import spectrumvisualizer
import gobject

pipeline = Pipeline.Pipeline("/home/maxi/Musik/Audio/jamendo_track_401871.ogg")
bus = pipeline.get_bus()
spectrum = pipeline.spectrum

class base(spectrumvisualizer.base):
    __gsignals__ = {
        'magnitudes_available' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                            (gobject.TYPE_FLOAT,))
    }

gobject.type_register(base)


#b = spectrumvisualizer.base(spectrum, bus)
b = base(spectrum, bus)

def sig(*args):
	print "mag_av:",args

b.connect("magnitudes_available", sig)
#b.emit("magnitudes_available",1)

print b.called
m=gobject.MainLoop()
gobject.timeout_add(100, pipeline.play)
gobject.timeout_add(1000, m.quit)
m.run()
print b.called
print spectrumvisualizer.base.__gsignals__
