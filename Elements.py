#!/usr/bin/env python

import gobject
gobject.threads_init()
import gst

import Math, numpy

class Noise(gst.BaseSrc):
	__gsttemplates__ = (
		gst.PadTemplate("src",
		gst.PAD_SRC,
		gst.PAD_ALWAYS,
		gst.Caps("audio/x-raw-spectrum"))
	)
	__gstdetails__ = ("spectrum_noise", "Audio/Source", "src for noise spectrum", "Leberwurscht")

	def __init__(self):
		self.__gobject_init__()
		self.pad = self.get_pad("src")
		self.pad.use_fixed_caps()
		phase = numpy.random.random(2049)*2.*numpy.pi
		self.spectrum = numpy.exp(phase*1j)

	def do_create(self, offset, size):
		b = gst.Buffer(self.spectrum)
		b.set_caps(self.pad.get_caps())
		return gst.FLOW_OK, b

gobject.type_register(Noise)
gst.element_register(Noise, "spectrum_noise")

class FFT(gst.Element):
	_sinkpadtemplate = gst.PadTemplate ("sink",
		gst.PAD_SINK,
		gst.PAD_ALWAYS,
		gst.Caps("audio/x-raw-float, rate=44100, channels=1, width=64, endianness=1234"))
	_srcpadtemplate = gst.PadTemplate ("src",
		gst.PAD_SRC,
		gst.PAD_ALWAYS,
		gst.Caps("audio/x-raw-spectrum"))
	__gstdetails__ = ("fft", "Audio/Filter", "fft element", "Leberwurscht")

#	__gproperties__ = {"":(gobject.TYPE_INT, "mode", "editing mode", 0, MODES_NUM-1, MODE_DEFAULT, gobject.PARAM_READWRITE)}

	def __init__(self):
		gst.Element.__init__(self)
		self.sinkpad = gst.Pad(self._sinkpadtemplate, "sink")
		self.sinkpad.use_fixed_caps()
		self.srcpad = gst.Pad(self._srcpadtemplate, "src")
		self.srcpad.use_fixed_caps()
		self.sinkpad.set_chain_function(self.chainfunc)
		self.sinkpad.set_event_function(self.eventfunc)
		self.add_pad (self.sinkpad)
		self.srcpad.set_event_function(self.srceventfunc)
		self.add_pad (self.srcpad)

		self.adapter = gst.Adapter()

	def chainfunc(self, pad, buffer):
		# fixme: need to reset adapter when starting - see gstspectrum.c
		self.adapter.push(buffer)
		end_time = buffer.timestamp + buffer.duration
		gst.log("Got buffer with ts %d and length %d" % (buffer.timestamp, len(buffer)))

		l = 4096
		bytes_num = l*8

		while self.adapter.available() >= bytes_num:
			time_till_end = int( self.adapter.available()/8. / 44100 * gst.SECOND )
			data = numpy.frombuffer(self.adapter.peek(bytes_num))
			fft = numpy.fft.rfft(data) # length of this array is l/2 + 1
			b = gst.Buffer(fft)
			b.timestamp = end_time - time_till_end
			b.set_caps(self.srcpad.get_caps())
			self.srcpad.push(b)
			self.adapter.flush(bytes_num)

		return gst.FLOW_OK

	def eventfunc(self, pad, event):
		return self.srcpad.push_event(event)
	def srceventfunc (self, pad, event):
		return self.sinkpad.push_event(event)

gobject.type_register(FFT)
gst.element_register(FFT, "fft")

class IFFT(gst.Element):
	_sinkpadtemplate = gst.PadTemplate ("sink",
		gst.PAD_SINK,
		gst.PAD_ALWAYS,
		gst.Caps("audio/x-raw-spectrum"))
	_srcpadtemplate = gst.PadTemplate ("src",
		gst.PAD_SRC,
		gst.PAD_ALWAYS,
		gst.Caps("audio/x-raw-float, rate=44100, channels=1, width=64, endianness=1234"))
	__gstdetails__ = ("ifft", "Audio/Filter", "inverse fft element", "Leberwurscht")

	def __init__(self):
		gst.Element.__init__(self)
		self.sinkpad = gst.Pad(self._sinkpadtemplate, "sink")
		self.sinkpad.use_fixed_caps()
		self.srcpad = gst.Pad(self._srcpadtemplate, "src")
		self.srcpad.use_fixed_caps()
		self.sinkpad.set_chain_function(self.chainfunc)
		self.sinkpad.set_event_function(self.eventfunc)
		self.add_pad (self.sinkpad)
		self.srcpad.set_event_function(self.srceventfunc)
		self.add_pad (self.srcpad)

	def chainfunc(self, pad, buffer):
		gst.log ("Passing buffer with ts %d" % (buffer.timestamp))

		fft = numpy.frombuffer(buffer, numpy.complex128)
		l = 2*len(fft) - 2
		data = numpy.fft.irfft(fft, l)
		b = gst.Buffer(data)
		b.set_caps(self.srcpad.get_caps())
		b.timestamp = buffer.timestamp
		return self.srcpad.push(b)

	def eventfunc(self, pad, event):
		return self.srcpad.push_event(event)
	def srceventfunc (self, pad, event):
		return self.sinkpad.push_event(event)

gobject.type_register(IFFT)
gst.element_register(IFFT, "ifft")

class Equalizer(gst.Element):
	_sinkpadtemplate = gst.PadTemplate ("sink",
		gst.PAD_SINK,
		gst.PAD_ALWAYS,
		gst.Caps("audio/x-raw-spectrum"))
	_srcpadtemplate = gst.PadTemplate ("src",
		gst.PAD_SRC,
		gst.PAD_ALWAYS,
		gst.Caps("audio/x-raw-spectrum"))
	__gstdetails__ = ("spectrum_equalizer", "Audio/Filter", "equalizer that deals with spectrum data", "Leberwurscht")

	__gproperties__ = {"transmission":(gobject.TYPE_PYOBJECT, "transmission", "transmission for each spectral band", gobject.PARAM_READWRITE)}

	def __init__(self, *args, **kwargs):
		self.frequencies = Math.get_frq(2049, 44100)
		self.transmission = None

		gst.Element.__init__(self, *args, **kwargs)

		if not self.transmission:
			self.transmission = numpy.ones(2049)

		self.sinkpad = gst.Pad(self._sinkpadtemplate, "sink")
		self.sinkpad.use_fixed_caps()
		self.srcpad = gst.Pad(self._srcpadtemplate, "src")
		self.srcpad.use_fixed_caps()
		self.sinkpad.set_chain_function(self.chainfunc)
		self.sinkpad.set_event_function(self.eventfunc)
		self.add_pad (self.sinkpad)
		self.srcpad.set_event_function(self.srceventfunc)
		self.add_pad (self.srcpad)

	# custom property
	def do_get_property(self,pspec):
		return getattr(self, pspec.name)

	def do_set_property(self,pspec,value):
		setattr(self, pspec.name, value)

	def chainfunc(self, pad, buffer):
		gst.log ("Passing buffer with ts %d" % (buffer.timestamp))

		fft = numpy.frombuffer(buffer, numpy.complex128)
		fft = fft * self.transmission
		b = gst.Buffer(fft)
		b.set_caps(self.srcpad.get_caps())
		b.timestamp = buffer.timestamp
		return self.srcpad.push(b)

	def eventfunc(self, pad, event):
		return self.srcpad.push_event(event)
	def srceventfunc (self, pad, event):
		return self.sinkpad.push_event(event)

gobject.type_register(Equalizer)
gst.element_register(Equalizer, "spectrum_equalizer")
