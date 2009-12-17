#!/usr/bin/env python

import pygst, threading, gobject, time
pygst.require("0.10")
import gst,math

#pipeline=gst.parse_launch('filesrc location=./C/test.wav ! decodebin ! scaletempo ! audioconvert ! flacenc ! matroskamux ! filesink location=out.mat')
#seek_on = pipeline

#pipeline=gst.parse_launch('filesrc location=./C/test.wav ! decodebin ! scaletempo ! audioconvert ! wavenc ! filesink location=out.wav')
#seek_on = pipeline

pipeline=gst.parse_launch('filesrc location=./C/test.wav ! decodebin ! scaletempo ! audioconvert ! vorbisenc name=encoder ! filesink location=out.ogg')
#seek_on = pipeline.get_by_name('encoder')
seek_on = pipeline

#pipeline=gst.parse_launch('filesrc location=./C/test.wav ! decodebin ! scaletempo ! audioconvert ! alsasink')
#seek_on = pipeline

def stop(*args):
	global loop, pipeline
	pipeline.set_state(gst.STATE_NULL)
	pipeline.get_state()
	loop.quit()
	

loop=gobject.MainLoop()
bus = pipeline.get_bus()
bus.add_signal_watch()
bus.connect("message::eos", stop)

gobject.threads_init()
#loop.run()
threading.Thread(target=loop.run).start()

print gst.STATE_CHANGE_ASYNC
print pipeline.set_state(gst.STATE_READY)
print pipeline.get_state()

fmt = gst.FORMAT_TIME
#fmt = gst.FORMAT_BYTES

#pipeline.seek(0.5,fmt,gst.SEEK_FLAG_FLUSH,gst.SEEK_TYPE_SET,0 * 1000000000,gst.SEEK_TYPE_NONE,0)

print gst.STATE_CHANGE_ASYNC
print pipeline.set_state(gst.STATE_PAUSED)
print pipeline.get_state()

print seek_on.seek(0.5,fmt,gst.SEEK_FLAG_FLUSH,gst.SEEK_TYPE_SET,0* gst.SECOND,gst.SEEK_TYPE_NONE,0)

print gst.STATE_CHANGE_ASYNC
print pipeline.set_state(gst.STATE_PLAYING)
print pipeline.get_state()
#for i in xrange(10000): print i

#loop.run()

#pipeline.seek_simple(gst.FORMAT_TIME,gst.SEEK_FLAG_FLUSH,20*1000000000)

#gobject.idle_add(pipeline.seek,0.5,gst.FORMAT_TIME,gst.SEEK_FLAG_FLUSH,gst.SEEK_TYPE_SET,50 * 1000000000,gst.SEEK_TYPE_NONE,0)
#pipeline.send_event(gst.event_new_seek(0.5,gst.FORMAT_TIME,gst.SEEK_FLAG_FLUSH,gst.SEEK_TYPE_SET,20.,gst.SEEK_TYPE_NONE,0))

