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
		self.last_mouse_position = None

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
		self.ax.set_ylim(-0.05,2)

		fig.canvas.mpl_connect('button_press_event', self.press)
		fig.canvas.mpl_connect('motion_notify_event', self.motion)
		fig.canvas.mpl_connect('button_release_event', self.release)

		self.connect("delete-event", self.close)

		btn = gtk.ToggleButton("Test with noise")
		btn.connect("toggled", self.toggle_noise)
		vbox.add(btn)

		self.pipeline = gst.parse_launch("spectrum_noise ! spectrum_equalizer name=eq ! ifft ! audioconvert ! gconfaudiosink")
		self.pipeline.get_by_name("eq").props.weights = self.y

	def toggle_noise(self, widget):
		if widget.get_active():
			self.pipeline.set_state(gst.STATE_PLAYING)
		else:
			self.pipeline.set_state(gst.STATE_NULL)

	def close(self, *args):
		self.pipeline.set_state(gst.STATE_NULL)

	def press(self, event):
		# don't edit if in pan or zoom mode
		if not self.ax.get_navigate_mode()==None: return

		# exclude events from outside of the plotting rectangle
		if not event.inaxes==self.ax: return

		self.mouse_button_pressed = True

		# get nearest x position
		l = len(self.x)

		i = 0
		while i<l and self.x[i] < event.xdata: i += 1

		assert (i==l and self.x[-1]<event.xdata) or (i==0 and event.xdata<=self.x[0]) or (self.x[i-1]<event.xdata and event.xdata<=self.x[i])

		if i==0:
			nearest_index = i
		elif i==l:
			nearest_index = -1
		elif abs(event.xdata-self.x[i])<abs(event.xdata-self.x[i-1]):
			nearest_index = i
		else:
			nearest_index = i-1

		# adjust y value
		self.y[nearest_index] = event.ydata
		self.line.recache()
		self.line.figure.canvas.draw()

		# save position
		self.last_mouse_position = event.x, event.y

	def motion(self, event):
		# don't edit if in pan or zoom mode
		if not self.ax.get_navigate_mode()==None: return

		# only edit if mouse button is pressed
		if not self.last_mouse_position: return

		# exclude events from outside of the plotting rectangle
		if not event.inaxes==self.ax: return

		# event.xdata is passed, but we need tolerance also so we calculate min and max values manually
		min_x = event.x - 0.5
		max_x = event.x + 0.5

		min_xdata,y = self.ax.transData.inverted().transform_point((min_x, 0))
		max_xdata,y = self.ax.transData.inverted().transform_point((max_x, 0))

		# same procedure for last mouse position
		xlast, ylast = self.last_mouse_position
		min_x = xlast - 0.5
		max_x = xlast + 0.5

		min_xlastdata,y = self.ax.transData.inverted().transform_point((min_x, 0))
		max_xlastdata,y = self.ax.transData.inverted().transform_point((max_x, 0))

		# get x range
		if xlast<event.x:
			min_x = min_xlastdata
			max_x = max_xdata
		else:
			min_x = min_xdata
			max_x = max_xlastdata

		assert max_x-min_x>0

		# compute coefficients for interpolation line
		xlastdata,ylastdata = self.ax.transData.inverted().transform_point((xlast, ylast))

		slope = 1.*(event.ydata - ylastdata)/(max_x - min_x) # use max_x and min_x to avoid zero division

		if xlast>=event.x:
			slope *= -1

		const = ylastdata - slope*xlastdata

		# adjust points
		for i in xrange(len(self.x)):
			if self.x[i]>max_x: break

			if min_x<=self.x[i]:
				self.y[i] = slope*self.x[i] + const

		# redraw
		self.line.recache()
		self.line.figure.canvas.draw()

		# save mouse position
		self.last_mouse_position = event.x, event.y

	def release(self, event):
		# matplotlib is smart enough to call this even if mouse is released outside of the window
		self.last_mouse_position = None
