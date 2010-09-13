#!/usr/bin/env python

import gtk, numpy, cairo, goocanvas, gobject
import spectrumvisualizer
import gst
import scipy.interpolate
from SpectrumData import base as SpectrumDataBase

REFERENCE_FREQUENCY = 440
standard_tuning = {6:-29, 5:-24, 4:-19, 3:-14, 2:-10, 1:-5}
note_names = ["a","ais","b","c","cis","d","dis","e","f","fis","g","gis"]

def note_name(semitone):
	return note_names[int(round(semitone + 1000*12)) % 12]

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

# == PLAN ==

# class SemitoneBase(goocanvas.ItemSimple, goocanvas.Item)
# class SemitoneGradient(SemitoneBase)
# class SemitoneCumulate(SemitoneBase)
# [class SemitoneAnalyze(SemitoneBase)]
# 
# class FretboardBase(goocanvas.Group)
# class Fretboard(FretboardBase)
# class SingleString(FretboardBase)
#
# class FretboardWindowBase(gtk.Window)
# class FretboardWindow(FretboardWindowBase)
# class SingleStringWindow(FretboardWindowBase)
# [class PlotWindow(gtk.Window)]

# right-click Semitone
# => show menu, callbacks connected for "add to tab", ""
# item "add to tabulature" connected to 

# Fretboard opens SingleString
# Fretboard and SingleString add markers to tabulature
# Fretboard and SingleString open Analyze

# problem: if x or y is changed, will update be called?
class Semitone(goocanvas.ItemSimple, goocanvas.Item):
	__gproperties__ = {
		'x': (gobject.TYPE_DOUBLE,'X','x coordinate',-gobject.G_MAXDOUBLE,gobject.G_MAXDOUBLE,0,gobject.PARAM_READWRITE),
		'y': (gobject.TYPE_DOUBLE,'Y','y coordinate',-gobject.G_MAXDOUBLE,gobject.G_MAXDOUBLE,0,gobject.PARAM_READWRITE),
		'width': (gobject.TYPE_DOUBLE,'Width','Width',-gobject.G_MAXDOUBLE,gobject.G_MAXDOUBLE,30,gobject.PARAM_READWRITE),
		'height': (gobject.TYPE_DOUBLE,'Height','Height',-gobject.G_MAXDOUBLE,gobject.G_MAXDOUBLE,20,gobject.PARAM_READWRITE)
	}

	__gsignals__ = {
		'right-clicked': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
	}

	def __init__(self, semitone, volume, **kwargs):
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

		self.spectrum = None
		self.matrix = None

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

		if not self.spectrum:
			cr.set_source_rgb(1.,1.,1.)
		else:
			assert not self.matrix==None
			gradient = self.spectrum.get_gradient()
			gradient.set_matrix(self.matrix)
			cr.set_source(gradient)

		cr.fill_preserve()
		cr.set_source_rgb(0.,0.,0.)
		cr.stroke()

	def do_simple_update(self, cr):
		half_line_width = self.get_line_width() / 2.

		self.bounds_x1 = self.x - half_line_width
		self.bounds_y1 = self.y - half_line_width
		self.bounds_x2 = self.x + self.width + half_line_width
		self.bounds_y2 = self.y + self.height + half_line_width

		self.matrix = cairo.Matrix()
		self.matrix.scale(1./self.width,1.)
		self.matrix.translate((self.semitone-0.5)*self.width, 0)

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
			self.emit('right-clicked', event)

#	def analyze(self,widget):
#		

	def release(self,item,target,event):
		self.pipeline.set_state(gst.STATE_NULL)

	def set_spectrum(self,obj,spectrum):
		self.spectrum = spectrum
		self.changed(False)

gobject.type_register(Semitone)

