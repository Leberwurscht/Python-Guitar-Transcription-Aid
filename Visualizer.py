#!/usr/bin/env python

import gtk, numpy, cairo, goocanvas, gobject
import spectrumvisualizer
import gst
import scipy.interpolate

REFERENCE_FREQUENCY = 440
standard_tuning = {6:-29, 5:-24, 4:-19, 3:-14, 2:-10, 1:-5}
note_names = ["a","ais","b","c","cis","d","dis","e","f","fis","g","gis"]

def note_name(semitone):
	return note_names[int(round(semitone + 1000*12)) % 12]

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

class Semitone(goocanvas.ItemSimple, goocanvas.Item):
	__gproperties__ = {
		'x': (gobject.TYPE_DOUBLE,'X','x coordinate',-gobject.G_MAXDOUBLE,gobject.G_MAXDOUBLE,0,gobject.PARAM_READWRITE),
		'y': (gobject.TYPE_DOUBLE,'Y','y coordinate',-gobject.G_MAXDOUBLE,gobject.G_MAXDOUBLE,0,gobject.PARAM_READWRITE),
		'width': (gobject.TYPE_DOUBLE,'Width','Width',-gobject.G_MAXDOUBLE,gobject.G_MAXDOUBLE,30,gobject.PARAM_READWRITE),
		'height': (gobject.TYPE_DOUBLE,'Height','Height',-gobject.G_MAXDOUBLE,gobject.G_MAXDOUBLE,20,gobject.PARAM_READWRITE)
	}

	def __init__(self, semitone, volume, spectrum, **kwargs):
		kwargs["tooltip"] = note_name(semitone)+" ("+str(semitone)+") ["+str(semitone_to_frequency(semitone))+" Hz]"

		goocanvas.ItemSimple.__init__(self,**kwargs)

		self.x = self.props.x
		self.y = self.props.y
		self.width = self.props.width
		self.height = self.props.height

		self.semitone = semitone
		self.connect("button_press_event", self.press)
		self.connect("button_release_event", self.release)

		self.pipeline = gst.parse_launch("audiotestsrc name=src wave=saw ! volume name=volume ! gconfaudiosink")
		self.volume = volume

		self.gradient = spectrum.get_gradient()
		self.matrix = cairo.Matrix()
		self.matrix.scale(1./self.width,1.)
		self.matrix.translate((semitone-0.5)*self.width, 0)

	# custom properties
	def do_get_property(self,pspec):
		if hasattr(self, pspec.name):
			return getattr(self, pspec.name)
		else:
			return pspec.default_value

	def do_set_property(self,pspec,value):
		setattr(self, pspec.name, value)

	# override ItemSimple
	def do_simple_paint(self, cr, bounds):
		cr.translate(self.x, self.y)
		cr.rectangle(0.0, 0.0, self.width, self.height)

		self.gradient.set_matrix(self.matrix)
		cr.set_source(self.gradient)
#		cr.set_source_rgb(0.,0.,1.)

		cr.fill_preserve()
		cr.set_source_rgb(0.,0.,0.)
		cr.stroke()

	def do_simple_update(self, cr):
		half_line_width = self.get_line_width() / 2.

		self.bounds_x1 = self.x - half_line_width
		self.bounds_y1 = self.y - half_line_width
		self.bounds_x2 = self.x + self.width + half_line_width
		self.bounds_y2 = self.y + self.height + half_line_width

	def do_simple_is_item_at(self, x, y, cr, is_pointer_event):
		if x < self.x: return False
		if y < self.y: return False
		if x > self.x+self.width: return False
		if y > self.y+self.height: return False
		return True

	# callbacks
	def press(self,item,target,event):
		if event.button==1:
			self.pipeline.get_by_name("volume").set_property("volume", self.volume.get_value())
			self.pipeline.get_by_name("src").set_property("freq", semitone_to_frequency(self.semitone))
			self.pipeline.set_state(gst.STATE_PLAYING)
		elif event.button==3:
			menu = gtk.Menu()
			item = gtk.MenuItem("Add to tabulature")
#			item.connect("activate", self.)
			menu.append(item)
			item.show_all()
			menu.popup(None, None, None, event.button, event.time)

	def release(self,item,target,event):
		self.pipeline.set_state(gst.STATE_NULL)

gobject.type_register(Semitone)

