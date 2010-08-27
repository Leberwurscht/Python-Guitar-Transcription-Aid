#!/usr/bin/env python

import gtk, numpy, cairo
import spectrumvisualizer, peakdetector

REFERENCE_FREQUENCY = 440

def integrate(frequency, power, semitone, overtone=0):
	center_frequency = REFERENCE_FREQUENCY * 1.0594630943592953**semitone
	center_frequency *= overtone+1

	# range is one semitone, so one quartertone up and down
	lower_limit = center_frequency * 0.97153194115360586
	upper_limit = center_frequency * 1.0293022366434921

	### interpolate power(lower_limit) and power(upper_limit)
	lower_right_index = numpy.min(numpy.nonzero(frequency > lower_limit))
	lower_left_index = lower_right_index-1

	lower_left = frequency[lower_left_index]
	lower_left_power = power[lower_left_index]

	lower_right = frequency[lower_right_index]
	lower_right_power = power[lower_right_index]

	upper_right_index = numpy.min(numpy.nonzero(frequency > upper_limit))
	upper_left_index = upper_right_index-1

	upper_left = frequency[upper_left_index]
	upper_left_power = power[upper_left_index]

	upper_right = frequency[upper_right_index]
	upper_right_power = power[upper_right_index]

	lower_limit_interpolated = (lower_right-lower_limit)*lower_left_power + (lower_limit-lower_left)*lower_right_power
	lower_limit_interpolated /= lower_right-lower_left

	upper_limit_interpolated = (upper_right-upper_limit)*upper_left_power + (upper_limit-upper_left)*upper_right_power
	upper_limit_interpolated /= upper_right-upper_left

	# build frequency, power for (lower_limit, upper_limit) range
	f = [lower_limit]
	p = [lower_limit_interpolated]

	for i in xrange(lower_right_index, upper_right_index):
		f.append(frequency[i])
		p.append(power[i])

	f.append(upper_limit)
	p.append(upper_limit_interpolated)

	r = numpy.trapz(p, f)

	return r

class Base(gtk.DrawingArea):
	def __init__(self,pipeline,spectrum_element=False):
		gtk.DrawingArea.__init__(self)
		self.connect("expose_event", self.draw)

		if spectrum_element:
			self.spectrum_element = spectrum_element
		else:
			self.spectrum_element = pipeline.get_by_name('spectrum')
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
			self.frequencies = 0.5 * ( bands_array + 0.5 ) * rate / bands
			self.semitones = 12. * numpy.log2(self.frequencies/REFERENCE_FREQUENCY)

			self.magnitudes = numpy.array(message.structure["magnitude"])

			self.magnitude_min = message.src.get_property("threshold")

			self.queue_draw()

		return True

	def draw(self, widget, event):
		pass

class Base2(gtk.DrawingArea):
	def __init__(self,pipeline,spectrum_element=False):
		gtk.DrawingArea.__init__(self)
		self.connect("expose_event", self.draw)
		self.pipeline=pipeline
		if spectrum_element:
			self.spectrum_element = spectrum_element
		else:
			self.spectrum_element = pipeline.get_by_name('spectrum')

		self.visbase = spectrumvisualizer.base(self.spectrum_element, pipeline)
		self.visbase.connect("magnitudes_available", self.on_magnitudes)

	def on_magnitudes(self,visbase,bands,rate,threshold,magnitudes):
#		print bands,rate,threshold,magnitudes
		bands_array = numpy.arange(bands)
		self.frequencies = 0.5 * ( bands_array + 0.5 ) * rate / bands
		self.semitones = 12. * numpy.log2(self.frequencies/REFERENCE_FREQUENCY)

		self.magnitudes = numpy.array(magnitudes)

		self.magnitude_min = threshold

		self.queue_draw()
		
	def draw(self,widget,event): pass

