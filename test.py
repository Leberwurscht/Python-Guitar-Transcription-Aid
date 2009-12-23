#!/usr/bin/env python

import gst, gobject

BANDS=4096
AUDIOFREQ=32000

bin = gst.Pipeline("bin")

src = gst.element_factory_make("audiotestsrc", "src")

audioconvert = gst.element_factory_make("audioconvert")

spectrum = gst.element_factory_make("spectrum","spectrum")
spectrum.set_property("bands",BANDS)

sink = gst.element_factory_make("alsasink","sink")

caps = gst.Caps("audio/x-raw-int",rate=AUDIOFREQ)


