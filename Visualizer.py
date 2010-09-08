#!/usr/bin/env python

import gtk, numpy, cairo
import spectrumvisualizer
import gst

REFERENCE_FREQUENCY = 440
standard_tuning = {6:-29, 5:-24, 4:-19, 3:-14, 2:-10, 1:-5}
note_names = ["a","ais","b","c","cis","d","dis","e","f","fis","g","gis"]

#class RhythmWindow(gtk.Window):
#	def __init__(self,project,**kwargs):
#		gtk.Window.__init__(self,**kwargs)
#
#		self.project = project
#
#		button = gtk.Button("Tap")
#		button.connect("pressed", self.tap)
#		button.connect("key-press-event", self.tap)
#		button.set_size_request(100,60)
#		self.add(button)
#		self.show_all()
#
#	def tap(self,*args):
#		if not self.project: return
#
#		self.project.timeline.rhythm.add_tap()

class CompareWindow(gtk.Window):
	def __init__(self, *args, **kwargs):
		if "strings" in kwargs:
			self.strings = kwargs["strings"]
			del kwargs["strings"]
		else:
			self.strings = standard_tuning

		if "frets" in kwargs:
			self.frets = kwargs["frets"]
			del kwargs["frets"]
		else:
			self.frets = 12

		gtk.Window.__init__(self,*args,**kwargs)

		self.set_title("Compare")

		vbox = gtk.VBox()
		self.add(vbox)

		hbox = gtk.HBox()
		hbox.add(gtk.Label("Volume"))
		self.adj = gtk.Adjustment(0.04,0.0,10.0,0.01)
		spinbtn = gtk.SpinButton(self.adj,0.01,2)
		hbox.add(spinbtn)
		vbox.add(hbox)

		self.table = gtk.Table(len(self.strings), self.frets)
		vbox.add(self.table)

		for string,tuning in self.strings.iteritems():
			for fret in xrange(self.frets+1):
				semitone = tuning+fret
				name = note_names[(semitone+1000*12) % 12]
				btn = gtk.Button(name)
				btn.set_size_request(40,30)
				if fret==0: btn.set_relief(gtk.RELIEF_NONE)
				frq = semitone_to_frequency(semitone)
				btn.connect("pressed",self.press,frq)
				btn.connect("released",self.release)
				btn.set_tooltip_text(str(frq)+" Hz")
				self.table.attach(btn,fret,fret+1,string-1,string)

		self.show_all()

		self.pipeline = gst.parse_launch("audiotestsrc name=src wave=saw ! volume name=volume ! gconfaudiosink")

	def press(self,btn,frq):
		self.pipeline.get_by_name("volume").set_property("volume", self.adj.get_value())
		self.pipeline.get_by_name("src").set_property("freq", frq)
		self.pipeline.set_state(gst.STATE_PLAYING)
	def release(self,semitone):
		self.pipeline.set_state(gst.STATE_NULL)

def integrate(x, y, lower_limit, upper_limit):
#	center_frequency = REFERENCE_FREQUENCY * 1.0594630943592953**semitone
#	center_frequency *= overtone+1

	# range is one semitone, so one quartertone up and down
#	lower_limit = center_frequency * 0.97153194115360586
#	upper_limit = center_frequency * 1.0293022366434921

	### interpolate power(lower_limit) and power(upper_limit)
	lower_right_index = numpy.min(numpy.nonzero(x > lower_limit))
	lower_left_index = lower_right_index-1

	lower_left = x[lower_left_index]
	lower_left_y = y[lower_left_index]

	lower_right = x[lower_right_index]
	lower_right_y = y[lower_right_index]

	upper_right_index = numpy.min(numpy.nonzero(x > upper_limit))
	upper_left_index = upper_right_index-1

	upper_left = x[upper_left_index]
	upper_left_y = y[upper_left_index]

	upper_right = x[upper_right_index]
	upper_right_y = y[upper_right_index]

	lower_limit_interpolated = (lower_right-lower_limit)*lower_left_y + (lower_limit-lower_left)*lower_right_y
	lower_limit_interpolated /= lower_right-lower_left

	upper_limit_interpolated = (upper_right-upper_limit)*upper_left_y + (upper_limit-upper_left)*upper_right_y
	upper_limit_interpolated /= upper_right-upper_left

	# build frequency, power for (lower_limit, upper_limit) range