class Fretboard(Base2):
	def __init__(self,*args,**kwargs):
		Base2.__init__(self,*args)

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

		brightness_slope=0
		brightness_const=0
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

		if hasattr(self,"magnitudes"):
			power = peakdetector.level_to_power(self.magnitudes)
			st = peakdetector.get_tones(self.frequencies, power)
			if not st:return True
			print st
			for semitone,power in st.iteritems():
				for string,stringtone in self.strings.iteritems():
					fret = semitone-stringtone
					if fret<0 or fret>self.frets: continue
					print string,fret
					context.rectangle(self.paddingx+fret*self.rectwidth, self.paddingy+self.rectheight*(string-1), self.rectwidth, self.rectheight)

					level=peakdetector.power_to_level(power)
					brightness = brightness_slope * level + brightness_const
					brightness = max(0.,min(1.,brightness))
					context.set_source_rgb(brightness,0,0)
					context.fill()

		return True

class SingleString(Fretboard):
	""" Displays spectrum on one string, but also for overtones. """
	def __init__(self,*args,**kwargs):
		if "tune" in kwargs: self.tune = kwargs["tune"]
		else: self.tune = -5

		if "overtones" in kwargs: self.overtones = kwargs["overtones"]
		else: self.overtones = 5

		if "rectheight" in kwargs: self.rectheight = kwargs["rectheight"]
		else: self.rectheight = 10

		kwargs["strings"] = {}
		for i in xrange(1,self.overtones+2):
			kwargs["strings"][i] = self.tune + 12.*numpy.log2(i)

		Fretboard.__init__(self,*args,**kwargs)

		markerspace = self.rectheight/2 + self.markers_radius
		self.sumy = len(self.strings)*self.rectheight + markerspace + 2*self.paddingy
		self.set_size_request((self.frets+1)*self.rectwidth + 2*self.paddingx, self.sumy + self.rectheight + self.paddingy)

	def draw(self, widget, event):
		Fretboard.draw(self, widget, event)

		if not hasattr(self,"magnitudes"): return True

#		power = 1.26**self.magnitudes # from dB to power
#		power = self.magnitudes

		brightness_slope = - 1.0 / (self.magnitude_max - self.magnitude_min)
		brightness_const = 1.0*self.magnitude_max / (self.magnitude_max - self.magnitude_min)

		brightness = brightness_slope * self.magnitudes + brightness_const
		brightness = 1.-numpy.clip(brightness, 0.,1.)
		power = brightness

		context = widget.window.cairo_create()

		for fret in xrange(self.frets+1):
			context.rectangle(self.paddingx+fret*self.rectwidth, self.sumy, self.rectwidth, self.rectheight)

			# calculate total power, including overtones
			t=0
			for i in xrange(self.overtones+1):
				t += integrate(self.frequencies, power, self.tune+fret, i)

			# convert to dB
			dB = 4.3269116591383208 * numpy.log(t)
			print fret,t,dB

			# calculate brightness
#			mag_max = self.magnitude_max * self.overtones/2.
			## in dB:
#			minimum=4.3269116591383208 * numpy.log(1.26**self.magnitude_min * (self.overtones+1))
#			maximum=4.3269116591383208 * numpy.log(1.26**self.magnitude_max * (self.overtones+1)*.6)
			## in power:
#			minimum = 1.26**self.magnitude_min * (self.overtones+1)
#			maximum = 1.26**self.magnitude_max * (self.overtones+1)*.05
#			maximum = 0.001
#			print minimum, maximum
			minimum = 0
			maximum = 5
			brightness_slope = - 1.0 / (maximum - minimum)
			brightness_const = 1.0*maximum / (maximum - minimum)

			brightness = brightness_slope * t + brightness_const
			brightness = max(0.,min(1.,brightness))
			
			context.set_source_rgb(brightness,brightness,brightness)
			context.fill_preserve()

			context.set_line_width(3)
			context.set_source_rgb(0,0,0)
			context.stroke()
