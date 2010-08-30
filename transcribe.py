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
import spectrumvisualizer

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
#		self.fretboard = Visualizer.Fretboard(self.pipeline, capo=2)
#		self.fretboard.connect_to_bus(bus)
#		self.builder.get_object("vbox").pack_start(self.fretboard,expand=False)
#		self.fretboard.show_all()

		self.spectrumlistener = spectrumvisualizer.base(self.pipeline.spectrum, self.pipeline)
		self.spectrumlistener.connect("magnitudes_available", self.on_magnitudes)

		self.visualizers = []
		self.autoupdate = False

		singlestring = self.builder.get_object("singlestring")
		singlestrings = gtk.Menu()

		for string, semitone in Visualizer.standard_tuning.iteritems():
			stringitem = gtk.MenuItem(str(string))
			stringitem.connect("activate", self.open_singlestring, string, semitone)
			singlestrings.append(stringitem)

		singlestring.set_submenu(singlestrings)
		singlestrings.show_all()

		# connect signals
		self.builder.connect_signals(self)

		# update position marker
		gobject.timeout_add(100, self.update_position_marker)

	def on_magnitudes(self,visbase,bands,rate,threshold,magnitudes):
		if not self.autoupdate: return

		magnitude_max = 0.

		frequencies = 0.5 * ( numpy.arange(bands) + 0.5 ) * rate / bands
		semitones = 12. * numpy.log2(frequencies/Visualizer.REFERENCE_FREQUENCY)
		magnitudes = numpy.array(magnitudes)

		brightness_slope = - 1.0 / (magnitude_max - threshold)
		brightness_const = 1.0 * magnitude_max / (magnitude_max - threshold)

		brightness = brightness_slope * magnitudes + brightness_const
		brightness = numpy.maximum(0.,numpy.minimum(1.,brightness))

		for viswindow in self.visualizers:
			viswindow.visualizer.semitones = semitones
			viswindow.visualizer.brightness = brightness
			viswindow.visualizer.queue_draw()

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

	def toggle_autoupdate(self,widget):
		if widget.get_active(): self.autoupdate = True
		else: self.autoupdate = False		

	def update_visualizers(self,widget):
		marker = self.timeline.get_marker()

		if marker:
			frq, power = self.appsinkpipeline.get_spectrum(marker[0],marker[0]+marker[1])

			power_max = 500.
			power_min = 0.

			semitones = 12. * numpy.log2(frq/Visualizer.REFERENCE_FREQUENCY)

			brightness_slope = - 1.0 / (power_max - power_min)
			brightness_const = 1.0 * power_max / (power_max - power_min)

			brightness = brightness_slope * power + brightness_const
			brightness = numpy.maximum(0.,numpy.minimum(1.,brightness))

			for viswindow in self.visualizers:
				viswindow.visualizer.semitones = semitones
				viswindow.visualizer.brightness = brightness
				viswindow.visualizer.queue_draw()

	def open_fretboard(self,widget):
		fretboard = Visualizer.Fretboard()
		Visualizer.VisualizerWindow(self.visualizers, "Fretboard", fretboard)

	def open_singlestring(self,widget,string,semitone):
		print string,semitone
		singlestring = Visualizer.SingleString(tune=semitone)
		Visualizer.VisualizerWindow(self.visualizers, "SingleString %d (%d)" % (string, semitone), singlestring)

	def open_plot(self, widget):
		marker = self.timeline.get_marker()

		if marker:
			frq, power = self.appsinkpipeline.get_spectrum(marker[0],marker[0]+marker[1])

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
