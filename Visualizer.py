#!/usr/bin/env python

import gtk, numpy, cairo, goocanvas, gobject
import gst
import scipy.interpolate
import Math
from VisualizerControlBase import base as VisualizerControlBase

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
	x = gobject.property(type=gobject.TYPE_DOUBLE)
	y = gobject.property(type=gobject.TYPE_DOUBLE)
	width = gobject.property(type=gobject.TYPE_DOUBLE, default=30)
	height = gobject.property(type=gobject.TYPE_DOUBLE, default=20)

	semitone = gobject.property(type=gobject.TYPE_DOUBLE, default=0)

	def __init__(self, control, method="gradient", **kwargs):
		goocanvas.ItemSimple.__init__(self,**kwargs)

		if not self.props.tooltip:
			self.props.tooltip = Math.note_name(self.semitone)+" ("+str(self.semitone)+") ["+str(Math.semitone_to_frequency(self.semitone))+" Hz]"

		self.method = method

		self.control = control
		self.control.connect("new_data", self.new_data)

		self.matrix = None

	# override ItemSimple
	def do_simple_paint(self, cr, bounds):
		cr.translate(self.x, self.y)
		cr.rectangle(0.0, 0.0, self.width, self.height)

		if not self.control.has_data:
			cr.set_source_rgb(1.,1.,1.)
		elif self.method=="cumulate":
			fpower, power, center, standard_deviation, upper_dependence, lower_dependence = self.control.analyze_semitone(self.semitone)
			magnitude = Math.power_to_magnitude(power / 1.5 / 1000)
			const,slope = self.control.get_brightness_coefficients_for_magnitude()
			brightness = slope*magnitude + const
			print self.semitone,"mag",magnitude,"tpow",power,"b",brightness,"pow",fpower
			cr.set_source_rgb(brightness,brightness,brightness)
		elif self.method=="test":
			fpower, power, center, standard_deviation, upper_dependence, lower_dependence = self.control.analyze_semitone(self.semitone)
			upper_dependence = min(1.,upper_dependence)
			lower_dependence = min(1.,lower_dependence)
			total_dependence = min(1., upper_dependence+lower_dependence)
			power *= 1. - total_dependence
			magnitude = Math.power_to_magnitude(power / 1.5 / 1000)
			const,slope = self.control.get_brightness_coefficients_for_magnitude()
			brightness = slope*magnitude + const
			cr.set_source_rgb(brightness,brightness,brightness)
		elif self.method=="inharmonicity":
			fpower, power, center, standard_deviation, upper_dependence, lower_dependence = self.control.analyze_semitone(self.semitone)
			brightness = standard_deviation / 0.5
			cr.set_source_rgb(brightness,brightness,brightness)
		elif self.method=="lower_dependence":
			fpower, power, center, standard_deviation, upper_dependence, lower_dependence = self.control.analyze_semitone(self.semitone)
			brightness = lower_dependence
			cr.set_source_rgb(brightness,brightness,brightness)
		elif self.method=="upper_dependence":
			fpower, power, center, standard_deviation, upper_dependence, lower_dependence = self.control.analyze_semitone(self.semitone)
			brightness = upper_dependence
			cr.set_source_rgb(brightness,brightness,brightness)
		elif self.method=="gradient":
			assert not self.matrix==None
			gradient = self.control.get_gradient()
			gradient.set_matrix(self.matrix)
			cr.set_source(gradient)
		else:
			raise ValueError, "Invalid method"

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
	def new_data(self, control):
		self.changed(False)

