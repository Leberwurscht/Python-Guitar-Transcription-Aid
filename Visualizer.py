#!/usr/bin/env python

import gtk, numpy, cairo
import spectrumvisualizer

REFERENCE_FREQUENCY = 440

class Base(gtk.DrawingArea):
	def __init__(self, spectrum_element,pipeline):
		gtk.DrawingArea.__init__(self)
		self.connect("expose_event", self.draw)

		self.spectrum_element = spectrum_element
#		self.spectrum_element.get_pad("sink").connect("notify", self.on_notify)
		self.pipeline=pipeline
		bus=self.pipeline.get_bus()
		bus.add_signal_watch()
		bus.connect("message::element", self.on_message)

#	def connect_to_bus(self, bus):
#		bus.add_signal_watch()
#		bus.connect("message::element", self.on_message)

	def on_notify(self, *args):
		print args

	def on_message(self, bus, message):
		if message.src==self.spectrum_element:
			bands = message.src.get_property("bands")
			rate = message.src.get_pad("sink").get_negotiated_caps()[0]["rate"]

			bands_array = numpy.arange(bands)
			frequencies = 0.5 * ( bands_array + 0.5 ) * rate / bands
			self.semitones = 12. * numpy.log2(frequencies/REFERENCE_FREQUENCY)

			self.magnitudes = numpy.array(message.structure["magnitude"])

			self.magnitude_min = message.src.get_property("threshold")

			self.queue_draw()

		return True

	def draw(self, widget, event):
		pass

class Base2(gtk.DrawingArea):
	def __init__(self,spectrum_element,pipeline):
		gtk.DrawingArea.__init__(self)
		self.connect("expose_event", self.draw)
		self.spectrum_element = spectrum_element
		self.pipeline=pipeline

		self.visbase = spectrumvisualizer.base(spectrum_element, pipeline)
		self.visbase.connect("magnitudes_available", self.on_magnitudes)

	def on_magnitudes(self,visbase,bands,rate,threshold,magnitudes):
#		print bands,rate,threshold,magnitudes
		bands_array = numpy.arange(bands)
		frequencies = 0.5 * ( bands_array + 0.5 ) * rate / bands
		self.semitones = 12. * numpy.log2(frequencies/REFERENCE_FREQUENCY)

		self.magnitudes = numpy.array(magnitudes)

		self.magnitude_min = threshold

		self.queue_draw()
		
	def draw(self,widget,event): pass

class Fretboard(Base2):
	def __init__(self, spectrum_element,pipeline,**kwargs):
		Base2.__init__(self, spectrum_element,pipeline)

		if "strings" in kwargs: self.strings = kwargs["strings"]
		else: self.strings = {6:-29, 5:-24, 4:-19, 3:-14, 2:-10, 1:-5}

		if "frets" in kwargs: self.frets = kwargs["frets"]
		else: self.frets = 12

		if "rectwidth" in kwargs: self.rectwidth = kwargs["rectwidth"]
		else: self.rectwidth = 30

		if "rectheight" in kwargs: self.rectheight = kwargs["rectheight"]
		else: self.rectheight = 20

		if "paddingx" in kwargs: self.paddingx = kwargs["paddingx"]
		else: self.paddingx = 5

		if "paddingy" in kwargs: self.paddingy = kwargs["paddingy"]
		else: self.paddingy = 7

		if "magnitude_max" in kwargs: self.magnitude_max = kwargs["magnitude_max"]
		else: self.magnitude_max = 0

		if "markers_radius" in kwargs: self.markers_radius = kwargs["markers_radius"]
		else: self.markers_radius = self.rectheight/4

		if "markers" in kwargs: self.markers = kwargs["markers"]
		else: self.markers = [5,7,9]

		if "capo" in kwargs: self.capo = kwargs["capo"]
		else: self.capo = 0

		markerspace = self.rectheight/2 + self.markers_radius

		if len(self.markers)==0: markerspace=0

		self.set_size_request((self.frets+1)*self.rectwidth + 2*self.paddingx, len(self.strings)*self.rectheight + markerspace + 2*self.paddingy)

	def draw(self, widget, event):
		context = widget.window.cairo_create()

		if hasattr(self,"magnitudes"):
			pattern = cairo.LinearGradient(self.semitones[0]*self.rectwidth, 0, self.semitones[-1]*self.rectwidth, 0)

			semitonerange = self.semitones[-1]-self.semitones[0]

			brightness_slope = - 1.0 / (self.magnitude_max - self.magnitude_min)
			brightness_const = 1.0*self.magnitude_max / (self.magnitude_max - self.magnitude_min)

			for i in xrange(len(self.semitones)):
				brightness = brightness_slope * self.magnitudes[i] + brightness_const
				brightness = max(0.,min(1.,brightness))

				pattern.add_color_stop_rgb( ( self.semitones[i]-self.semitones[0] ) / semitonerange, brightness,brightness,brightness)
		else:
			pattern = cairo.SolidPattern(1., 1., 1.)

		matrix = pattern.get_matrix()

		for string,semitone in self.strings.iteritems():
			matrix_copy = cairo.Matrix() * matrix
			matrix_copy.translate(self.rectwidth*semitone - self.rectwidth/2.,0)
			
			pattern.set_matrix(matrix_copy)
			
			for fret in xrange(self.frets+1):
				context.rectangle(self.paddingx+fret*self.rectwidth, self.paddingy+self.rectheight*(string-1), self.rectwidth, self.rectheight)
				context.set_source(pattern)
				context.fill_preserve()

				context.set_line_width(3)
				context.set_source_rgb(0,0,0)
				context.stroke()

		markersy = self.paddingy+self.rectheight*(len(self.strings) + 0.5)

		for i in self.markers:
			context.set_source_rgb(.2,.2,.2)
			context.arc(self.paddingx + self.rectwidth*(i+0.5), markersy, self.markers_radius, 0, 2 * numpy.pi)
			context.fill()

		if self.capo:
			context.set_source_rgb (.4,0,0)
			context.set_line_width(self.rectwidth/3)
			context.set_line_cap(cairo.LINE_CAP_ROUND)
			context.move_to(self.paddingx+self.rectwidth*(self.capo+.3),self.paddingy)
			context.line_to(self.paddingx+self.rectwidth*(self.capo+.3),self.paddingy+self.rectheight*len(self.strings))
			context.stroke()

		context.set_source_rgb (.8,0,0)
		context.set_line_width(self.rectwidth/4)
		context.set_line_cap(cairo.LINE_CAP_ROUND)
		context.move_to(self.paddingx+self.rectwidth*.3,self.paddingy)
		context.line_to(self.paddingx+self.rectwidth*.3,self.paddingy+self.rectheight*len(self.strings))
		context.stroke()

		return True

class SingleString(Fretboard):
	""" Displays spectrum on one string, but also for overtones. """
	def __init__(self, spectrum_element,pipeline,**kwargs):
		if "tune" in kwargs: self.tune = kwargs["tune"]
		else: self.tune = -5

		if "overtones" in kwargs: self.overtones = kwargs["overtones"]
		else: self.overtones = 10

		if "rectheight" in kwargs: self.rectheight = kwargs["rectheight"]
		else: self.rectheight = 10

		kwargs["strings"] = {}
		for i in xrange(1,self.overtones+2):
			kwargs["strings"][i] = self.tune + 12.*numpy.log2(i)

		Fretboard.__init__(self, spectrum_element,pipeline,**kwargs)
