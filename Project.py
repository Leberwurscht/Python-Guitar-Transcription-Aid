#!/usr/bin/env python

import json
import Pipeline, Timeline, spectrumvisualizer

class InvalidFileFormat(Exception): pass

FILENAME_EXTENSION = "tr"
FILE_TYPE = "http://www.hoegners.de/Maxi/transcribe"
FILE_FORMAT_VERSION = "0.1"

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
#		raise NotImplementedError
#		marker = Timeline.Marker(json_marker_object["start"],json_marker_object["duration"],json_marker_object["name"],)
		marker = Timeline.Marker(
			project.timeline,
			json_marker_object["start"],
			json_marker_object["duration"],
			json_marker_object["text"],
			x = json_marker_object["x"]
		)
		project.timeline.markers.append(marker)

	for json_annotation_object in json_object["annotations"]:
		marker = Timeline.Annotation(
			project.timeline,
			x = json_annotation_object["x"],
			time = json_annotation_object["time"],
			text = json_annotation_object["text"]
		)
		project.timeline.annotations.append(marker)

	project.touched = False

	return project

class Project:
	def __init__(self, audiofile, filename=None):
		self.filename = filename
		self.audiofile = audiofile
		self.touched = True

		self.appsinkpipeline = Pipeline.AppSinkPipeline(self.audiofile)
		self.pipeline = Pipeline.Pipeline(self.audiofile)
		self.timeline = Timeline.Timeline(self)
		self.timeline.show_all()
		self.spectrumlistener = spectrumvisualizer.base(self.pipeline.spectrum, self.pipeline)

	def save(self):
		f = open(self.filename, "w")

		json_object = {}
		json_object["audiofile"] = self.audiofile
		json_object["markers"] = []
		json_object["annotations"] = []
		json_object["format_version"] = FILE_FORMAT_VERSION
		json_object["file_type"] = FILE_TYPE

		for marker in self.timeline.markers:
#			print NotImplementedError
			json_object["markers"].append({"start":marker.get_start(), "duration":marker.get_duration(), "text":marker.get_text(), "x":marker.props.x})

		for annotation in self.timeline.annotations:
			json_object["annotations"].append({"x":annotation.props.x, "time":annotation.get_time(), "text":annotation.props.text})

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