class FretboardBase(goocanvas.Group):
	def __init__(self, spectrum, volume, **kwargs):
		self.volume = volume
		self.spectrum = spectrum

		if "strings" in kwargs:
			self.strings = kwargs["strings"]
			del kwargs["strings"]
		else: self.strings = [-5,-10,-14,-19,-24,-29]

		if "frets" in kwargs:
			self.frets = kwargs["frets"]
			del kwargs["frets"]
		else: self.frets = 12

		if "rectwidth" in kwargs:
			self.rectwidth = kwargs["rectwidth"]
			del kwargs["rectwidth"]
		else: self.rectwidth = 30

		if "rectheight" in kwargs:
			self.rectheight = kwargs["rectheight"]
			del kwargs["rectheight"]
		else: self.rectheight = 20

		if "paddingx" in kwargs:
			self.paddingx = kwargs["paddingx"]
			del kwargs["paddingx"]
		else: self.paddingx = 5

		if "paddingy" in kwargs:
			self.paddingy = kwargs["paddingy"]
			del kwargs["paddingy"]
		else: self.paddingy = 7

		if "markers_radius" in kwargs:
			self.markers_radius = kwargs["markers_radius"]
			del kwargs["markers_radius"]
		else: self.markers_radius = self.rectheight/4.

		if "markers" in kwargs:
			self.markers = kwargs["markers"]
			del kwargs["markers"]
		else: self.markers = [5,7,9]

		if "capo" in kwargs:
			self.capo = kwargs["capo"]
			del kwargs["capo"]
		else: self.capo = 0

		if "method" in kwargs:
			self.method = kwargs["method"]
			del kwargs["method"]
		else: self.method = "gradient"

		goocanvas.Group.__init__(self,**kwargs)

		self.construct(self.paddingx, self.paddingy)

	def construct(self, posx, posy):
		# fretboard
		for string in xrange(len(self.strings)):
			semitone = self.strings[string]

			for fret in xrange(self.frets+1):
				x = posx + fret*self.rectwidth
				y = posy + self.rectheight*string
				rect = Semitone(semitone+fret, self.volume, parent=self, x=x, y=y, width=self.rectwidth, height=self.rectheight)
				rect.connect("right_clicked", self.open_context_menu, string, fret)
				self.spectrum.connect("new_data", rect.set_spectrum, self.spectrum)

		y = posy + self.rectheight*(len(self.strings) + 0.5)
		for fret in self.markers:
			x = posx + self.rectwidth*(fret+0.5)
			circle = goocanvas.Ellipse(parent=self, center_x=x, center_y=y, radius_x=self.markers_radius, radius_y=self.markers_radius)
			circle.props.fill_color_rgba=0x333333ff
			circle.props.line_width=0

		if self.capo:
			x = posx + self.rectwidth*(self.capo+.3)
			y1 = posy
			y2 = posy + self.rectheight*len(self.strings)
			width = self.rectwidth/3
			goocanvas.polyline_new_line(self, x,y1,x,y2, width=line_width, stroke_color_rgba=0x660000cc, pointer_events=0)

		# draw nut
		x = posx + self.rectwidth*.3
		y1 = posy
		y2 = posy + self.rectheight*len(self.strings)
		width = self.rectwidth/3
		goocanvas.polyline_new_line(self, x,y1,x,y2, line_width=width, stroke_color_rgba=0xcc0000cc, pointer_events=0)
		
	def get_width(self):
		return self.get_bounds().x2 - self.get_bounds().x1 + 2*self.paddingx

	def get_height(self):
		return self.get_bounds().y2 - self.get_bounds().y1 + 2*self.paddingy

	# callbacks
	def open_context_menu(self, rect, event, string, fret):
		raise NotImplementedError, "override this method!"

	# custom properties
	def do_get_property(self,pspec):
		return getattr(self, pspec.name)

	def do_set_property(self,pspec,value):
		setattr(self, pspec.name, value)

