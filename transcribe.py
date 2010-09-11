#!/usr/bin/env python

import gtk, gobject, goocanvas
gobject.threads_init()

import sys

import Project, Visualizer, Analyze, Timeline, Pipeline
import numpy

class Transcribe:
	def __init__(self):
		self.visualizers = []
		self.autoupdate = False
		self.project = None

		# create gui
		self.builder = gtk.Builder()
		self.builder.add_from_file("gui.glade")
		self.builder.get_object("rate").set_value(1.0)
		self.builder.get_object("cutoff_button").set_active(False)
		self.builder.get_object("cutoff").set_value(1.0)
		self.builder.get_object("cutoff").set_sensitive(False)
		self.builder.get_object("delta_t").set_value(0.05)
		self.builder.get_object("decay").set_value(0.2)
		self.builder.get_object("beat_separation").set_value(0.01)
		self.builder.connect_signals(self)

		agr = gtk.AccelGroup()
		self.builder.get_object("mainwindow").add_accel_group(agr)
		key, mod = gtk.accelerator_parse("<Control>t")
		self.builder.get_object("tap").add_accelerator("clicked", agr, key, mod, gtk.ACCEL_VISIBLE)

		# create menu items for SingleString visualizers
		singlestring = self.builder.get_object("singlestring")
		singlestrings = gtk.Menu()

		for string, semitone in Visualizer.standard_tuning.iteritems():
			stringitem = gtk.MenuItem(str(string))
			stringitem.connect("activate", self.open_singlestring, string, semitone)
			singlestrings.append(stringitem)

		singlestring.set_submenu(singlestrings)
		singlestrings.show_all()

		singlestring = self.builder.get_object("singlestringarea")
		singlestrings = gtk.Menu()

		for string, semitone in Visualizer.standard_tuning.iteritems():
			stringitem = gtk.MenuItem(str(string))
			stringitem.connect("activate", self.open_singlestringarea, string, semitone)
			singlestrings.append(stringitem)

		singlestring.set_submenu(singlestrings)
		singlestrings.show_all()

		# update position marker
		gobject.timeout_add(100, self.update_position_marker)

		# open project
		if len(sys.argv)>1:
			project = Project.load(sys.argv[1])
			self.set_project(project)

	def run(self):
		self.builder.get_object("mainwindow").show_all()

		gtk.main()

	def set_project(self, project):
		if self.project: return False

		project.spectrumlistener.connect("magnitudes_available", self.on_magnitudes)
		project.timeline.connect("notify::mode", self.mode_changed)
		project.timeline.props.mode = Project.Timeline.MODE_DEFAULT
		self.builder.get_object("position").set_adjustment(project.timeline.ruler.marker_start)
		self.builder.get_object("duration").set_adjustment(project.timeline.ruler.marker_duration)
		self.builder.get_object("timelinecontainer").add(project.timeline)

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

		project = Project.Project(audiofile)
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

		project = Project.load(filename)
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
		if not self.close_project(): return True

		gtk.main_quit()

	# glade callbacks - windows menu
	def open_fretboard(self,widget):
		fretboard = Visualizer.FretboardVis()
		Visualizer.VisualizerWindow(self.visualizers, "Fretboard", fretboard)

	def open_total(self,widget):
#		fretboard = Visualizer.TotalFretboard()
		fretboard = Visualizer.Fretboard(method="cumulate")
		Visualizer.VisualizerWindow(self.visualizers, "TotalFretboard", fretboard)

	def open_singlestring(self,widget,string,semitone):
		singlestring = Visualizer.SingleString(tune=semitone)
		Visualizer.VisualizerWindow(self.visualizers, "SingleString %d (%d)" % (string, semitone), singlestring)

	def open_singlestringarea(self,widget,string,semitone):
		fretboard = Visualizer.SingleString(tune=semitone, method="cumulate")
