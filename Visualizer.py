#!/usr/bin/env python

import gtk, numpy, cairo, goocanvas, gobject
import gst
import Math

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
