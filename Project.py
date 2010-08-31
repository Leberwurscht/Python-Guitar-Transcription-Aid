#!/usr/bin/env python

### usage
#
# a = Project("test.proj","audiofile")
# a.markers.append(Marker(0,3,"bla"))
# a.save()
#
# a = load_project(filename)
# print a.markers[0]
#

import json
import Pipeline, Timeline, spectrumvisualizer

class InvalidFileFormat(Exception): pass

FILENAME_EXTENSION = "tr"
FILE_TYPE = "http://www.hoegners.de/Maxi/transcribe"
FILE_FORMAT_VERSION = "0"

def load(filename):
	f = open(filename)
	try: json_object = json.load(f)
	except:	raise InvalidFileFormat, "Need JSON file!"
	f.close()

	if not "file_type" in json_object or not json_object["file_type"]==FILE_TYPE:
		raise InvalidFileFormat, "Invalid JSON file."

	if not json_object["format_version"]==FILE_FORMAT_VERSION:
		raise InvalidFileFormat, "Got file format version %s, need version %s" % (json_object["format_version"], FILE_FORMAT_VERSION)

	project = Project(json_object["audiofile"], filename)

	for json_marker_object in json_object["markers"]:
		marker = Marker(json_marker_object["start"],json_marker_object["duration"],json_marker_object["name"],)
		project.markers.append(marker)

	return project

class Project:
	def __init__(self, audiofile, filename=None):
		self.filename = filename
		self.audiofile = audiofile
		self.markers = []
		self.touched = True

		self.appsinkpipeline = Pipeline.AppSinkPipeline(self.audiofile)
		self.pipeline = Pipeline.Pipeline(self.audiofile)
		self.timeline = Timeline.Timeline(self.pipeline.duration)
		self.timeline.show_all()
		self.spectrumlistener = spectrumvisualizer.base(self.pipeline.spectrum, self.pipeline)

	def save(self):
		f = open(self.filename, "w")

		json_object = {}
		json_object["audiofile"] = self.audiofile
		json_object["markers"] = []
		json_object["format_version"] = "0"
		json_object["file_type"] = "http://www.hoegners.de/Maxi/transcribe"

		for marker in self.markers:
			json_object["markers"].append({"start":marker.start, "duration":marker.duration, "name":marker.name})

		a = json.dump(json_object, f)

		f.close()
		self.touched = False

	def close(self):
		self.appsinkpipeline.set_state(Pipeline.gst.STATE_NULL)
		self.pipeline.set_state(Pipeline.gst.STATE_NULL)
		self.timeline.destroy()
		self.appsinkpipeline.get_state()
		self.pipeline.get_state()
		del self.appsinkpipeline
		del self.pipeline
		del self.timeline
		del self.spectrumlistener