class FretboardBase(goocanvas.Group):
	def __init__(self, control, volume, **kwargs):
		self.volume = volume
		self.control = control

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

		self.pipeline = gst.parse_launch("audiotestsrc name=src wave=saw ! volume name=volume ! gconfaudiosink")

		self.construct(self.paddingx, self.paddingy)

	def construct(self, posx, posy):
		# fretboard
		for string in xrange(len(self.strings)):
			semitone = self.strings[string]

			for fret in xrange(self.frets+1):
				x = posx + fret*self.rectwidth
				y = posy + self.rectheight*string

				rect = Semitone(self.control, semitone=semitone+fret, method=self.method,
					parent=self, x=x, y=y, width=self.rectwidth, height=self.rectheight)

				rect.connect("button_press_event", self.press_semitone, string, fret)
				rect.connect("button_release_event", self.release_semitone)

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
	def press_semitone(self,semitone,target,event,string,fret):
		if event.button==1:
			self.pipeline.get_by_name("volume").set_property("volume", self.volume.get_value())
			self.pipeline.get_by_name("src").set_property("freq", Math.semitone_to_frequency(semitone.semitone))
			self.pipeline.set_state(gst.STATE_PLAYING)
		elif event.button==3:
			self.open_context_menu(semitone,event,string,fret)

	def release_semitone(self,item,target,event):
		self.pipeline.set_state(gst.STATE_NULL)

	def open_context_menu(self, rect, event, string, fret):
		raise NotImplementedError, "override this method!"

	def add_tab_marker(self, item, target, event, string, fret):
		self.control.emit("add-tab-marker", string, fret)

	def plot_evolution(self, item, target, event, semitone):
		self.control.emit("plot-evolution", semitone)

	def find_onset(self, item, target, event, semitone):
		self.control.emit("find-onset", semitone)

	def analyze_semitone(self, item, target, event, semitone):
		self.control.emit("analyze-semitone", semitone)

	# custom properties
	def do_get_property(self,pspec):
		return getattr(self, pspec.name)

	def do_set_property(self,pspec,value):
		setattr(self, pspec.name, value)

class Fretboard(FretboardBase):
	def __init__(self, control, volume, **kwargs):
		FretboardBase.__init__(self, control, volume, **kwargs)

	def construct(self, posx, posy):
		# captions
		fretcaptions = goocanvas.Group(parent=self)
		for fret in xrange(1,self.frets+1):
			goocanvas.Text(parent=fretcaptions, x=fret*self.rectwidth, y=0, text=str(fret), anchor=gtk.ANCHOR_NORTH, font=10)

		stringcaptions = goocanvas.Group(parent=self)
		for string in xrange(len(self.strings)):
			semitone = self.strings[string]
			name = Math.note_name(semitone).upper()
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
		item.connect("activate", self.analyze_semitone, item, None, self.strings[string]+fret)
		menu.append(item)

		item = gtk.MenuItem("Plot")
		item.connect("activate", self.plot_evolution, item, None, self.strings[string]+fret)
		menu.append(item)

		item = gtk.MenuItem("Find onset")
		item.connect("activate", self.find_onset, item, None, self.strings[string]+fret)
		menu.append(item)

		item = gtk.MenuItem("Add to tabulature")
		item.connect("activate", self.add_tab_marker, item, None, string, fret)
		menu.append(item)

		menu.show_all()
		menu.popup(None, None, None, event.button, event.time)

	def open_string(self, item, target, event, string):
		w = SingleStringWindow(self.control, self.strings[string])
		w.show_all()