#	newx = [lower_limit]
#	newy = [lower_limit_interpolated]
#
#	for i in xrange(lower_right_index, upper_right_index):
#		f.append(x[i])
#		p.append(y[i])
#
#	newx.append(upper_limit)
#	newy.append(upper_limit_interpolated)

	int_x = numpy.zeros(upper_right_index-lower_right_index + 2)
	int_y = numpy.zeros(upper_right_index-lower_right_index + 2)

	int_x[0] = lower_limit
	int_x[1:-1] = x[lower_right_index:upper_right_index]
	int_x[-1] = upper_limit

	int_y[0] = lower_limit_interpolated
	int_y[1:-1] = y[lower_right_index:upper_right_index]
	int_y[-1] = upper_limit_interpolated

	r = numpy.trapz(int_y, int_x)

	return r

class VisualizerWindow(gtk.Window):
	def __init__(self, vislist, title, visualizer):
		gtk.Window.__init__(self)
		self.visualizer = visualizer
		self.vislist = vislist
		self.vislist.append(self)

		self.set_title(title)
		self.add(visualizer)
		self.show_all()

		self.connect("delete-event", self.delete)

	def delete(self, *args):
		self.vislist.remove(self)
		return False

def power_to_magnitude(power, threshold=-60):
	magnitudes = numpy.maximum(threshold, 10.0*numpy.log10(power))
	return magnitudes

def magnitude_to_power(magnitude):
	power = 10.0**(magnitude/10.0)
	return power

def frequency_to_semitone(frequency):
	semitone = 12.*numpy.log2(frequency/REFERENCE_FREQUENCY)
	return semitone

def semitone_to_frequency(semitone):
	frequency = REFERENCE_FREQUENCY * (2.**(1./12.))**semitone
	return frequency

class SpectrumData:
	""" holds data for visualizers, calculates and caches different scales """
	def __init__(self, frequency, **kwargs):
		self.frequency = frequency
		self.power = None
		self.magnitude = None
		self.brightness = None
		self.semitone = None

		if "method" in kwargs:
			self.method = kwargs["method"]
		else:
			self.method = "from_magnitude"

		if self.method=="from_magnitude":
			if "min_magnitude" in kwargs:
				self.min_magnitude = kwargs["min_magnitude"]
			else:
				self.min_magnitude = None #-60.

			if "max_magnitude" in kwargs:
				self.max_magnitude = kwargs["max_magnitude"]
			else:
				self.max_magnitude = None #0.
		elif self.method=="from_power":
			if "min_power" in kwargs:
				self.min_power = kwargs["min_power"]
			else:
				self.min_power = None #0.0

			if "max_power" in kwargs:
				self.max_power = kwargs["max_power"]
			else:
				self.max_power = None #0.001
		else:
			raise Exception, "invalid method"

		if "magnitude" in kwargs:
			self.magnitude = kwargs["magnitude"]
		elif "power" in kwargs:
			self.power = kwargs["power"]
		else:
			raise Exception, "Need magnitude or power as keyword argument"

	def get_semitone(self):
		if self.semitone==None: self.semitone = frequency_to_semitone(self.frequency)
		return self.semitone

	def get_magnitude(self):
		if self.magnitude==None: self.magnitude = power_to_magnitude(self.power)
		return self.magnitude

	def get_power(self):
		if self.power==None: self.power = magnitude_to_power(self.magnitude)
		return self.power

	def get_brightness(self):
		if self.brightness==None:
			if self.method=="from_magnitude":
				if self.max_magnitude==None:
					self.max_magnitude=numpy.max(self.get_magnitude())
				if self.min_magnitude==None:
					self.min_magnitude=numpy.min(self.get_magnitude())

				brightness_slope = - 1.0 / (self.max_magnitude - self.min_magnitude)
				brightness_const = 1.0 * self.max_magnitude / (self.max_magnitude- self.min_magnitude)

				brightness = brightness_slope * self.get_magnitude() + brightness_const
				self.brightness = numpy.maximum(0.,numpy.minimum(1.,brightness))
			elif self.method=="from_power":
				if self.max_power==None:
					self.max_power=numpy.max(self.get_power())
				if self.min_power==None:
					self.min_power=numpy.min(self.get_power())

				brightness_slope = - 1.0 / (self.max_power - self.min_power)
				brightness_const = 1.0 * self.max_power/ (self.max_power - self.min_power)

				brightness = brightness_slope * self.get_power() + brightness_const
				self.brightness = numpy.maximum(0.,numpy.minimum(1.,brightness))

		return self.brightness

	def get_total_power_in_semitone_range(self,lower,upper,overtones=10):
		l = semitone_to_frequency(lower)
		u = semitone_to_frequency(upper)
		return self.get_total_power_in_frequency_range(l,u,overtones)

	def get_total_power_in_frequency_range(self,lower,upper,overtones=10):
		total = 0

		for i in xrange(overtones+1):
			total += integrate(self.frequency, self.get_power(), lower*(i+1), upper*(i+1))

		return total

		# spectrum element calculation for comparison:
