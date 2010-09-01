#!/usr/bin/env python

import gtk, gobject
gobject.threads_init()

import sys

import Project, Visualizer, Analyze
import numpy

class Transcribe:
	def __init__(self):
		self.visualizers = []
		self.autoupdate = False
		self.project = None

		# create gui
		self.builder = gtk.Builder()
		self.builder.add_from_file("gui.glade")
		self.builder.get_object("rate").set_value(100)
		self.builder.connect_signals(self)

		# create menu items for SingleString visualizers
		singlestring = self.builder.get_object("singlestring")
		singlestrings = gtk.Menu()

		for string, semitone in Visualizer.standard_tuning.iteritems():
			stringitem = gtk.MenuItem(str(string))
			stringitem.connect("activate", self.open_singlestring, string, semitone)
			singlestrings.append(stringitem)

		singlestring.set_submenu(singlestrings)
		singlestrings.show_all()

		# update position marker
		gobject.timeout_add(100, self.update_position_marker)

		# open project
		if len(sys.argv)>1:
			project = Project.load(self, sys.argv[1])
			self.set_project(project)

	def run(self):
		self.builder.get_object("mainwindow").show_all()
		gtk.main()

	def set_project(self, project):
		if self.project: return False

		project.spectrumlistener.connect("magnitudes_available", self.on_magnitudes)
#		project.timeline.ruler.set_playback_marker_changed_cb(self.update_playback_marker)
		self.builder.get_object("timelinecontainer").add(project.timeline)
