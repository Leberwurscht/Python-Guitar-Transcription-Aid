#!/usr/bin/env python

import gtk
import gtk.glade

import Visualizer
import Pipeline
import Timeline

class Transcribe:
	def __init__(self):
		# create gui
		self.glade = gtk.glade.XML("gui.glade", "mainwindow")

		# create pipeline
		self.pipeline = Pipeline.Pipeline("/home/maxi/Musik/ogg/jamendo_track_401871.ogg")

		# create timeline
		self.timeline = Timeline.Timeline(self.pipeline.duration)
		self.glade.get_widget("scrolledwindow").add(self.timeline)
		self.timeline.show_all()

		# create fretboard
		self.fretboard = Visualizer.Fretboard(self.pipeline.get_bus())
		self.glade.get_widget("vbox").pack_start(self.fretboard,expand=False)
		self.fretboard.show_all()

		# connect signals
		self.glade.signal_autoconnect({
			'gtk_main_quit':gtk.main_quit,
			'insert_text':self.insert_text,
			'playpause':self.playpause,
			'stop':self.stop,
		})

	def run(self):
		self.glade.get_widget("mainwindow").show_all()
		gtk.main()

	# callbacks

	def insert_text(self,widget):
		self.timeline.mode="insert_text"

	def playpause(self,widget):
		if widget.get_active():
			self.pipeline.play()
			# play from current position if paused
			# play from marker start if stopped
		else:
			self.pipeline.pause()
			
#		marker = self.timeline.get_marker()
#
#		if marker:
#			self.pipeline.play(start=marker[0],stop=marker[0]+marker[1])

	def stop(self,widget):
		# set 
		self.pipeline.stop()
		self.glade.get_widget("playpause").set_active(False)


if __name__=="__main__":
	transcribe = Transcribe()
	transcribe.run()
