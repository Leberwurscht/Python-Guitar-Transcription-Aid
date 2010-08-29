#!/usr/bin/env python

import gtk, numpy, scipy

import matplotlib
import matplotlib.backends.backend_gtkcairo as mpl_backend

def get_power(data, rate):
	# calculate frequencies
	bands = len(data)/2 + 1
	frq = 0.5 * ( numpy.arange(bands) + 0.5 ) * rate / bands

	# apply window
	window = numpy.hanning(len(data))
	data *= window

	# fft
	power = numpy.abs(numpy.fft.rfft(data))
	smoothed = numpy.convolve(power, numpy.hanning(1), "same")

	return frq, smoothed

def find_peaks(frq,power,max_window=3,min_window=3,height=0.0001):
	max_filtered = scipy.ndimage.maximum_filter1d(power,size=max_window)
	min_filtered = scipy.ndimage.minimum_filter1d(power,size=min_window)
	maxima = numpy.logical_and(max_filtered==power, max_filtered-min_filtered>height)
	maxima_indices = numpy.nonzero(maxima)[0]
	return maxima_indices

class Analyze(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)

		fig = matplotlib.figure.Figure(figsize=(5,4))
		self.ax = fig.add_subplot(111)

		vbox = gtk.VBox()
		self.add(vbox)

		self.figure = mpl_backend.FigureCanvasGTK(fig)
		self.figure.set_size_request(400,300)
		self.navbar = mpl_backend.NavigationToolbar2Cairo(self.figure, self)
		vbox.pack_start(self.figure)
		vbox.pack_start(self.navbar, False, False)

	def plot_spectrum(self, frq, power):
		self.ax.plot(frq, power, color="g")
		self.ax.plot(frq, numpy.log(power), color="g")

		for semitone in xrange(-29,50):
			f = 440. * ( 2.**(1./12.) )**semitone
			self.ax.axvline(f, color="r")

		for maximum in find_peaks(frq, power, 3, 3, .5):
			self.ax.axvline(frq[maximum], color="k")
