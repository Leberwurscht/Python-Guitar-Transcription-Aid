#!/usr/bin/env python

import sys, os, thread, time
import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
import gst

pipeline=gst.parse_launch('filesrc name=file-source ! decodebin ! scaletempo ! audioconvert ! autoaudiosink')

pipeline.get_by_name("file-source").set_property("location", sys.argv[1])
pipeline.set_state(gst.STATE_PLAYING)
time.sleep(5)
pipeline.seek(0.5,gst.FORMAT_TIME,gst.SEEK_FLAG_FLUSH,gst.SEEK_TYPE_SET,0 * 1000000000,gst.SEEK_TYPE_NONE,0)
		
gtk.main()
