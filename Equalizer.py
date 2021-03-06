#!/usr/bin/env python

import gtk

import matplotlib
import matplotlib.backends.backend_gtkcairo as mpl_backend

import gst
import Elements # we do not refer to classes contained in Elements directly, but we need to import this for gst.parse_launch to recognise the elements

class EqualizerWindow(gtk.Window):
	def __init__(self, equalizer_element):
		gtk.Window.__init__(self)

		# last mouse position must be saved when dragging - if mouse is moved fast,
		# pixels are skipped so we need to interpolate
		self.last_mouse_position = None

		# redraw when transmission function of equalizer is changed
		self.equalizer_element = equalizer_element
		equalizer_element.connect("notify::transmission", self.redraw)

		# create vbox
		vbox = gtk.VBox()
		self.add(vbox)

		# setup plot
		fig = matplotlib.figure.Figure(figsize=(5,4))
		self.ax = fig.add_subplot(111)

		self.figure = mpl_backend.FigureCanvasGTK(fig)
		self.figure.set_size_request(500,400)
		vbox.pack_start(self.figure)

		self.line, = self.ax.plot(equalizer_element.frequencies, equalizer_element.props.transmission)
		self.ax.set_ylim(-0.05,2)

		# connect mouse callbacks
		fig.canvas.mpl_connect('button_press_event', self.press)
		fig.canvas.mpl_connect('motion_notify_event', self.motion)
		fig.canvas.mpl_connect('button_release_event', self.release)

		# setup navbar
		self.navbar = mpl_backend.NavigationToolbar2Cairo(self.figure, self)
		vbox.pack_start(self.navbar, False, False)

		# add buttons
		btn = gtk.ToggleButton("Test with noise")
		btn.connect("toggled", self.toggle_noise)
		vbox.pack_start(btn, False, False)

		btn = gtk.Button("Reset")
		btn.connect("clicked", self.set_constant, 1.)
		vbox.pack_start(btn, False, False)

		btn = gtk.Button("Set to zero")
		btn.connect("clicked", self.set_constant, 0.)
		vbox.pack_start(btn, False, False)

		# connect close callback
		self.connect("delete-event", self.close)

		# setup gstreamer pipeline to test the equalizer with noise
		self.pipeline = gst.parse_launch("spectrum_noise ! spectrum_equalizer name=eq ! ifft ! audioconvert ! gconfaudiosink")
		self.pipeline.get_by_name("eq").props.transmission = self.equalizer_element.props.transmission

	def redraw(self, *args):
		self.line.recache()
		self.line.figure.canvas.draw()

	def set_constant(self, widget, c):
		transmission = self.equalizer_element.props.transmission
		transmission[:] = c
		self.equalizer_element.props.transmission = transmission

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

		# get abscissa and ordinate
		x = self.line.get_xdata()
		y = self.line.get_ydata()

		# get nearest x position
		l = len(x)

		i = 0
		while i<l and x[i] < event.xdata: i += 1

		assert (i==l and x[-1]<event.xdata) or (i==0 and event.xdata<=x[0]) or (x[i-1]<event.xdata and event.xdata<=x[i])

		if i==0:
			nearest_index = i
		elif i==l:
			nearest_index = -1
		elif abs(event.xdata-x[i])<abs(event.xdata-x[i-1]):
			nearest_index = i
		else:
			nearest_index = i-1

		# adjust y value
		y[nearest_index] = event.ydata

		# transfer y to equalizer_element
		self.equalizer_element.props.transmission = y

		# save position
		self.last_mouse_position = event.x, event.y

	def motion(self, event):
		# don't edit if in pan or zoom mode
		if not self.ax.get_navigate_mode()==None: return

		# only edit if mouse button is pressed
		if not self.last_mouse_position: return

		# exclude events from outside of the plotting rectangle
		if not event.inaxes==self.ax: return

		# get abscissa and ordinate
		x = self.line.get_xdata()
		y = self.line.get_ydata()

		# event.xdata is passed, but we need tolerance also so we calculate min and max values manually
		min_x = event.x - 0.5
		max_x = event.x + 0.5

		min_xdata,ydrop = self.ax.transData.inverted().transform_point((min_x, 0))
		max_xdata,ydrop = self.ax.transData.inverted().transform_point((max_x, 0))

		# same procedure for last mouse position
		xlast, ylast = self.last_mouse_position
		min_x = xlast - 0.5
		max_x = xlast + 0.5

		min_xlastdata,ydrop = self.ax.transData.inverted().transform_point((min_x, 0))
		max_xlastdata,ydrop = self.ax.transData.inverted().transform_point((max_x, 0))

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
		for i in xrange(len(x)):
			if x[i]>max_x: break

			if min_x<=x[i]:
				y[i] = slope*x[i] + const

		# transfer y to equalizer_element
		self.equalizer_element.props.transmission = y

		# save mouse position
		self.last_mouse_position = event.x, event.y

	def release(self, event):
		# matplotlib is smart enough to call this even if mouse is released outside of the window
		self.last_mouse_position = None