class SemitoneOld(goocanvas.Rect):
	def __init__(self,semitone,volume,**kwargs):
		if not "width" in kwargs: kwargs["width"]=30
		if not "height" in kwargs: kwargs["height"]=20
		kwargs["tooltip"] = note_name(semitone)+" ("+str(semitone)+") ["+str(semitone_to_frequency(semitone))+" Hz]"
		kwargs["fill_color_rgba"] = 0x0000ffff

		goocanvas.Rect.__init__(self,**kwargs)

		self.semitone = semitone
		self.connect("button_press_event", self.press)
		self.connect("button_release_event", self.release)

		self.pipeline = gst.parse_launch("audiotestsrc name=src wave=saw ! volume name=volume ! gconfaudiosink")
		self.volume = volume

	def press(self,item,target,event):
		if event.button==1:
			self.pipeline.get_by_name("volume").set_property("volume", self.volume.get_value())
			self.pipeline.get_by_name("src").set_property("freq", semitone_to_frequency(self.semitone))
			self.pipeline.set_state(gst.STATE_PLAYING)
		elif event.button==3:
			menu = gtk.Menu()
			item = gtk.MenuItem("Add to tabulature")
#			item.connect("activate", self.)
			menu.append(item)
			item.show_all()
			menu.popup(None, None, None, event.button, event.time)

	def release(self,item,target,event):
		self.pipeline.set_state(gst.STATE_NULL)

class Fretboard2(goocanvas.Table):
	__gproperties__ = {
		'spectrum': (gobject.TYPE_DOUBLE,'X','x coordinate',-gobject.G_MAXDOUBLE,gobject.G_MAXDOUBLE,0,gobject.PARAM_READWRITE)
	}

	def __init__(self, frets=12, strings=None, spectrum=None,**kwargs):
		goocanvas.Table.__init__(self,**kwargs)

		if "width" in kwargs:
			self.width = kwargs["width"]
			del kwargs["width"]
		else:
			self.width = 30

		if "height" in kwargs:
			self.height = kwargs["height"]
			del kwargs["height"]
		else:
			self.height = 20

		if not strings:
			strings = [-5,-10,-14,-19,-24,-29]

		self.volume = gtk.Adjustment(0.04,0.0,10.0,0.01)

		for i in xrange(len(strings)):
			semitone = strings[i]

			for fret in xrange(frets+1):
				rect = Semitone(semitone+fret, self.volume, spectrum, parent=self)
				self.set_child_properties(rect, row=i, column=fret)

#		r = Semitone2(0,self.volume,parent=self)
#		self.set_child_properties(r, row=0, column=frets+1)
#		print "width",r.get_bounds().x2 - r.get_bounds().x1

		self.strings = strings
		self.frets = frets

	def get_width(self):
		return self.get_bounds().x2 - self.get_bounds().x1

	def get_height(self):
		return self.get_bounds().y2 - self.get_bounds().y1

class SpectrumData:
	""" holds data for visualizers, calculates and caches different scales """
	def __init__(self, frequency, **kwargs):
		self.frequency = frequency
		self.power = None
		self.magnitude = None
		self.brightness = None
		self.semitone = None
		self.power_spline = None
		self.powerfreq_spline = None
		self.gradient = None

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

	def get_gradient(self):
		if not self.gradient:
			semitones = self.get_semitone()
			semitonerange = semitones[-1]-semitones[0]
			brightness = self.get_brightness()

			self.gradient = cairo.LinearGradient(semitones[0], 0, semitones[-1], 0)

			for i in xrange(len(semitones)):
				b = brightness[i]
				self.gradient.add_color_stop_rgb( ( semitones[i]-semitones[0] ) / semitonerange, b,b,b)

		return self.gradient

	def get_total_power_in_semitone_range(self,lower,upper,overtones=10):
		l = semitone_to_frequency(lower)
		u = semitone_to_frequency(upper)
		return self.get_total_power_in_frequency_range(l,u,overtones)

	def get_total_power_in_frequency_range(self,lower,upper,overtones=10):
		total = 0

		for i in xrange(overtones+1):
