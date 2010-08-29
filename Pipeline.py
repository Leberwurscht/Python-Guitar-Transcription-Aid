#!/usr/bin/env python

import gst, gobject

class AppSinkPipeline(gst.Pipeline):
	def __init__(self,filename):
		gst.Pipeline.__init__(self)

#		self.mainloop = gobject.MainLoop()

		# filesrc
		self.filesrc = gst.element_factory_make("filesrc")
		self.filesrc.set_property("location",filename)
		self.add(self.filesrc)

		# decodebin
		decodebin = gst.element_factory_make("decodebin")
		decodebin.connect("new-decoded-pad", self.on_decoded_pad)
		self.add(decodebin)
		self.filesrc.link(decodebin)

		# audioconvert
		self.convert = gst.element_factory_make("audioconvert")
		self.add(self.convert)

		# sink
#		self.sink = gst.element_factory_make("gconfaudiosink")
		self.sink = gst.element_factory_make("appsink")
		self.sink.set_property("sync", False)
#		self.sink.set_property("emit-signals", True)
#		self.sink.connect("new-buffer", self.new_buffer)
#		self.sink.connect("eos", self.eos)
#		bus = self.get_bus()
#		bus.add_signal_watch()
#		bus.connect("message::eos", self.eos)
		self.add(self.sink)
		self.convert.link(self.sink)

	def on_decoded_pad(self, bin, pad, last):
		compatible_pad = self.convert.get_compatible_pad(pad)
		pad.link(compatible_pad)

#	def new_buffer(*args):
#		print args
#
#	def eos(*args):
#		self.finished = True
#		self.mainloop.quit()

	def get_raw(self,start,stop):
		print start, stop
		self.set_state(gst.STATE_PAUSED)
		self.get_state()

		self.seek(1.0,gst.FORMAT_TIME,gst.SEEK_FLAG_FLUSH,gst.SEEK_TYPE_SET,start*gst.SECOND,gst.SEEK_TYPE_SET,stop*gst.SECOND)
		self.get_state()

		self.set_state(gst.STATE_PLAYING)
		self.get_state()

		buf = gst.Buffer()

		while True:
			try:
				print "PULL"
				b = self.sink.emit('pull-buffer')
				if not buf: break
				print "PULLED",len(b)
				buf = buf.merge(b)
			except Exception,e: print "Error",e

		print "DONE",len(buf)

#	def get_raw(self,start,stop):
#		print start, stop
#		self.set_state(gst.STATE_PAUSED)
#		self.get_state()
#
#		self.seek(1.0,gst.FORMAT_TIME,gst.SEEK_FLAG_FLUSH,gst.SEEK_TYPE_SET,start*gst.SECOND,gst.SEEK_TYPE_SET,stop*gst.SECOND)
#		self.get_state()
#
#		self.finished = False
#		self.set_state(gst.STATE_PLAYING)
#		self.get_state()
#
#		print "1"
#		if not self.finished: self.mainloop.run()
#		print "2"
#
#		while True:
##			try:
##				buf = self.sink.emit('pull-buffer')
##			except SystemError, e:
##				# it's probably a bug that emits triggers a SystemError
##				print 'SystemError', e
##				break
##
##			print buf
#
#		self.set_state(gst.STATE_PAUSED)
#		self.get_state()

class Pipeline(gst.Pipeline):
	def __init__(self,filename=None, bands=4096):
		gst.Pipeline.__init__(self)

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
		self.spectrum = gst.element_factory_make("spectrum","spectrum")
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
		self.set_state(gst.STATE_NULL)
		self.get_state()

		self.filesrc.set_property("location",filename)

		self.set_state(gst.STATE_PAUSED)
		self.get_state()
		self.duration = 1.*self.query_duration(gst.FORMAT_TIME)[0] / gst.SECOND

	def set_bands(self, bands):
		self.spectrum.set_property("bands",bands)

	def on_decoded_pad(self, bin, pad, last):
		compatible_pad = self.convert.get_compatible_pad(pad)
		pad.link(compatible_pad)

	def play(self,rate=1.0,start=None,stop=None):
		self.set_state(gst.STATE_PAUSED)
		self.get_state()

		if start and stop:
			self.seek(rate,gst.FORMAT_TIME,gst.SEEK_FLAG_FLUSH,gst.SEEK_TYPE_SET,start*gst.SECOND,gst.SEEK_TYPE_SET,stop*gst.SECOND)
			self.get_state()
		elif start:
			self.seek(rate,gst.FORMAT_TIME,gst.SEEK_FLAG_FLUSH,gst.SEEK_TYPE_SET,start*gst.SECOND,gst.SEEK_TYPE_NONE,-1)
			self.get_state()
		else:
			self.seek(rate,gst.FORMAT_TIME,gst.SEEK_FLAG_FLUSH,gst.SEEK_TYPE_NONE,-1,gst.SEEK_TYPE_NONE,-1)
			self.get_state()
		
		self.set_state(gst.STATE_PLAYING)
		return self.get_state()

	def pause(self):
		self.set_state(gst.STATE_PAUSED)
		return self.get_state()

	def get_position(self):
		return 1.*self.query_position(gst.FORMAT_TIME)[0] / gst.SECOND