#		fretboard = Visualizer.SingleStringArea(tune=semitone)
		Visualizer.VisualizerWindow(self.visualizers, "SingleStringArea %d (%d)" % (string, semitone), fretboard)

	def open_plot(self, widget):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return

		start,duration = marker

		frq, power = self.project.appsinkpipeline.get_spectrum(start,start+duration)

		w = Analyze.Analyze()
		w.show_all()
		w.plot_spectrum(frq, power)

	def compare(self,widget):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return

		start,duration = marker

		frq, power = self.project.appsinkpipeline.get_spectrum(start,start+duration)

		if self.builder.get_object("cutoff_button").get_active():
			max_magnitude = self.builder.get_object("cutoff").get_value()
		else:
			max_magnitude = None

		spectrum = Visualizer.SpectrumData(frq, power=power, max_magnitude=max_magnitude)

		c = goocanvas.Canvas()
		c.set_property("has-tooltip",True)
		f = Visualizer.Fretboard2(spectrum=spectrum,parent=c.get_root_item())
		width = f.get_width()
		height = f.get_height()
		c.set_bounds(0,0,width,height)
		c.set_size_request(width,height)
		w = gtk.Window()
		w.set_title("Compare")
		w.add(c)
		w.show_all()

#		w = Visualizer.CompareWindow()

	# glade callbacks - toolbar
	def set_default_mode(self,widget):
		if not self.project: return
		if not widget.get_active(): return

		# set mode without triggering notify event because radiobutton is up to date
		self.project.timeline.mode=Project.Timeline.MODE_DEFAULT

	def insert_annotation(self,widget):
		if not self.project: return
		if not widget.get_active(): return

		# set mode without triggering notify event because radiobutton is up to date
		self.project.timeline.mode=Project.Timeline.MODE_ANNOTATE

	def delete_item(self,widget):
		if not self.project: return
		if not widget.get_active(): return

		# set mode without triggering notify event because radiobutton is up to date
		self.project.timeline.mode=Project.Timeline.MODE_DELETE

	def insert_tab_marker(self,widget):
		if not self.project: return

		playback_marker = self.project.timeline.ruler.get_playback_marker()
		if not playback_marker: return

		start,duration = playback_marker

		dialog = gtk.Dialog(title="Fret", flags=gtk.DIALOG_DESTROY_WITH_PARENT|gtk.DIALOG_MODAL, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

		combobox = gtk.combo_box_new_text()
		for i in xrange(len(self.project.timeline.tabulature.strings)):
			string = self.project.timeline.tabulature.strings[i]
			combobox.append_text(str(i+1)+" ("+str(string.tuning)+")")
		combobox.set_active(0)

		dialog.vbox.add(combobox)
		entry = gtk.Entry()
		dialog.vbox.add(entry)
		dialog.show_all()
		if dialog.run()==gtk.RESPONSE_ACCEPT:
			try:
				string = self.project.timeline.tabulature.strings[combobox.get_active()]
				fret=int(entry.get_text())
			except:
				return
			finally:
				dialog.destroy()
		else:
			dialog.destroy()
			return

		marker = Project.Timeline.TabMarker(
			string,
			start,
			duration,
			fret
		)
		string.markers.append(marker)
		self.project.touch()

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

	def tap(self,widget):
		if not self.project: return

		self.project.timeline.rhythm.add_tap()

	def clear_taps(self,widget):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return

		start, duration = marker
		self.project.timeline.rhythm.clear_taps(start,duration)

	def pause(self, widget):
		if not self.project: return

		if widget.get_active():
			self.project.pipeline.pause()
		else:
			rate = self.builder.get_object("rate").get_value()
			self.project.pipeline.play()

	def play(self, *args):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return

		start, duration = marker
		rate = self.builder.get_object("rate").get_value()

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

		if self.builder.get_object("cutoff_button").get_active():
			max_magnitude = self.builder.get_object("cutoff").get_value()
		else:
			max_magnitude = None

		spectrum = Visualizer.SpectrumData(frq, power=power, max_magnitude=max_magnitude)

		for viswindow in self.visualizers:
			viswindow.visualizer.set_spectrum(spectrum)

	def playback_marker_previous(self, *args):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return

		start,duration = marker
		start -= duration
		start = max(0,start)

		self.project.timeline.ruler.set_playback_marker(start, duration)
		self.update_playback_marker_spinbuttons()

	def playback_marker_next(self, *args):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return

		start,duration = marker
		start += duration

		self.project.timeline.ruler.set_playback_marker(start, duration)
		self.update_playback_marker_spinbuttons()

	def top_align(self,*args):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return
		
		start,duration = marker

		taps = []
		for tap in self.project.timeline.rhythm.taps:
			time = tap.get_time()
			if start<time and time<start+duration:
				taps.append(time)

		try: first = min(taps)
		except ValueError: return

		self.project.timeline.ruler.set_playback_marker(first, start+duration-first)

	def bottom_align(self,*args):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return
		
		start,duration = marker

		taps = []
		for tap in self.project.timeline.rhythm.taps:
			time = tap.get_time()
			if start<time and time<start+duration:
				taps.append(time)

		try: last = max(taps)
		except ValueError: return

		self.project.timeline.ruler.set_playback_marker(start, last-start)

	def divide(self,*args):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return
		
		start,duration = marker
		self.project.timeline.ruler.set_playback_marker(start, 0.5*duration)
		
	def double(self,*args):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return
		
		start,duration = marker
		self.project.timeline.ruler.set_playback_marker(start, 2.0*duration)

	def find_beats(self,*args):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return
		
		start,duration = marker
		power = numpy.array(self.project.appsinkpipeline.get_data(start,start+duration)) ** 2.0
		rate = self.project.appsinkpipeline.caps[0]["rate"]

		delta_t = self.builder.get_object("delta_t").get_value()
		decay = self.builder.get_object("decay").get_value()
		separation = self.builder.get_object("beat_separation").get_value()
#		delta_t = 0.01
#		decay = 0.5 # time needed to get to 1/e
		# k*decay = 1
		# power(t) = exp(-1)*power(t-decay)
		# power(t) = exp(-k*decay)*power(t-decay)
		# power(t) = exp(-k*delta_t)*power(t-delta_t)
		decay_per_chunk = numpy.exp(-delta_t/decay)
		samples = int(rate*delta_t)

		limit = numpy.average(power[0:samples])

		for i in xrange(1,int(len(power)/samples)):
			limit *= decay_per_chunk
			avg_power = numpy.average(power[samples*i : samples*(i+1)])

			if avg_power>=limit*(1+separation):
				time = delta_t*i
				t=self.project.timeline.rhythm.add_tap(start+time, round((avg_power-limit)/separation,2))
				t.props.x += 30
			if avg_power>=limit:
				limit=avg_power

	def test(self,widget):
		if not self.project: return

		marker = self.project.timeline.ruler.get_playback_marker()
		if not marker: return
		
		start,duration = marker
		power = numpy.array(self.project.appsinkpipeline.get_data(start,start+duration)) ** 2.0
		rate = self.project.appsinkpipeline.caps[0]["rate"]

		delta_t = self.builder.get_object("delta_t").get_value()
		decay = self.builder.get_object("decay").get_value()
		separation = self.builder.get_object("beat_separation").get_value()
#		delta_t = 0.01
#		decay = 0.5 # time needed to get to 1/e
		# k*decay = 1
		# power(t) = exp(-1)*power(t-decay)
		# power(t) = exp(-k*decay)*power(t-decay)
		# power(t) = exp(-k*delta_t)*power(t-delta_t)
		decay_per_chunk = numpy.exp(-delta_t/decay)
		samples = int(rate*delta_t)

		limit = numpy.average(power[0:samples])
		t = []
		level = []
		lim = []
		tp1 = []

		w = Analyze.Analyze()

		for i in xrange(1,int(len(power)/samples)):
			limit *= decay_per_chunk
			chunk = power[samples*i : samples*(i+1)]
			avg_power = numpy.average(chunk)
			power_spectrum = Pipeline.windowed_fft(chunk)
			bands = len(power_spectrum)
			frqs = 0.5 * ( numpy.arange(bands) + 0.5 ) * rate / bands
			time = delta_t*i+start
			min_frq_idx = numpy.min(numpy.nonzero(frqs>80.))
			max_frq_idx = numpy.max(numpy.nonzero(frqs<1000.))
			min_frq = frqs[min_frq_idx]
			max_frq = frqs[max_frq_idx]
			print frqs[0], min_frq, max_frq, frqs[-1]
			total_power1 = numpy.trapz(power_spectrum[min_frq_idx:max_frq_idx], frqs[min_frq_idx:max_frq_idx])
			tp1.append(total_power1)

#			if avg_power>=limit*(1.0+separation):
#			if avg_power>=limit+separation:
#				w.add_line(time, color="g")
			if avg_power>=limit:
				limit=avg_power

			t.append(time)
			level.append(avg_power)
			lim.append(limit)

		w.show_all()
		w.simple_plot(numpy.array(t), numpy.array(level), color="r")
		w.simple_plot(numpy.array(t), numpy.array(tp1), color="b")
		w.simple_plot(numpy.array(t), numpy.array(lim), color="g")

		# markers
		for tap in self.project.timeline.rhythm.taps:
			time = tap.get_time()
			if not start<time and time<start+duration: continue

			if type(tap.weight)==float: pass
			else:
				w.add_line(time, color="r")

	# glade callbacks - radioboxes
	def playback_marker_radioboxes_changed(self,widget):
		if not self.project: return

		start = self.builder.get_object("position").get_value()
		duration = self.builder.get_object("duration").get_value()
		self.project.timeline.ruler.set_playback_marker(start,duration)

	def cutoff_toggle(self,widget):
		self.builder.get_object("cutoff").set_sensitive(widget.get_active())

	# update spinbuttons when playback marker is moved
	def update_playback_marker_spinbuttons(self,*args):
		if not self.project: return

		start,duration = self.project.timeline.ruler.get_playback_marker()
		self.builder.get_object("position").set_value(start)
		self.builder.get_object("duration").set_value(duration)

	# update radiobuttons when mode is changed by timeline
	def mode_changed(self,timeline,pspec):
		if timeline.props.mode==Timeline.MODE_DEFAULT:
			self.builder.get_object("mode_default").set_active(True)
		elif timeline.props.mode==Timeline.MODE_ANNOTATE:
			self.builder.get_object("mode_annotate").set_active(True)
		elif timeline.props.mode==Timeline.MODE_DELETE:
			self.builder.get_object("mode_delete").set_active(True)

	# spectrumlistener callback
	def on_magnitudes(self, spectrumlistener, bands, rate, threshold, magnitudes):
		if not self.autoupdate or not self.project: return

		magnitude_max = 0.

		frequencies = 0.5 * ( numpy.arange(bands) + 0.5 ) * rate / bands
		magnitudes = numpy.array(magnitudes)

		if self.builder.get_object("cutoff_button").get_active():
			max_magnitude = self.builder.get_object("cutoff").get_value()
		else:
			max_magnitude = None
				
		spectrum = Visualizer.SpectrumData(frequencies, magnitude=magnitudes, min_magnitude=threshold, max_magnitude=max_magnitude)

		for viswindow in self.visualizers:
			viswindow.visualizer.set_spectrum(spectrum)

	# position marker callback
	def update_position_marker(self,*args):
		if self.project:
			pos = self.project.pipeline.get_position()
			self.project.timeline.set_position(pos)

		return True

if __name__=="__main__":
	transcribe = Transcribe()
	transcribe.run()