#			total += integrate(self.frequency, self.get_power(), lower*(i+1), upper*(i+1))
			total += self.get_power_in_frequency_range(lower*(i+1), upper*(i+1))

		return total

	def get_points_in_semitone_range(self,lower,upper,overtones=10):
		l = semitone_to_frequency(lower)
		u = semitone_to_frequency(upper)
		return self.get_points_in_frequency_range(l,u,overtones)

	def analyze_semitone(self,semitone,overtones=10):
		bands = len(self.frequency)
		rate = 2.0 * bands * self.frequency[-1] / ( bands-0.5 )
		data_length = 2*bands - 2

		# http://mathworld.wolfram.com/HammingFunction.html: position of first root of apodization function
		peak_radius = 1.299038105676658 * rate / data_length

		frequency = semitone_to_frequency(semitone)

		total_power = 0
		diff_squares = 0
		diffs = 0

		for i in xrange(1,overtones+2):
			f = frequency*i
			osemitone = frequency_to_semitone(f)
			lower_frequency = f - peak_radius*1.65
			upper_frequency = f + peak_radius*1.65

			lower_frequency = min(lower_frequency, semitone_to_frequency(osemitone-0.5))
			upper_frequency = max(upper_frequency, semitone_to_frequency(osemitone+0.5))

			power = self.get_power_in_frequency_range(lower_frequency,upper_frequency)
			peak_center = self.get_powerfreq_spline().integral(lower_frequency,upper_frequency) / power

			difference_in_semitones = frequency_to_semitone(peak_center) - osemitone

			total_power += power
			diff_squares += power * difference_in_semitones**2.
			diffs += power * difference_in_semitones

		center = diffs/total_power
		variance = diff_squares/total_power - center**2.
		standard_deviation = numpy.sqrt(variance)

		if standard_deviation<0.1:
#			print semitone, standard_deviation, center
			if abs(center)>0.5: print "oops",semitone, standard_deviation, center

	def get_powerfreq_spline(self):
		if not self.powerfreq_spline:
			self.powerfreq_spline = scipy.interpolate.InterpolatedUnivariateSpline(self.frequency, self.get_power()*self.frequency, None, [None, None], 1)

		return self.powerfreq_spline

	def get_points_in_frequency_range(self,lower,upper,overtones=10):
		# string 6: consider range of 3 semitones for key and 1st overtone
		# string 5: consider range of 3 semitones for key tone
		## better: estimate peak width through window function and use range of one semitone
		## or, if greater, peak width

		# low-pitched tones have more overtones (up to 9) and have them most of the time
		# key tone often lower-toned than first overtone for low-pitched notes

		# high-pitched tones tend to have less, but can have up to 6

		# calculate variance of peak center among overtones, should be small (inharmonicity)

		# return total power, inharmonicity, and perhaps some "independence" coefficients that
		# say how probable it is that this total power is just overtones of other notes or whether
		# the power belongs to an overtone of this note.
		# the second one can be seen by -X-X-X-X-X-X or --X--X--X--X patterns
		# the first one can be seen by checking for alternative key tones explaining these peaks

		# problem: if only one overtone exists, inharmonity is 0 but this is not necessarily a note

		points = 0
		power = 0

		power = self.get_total_power_in_frequency_range(lower,upper,overtones)

		return points

	def get_power_spline(self):
		if not self.power_spline:
			self.power_spline = scipy.interpolate.InterpolatedUnivariateSpline(self.frequency, self.get_power(), None, [None, None], 1)

		return self.power_spline

	def get_power_in_frequency_range(self,lower,upper):
		return self.get_power_spline().integral(lower, upper)

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

		if "method" in kwargs: self.method = kwargs["method"]
		else: self.method = "gradient"

		if self.method=="gradient":
			self.prepare_fretboard = self.prepare_fretboard_gradient
			self.prepare_string = self.prepare_string_gradient
			self.set_fill_source = self.set_fill_source_gradient
		elif self.method=="cumulate":
			self.prepare_fretboard = self.prepare_fretboard_cumulate
			self.prepare_string = self.prepare_string_cumulate
			self.set_fill_source = self.set_fill_source_cumulate
#		elif self.method=="points":
#			self.prepare_fretboard = self.prepare_fretboard_points
#			self.prepare_string = self.prepare_string_points
#			self.set_fill_source = self.set_fill_source_points
		else:
			raise ValueError, "Invalid method"

		markerspace = self.rectheight/2 + self.markers_radius

		if len(self.markers)==0: markerspace=0

		self.set_size_request((self.frets+1)*self.rectwidth + 2*self.paddingx, len(self.strings)*self.rectheight + markerspace + 2*self.paddingy)

		self.spectrum = None

	def set_spectrum(self, spectrum):
		self.spectrum = spectrum

	def draw(self, widget, event):
		context = widget.window.cairo_create()

		fretboard_data = self.prepare_fretboard()

		for string,semitone in self.strings.iteritems():
			string_data = self.prepare_string(semitone, fretboard_data)

			for fret in xrange(self.frets+1):
				context.rectangle(self.paddingx+fret*self.rectwidth, self.paddingy+self.rectheight*(string-1), self.rectwidth, self.rectheight)
				self.set_fill_source(context, fret, string_data)
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

	def prepare_fretboard_gradient(self):
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

	def prepare_string_gradient(self, semitone, prepared_fretboard):
		matrix, pattern = prepared_fretboard
		matrix_copy = cairo.Matrix() * matrix
		matrix_copy.translate(semitone*self.rectwidth, 0)
		pattern.set_matrix(matrix_copy)

		return pattern

	def set_fill_source_gradient(self,context,fret,prepared_string):
		pattern = prepared_string
		context.set_source(pattern)

	def prepare_fretboard_cumulate(self):
		if not self.spectrum: return

		min_power = 0
		max_power = 0
