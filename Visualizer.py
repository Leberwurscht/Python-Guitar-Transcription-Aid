#!/usr/bin/env python

import gobject

import gst

class Base(gst.Bin):
	def __init__(self,bus,bands=4096):
		gst.Bin.__init__(self)

		self.bands = bands

		self.spectrum = gst.element_factory_make("spectrum")
		self.spectrum.set_property("bands",self.bands)
		self.spectrum.set_property("bands",self.bands)
		self.spectrum.set_property("bands",self.bands)
		self.spectrum.get_pad("sink").connect("notify::caps", self.on_notify_caps)
		self.add(self.spectrum)

		bus.add_signal_watch()
		bus.connect("message", self.on_message)

		self.add_pad(gst.GhostPad('sink', self.spectrum.get_pad('sink')))
		self.add_pad(gst.GhostPad('src', self.spectrum.get_pad('src')))

	def on_notify_caps(self, pad, caps):
		self.rate = pad.get_negotiated_caps()[0]["rate"]
		print "notify", self.spectrum.get_bus()
		return True

	def on_message(self, bus, message):
		if message.structure and message.structure.get_name()=="spectrum":
			print message.src
#			print [message.structure.nth_field_name(i) for i in xrange(message.structure.n_fields())]
			magnitudes = message.structure["magnitude"]
#			magnitudes = array.array('f', message.structure["magnitude"])
#			self.visualize(magnitudes)
#			self.emit("visualize_data", magnitudes)

		return True

	def visualize(self, magnitudes):
		print "test"
		pass

class Base

#gobject.type_register(Base)
#gobject.signal_new("visualize_data",  Base, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (list))

import gtk

class BaseDrawingArea(gtk.DrawingArea):
	def __init__(self, bus):
		self.bus = 
