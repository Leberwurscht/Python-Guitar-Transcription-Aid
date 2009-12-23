#!/usr/bin/env python

import gtk
import gtk.glade
import gst
import math
import cairo
import goocanvas
import threading

AUDIOFREQ=32000
BANDS=4096

freq = [((AUDIOFREQ / 2.) * i + AUDIOFREQ / 4.) / BANDS for i in xrange(BANDS)]

l = len(freq)

class Pipeline(gst.Pipeline):
	def __init__(self):
		# creating the pipeline
		gst.Pipeline.__init__(self,"mypipeline")

		self.src=gst.element_factory_make("audiotestsrc","src")
		self.add(self.src)
#		self.src.set_property("freq",440)

		# create an audioconvert
		self.compconvert = gst.element_factory_make("audioconvert", "compconvert")
		self.add(self.compconvert)
		self.src.link(self.compconvert)

		# create spectrum
		self.spectrum = gst.element_factory_make("spectrum", "spectrum")
		self.spectrum.set_property("bands",BANDS)
		self.add(self.spectrum)
		self.compconvert.link(self.spectrum)

		# create caps
		self.caps = gst.element_factory_make("capsfilter", "filter")
		self.caps.set_property("caps", gst.Caps("audio/x-raw-int, rate=%d"  % AUDIOFREQ))
		self.add(self.caps)
		self.spectrum.link(self.caps)

		# create an alsasink
		self.sink = gst.element_factory_make("alsasink", "alsasink")
		self.add(self.sink)
		self.caps.link(self.sink)

		# spectrum
		bus = self.get_bus()
		bus.add_signal_watch()
		bus.connect("message", self.on_message)

	def on_message(self, bus, message):
		s = message.structure

		if s and s.get_name() == "spectrum":
			mags=s['magnitude']
			print freq[mags.index(max(mags))]
			for i in xrange(100,120):
				print "band %d (freq %g): magnitude %f dB" % (i,freq[i], mags[i])

		return True

	def play(self):
		self.set_state(gst.STATE_PLAYING)
		print "play"

if __name__=="__main__":
	pl = Pipeline()
	pl.play()
	gtk.main()