#		self.builder.get_object("timelinecontainer").pack_start(project.timeline, False, False)

		self.project = project
		return True

	# glade callbacks - file menu
	def new_project(self,*args):
		if not self.close_project(): return

		audiofilechooser = gtk.FileChooserDialog(title="Select audio file",action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		audiofilechooser.run()
		audiofile = audiofilechooser.get_filename()
		audiofilechooser.destroy()

		if not audiofile: return

		project = Project.Project(self, audiofile)
		self.set_project(project)

	def open_project(self,widget):
		if not self.close_project(): return

		chooser = gtk.FileChooserDialog(title="Open File",action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		f = gtk.FileFilter()
		f.set_name("All Files")
		f.add_pattern("*")
		chooser.add_filter(f)
		f = gtk.FileFilter()
		f.set_name("Project Files")
		f.add_pattern("*.%s" % Project.FILENAME_EXTENSION)
		chooser.add_filter(f)
		chooser.set_filter(f)
		chooser.run()
		filename = chooser.get_filename()
		chooser.destroy()

		if not filename: return

		project = Project.load(self, filename)
		self.set_project(project)

	def save_project_as(self,*args):
		self.save_project(self,override_filename=True)

	def save_project(self,*args,**kwargs):
		if not self.project: return True

		override_filename=False
		if "override_filename" in kwargs: override_filename=kwargs["override_filename"]

		if not self.project.filename or override_filename:
			chooser = gtk.FileChooserDialog(title="Save File As",action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
			f = gtk.FileFilter()
			f.set_name("All Files")
			f.add_pattern("*")
			chooser.add_filter(f)
			f = gtk.FileFilter()
			f.set_name("Project Files")
			f.add_pattern("*.%s" % Project.FILENAME_EXTENSION)
			chooser.add_filter(f)
			chooser.set_filter(f)
			chooser.run()
			self.project.filename = chooser.get_filename()
			chooser.destroy()

		if not self.project.filename: return False

		self.project.save()
		return True

	def close_project(self,*args):
		self.stop()

		if not self.project: return True
		if not self.project.touched:
			self.project.close()
			self.project = None
			return True

		d = gtk.Dialog("Unsaved changes", self.builder.get_object("mainwindow"), gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
				(gtk.STOCK_YES, gtk.RESPONSE_YES, gtk.STOCK_NO, gtk.RESPONSE_NO, gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
		d.vbox.add(gtk.Label("Save project?"))
		d.show_all()
		r = d.run()
		d.destroy()

		if r==gtk.RESPONSE_YES:
			if not self.save_project(): return False
			self.project.close()
			self.project = None
			return True
		elif r==gtk.RESPONSE_NO:
			self.project.close()
			self.project = None
			return True
		else:
			return False

	def quit(self, *args):
		if not self.close_project(): return False

		gtk.main_quit()

	# glade callbacks - analyze menu
	def open_fretboard(self,widget):
		fretboard = Visualizer.Fretboard()
		Visualizer.VisualizerWindow(self.visualizers, "Fretboard", fretboard)

	def open_singlestring(self,widget,string,semitone):
		singlestring = Visualizer.SingleString(tune=semitone)
		Visualizer.VisualizerWindow(self.visualizers, "SingleString %d (%d)" % (string, semitone), singlestring)

	def open_plot(self, widget):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return

		start,duration = marker

		frq, power = self.project.appsinkpipeline.get_spectrum(start,start+duration)

		w = Analyze.Analyze()
		w.show_all()
		w.plot_spectrum(frq, power)

	# glade callbacks - toolbar
	def set_default_mode(self,widget):
		if not widget.get_active(): return

		self.project.timeline.mode=Project.Timeline.MODE_DEFAULT

	def insert_annotation(self,widget):
		if not self.project: return
		if not widget.get_active(): return

		self.project.timeline.mode=Project.Timeline.MODE_ANNOTATE

	def delete_item(self,widget):
		if not self.project: return
		if not widget.get_active(): return

		self.project.timeline.mode=Project.Timeline.MODE_DELETE

	def insert_marker(self,widget):
		if not self.project: return

		playback_marker = self.project.timeline.ruler.get_playback_marker()
		if not playback_marker: return

		start,duration = playback_marker

		dialog = gtk.Dialog(title="Text", flags=gtk.DIALOG_DESTROY_WITH_PARENT|gtk.DIALOG_MODAL, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
		entry = gtk.Entry()
		dialog.vbox.add(entry)
		dialog.show_all()
		if dialog.run()==gtk.RESPONSE_ACCEPT:
			text=entry.get_text()	
			dialog.destroy()
		else:
			dialog.destroy()
			return

		marker = Project.Timeline.Marker(
			self.project.timeline,
			start,
			duration,
			text
		)
		self.project.timeline.markers.append(marker)
		self.project.touch()

	def pause(self, widget):
		if not self.project: return

		if widget.get_active():
			self.project.pipeline.pause()
		else:
			rate = self.builder.get_object("rate").get_value()/100.
			self.project.pipeline.play()

	def play(self, *args):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return

		start, duration = marker
		rate = self.builder.get_object("rate").get_value()/100.

		self.project.pipeline.play(rate,start=start,stop=start+duration)

		self.builder.get_object("pause").set_active(False)
		self.builder.get_object("stop").set_sensitive(True)

	def stop(self, *args):
		if not self.project: return

		self.project.pipeline.pause()
		self.builder.get_object("pause").set_active(False)
		self.builder.get_object("stop").set_sensitive(False)

	def toggle_autoupdate(self,widget):
		if widget.get_active(): self.autoupdate = True
		else: self.autoupdate = False		

	def update_visualizers(self,widget):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return

		start,duration = marker

		frq, power = self.project.appsinkpipeline.get_spectrum(start,start+duration)

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

	def playback_marker_previous(self, *args):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return

		start,duration = marker
		start -= duration
		start = max(0,start)

		self.project.timeline.ruler.set_playback_marker(start, duration)
		self.update_playback_marker_spinbuttons()
#		self.update_playback_marker()

	def playback_marker_next(self, *args):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return

		start,duration = marker
		start += duration

		self.project.timeline.ruler.set_playback_marker(start, duration)
		self.update_playback_marker_spinbuttons()
#		self.update_playback_marker()

	# glade callbacks - radioboxes
	def playback_marker_radioboxes_changed(self,widget):
		if not self.project: return

		start = self.builder.get_object("position").get_value()
		duration = self.builder.get_object("duration").get_value()
		self.project.timeline.ruler.set_playback_marker(start,duration)

	# playback marker spinbuttons are updated by Timeline
	def update_playback_marker_spinbuttons(self):
		if not self.project: return

		start,duration = self.project.timeline.ruler.get_playback_marker()
		self.builder.get_object("position").set_value(start)
		self.builder.get_object("duration").set_value(duration)

	# spectrumlistener callback
	def on_magnitudes(self, spectrumlistener, bands, rate, threshold, magnitudes):
		if not self.autoupdate or not self.project: return

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

	# position marker callback
	def update_position_marker(self,*args):
		if self.project:
			pos = self.project.pipeline.get_position()
			self.project.timeline.set_position(pos)

		return True

if __name__=="__main__":
	transcribe = Transcribe()
	transcribe.run()