#		magnitude = max(threshold, dB)
#		dB = 10.0 * log10(power)
#		power = fft_result**2 / nfft**2
#		nfft = len(data) = 2*bands - 2,
#		bands=len(fft_result)
#		fft_result = fft(hamming(data))
#		len(fft_result) = len(data)/2+1 => len(data)=2*bands-2

class Fretboard(gtk.DrawingArea):
	def __init__(self,*args,**kwargs):
		gtk.DrawingArea.__init__(self,*args)
		self.connect("expose_event", self.draw)

		if "strings" in kwargs: self.strings = kwargs["strings"]
		else: self.strings = standard_tuning

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

		self.spectrum = None

	def set_spectrum(self, spectrum):
		self.spectrum = spectrum

	def draw(self, widget, event):
		context = widget.window.cairo_create()

		# build pattern
		prepared_fretboard = self.prepare_fretboard()
#		matrix, pattern = self.prepare_patterns()

		for string,semitone in self.strings.iteritems():
			prepared_string = self.prepare_string(semitone,prepared_fretboard)

			for fret in xrange(self.frets+1):
				context.rectangle(self.paddingx+fret*self.rectwidth, self.paddingy+self.rectheight*(string-1), self.rectwidth, self.rectheight)
				self.set_fill_source(context,semitone,fret,prepared_fretboard,prepared_string)
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

	def set_fill_source(self,context,semitone,fret,prepared_fretboard,prepared_string):
		matrix, pattern = prepared_fretboard
		context.set_source(pattern)

	def prepare_fretboard(self):
		if self.spectrum:
			semitones = self.spectrum.get_semitone()
			brightness = self.spectrum.get_brightness()
			semitonerange = semitones[-1]-semitones[0]
			pattern = cairo.LinearGradient(0, 0, semitonerange, 0)

			for i in xrange(len(semitones)):
				b = brightness[i]
				pattern.add_color_stop_rgb( ( semitones[i]-semitones[0] ) / semitonerange, b,b,b)

			matrix = pattern.get_matrix()
			matrix.scale(1./self.rectwidth,1.)
			matrix.translate(-self.paddingx-0.5*self.rectwidth, 0)
			matrix.translate(-semitones[0]*self.rectwidth, 0)
			pattern.set_matrix(matrix)
		else:
			pattern = cairo.SolidPattern(1., 1., 1.)
			matrix = pattern.get_matrix()

		return matrix, pattern

	def prepare_string(self, semitone, prepared_fretboard):
		matrix, pattern = prepared_fretboard
		matrix_copy = cairo.Matrix() * matrix
		matrix_copy.translate(semitone*self.rectwidth, 0)
		pattern.set_matrix(matrix_copy)

		return None

class TotalFretboard(Fretboard):
	def __init__(self,*args,**kwargs):
		if "overtones" in kwargs: self.overtones = kwargs["overtones"]
		else: self.overtones = 10

		Fretboard.__init__(self,*args,**kwargs)

	def prepare_fretboard(self):
		if not self.spectrum: return

		total = []

		min_semitone = min(self.strings.values())

		for semitone in xrange(min_semitone, max(self.strings.values())+self.frets+1):
			total.append( self.spectrum.get_total_power_in_semitone_range(semitone-0.5,semitone+0.5,self.overtones) )

		return min_semitone, total

	def prepare_string(self, semitone, prepared_fretboard):
		if not self.spectrum: return

		min_semitone, total = prepared_fretboard

		# get maximum total power on fretboard
		max_power = max(total)