class SingleString(FretboardBase):
	def __init__(self, control, volume, **kwargs):
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

		if "method" in kwargs:
			if not kwargs["method"] in ["gradient","cumulate"]:
				raise ValueError, "invalid method for SingleString"

		FretboardBase.__init__(self, control, volume, **kwargs)

	def construct(self, posx, posy):
		# captions
		fretcaptions = goocanvas.Group(parent=self)
		for fret in xrange(0,self.frets+1):
			text = goocanvas.Text(parent=fretcaptions, x=fret*self.rectwidth, y=0, text=str(fret), anchor=gtk.ANCHOR_NORTH, font=10)

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

		# analyze
		y = self.get_bounds().y2 + 10
		for fret in xrange(0,self.frets+1):
			x = startx + self.rectwidth*fret
			rect = Semitone(self.control, semitone=self.tuning+fret, method="inharmonicity", parent=self, x=x, y=y, width=self.rectwidth, height=self.rectheight)

		y += self.rectheight
		for fret in xrange(0,self.frets+1):
			x = startx + self.rectwidth*fret
			rect = Semitone(self.control, semitone=self.tuning+fret, method="lower_dependence", parent=self, x=x, y=y, width=self.rectwidth, height=self.rectheight)

		y += self.rectheight
		for fret in xrange(0,self.frets+1):
			x = startx + self.rectwidth*fret
			rect = Semitone(self.control, semitone=self.tuning+fret, method="upper_dependence", parent=self, x=x, y=y, width=self.rectwidth, height=self.rectheight)

		y += self.rectheight
		for fret in xrange(0,self.frets+1):
			x = startx + self.rectwidth*fret
			rect = Semitone(self.control, semitone=self.tuning+fret, method="cumulate", parent=self, x=x, y=y, width=self.rectwidth, height=self.rectheight)

		y += self.rectheight
		for fret in xrange(0,self.frets+1):
			x = startx + self.rectwidth*fret
			rect = Semitone(self.control, semitone=self.tuning+fret, method="test", parent=self, x=x, y=y, width=self.rectwidth, height=self.rectheight)

	# callbacks
	def open_context_menu(self, rect, event, string, fret):
		semitone = self.tuning + fret

		menu = gtk.Menu()

		item = gtk.MenuItem("Analyze")
		item.connect("activate", self.analyze_semitone, item, None, self.tuning+fret)
		menu.append(item)

		item = gtk.MenuItem("Plot")
		item.connect("activate", self.plot_evolution, item, None, self.strings[string]+fret)
		menu.append(item)

		item = gtk.MenuItem("Find onset")
		item.connect("activate", self.find_onset, item, None, self.strings[string]+fret)
		menu.append(item)

#		item = gtk.MenuItem("Add to tabulature")
#		item.connect("activate", self.add_tab_marker, item, None, string, fret)
#		menu.append(item)

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

class FretboardWindow(FretboardWindowBase):
	def __init__(self, control, **kwargs):
		FretboardWindowBase.__init__(self, **kwargs)

		self.set_title("Fretboard")

		root = self.canvas.get_root_item()
		self.visualizer = Fretboard(control, self.volume, parent=root)

		self.adjust_canvas_size()

		hbox = gtk.HBox()
		self.controls.add(hbox)

		label = gtk.Label("Method")
		hbox.add(label)

		combobox = gtk.combo_box_new_text()
#		string = self.project.timeline.tabulature.strings[i]
#		combobox.append_text(str(i+1)+" ("+str(string.tuning)+")")
		combobox.set_active(0)

class SingleStringWindow(FretboardWindowBase):
	def __init__(self, control, tuning=-5, **kwargs):
		FretboardWindowBase.__init__(self, **kwargs)

		self.set_title("SingleString "+Math.note_name(tuning)+" ("+str(tuning)+")")

		root = self.canvas.get_root_item()
		self.visualizer = SingleString(control, self.volume, parent=root, tuning=tuning)

		self.adjust_canvas_size()