class Fretboard(FretboardBase):
	def __init__(self, spectrum, volume, **kwargs):
		FretboardBase.__init__(self, spectrum, volume, **kwargs)

	def construct(self, posx, posy):
		# captions
		fretcaptions = goocanvas.Group(parent=self)
		for fret in xrange(1,self.frets+1):
			goocanvas.Text(parent=fretcaptions, x=fret*self.rectwidth, y=0, text=str(fret), anchor=gtk.ANCHOR_NORTH, font=10)

		stringcaptions = goocanvas.Group(parent=self)
		for string in xrange(len(self.strings)):
			semitone = self.strings[string]
			name = note_name(semitone).upper()
			text = goocanvas.Text(parent=stringcaptions, x=0, y=string*self.rectheight, text=name, anchor=gtk.ANCHOR_EAST, font=10)
			text.connect("button_release_event", self.open_string, string)

		startx = posx + stringcaptions.get_bounds().x2-stringcaptions.get_bounds().x1 + 5
		starty = posy + fretcaptions.get_bounds().y2-fretcaptions.get_bounds().y1

		fretcaptions.props.x = startx + 0.5*self.rectwidth
		fretcaptions.props.y = posy

		stringcaptions.props.x = startx - 5
		stringcaptions.props.y = starty + 0.5*self.rectheight

		# fretboard
		FretboardBase.construct(self, startx, starty)

	def open_context_menu(self, rect, event, string, fret):
		menu = gtk.Menu()

		item = gtk.MenuItem("Open string")
		item.connect("activate", self.open_string, item, None, string)
		menu.append(item)

		item = gtk.MenuItem("Analyze")
#		item.connect("activate", self.analyze)
		menu.append(item)

		item = gtk.MenuItem("Add to tabulature")
#		item.connect("activate", self.)
		menu.append(item)

		menu.show_all()
		menu.popup(None, None, None, event.button, event.time)

	def open_string(self, item, target, event, string):
		w = SingleStringWindow(self.spectrum, self.strings[string])
		w.show_all()

class SingleString(FretboardBase):
	def __init__(self, spectrum, volume, **kwargs):
		if "tuning" in kwargs:
			self.tuning = kwargs["tuning"]
			del kwargs["tuning"]
		else: self.tuning = -5

		if "overtones" in kwargs:
			self.overtones = kwargs["overtones"]
			del kwargs["overtones"]
		else: self.overtones = 10

		if not "rectheight" in kwargs: kwargs["rectheight"] = 10

		kwargs["strings"] = []
		for multiplicator in xrange(1,self.overtones+2):
			semitone = self.tuning + 12.*numpy.log2(multiplicator)
			kwargs["strings"].append(semitone)

		FretboardBase.__init__(self, spectrum, volume, **kwargs)

	def construct(self, posx, posy):
		# captions
		fretcaptions = goocanvas.Group(parent=self)
		for fret in xrange(0,self.frets+1):
			text = goocanvas.Text(parent=fretcaptions, x=fret*self.rectwidth, y=0, text=str(fret), anchor=gtk.ANCHOR_NORTH, font=10)
#			text.connect("button_release_event", self.fret_clicked, fret)

		stringcaptions = goocanvas.Group(parent=self)
		goocanvas.Text(parent=stringcaptions, x=0, y=0, text="f.", anchor=gtk.ANCHOR_EAST, font=10)
		for overtone in xrange(1,self.overtones+1):
			name = str(overtone)+"."
			goocanvas.Text(parent=stringcaptions, x=0, y=overtone*self.rectheight, text=name, anchor=gtk.ANCHOR_EAST, font=10)

		startx = posx + stringcaptions.get_bounds().x2-stringcaptions.get_bounds().x1 + 5
		starty = posy + fretcaptions.get_bounds().y2-fretcaptions.get_bounds().y1

		fretcaptions.props.x = startx + 0.5*self.rectwidth
		fretcaptions.props.y = posy

		stringcaptions.props.x = startx - 5
		stringcaptions.props.y = starty + 0.5*self.rectheight

		# fretboard
		FretboardBase.construct(self, startx, starty)

	# callbacks
	def fret_clicked(self,item,target,event, fret):
		if self.props.spectrum:
			text = ""

			for overtone, frequency, power, peak_center, difference_in_semitones in self.props.spectrum.analyze_overtones(self.tuning+fret, 10):
				semitone = frequency_to_semitone(frequency)
				near = int(round(semitone))
				text += "%d. overtone: %f Hz (semitone %f; near %s)\n" % (overtone, frequency, semitone, note_name(near))
				text += "\tPower: %f (%f dB)\n" % (power, power_to_magnitude(power))
				text += "\tPosition: %f Hz (off by %f semitones)\n" % (peak_center, difference_in_semitones)
				text += "\n"

			d = gtk.Dialog("Info on semitone %f (fret %d)" % (self.tuning+fret, fret), None, 0,
					(gtk.STOCK_OK, gtk.RESPONSE_OK))
			sw = gtk.ScrolledWindow()
			d.set_size_request(500,400)
