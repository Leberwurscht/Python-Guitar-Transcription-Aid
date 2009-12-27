#!/usr/bin/env python

import gst, gobject

import Visualizer

pipeline = gst.Pipeline()

src = gst.element_factory_make("filesrc")
src.set_property("location", "/home/maxi/Musik/ogg/jamendo_track_401871.ogg")
pipeline.add(src)

def on_decoded_pad(bin, pad, *args):
	global convert
	convertpad=convert.get_compatible_pad(pad)
	pad.link(convertpad)

decode = gst.element_factory_make("decodebin")
decode.connect("new-decoded-pad", on_decoded_pad)
pipeline.add(decode)
src.link(decode)

convert = gst.element_factory_make("audioconvert")
pipeline.add(convert)

#fretboard = gst.element_factory_make("spectrum")
fretboard = Visualizer.Base(pipeline.get_bus())
pipeline.add(fretboard)
convert.link(fretboard)

#sink = gst.element_factory_make("gconfaudiosink")
sink = gst.element_factory_make("alsasink")
pipeline.add(sink)
fretboard.link(sink)

pipeline.set_state(gst.STATE_PLAYING)

print pipeline.get_bus()

mainloop = gobject.MainLoop()
mainloop.run()
