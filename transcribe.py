#!/usr/bin/env python

import gtk
import gtk.glade

import Visualizer
import Pipeline
import Timeline

class Transcribe:
	def __init__(self):
		# create gui
		glade = gtk.glade.XML("gui.glade", "mainwindow")
		glade.get_widget("mainwindow").show_all()
		vbox=glade.get_widget("vbox")

		# create pipeline
		self.pipeline = Pipeline.Pipeline("/home/maxi/Musik/ogg/jamendo_track_401871.ogg")

		# create timeline
		self.timeline = Timeline.Timeline(self.pipeline.duration)
		glade.get_widget("scrolledwindow").add(self.timeline)
		self.timeline.show_all()

		# create fretboard
		self.fretboard = Visualizer.Fretboard(self.pipeline.get_bus())
		vbox.pack_start(self.fretboard,expand=False)
		self.fretboard.show_all()

		# connect signals
		glade.signal_autoconnect({
			'gtk_main_quit':gtk.main_quit,
			'insert_text':self.insert_text,
			'play':self.play,
			'stop':self.stop,
			'set_tempo':self.set_tempo
		})

	def insert_text(self,widget):
		self.timeline.mode="insert_text"

	def play(self,widget):
		marker = self.timeline.get_marker()

		if marker:
			self.pipeline.play(start=marker[0],stop=marker[0]+marker[1])

	def stop(self,widget):
		self.pipeline.stop()

	def set_tempo(self,widget):
		self.pipeline.set_rate(widget.get_value()/100.)

if __name__=="__main__":
	app = Transcribe()

	gtk.main()