#			sw.set_policy(gtk.POLICY_NEVER,gtk.POLICY_ALWAYS); 
			d.vbox.add(sw)
			tv = gtk.TextView()
			b = tv.get_buffer()
			b.set_text(text)
			tv.set_editable(False)
			sw.add(tv)
			d.show_all()
			d.run()
			d.destroy()
#			dialog = gtk.MessageDialog(None, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, text)
#			dialog.run()
#			dialog.destroy()

	def open_context_menu(self, rect, event, string, fret):
		semitone = self.tuning + fret

		menu = gtk.Menu()

		item = gtk.MenuItem("Analyze")
#		item.connect("activate", self.analyze)
		menu.append(item)

		item = gtk.MenuItem("Add to tabulature")
#		item.connect("activate", self.)
		menu.append(item)

		menu.show_all()
		menu.popup(None, None, None, event.button, event.time)

class FretboardWindowBase(gtk.Window):
	def __init__(self, **kwargs):
		gtk.Window.__init__(self, **kwargs)

		vbox = gtk.VBox()
		self.add(vbox)

		self.controls = gtk.VBox()
		vbox.add(self.controls)

		hbox = gtk.HBox()
		vbox.add(hbox)

		label = gtk.Label("Volume")
		hbox.add(label)

		self.volume = gtk.Adjustment(0.04,0.0,10.0,0.01)
		spinbtn = gtk.SpinButton(self.volume,0.01,2)
		hbox.add(spinbtn)

		self.canvas = goocanvas.Canvas()
		self.connect_after("realize", self.set_default_background, self.canvas)
		self.canvas.set_property("has-tooltip", True)
		vbox.add(self.canvas)

	def adjust_canvas_size(self):
		width = self.visualizer.get_width()
		height = self.visualizer.get_height()
		self.canvas.set_bounds(0,0,width,height)
		self.canvas.set_size_request(int(width),int(height))

	def set_default_background(self, from_widget, to_widget):
		# background color is only available when widget is realized
		color = from_widget.get_style().bg[gtk.STATE_NORMAL]
		to_widget.set_property("background_color", color)

	def set_spectrum(self, spectrum):
		self.visualizer.props.spectrum = spectrum

class FretboardWindow(FretboardWindowBase):
	def __init__(self, spectrum, **kwargs):
		FretboardWindowBase.__init__(self, **kwargs)

		self.set_title("Fretboard")

		root = self.canvas.get_root_item()
		self.visualizer = Fretboard(spectrum, self.volume, parent=root)

		self.adjust_canvas_size()

class SingleStringWindow(FretboardWindowBase):
	def __init__(self, spectrum, tuning=-5, **kwargs):
		FretboardWindowBase.__init__(self, **kwargs)

		self.set_title("SingleString "+note_name(tuning)+" ("+str(tuning)+")")

		root = self.canvas.get_root_item()
		self.visualizer = SingleString(spectrum, self.volume, parent=root, tuning=tuning)

		self.adjust_canvas_size()