#		# get maximum total power on string
#		max_power = max(total[ semitone-min_semitone : semitone-min_semitone+self.frets ])
		min_power=0
		brightness_slope = - 1.0 / (max_power - min_power)
		brightness_const = 1.0 * max_power/ (max_power - min_power)

		return brightness_slope, brightness_const

	def set_fill_source(self,context,semitone,fret,prepared_fretboard,prepared_string):
		if not self.spectrum: return
			
		min_semitone, total = prepared_fretboard
		brightness_slope, brightness_const = prepared_string
		brightness = brightness_slope*total[semitone+fret-min_semitone] + brightness_const
		brightness = numpy.maximum(0.,numpy.minimum(1.,brightness))

		context.set_source_rgb(brightness, brightness, brightness)

class SingleString(Fretboard):
	""" Displays spectrum on one string, but also for overtones. """
	def __init__(self,*args,**kwargs):
		if "tune" in kwargs: self.tune = kwargs["tune"]
		else: self.tune = -5

		if "overtones" in kwargs: self.overtones = kwargs["overtones"]
		else: self.overtones = 10

		if not "rectheight" in kwargs: kwargs["rectheight"] = 10

		kwargs["strings"] = {}
		for i in xrange(1,self.overtones+2):
			kwargs["strings"][i] = self.tune + 12.*numpy.log2(i)

		Fretboard.__init__(self,*args,**kwargs)

		markerspace = self.rectheight/2 + self.markers_radius
		self.sumy = len(self.strings)*self.rectheight + markerspace + 2*self.paddingy
		self.set_size_request((self.frets+1)*self.rectwidth + 2*self.paddingx, self.sumy + self.rectheight + self.paddingy)

	def draw(self, widget, event):
		Fretboard.draw(self, widget, event)

#		return True

		if not self.spectrum: return True

#		power = 1.26**self.magnitudes # from dB to power
#		power = self.magnitudes

#		brightness_slope = - 1.0 / (self.magnitude_max - self.magnitude_min)
#		brightness_const = 1.0*self.magnitude_max / (self.magnitude_max - self.magnitude_min)

#		brightness = brightness_slope * self.magnitudes + brightness_const
#		brightness = 1.-numpy.clip(brightness, 0.,1.)
#		power = brightness

		t = []
		context = widget.window.cairo_create()

		for fret in xrange(self.frets+1):

#			darkness = 1. - self.brightness

			# calculate total
#			total=0
#			for string in self.strings.values():
#				semitone = string + fret
##				total += integrate(self.semitones, darkness, semitone-0.5, semitone+0.5)
#				t += integrate(self.frequencies, power, self.tune+fret, i)
#				f = semitone_to_frequency(semitone)
#				total += integrate(self.spectrum.frequency, self.spectrum.get_power(), f/1.0293022366434921, f*1.0293022366434921)

#			t.append(total)
			semitone = self.tune + fret
			total = self.spectrum.get_total_power_in_semitone_range(semitone-0.5,semitone+0.5,self.overtones)
			t.append(total)

		min_power=0
		max_power=max(t)
		brightness_slope = - 1.0 / (max_power - min_power)
		brightness_const = 1.0 * max_power/ (max_power - min_power)
#		print t
#		print min_power, max_power

		for fret in xrange(self.frets+1):
			context.rectangle(self.paddingx+fret*self.rectwidth, self.sumy, self.rectwidth, self.rectheight)

			total = t[fret]
			brightness = brightness_slope*total + brightness_const
			brightness = numpy.maximum(0.,numpy.minimum(1.,brightness))
			# convert to dB
			context.rectangle(self.paddingx+fret*self.rectwidth, self.sumy, self.rectwidth, self.rectheight)
#			dB = 4.3269116591383208 * numpy.log(t)
#			print fret,t,dB

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
#			minimum = 0
#			maximum = 5
#			brightness_slope = - 1.0 / (maximum - minimum)
#			brightness_const = 1.0*maximum / (maximum - minimum)
#
#			brightness = brightness_slope * t + brightness_const
#			brightness = max(0.,min(1.,brightness))

#			avg = total / (self.overtones+1.)

#			brightness = 1.-avg
#			brightness = max(0.,min(1.,brightness))
			
			context.set_source_rgb(brightness, brightness, brightness)
			context.fill_preserve()

			context.set_line_width(3)
			context.set_source_rgb(0,0,0)
			context.stroke()
