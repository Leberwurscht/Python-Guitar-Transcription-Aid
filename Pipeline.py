#!/usr/bin/env python

import gst

class Pipeline(gst.Pipeline):
	def __init__(self,filename=None, bands=4096):
		gst.Pipeline.__init__(self)

		self.rate=1.
		self.start_pos=0.
		self.stop_pos=None

		# filesrc
		self.filesrc = gst.element_factory_make("filesrc")
		self.add(self.filesrc)

		# decodebin
		decodebin = gst.element_factory_make("decodebin")
		decodebin.connect("new-decoded-pad", self.on_decoded_pad)
		self.add(decodebin)
		self.filesrc.link(decodebin)

		# audioconvert
		self.convert = gst.element_factory_make("audioconvert")
		self.add(self.convert)

		# scaletempo
		scaletempo = gst.element_factory_make("scaletempo")
		self.add(scaletempo)
		self.convert.link(scaletempo)

		# spectrum
		self.spectrum = gst.element_factory_make("spectrum")
		self.add(self.spectrum)
		scaletempo.link(self.spectrum)

		# sink
		sink = gst.element_factory_make("gconfaudiosink")
		self.add(sink)
		self.spectrum.link(sink)

		# set properties
		self.set_bands(bands)
		if not filename==None: self.set_file(filename)

	def set_file(self, filename):
		self.filesrc.set_property("location",filename)

		self.set_state(gst.STATE_PAUSED)
		self.get_state()
		self.duration = 1.*self.query_duration(gst.FORMAT_TIME)[0] / gst.SECOND

	def set_bands(self, bands):
		self.spectrum.set_property("bands",bands)

	def on_decoded_pad(self, bin, pad, last):
		compatible_pad = self.convert.get_compatible_pad(pad)
		pad.link(compatible_pad)

	def set_rate(self,rate):
		self.rate=rate
		print self.seek(self.rate,gst.FORMAT_TIME,gst.SEEK_FLAG_FLUSH,gst.SEEK_TYPE_NONE,-1,gst.SEEK_TYPE_NONE,-1)

	def play(self,start=None,stop=None):
		if start==None: start=self.start_pos
		if stop==None: stop=self.stop_pos

		if stop<0:
			self.seek(self.rate,gst.FORMAT_TIME,gst.SEEK_FLAG_FLUSH,gst.SEEK_TYPE_SET,start*gst.SECOND,gst.SEEK_TYPE_NONE,-1)
		else:
			self.seek(self.rate,gst.FORMAT_TIME,gst.SEEK_FLAG_FLUSH,gst.SEEK_TYPE_SET,start*gst.SECOND,gst.SEEK_TYPE_SET,stop*gst.SECOND)
		
		self.start_pos=start
		self.stop_pos=stop
		self.set_state(gst.STATE_PLAYING)

	def pause(self):
		self.set_state(gst.STATE_PAUSED)

	def stop(self):
		self.set_state(gst.STATE_NULL)

	def get_position(self):
		return 1.*self.query_position(gst.FORMAT_TIME)[0] / gst.SECOND
