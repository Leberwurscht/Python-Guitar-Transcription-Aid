#!/usr/bin/env python

import gobject
gobject.threads_init()

import gst
import Pipeline

#p = Pipeline.AppSrcPipeline()
#p.sw = Pipeline.Sinewave(440)
p = gst.parse_launch("sinesrc ! gconfaudiosink")

p.set_state(gst.STATE_PLAYING)
gobject.MainLoop().run()
