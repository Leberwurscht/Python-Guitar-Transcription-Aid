#!/usr/bin/env python

import gst, gobject, array, numpy

MAX_FFT_SAMPLES = 8192

def windowed_fft(data):
	# apply window
	window = numpy.hamming(len(data))
	data *= window

	# fft
	power = numpy.abs(numpy.fft.rfft(data))**2. / len(data)**2.

	return power

class AppSinkPipeline(gst.Pipeline):
	def __init__(self,filename=None):
		gst.Pipeline.__init__(self)

		# filesrc
		self.filesrc = gst.element_factory_make("filesrc")
		self.add(self.filesrc)

		if filename:
			self.set_file(filename)

		# decodebin
		decodebin = gst.element_factory_make("decodebin")
		decodebin.connect("new-decoded-pad", self.on_decoded_pad)
		self.add(decodebin)
		self.filesrc.link(decodebin)

		# audioconvert
		self.convert = gst.element_factory_make("audioconvert")
		self.add(self.convert)

		# audioresample
		resample = gst.element_factory_make("audioresample")
		self.add(resample)
		self.convert.link(resample)

		# capsfilter
		capsfilter = gst.element_factory_make("capsfilter")
		self.caps = gst.caps_from_string('audio/x-raw-float, rate=44100, channels=1, width=32')
		capsfilter.set_property("caps", self.caps)
		self.add(capsfilter)
		resample.link(capsfilter)

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
		capsfilter.link(self.sink)

	def on_decoded_pad(self, bin, pad, last):
		compatible_pad = self.convert.get_compatible_pad(pad)
		pad.link(compatible_pad)

	def set_file(self, filename):
		self.filesrc.set_property("location",filename)

#	def new_buffer(*args):
#		print args
#
#	def eos(*args):
#		self.finished = True
#		self.mainloop.quit()

	def get_data(self,start,stop):
		#print start, stop
		self.set_state(gst.STATE_PAUSED)
		self.get_state()

		self.seek(1.0,gst.FORMAT_TIME,gst.SEEK_FLAG_FLUSH,gst.SEEK_TYPE_SET,start*gst.SECOND,gst.SEEK_TYPE_SET,stop*gst.SECOND)
		self.get_state()

		self.set_state(gst.STATE_PLAYING)
		self.get_state()

		buf = gst.Buffer()
		buf.set_caps(self.caps)

		while True:
			try:
#				print "PULL"
				b = self.sink.emit('pull-buffer')
				if not b: break
#				print "PULLED",len(b)
#				print b.get_caps()
				buf = buf.merge(b)
			except Exception,e: print "Error",e

#		print "DONE",len(buf)
		r = array.array("f", str(buf))

		self.set_state(gst.STATE_PAUSED)
		self.get_state()

		return r

	def get_spectrum(self,start,stop):
		data = self.get_data(start,stop)
		if not len(data)>0: return numpy.array([]), numpy.array([])

		rate = self.caps[0]["rate"]

		samples = min(MAX_FFT_SAMPLES, len(data))	# number of data points to consider for each fft

		ffts = len(data) / int(samples/2.) - 1		# number of ffts

		# calculate average over powers
		power = 0.

		for i in xrange(ffts):
				shift = int(0.5*i*samples)
				power += windowed_fft(data[ shift : shift+samples ])

		power /= ffts

		# calculate frequencies
		bands = len(power)
		frq = 0.5 * ( numpy.arange(bands) + 0.5 ) * rate / bands

		return frq, power

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

		bus = self.get_bus()
		bus.add_signal_watch()

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

		if not start==None and not stop==None:
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
