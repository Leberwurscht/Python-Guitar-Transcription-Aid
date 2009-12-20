#!/usr/bin/env python

import gtk
import gtk.glade
import gst
import goocanvas
import threading

AUDIOFREQ=32000

class Pipeline(gst.Pipeline):
	def __init__(self,filename):
		# creating the pipeline
		gst.Pipeline.__init__(self,"mypipeline")
		self.tempo=1.

		# creating a gnlcomposition
		self.comp = gst.element_factory_make("gnlcomposition", "mycomposition")
		self.add(self.comp)
		self.comp.connect("pad-added", self.OnPad)

		# create spectrum
		self.spectrum = gst.element_factory_make("spectrum", "spectrum")
		self.spectrum.set_property("bands",1024)
		self.add(self.spectrum)

		# create caps
		self.caps2 = gst.element_factory_make("capsfilter", "filter")
		self.caps2.set_property("caps", gst.Caps("audio/x-raw-int", rate=AUDIOFREQ))
		self.add(self.caps2)
		self.spectrum.link(self.caps2)

		# create scaletempo
		self.scaletempo = gst.element_factory_make("scaletempo", "scaletempo")
		self.add(self.scaletempo)
		self.caps2.link(self.scaletempo)

		# create an audioconvert
		self.compconvert = gst.element_factory_make("audioconvert", "compconvert")
		self.add(self.compconvert)
		self.scaletempo.link(self.compconvert)

		# create an alsasink
		self.sink = gst.element_factory_make("alsasink", "alsasink")
		self.add(self.sink)
		self.compconvert.link(self.sink)
		
		# create a gnlfilesource
		self.audio1 = gst.element_factory_make("gnlfilesource", "audio1")
		self.comp.add(self.audio1)

		# set the gnlfilesource properties
		self.audio1.set_property("location", filename)
		self.audio1.set_property("start", 0 * gst.SECOND)
		self.audio1.set_property("duration", 15* gst.SECOND)
		self.audio1.set_property("media-start", 10 * gst.SECOND)
		self.audio1.set_property("media-duration", 5 * gst.SECOND)

		# spectrum
		bus = self.get_bus()
		bus.add_signal_watch()
		bus.connect("message", self.on_message)

	def on_message(self, bus, message):
		s = message.structure

		if s and s.get_name() == "spectrum":
#			for i in s: print i
			print s['magnitude']

	def OnPad(self, comp, pad):
		convpad = self.spectrum.get_compatible_pad(pad, pad.get_caps())
		pad.link(convpad)

	def play(self,start,duration):
		self.audio1.set_property("start", 0)
		self.audio1.set_property("duration", int(duration/self.tempo * gst.SECOND))
		self.audio1.set_property("media-start", int(start * gst.SECOND))
		self.audio1.set_property("media-duration", int(duration * gst.SECOND))

		print "start",0
		print "duration",int(duration/self.tempo * gst.SECOND)
		print "media-start", int(start * gst.SECOND)
		print "media-duration", int(duration * gst.SECOND)
		
		self.set_state(gst.STATE_PLAYING)

	def stop(self,*args):
		self.set_state(gst.STATE_NULL)

	def set_tempo(self,widget):
		self.tempo=widget.get_value() / 100.

class Fretboard(goocanvas.Canvas):
	def __init__(self):
		goocanvas.Canvas.__init__(self)

class Timeline(goocanvas.Canvas):
	def __init__(self, seconds, pl):
		goocanvas.Canvas.__init__(self)

		self.pl=pl

		self.mode = None
		self.dragging=False

		### Setup canvas ###
		self.seconds = seconds
		self.length = seconds*50

		self.set_bounds(0,0,400,self.length)
		self.connect("button_release_event",self.canvas_button_release)

		self.root = self.get_root_item()

		### Create Timeline + Space for elements ###

		self.timeline = goocanvas.Group(parent=self.root)
		self.timerect = goocanvas.Rect(parent=self.timeline,width=40,height=self.length,fill_color="blue")
		self.marker = goocanvas.Rect(parent=self.timeline,width=40,height=10,visibility=goocanvas.ITEM_INVISIBLE, fill_color_rgba=0xaa000044)
		self.marker.props.pointer_events = 0
		self.timerect.connect("motion_notify_event", self.timerect_on_motion_notify)
        	self.timerect.connect("button_press_event", self.timerect_on_button_press)
		self.timerect.connect("button_release_event", self.timerect_on_button_release)

		for i in xrange(seconds):
			goocanvas.Text(parent=self.timeline, text=str(i), y=i*50)

		self.space = goocanvas.Group(parent=self.root)
		self.space.translate(50,0)