#		min_mag = -60
#		max_mag = 0

		strings = {}
		for string,semitone in self.strings.iteritems():
			strings[semitone] = []
			max_on_string = 0
			for fret in xrange(self.frets+1):
				lower = semitone_to_frequency(semitone+fret-0.5)
				upper = semitone_to_frequency(semitone+fret+0.5)
				self.spectrum.analyze_semitone(semitone+fret)
				p = self.spectrum.get_power_in_frequency_range(lower, upper)
				strings[semitone].append(p)
#				m = power_to_magnitude(p)
#				strings[semitone].append(m)

				if p>max_on_string: max_on_string = p
#				if m>max_on_string: max_on_string = m

			if max_on_string > max_power: max_power = max_on_string
#			if max_on_string > max_mag: max_mag = max_on_string

		brightness_slope = - 1.0 / (max_power - min_power)
		brightness_const = 1.0 * max_power / (max_power - min_power)
#		brightness_slope = - 1.0 / (max_mag - min_mag)
#		brightness_const = 1.0 * max_mag / (max_mag - min_mag)

		return strings, brightness_slope, brightness_const

	def prepare_string_cumulate(self, semitone, prepared_fretboard):
		if not self.spectrum: return

		strings, brightness_slope, brightness_const = prepared_fretboard

		power = numpy.array(strings[semitone])
		brightness = brightness_slope*power + brightness_const
		brightness = numpy.maximum(0.,numpy.minimum(1.,brightness))

		return brightness

	def set_fill_source_cumulate(self,context,fret,prepared_string):
		if not self.spectrum:
			context.set_source_rgb(1.0,1.0,1.0)
			return

		brightness = prepared_string
		b = brightness[fret]
		context.set_source_rgb(b,b,b)

class TotalFretboard(Fretboard):
	def __init__(self,*args,**kwargs):
		if "overtones" in kwargs: self.overtones = kwargs["overtones"]
		else: self.overtones = 10

		if "calculation_overtones" in kwargs: self.calculation_overtones = kwargs["calculation_overtones"]
		else: self.calculation_overtones = self.overtones

		Fretboard.__init__(self,*args,**kwargs)

	def prepare_fretboard(self):
		if not self.spectrum: return

		total = []

		min_semitone = min(self.strings.values())

		for semitone in xrange(min_semitone, max(self.strings.values())+self.frets+1):
			total.append( self.spectrum.get_total_power_in_semitone_range(semitone-0.5,semitone+0.5,self.calculation_overtones) )

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
		if not self.spectrum:
			context.set_source_rgb(1.0,1.0,1.0)
			return
			
		min_semitone, total = prepared_fretboard
		brightness_slope, brightness_const = prepared_string
		brightness = brightness_slope*total[semitone+fret-min_semitone] + brightness_const
		brightness = numpy.maximum(0.,numpy.minimum(1.,brightness))

		context.set_source_rgb(brightness, brightness, brightness)

class SingleStringArea(TotalFretboard):
	""" Displays spectrum on one string, but also for overtones. """
	def __init__(self,*args,**kwargs):
		if "tune" in kwargs: self.tune = kwargs["tune"]
		else: self.tune = -5

		if "overtones" in kwargs: self.overtones = kwargs["overtones"]
		else: self.overtones = 10

		self.calculation_overtones = 0

		if not "rectheight" in kwargs: kwargs["rectheight"] = 10

		kwargs["strings"] = {}
		for i in xrange(1,self.overtones+2):
			kwargs["strings"][i] = self.tune + 12.*numpy.log2(i)

		TotalFretboard.__init__(self,*args,**kwargs)

		markerspace = self.rectheight/2 + self.markers_radius
		self.sumy = len(self.strings)*self.rectheight + markerspace + 2*self.paddingy
		self.set_size_request((self.frets+1)*self.rectwidth + 2*self.paddingx, self.sumy + self.rectheight + self.paddingy)

	def draw(self, widget, event):
		Fretboard.draw(self, widget, event)

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

		if "method" in kwargs:
			if not kwargs["method"] in ["gradient","cumulate"]:
				raise ValueError, "Invalid method"

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
