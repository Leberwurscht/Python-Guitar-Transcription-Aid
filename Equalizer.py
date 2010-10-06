#!/usr/bin/env python

import gtk
import Elements

import matplotlib
import matplotlib.backends.backend_gtkcairo as mpl_backend

import numpy

import gst, Elements

class PlotEditable(gtk.Window):
	def __init__(self, x, y):
		gtk.Window.__init__(self)

		self.x = x
		self.y = y
		self.mouse_button_pressed = False

		fig = matplotlib.figure.Figure(figsize=(5,4))
		self.ax = fig.add_subplot(111)

		vbox = gtk.VBox()
		self.add(vbox)

		self.figure = mpl_backend.FigureCanvasGTK(fig)
		self.figure.set_size_request(500,400)
		self.navbar = mpl_backend.NavigationToolbar2Cairo(self.figure, self)
		vbox.pack_start(self.figure)
		vbox.pack_start(self.navbar, False, False)

		self.line, = self.ax.plot(self.x, self.y)

		fig.canvas.mpl_connect('button_press_event', self.press)
		fig.canvas.mpl_connect('motion_notify_event', self.motion)
		fig.canvas.mpl_connect('button_release_event', self.release)

		self.connect("delete-event", self.close)

		btn = gtk.ToggleButton("Test with noise")
		btn.connect("toggled", self.toggle_noise)
		vbox.add(btn)

		self.pipeline = gst.parse_launch("spectrum_noise0 ! spectrum_equalizer name=eq ! ifft ! audioconvert ! gconfaudiosink")

	def toggle_noise(self, widget):
		if widget.get_active():
			self.pipeline.set_state(gst.STATE_PLAYING)
		else:
			self.pipeline.set_state(gst.STATE_NULL)

	def close(self, *args):
		self.pipeline.set_state(gst.STATE_NULL)

	def press(self, event):
		self.mouse_button_pressed = True

		# call motion
		self.motion(event)

	def motion(self, event):
		# don't edit if in pan or zoom mode
		if not self.ax.get_navigate_mode()==None: return

		# only edit if mouse button is pressed
		if not self.mouse_button_pressed: return

		# exclude events from outside of the plotting rectangle
		if not event.inaxes==self.ax: return

		# event.xdata is passed, but we need tolerance also so we calculate min and max values manually
		min_x = event.x - 0.5
		max_x = event.x + 0.5

		min_xdata,y = self.ax.transData.inverted().transform_point((min_x, 0))
		max_xdata,y = self.ax.transData.inverted().transform_point((max_x, 0))

		# make copy of data (matplotlib will not recognise change when it's done in place)
		self.y = numpy.array(self.y)

		# adjust all points within tolerance
		for i in xrange(len(self.x)):
			if min_xdata<self.x[i] and self.x[i]<max_xdata:
				self.y[i] = event.ydata

		self.line.set_ydata(self.y)
		self.line.figure.canvas.draw()

		self.pipeline.get_by_name("eq").props.weights = self.y

	def release(self, event):
		# matplotlib is smart enough to call this even if mouse is released outside of the window
		self.mouse_button_pressed = False
