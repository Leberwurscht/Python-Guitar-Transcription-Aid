#!/usr/bin/env python

import gst

class Base(gst.Bin):
	def __init__(self):
		gst.Bin.__init__(self):
			