class SpectrumData(SpectrumDataBase):
	__gproperties__ = {
		'autoupdate': (gobject.TYPE_BOOLEAN,'AutoUpdate','Whether to update visualizers while playback',False,gobject.PARAM_READWRITE)
	}

	__gsignals__ = {
		'new-data': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
	}

	""" holds data for visualizers, calculates and caches different scales """
	def __init__(self, pipeline, **kwargs):
		SpectrumDataBase.__init__(self, pipeline.spectrum, pipeline)
		self.autoupdate_handler = self.connect("magnitudes_available", self.autoupdate)
		self.handler_block(self.autoupdate_handler)
		self.autoupdate = False

		if "brightness_method" in kwargs:
			self.brightness_method = kwargs["brightness_method"]
		else:
			self.brightness_method = "from_magnitude"

		if self.brightness_method=="from_magnitude":
			if "min_magnitude" in kwargs:
				self.min_magnitude = kwargs["min_magnitude"]
			else:
				self.min_magnitude = None #-60.

			if "max_magnitude" in kwargs:
				self.max_magnitude = kwargs["max_magnitude"]
			else:
				self.max_magnitude = None #0.
		elif self.brightness_method=="from_power":
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

	# custom properties
	def do_get_property(self,pspec):
		if pspec.name=="autoupdate":
			return self.autoupdate
		else:
			raise Exception, "Invalid property name"

	def do_set_property(self,pspec,value):
		if pspec.name=="autoupdate":
			if value and not self.autoupdate:
				self.handler_unblock(self.autoupdate_handler)
				self.autoupdate = True
			elif not value and self.autoupdate:
				self.handler_block(self.autoupdate_handler)
				self.autoupdate = False
		else:
			raise Exception, "Invalid property name"

	# callbacks
	def autoupdate(self, spectrumdata, bands, rate, threshold, magnitude):
#		magnitude_max = 0.
#
		frequency = 0.5 * ( numpy.arange(bands) + 0.5 ) * rate / bands
#		magnitudes = numpy.array(magnitudes)
#
#		if self.builder.get_object("cutoff_button").get_active():
#			max_magnitude = self.builder.get_object("cutoff").get_value()
#		else:
#			max_magnitude = None
				
#		spectrum = Visualizer.SpectrumData(frequencies, magnitude=magnitudes, min_magnitude=threshold, max_magnitude=max_magnitude)
		self.set_magnitude(frequency, numpy.array(magnitude))

	# set data
	def clear(self):
		self.power = None
		self.magnitude = None
		self.brightness = None
		self.semitone = None
		self.power_spline = None
		self.powerfreq_spline = None
		self.gradient = None

	def set_magnitude(self, frequency, magnitude):
		self.clear()
		self.frequency = frequency
		self.magnitude = magnitude
		self.emit("new_data")
		
	def set_power(self, frequency, power):
		self.clear()
		self.frequency = frequency
		self.power = power
		self.emit("new_data")

	# get data
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
			if self.brightness_method=="from_magnitude":
				if self.max_magnitude==None:
					max_magnitude=numpy.max(self.get_magnitude())
				else:
					max_magnitude = self.max_magnitude

				if self.min_magnitude==None:
					min_magnitude=numpy.min(self.get_magnitude())
				else:
					min_magnitude = self.min_magnitude

				brightness_slope = - 1.0 / (max_magnitude - min_magnitude)
				brightness_const = 1.0 * max_magnitude / (max_magnitude - min_magnitude)

				brightness = brightness_slope * self.get_magnitude() + brightness_const
				self.brightness = numpy.maximum(0.,numpy.minimum(1.,brightness))
			elif self.brightness_method=="from_power":
				if self.max_power==None:
					max_power=numpy.max(self.get_power())
				else:
					max_power = self.max_power

				if self.min_power==None:
					min_power=numpy.min(self.get_power())
				else:
					min_power = self.min_power

				brightness_slope = - 1.0 / (max_power - min_power)
				brightness_const = 1.0 * max_power/ (max_power - min_power)

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

#	def get_total_power_in_semitone_range(self,lower,upper,overtones=10):
#		l = semitone_to_frequency(lower)
#		u = semitone_to_frequency(upper)
#		return self.get_total_power_in_frequency_range(l,u,overtones)
#
#	def get_total_power_in_frequency_range(self,lower,upper,overtones=10):
#		total = 0
#
#		for i in xrange(overtones+1):
##			total += integrate(self.frequency, self.get_power(), lower*(i+1), upper*(i+1))
#			total += self.get_power_in_frequency_range(lower*(i+1), upper*(i+1))
#
#		return total