class VisualizerControl(VisualizerControlBase):
	__gproperties__ = {
		'autoupdate': (gobject.TYPE_BOOLEAN,'AutoUpdate','Whether to update visualizers while playback',False,gobject.PARAM_READWRITE)
	}

	__gsignals__ = {
		'new-data': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
		'add-tab-marker': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_INT, gobject.TYPE_INT)),
		'plot-evolution': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_INT,)),
		'find-onset': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_INT,)),
		'analyze-semitone': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_INT,))
	}

	""" holds data for visualizers, calculates and caches different scales """
	def __init__(self, pipeline, **kwargs):
		VisualizerControlBase.__init__(self, pipeline.spectrum, pipeline)
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

		self.clear()

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
	def autoupdate(self, control, bands, rate, threshold, start, duration, magnitude):
		frequency = 0.5 * ( numpy.arange(bands) + 0.5 ) * rate / bands
		self.set_magnitude(start, duration, frequency, numpy.array(magnitude))

	# set data
	def clear(self):
		self.power = None
		self.magnitude = None
		self.brightness = None
		self.semitone = None
		self.power_spline = None
		self.powerfreq_spline = None
		self.gradient = None
		self.has_data = None
		self.start = None
		self.duration = None

	def set_magnitude(self, start, duration, frequency, magnitude):
		self.clear()
		self.start = start
		self.duration = duration
		self.frequency = frequency
		self.magnitude = magnitude
		self.has_data = True
		self.emit("new_data")
		
	def set_power(self, start, duration, frequency, power):
		self.clear()
		self.start = start
		self.duration = duration
		self.frequency = frequency
		self.power = power
		self.has_data = True
		self.emit("new_data")

	# get data
	def get_semitone(self):
		if self.semitone==None: self.semitone = Math.frequency_to_semitone(self.frequency)
		return self.semitone

	def get_magnitude(self):
		if self.magnitude==None: self.magnitude = Math.power_to_magnitude(self.power)
		return self.magnitude

	def get_power(self):
		if self.power==None: self.power = Math.magnitude_to_power(self.magnitude)
		return self.power

	def get_brightness_coefficients_for_magnitude(self):
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

		return brightness_const, brightness_slope

	def get_brightness_coefficients_for_power(self):
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

		return brightness_const, brightness_slope

	def get_brightness(self):
		if self.brightness==None:
			if self.brightness_method=="from_magnitude":
				brightness_const, brightness_slope = self.get_brightness_coefficients_for_magnitude()

				brightness = brightness_slope * self.get_magnitude() + brightness_const
				self.brightness = numpy.maximum(0.,numpy.minimum(1.,brightness))
			elif self.brightness_method=="from_power":
				brightness_const, brightness_slope = self.get_brightness_coefficients_for_power()

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

	def get_peak_radius(self):
		bands = len(self.frequency)
		rate = 2.0 * bands * self.frequency[-1] / ( bands-0.5 )
		data_length = 2*bands - 2

		# http://mathworld.wolfram.com/HammingFunction.html: position of first root of apodization function
		peak_radius = 1.299038105676658 * rate / data_length

		return peak_radius

	def analyze_overtones(self,semitone,overtones=None):
		""" calculates power and peak center for each overtone and yields tuples (overtone, frequency, power, peak_center, difference_in_semitones) """
		frequency = Math.semitone_to_frequency(semitone)
		peak_radius = self.get_peak_radius()

		overtone=0

		while overtones==None or overtone<overtones:
			f = frequency*(overtone+1)
			s = Math.frequency_to_semitone(f)

			lower_frequency = f - peak_radius*1.65
			upper_frequency = f + peak_radius*1.65

			lower_frequency = min(lower_frequency, Math.semitone_to_frequency(s-0.5))
			upper_frequency = max(upper_frequency, Math.semitone_to_frequency(s+0.5))

			power = self.get_power_in_frequency_range(lower_frequency,upper_frequency)
			peak_center = self.get_powerfreq_spline().integral(lower_frequency,upper_frequency) / power

			difference_in_semitones = Math.frequency_to_semitone(peak_center) - s

			yield overtone, f, power, peak_center, difference_in_semitones

			overtone += 1

	def analyze_semitone(self,semitone,overtones=10, undertones=2, undertone_limit=80.):
		""" calculate total power, inharmonicity and independence coefficients """

		analysis = self.analyze_overtones(semitone,overtones)

		# fundamental tone
		overtone, fundamental_frequency, power, peak_center, difference_in_semitones = analysis.next()

		fundamental_power = power
		fundamental_diff_square = power * difference_in_semitones**2.
		fundamental_diff = power * difference_in_semitones

		# overtones
		overtone_power = 0
		overtone_diff_squares = 0
		overtone_diffs = 0

		for overtone, frequency, power, peak_center, difference_in_semitones in analysis:
			overtone_power += power
			overtone_diff_squares += power * difference_in_semitones**2.
			overtone_diffs += power * difference_in_semitones

		total_power = fundamental_power + overtone_power
		diff_squares = fundamental_diff_square + overtone_diff_squares
		diffs = fundamental_diff + overtone_diffs

		center = diffs/total_power
		variance = diff_squares/total_power - center**2.
		standard_deviation = numpy.sqrt(variance)

		# calculate upper_dependence
