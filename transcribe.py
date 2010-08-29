#!/usr/bin/env python

import gtk, gobject
gobject.threads_init()

import Visualizer
import Pipeline
import Timeline
import sys

#import numpy,array,struct
import numpy
import Analyze

class Transcribe:
	def __init__(self):
		# create gui
		self.builder = gtk.Builder()
		self.builder.add_from_file("gui.glade")
		self.builder.get_object("rate").set_value(100)

		# create pipelines
		self.appsinkpipeline = Pipeline.AppSinkPipeline(sys.argv[1])
#		self.pipeline = Pipeline.Pipeline("/home/maxi/Musik/Audio/jamendo_track_401871.ogg")
		self.pipeline = Pipeline.Pipeline(sys.argv[1])
		bus = self.pipeline.get_bus()
		bus.add_signal_watch()
#		bus.connect()

		# create timeline
		self.timeline = Timeline.Timeline(self.pipeline.duration)
		self.builder.get_object("scrolledwindow").add(self.timeline)
		self.timeline.show_all()

		# create fretboard
#		self.fretboard = Visualizer.SingleString(self.pipeline, tune=-5, capo=2)
		self.fretboard = Visualizer.Fretboard(self.pipeline, capo=2)
#		self.fretboard.connect_to_bus(bus)
		self.builder.get_object("vbox").pack_start(self.fretboard,expand=False)
		self.fretboard.show_all()

		# connect signals
		self.builder.connect_signals(self)

		# update position marker
		gobject.timeout_add(100, self.update_position_marker)

	def update_position_marker(self,*args):
		pos = self.pipeline.get_position()
		self.timeline.set_position(pos)
		return True

	def run(self):
		self.builder.get_object("mainwindow").show_all()
		gtk.main()

	# callbacks

	def quit(self, *args):
		gtk.main_quit()

	def insert_text(self,widget):
		self.timeline.mode="insert_text"

	def play(self,widget):
		marker = self.timeline.get_marker()
		rate = self.builder.get_object("rate").get_value()/100.

		if marker:
			self.pipeline.play(rate,start=marker[0],stop=marker[0]+marker[1])

		self.builder.get_object("pause").set_active(False)
		self.builder.get_object("stop").set_sensitive(True)

	def pause(self, widget):
		if widget.get_active():
			self.pipeline.pause()
		else:
			rate = self.builder.get_object("rate").get_value()/100.
			self.pipeline.play()

	def analyze(self, widget):
		marker = self.timeline.get_marker()

		if marker:
			data = self.appsinkpipeline.get_raw(marker[0],marker[0]+marker[1])
			rate = self.appsinkpipeline.caps[0]["rate"]
#			a = str(buf)
#			a = array.array("f", a)
#			print len(a)

			frq, power = Analyze.get_power(data[:8192], rate)
			print "LEN",len(power)

			self.fretboard.frequencies = frq
			self.fretboard.semitones = 12. * numpy.log2(frq/440.)
			self.fretboard.magnitudes = 10.*numpy.log10(power / 8192.**2)
			self.fretboard.magnitude_max = 5.
			self.fretboard.magnitude_min = -5.
			self.fretboard.queue_draw()

			w = Analyze.Analyze()
			w.show_all()
			w.plot_spectrum(frq, power)

	def stop(self,widget):
		self.pipeline.pause()
		self.builder.get_object("pause").set_active(False)
		self.builder.get_object("stop").set_sensitive(False)

if __name__=="__main__":
	transcribe = Transcribe()
	transcribe.run()