#		self.spacerect = goocanvas.Rect(parent=self.space,width=350,height=self.length)

	def enable_dragging(self,item):
		item.connect("motion_notify_event", self.on_motion_notify)
        	item.connect("button_press_event", self.on_button_press)
		item.connect("button_release_event", self.on_button_release)

	def timerect_on_motion_notify (self, item, target, event):
		if (self.dragging == True) and (event.state & gtk.gdk.BUTTON1_MASK):
			if self.drag_y<0:
				self.marker.props.y=0
			if event.y>self.drag_y:
				self.marker.props.y=self.drag_y
				self.marker.props.height=event.y-self.drag_y
			else:
				self.marker.props.y=event.y
				self.marker.props.height=self.drag_y-event.y
				
		return True
    
	def timerect_on_button_press (self, item, target, event):
		if event.button == 1:
			self.drag_y = event.y

			canvas = item.get_canvas()
			canvas.pointer_grab (item, gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.BUTTON_RELEASE_MASK, None, event.time)
        	        self.dragging = True

			self.marker.props.visibility = goocanvas.ITEM_VISIBLE
			self.marker.props.y=event.y
			self.marker.props.height=0
	        return True

	def timerect_on_button_release (self, item, target, event):
		canvas = item.get_canvas()
		canvas.pointer_ungrab(item, event.time)
		self.dragging = False

	def on_motion_notify (self, item, target, event):
		if (self.dragging == True) and (event.state & gtk.gdk.BUTTON1_MASK):
			new_x = event.x
			new_y = event.y
			item.translate (new_x - self.drag_x, new_y - self.drag_y)
		return True
    
	def on_button_press (self, item, target, event):
		if event.button == 1:
			self.drag_x = event.x
			self.drag_y = event.y

			canvas = item.get_canvas()
			canvas.pointer_grab (item, gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.BUTTON_RELEASE_MASK, None, event.time)
        	        self.dragging = True
	        return True

	def on_button_release (self, item, target, event):
		canvas = item.get_canvas()
		canvas.pointer_ungrab(item, event.time)
		self.dragging = False

	def canvas_button_release(self,widget,event):
		if self.mode=="text":
			dialog = gtk.Dialog(title="Text", flags=gtk.DIALOG_DESTROY_WITH_PARENT|gtk.DIALOG_MODAL, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
			entry = gtk.Entry()
			dialog.vbox.add(entry)
			dialog.show_all()
			if dialog.run()==gtk.RESPONSE_ACCEPT:
				x,y,scale,rotation = self.space.get_simple_transform()
				text = goocanvas.Text(parent=self.space, text=entry.get_text(), x=event.x-x, y=event.y-y)
				self.enable_dragging(text)
			dialog.destroy()
			self.mode=None

	def insert_text(self,*args):
		self.mode="text"
	def play(self,*args):
		self.pl.play(self.marker.props.y/50.,self.marker.props.height/50.)

if __name__=="__main__":
	glade = gtk.glade.XML("gui.glade", "mainwindow")
	glade.get_widget("mainwindow").show_all()

	pl = Pipeline("/home/maxi/Musik/ogg/jamendo_track_9087.ogg")

	tl = Timeline(200,pl)
	glade.get_widget("scrolledwindow").add(tl)
	tl.show_all()

	glade.signal_autoconnect({'gtk_main_quit':gtk.main_quit,'insert_text':tl.insert_text, 'play':tl.play, 'stop':pl.stop, 'set_tempo':pl.set_tempo})
	gtk.main()