#		if fundamental_frequency<150.: fp = fundamental_power*15.	# exception for low-pitched tones
#		else: fp = fundamental_power
#		alien_power = max(0, overtone_power - 0.5*fp)
		alien_power = max(0, overtone_power - 0.5*fundamental_power)
		upper_dependence = alien_power / total_power
		print "upperdependence of %d is %f" % (semitone, upper_dependence)

		# calculate lower_dependence
		peak_radius = self.get_peak_radius()

		undertone_power = 0

		for undertone in xrange(2,undertones+2):
			undertone_frequency = fundamental_frequency / undertone
			if undertone_frequency < undertone_limit: break

			s = Math.frequency_to_semitone(undertone_frequency)

			lower_frequency = undertone_frequency - peak_radius*1.65
			upper_frequency = undertone_frequency + peak_radius*1.65

			lower_frequency = min(lower_frequency, Math.semitone_to_frequency(s-0.5))
			upper_frequency = max(upper_frequency, Math.semitone_to_frequency(s+0.5))

			power = self.get_power_in_frequency_range(lower_frequency,upper_frequency)

			power /= undertone**2.

#			if undertone_frequency>150.: power *= 15

			undertone_power += power

		lower_dependence = undertone_power / total_power
		print "lowerdependence of %d is %f (%f/%f)" % (semitone, lower_dependence, undertone_power, total_power)

		return fundamental_power, total_power, center, standard_deviation, upper_dependence, lower_dependence

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

		#1> ~total power in mother tones with some weights
		# to get a big number, we need more power in one mother tone(except for low-pitched ones->amplify them).
		# -> ALGORITHM:
		#	weights = 1/frequency**2
		#	weights[0 Hz : 150 Hz] = weights[150 Hz] (exception for low-pitched tones)
		#	weighted_power = weights * power
		#	lower_dependence = sum[weighted_power(f/i) for i in xrange()] * f**2

		#2> if one overtone has much greater power, subtract it from total power (except for low-pitched tones)
		# [   1 + 1/4 + 1/9 + 1/16 + ... ~= 1.5 ]
		# 1 1/4 1/9
		# so overtones should have same power or less as fundamental tone*.5
		# (if fundamental frequency < 150Hz, fundamental frequency is given a bonus *= 15)
		# if not, an overtone note is also played.
		## find position of this overtone note (maximum?)
		## => subtract overtone note power from total power, divide by total power
		## => this is the percentage of power that belongs to this tone
		# so clip total power to fundamental_power * 1.5
		# upper_dependence is percentage of power not belonging to fundamental tone.
		# -> ALGORITHM:
		#	if fundamental_frequency<150Hz: fundamental_power *= 15
		#	alien_power = max(0, overtone_power - .5*fundamental_power)
		#	total power = overtone_power + fundamental_power
		#	upper_dependence = alien_power / total_power
		#
		#	( => upper_dependence = (overtone_power - .5*fundamental_power) / (overtone_power+fundamental_power) < 1 )

		# problem: if only one overtone exists, inharmonicity is 0 but this is not necessarily a note

		points = 0
		power = 0

		power = self.get_total_power_in_frequency_range(lower,upper,overtones)

		return points

gobject.type_register(VisualizerControl)