#	def get_points_in_semitone_range(self,lower,upper,overtones=10):
#		l = semitone_to_frequency(lower)
#		u = semitone_to_frequency(upper)
#		return self.get_points_in_frequency_range(l,u,overtones)

	def analyze_overtones(self,semitone,overtones=None):
		""" calculates power and peak center for each overtone and yields tuples (overtone, frequency, power, peak_center, difference_in_semitones) """

		bands = len(self.frequency)
		rate = 2.0 * bands * self.frequency[-1] / ( bands-0.5 )
		data_length = 2*bands - 2

		# http://mathworld.wolfram.com/HammingFunction.html: position of first root of apodization function
		peak_radius = 1.299038105676658 * rate / data_length

		frequency = semitone_to_frequency(semitone)

		overtone=0

		while overtones==None or overtone<overtones:
			f = frequency*(overtone+1)
			s = frequency_to_semitone(f)

			lower_frequency = f - peak_radius*1.65
			upper_frequency = f + peak_radius*1.65

			lower_frequency = min(lower_frequency, semitone_to_frequency(s-0.5))
			upper_frequency = max(upper_frequency, semitone_to_frequency(s+0.5))

			power = self.get_power_in_frequency_range(lower_frequency,upper_frequency)
			peak_center = self.get_powerfreq_spline().integral(lower_frequency,upper_frequency) / power

			difference_in_semitones = frequency_to_semitone(peak_center) - s

			yield overtone, f, power, peak_center, difference_in_semitones

			overtone += 1

	def analyze_semitone(self,semitone,overtones=10):
		""" calculate total power, inharmonicity and independence coefficients """
#		frequency = semitone_to_frequency(semitone)

		total_power = 0
		diff_squares = 0
		diffs = 0

		for overtone, frequency, power, peak_center, difference_in_semitones in self.analyze_overtones(semitone,overtones):
			total_power += power
			diff_squares += power * difference_in_semitones**2.
			diffs += power * difference_in_semitones

#		for i in xrange(1,overtones+2):
#			f = frequency*i
#			osemitone = frequency_to_semitone(f)
#			lower_frequency = f - peak_radius*1.65
#			upper_frequency = f + peak_radius*1.65
#
#			lower_frequency = min(lower_frequency, semitone_to_frequency(osemitone-0.5))
#			upper_frequency = max(upper_frequency, semitone_to_frequency(osemitone+0.5))
#
#			power = self.get_power_in_frequency_range(lower_frequency,upper_frequency)
#			peak_center = self.get_powerfreq_spline().integral(lower_frequency,upper_frequency) / power
#
#			difference_in_semitones = frequency_to_semitone(peak_center) - osemitone
#
#			total_power += power
#			diff_squares += power * difference_in_semitones**2.
#			diffs += power * difference_in_semitones

		center = diffs/total_power
		variance = diff_squares/total_power - center**2.
		standard_deviation = numpy.sqrt(variance)

		print center, variance, standard_deviation
#		if standard_deviation<0.1:
#			print semitone, standard_deviation, center
#			if abs(center)>0.5: print "oops",semitone, standard_deviation, center

	def get_power_spline(self):
		if not self.power_spline:
			self.power_spline = scipy.interpolate.InterpolatedUnivariateSpline(self.frequency, self.get_power(), None, [None, None], 1)

		return self.power_spline

	def get_powerfreq_spline(self):
		if not self.powerfreq_spline:
			self.powerfreq_spline = scipy.interpolate.InterpolatedUnivariateSpline(self.frequency, self.get_power()*self.frequency, None, [None, None], 1)

		return self.powerfreq_spline

	def get_power_in_frequency_range(self,lower,upper):
		return self.get_power_spline().integral(lower, upper)

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

gobject.type_register(SpectrumData)

#############################################################################

class FretboardCairo(gtk.DrawingArea):
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

class TotalFretboardCairo(FretboardCairo):
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

class SingleStringAreaCairo(TotalFretboardCairo):
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

class SingleStringCairo(FretboardCairo):
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
