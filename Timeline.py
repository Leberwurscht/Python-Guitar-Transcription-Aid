#!/usr/bin/env python

import gobject
import gtk
import goocanvas

# click modes
MODES_NUM = 3
MODE_DEFAULT, MODE_ANNOTATE, MODE_DELETE = xrange(MODES_NUM)

class TimelineItem(goocanvas.Group):
	def __init__(self, timeline, *args, **kwargs):
		if "allow_drag_x" in kwargs:
			self.allow_drag_x = kwargs["allow_drag_x"]
			del kwargs["allow_drag_x"]
		else:
			self.allow_drag_x = True

		if "allow_drag_y" in kwargs:
			self.allow_drag_y = kwargs["allow_drag_y"]
			del kwargs["allow_drag_y"]
		else:
			self.allow_drag_y = True

		if not "parent" in kwargs:
			kwargs["parent"] = timeline.space

		if "time" in kwargs:
			kwargs["y"] = timeline.get_pts(kwargs["time"])
			del kwargs["time"]

		goocanvas.Group.__init__(self, *args, **kwargs)

		self.timeline = timeline

		self.connect("button_press_event", self.button_press)
		self.motion_handler_id = None
		self.release_handler_id = None

	def button_press(self, item, target, event):
		if not event.button==1: return True

		if self.timeline.props.mode==MODE_DEFAULT:
			if self.motion_handler_id:
				self.handler_disconnect(self.motion_handler_id)
				self.motion_handler_id = None
			if self.release_handler_id:
				self.handler_disconnect(self.release_handler_id)
				self.release_handler_id = None

			if not self.allow_drag_x and not self.allow_drag_y: return True

			# grab pointer
			canvas = item.get_canvas()
			canvas.pointer_grab(item, gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.BUTTON_RELEASE_MASK, None, event.time)

			# connect callbacks
			self.motion_handler_id = self.connect("motion_notify_event", self.motion_notify, event.x-self.props.x, event.y-self.props.y)
			self.release_handler_id = self.connect("button_release_event", self.button_release, event.x, event.y)

			return False

		elif self.timeline.props.mode==MODE_DELETE:
			self.delete_item()
			self.remove()
			self.timeline.project.touch()
			self.timeline.props.mode=MODE_DEFAULT

			return False

	def motion_notify(self, item, target, event, offsetx, offsety):
		assert not self.motion_handler_id==None

		if self.allow_drag_x:
			self.props.x = event.x - offsetx
		if self.allow_drag_y:
			self.props.y = event.y - offsety

		self.timeline.project.touch()

		return False

	def button_release(self, item, target, event, x, y):
		assert not self.motion_handler_id==None
		assert not self.release_handler_id==None

		# ungrab pointer
		canvas = item.get_canvas()
		canvas.pointer_ungrab(item, event.time)

		# delete handlers
		self.handler_disconnect(self.motion_handler_id)
		self.handler_disconnect(self.release_handler_id)
		self.motion_handler_id = None
		self.release_handler_id = None

		if event.x==x and event.y==y: self.clicked()

		return False

	def get_time(self):
		return self.timeline.get_seconds(self.props.y)

	def clicked(self): pass

	def delete_item(self): pass

class Marker(TimelineItem):
	def __init__(self,timeline,start,duration,text,**kwargs):
		kwargs["allow_drag_y"] = False
		kwargs["time"] = start
		TimelineItem.__init__(self,timeline,**kwargs)

		width = 5
		height = self.timeline.get_pts(duration)
		self.rect = goocanvas.Rect(parent=self,width=width,height=height,fill_color_rgba=0xaa0000aa)
		self.text = goocanvas.Text(parent=self,text=text, x=width*1.3)

	def get_start(self):
		return self.get_time()

	def get_duration(self):
		return self.timeline.get_seconds(self.rect.props.height)

	def get_text(self):
		return self.text.props.text

	def delete_item(self):
		self.timeline.markers.remove(self)

	def clicked(self):
		self.timeline.ruler.set_playback_marker(self.get_start(), self.get_duration())

class Annotation(TimelineItem):
	def __init__(self,timeline,text,**kwargs):
		TimelineItem.__init__(self,timeline,**kwargs)

		self.text = goocanvas.Text(parent=self,text=text)

	def get_text(self):
		return self.text.props.text

	def delete_item(self):
		self.timeline.annotations.remove(self)

class TabMarker(goocanvas.Group):
	def __init__(self,string,start,duration,fret,**kwargs):
		kwargs["parent"] = string
		goocanvas.Group.__init__(self,**kwargs)

		self.fret = fret
		self.string = string

		width = 4
		height = self.string.tabulature.timeline.get_pts(duration)
		self.rect = goocanvas.Rect(parent=self,width=width,height=height,fill_color_rgba=0xaa0000aa)
		self.text = goocanvas.Text(parent=self,text=str(fret), x=width*1.3)

		self.props.y = self.string.tabulature.timeline.get_pts(start)

		self.connect("button_release_event", self.clicked)

	def get_start(self):
		return self.string.tabulature.timeline.get_seconds(self.props.y)

	def get_duration(self):
		return self.string.tabulature.timeline.get_seconds(self.rect.props.height)

	def clicked(self,*args):
		timeline = self.string.tabulature.timeline

		if timeline.props.mode==MODE_DEFAULT:
			timeline.ruler.set_playback_marker(self.get_start(), self.get_duration())
			return True
		elif timeline.props.mode==MODE_DELETE:
			self.string.markers.remove(self)
			self.remove()
			timeline.props.mode=MODE_DEFAULT
			return True

		return False

class String(goocanvas.Group):
	def __init__(self,tabulature,tuning,**kwargs):
		kwargs["parent"] = tabulature
		goocanvas.Group.__init__(self,**kwargs)

		self.tuning = tuning
		self.tabulature = tabulature

		height = tabulature.timeline.get_pts(tabulature.timeline.project.pipeline.duration)
		goocanvas.polyline_new_line(self, 2,0, 2,height)

		self.markers = []

class Tabulature(goocanvas.Group):
	def __init__(self,timeline,strings,**kwargs):
		kwargs["parent"] = timeline.get_root_item()

		if "spacing" in kwargs:
			self.spacing = kwargs["spacing"]
			del kwargs["spacing"]
		else:
			self.spacing = 30

		goocanvas.Group.__init__(self,**kwargs)

		self.timeline = timeline
	
		self.strings = []
		for i in xrange(len(strings)):
			tuning = strings[i]
			string = String(self, tuning)
			string.props.x = i*self.spacing
			self.strings.append(string)

	def get_width(self):
		return len(self.strings)*self.spacing

class Tap(goocanvas.Group):
	def __init__(self,rhythm,weight=1,**kwargs):
		kwargs["parent"] = rhythm

		if "time" in kwargs:
			kwargs["y"] = rhythm.timeline.get_pts(kwargs["time"])
			del kwargs["time"]

		goocanvas.Group.__init__(self,**kwargs)

		self.rhythm = rhythm
		self.line = goocanvas.polyline_new_line(self, 0, 0, 10, 0)
		self.time_sum = self.get_time()*weight
		self.weight = weight
		self.text = goocanvas.Text(parent=self, text=str(self.weight), x=10, anchor=gtk.ANCHOR_W)

	def append_tap(self,time):
		self.weight += 1
		self.time_sum += time
		self.props.y = 1.0*self.rhythm.timeline.get_pts(self.time_sum)/self.weight
		self.text.props.text = str(self.weight)

	def get_time(self):
		return self.rhythm.timeline.get_seconds(self.props.y)

class Rhythm(goocanvas.Group):
	def __init__(self, timeline, **kwargs):
		kwargs["parent"] = timeline.get_root_item()

		goocanvas.Group.__init__(self,**kwargs)

		self.timeline = timeline
		self.tolerance = 0.10

		self.rect = goocanvas.Rect(parent=self, width=20, height=timeline.get_pts(timeline.project.pipeline.duration), fill_color="red")
		self.taps = []

	def add_tap(self, pos=None, weight=1):
		if pos:
			tap = Tap(self,weight,time=pos)
			self.taps.append(tap)
			self.timeline.project.touch()
			return tap

		pos = self.timeline.project.pipeline.get_position()

		# find near taps
		near = []
		for tap in self.taps:
			time = tap.get_time()
			if abs(time-pos)<self.tolerance: near.append(tap)

		l = len(near)
		if l>1:
			print "ambiguous tap"
		elif l==1:
			near[0].append_tap(pos)
			self.timeline.project.touch()
			return near[0]
		else:
			tap = Tap(self,time=pos)
			self.taps.append(tap)
			self.timeline.project.touch()
			return tap

	def clear_taps(self,start,duration):
		remove = []

		for tap in self.taps:
			time = tap.get_time()
			if start<time and time<start+duration:
				remove.append(tap)

		for tap in remove:
			tap.remove()
			self.taps.remove(tap)

		self.timeline.project.touch()

	def get_width(self):
		return 20

class Ruler(goocanvas.Group):
	def __init__(self, timeline, **kwargs):
		kwargs["parent"] = timeline.get_root_item()

		if "width" in kwargs:
			width = kwargs["width"]
			del kwargs["width"]
		else:
			width = 50

		goocanvas.Group.__init__(self,**kwargs)

		self.timeline = timeline

		self.rect = goocanvas.Rect(parent=self, width=width, height=timeline.get_pts(timeline.project.pipeline.duration), fill_color="blue")
		self.rect.connect("button_press_event", self.button_press)
		self.motion_handler_id = None
		self.release_handler_id = None

		# labelling
		for i in xrange(int(timeline.project.pipeline.duration)):
			goocanvas.Text(parent=self, text=str(1.0*i), y=timeline.get_pts(i), pointer_events=0)

		# playback marker
		self.playback_marker = goocanvas.Rect(parent=self, width=width, height=0, visibility=goocanvas.ITEM_INVISIBLE, fill_color_rgba=0x00000044)
		self.playback_marker.props.pointer_events = 0 # let self.rect receive pointer events

		# playback marker adjustments
		self.marker_start = gtk.Adjustment(0, 0, timeline.project.pipeline.duration, 0.01)
		self.marker_duration = gtk.Adjustment(0, 0, timeline.project.pipeline.duration, 0.01)
		self.start_handler = self.marker_start.connect("value-changed", self.start_changed)
		self.duration_handler = self.marker_duration.connect("value-changed", self.duration_changed)

	def get_width(self):
		return self.rect.props.width

	def start_changed(self,adjustment):
		self.playback_marker.props.y = self.timeline.get_pts(self.marker_start.get_value())

	def duration_changed(self,adjustment):
		self.playback_marker.props.height = self.timeline.get_pts(self.marker_duration.get_value())

	# playback marker
	def button_press (self, item, target, event):
		if not event.button==1: return

		if self.motion_handler_id:
			self.rect.handler_disconnect(self.motion_handler_id)
			self.motion_handler_id = None
		if self.release_handler_id:
			self.rect.handler_disconnect(self.release_handler_id)
			self.release_handler_id = None

		# hide playback marker
		self.playback_marker.props.visibility = goocanvas.ITEM_INVISIBLE

		# grab pointer
		canvas = item.get_canvas()
		canvas.pointer_grab(item, gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.BUTTON_RELEASE_MASK, None, event.time)

		# connect callbacks
		self.motion_handler_id = self.rect.connect("motion_notify_event", self.motion_notify, event.y)
		self.release_handler_id = self.rect.connect("button_release_event", self.button_release)

		return True

	def motion_notify (self, item, target, event, y):
		assert not self.motion_handler_id==None

		if event.y<0:
			self.playback_marker.props.y = 0
			self.playback_marker.props.height = y
		elif event.y>y:
			self.playback_marker.props.y = y
			self.playback_marker.props.height = event.y - y
		else:
			self.playback_marker.props.y = event.y
			self.playback_marker.props.height = y - event.y

		# update adjustments
		self.marker_start.handler_block(self.start_handler)
		self.marker_duration.handler_block(self.duration_handler)
		self.marker_start.set_value(self.timeline.get_seconds(self.playback_marker.props.y))
		self.marker_duration.set_value(self.timeline.get_seconds(self.playback_marker.props.height))
		self.marker_start.handler_unblock(self.start_handler)
		self.marker_duration.handler_unblock(self.duration_handler)

		# make marker visible
		self.playback_marker.props.visibility = goocanvas.ITEM_VISIBLE

		return True

	def button_release (self, item, target, event):
		assert not self.motion_handler_id==None
		assert not self.release_handler_id==None

		# ungrab pointer
		canvas = item.get_canvas()
		canvas.pointer_ungrab(item, event.time)

		# delete handlers
		self.rect.handler_disconnect(self.motion_handler_id)
		self.rect.handler_disconnect(self.release_handler_id)
		self.motion_handler_id = None
		self.release_handler_id = None

	# marker access functions
	def get_playback_marker(self):
		if not self.playback_marker.props.visibility==goocanvas.ITEM_VISIBLE: return None

		return self.marker_start.get_value(), self.marker_duration.get_value()

	def set_playback_marker(self,start,duration):
		self.marker_start.set_value(start)
		self.marker_duration.set_value(duration)
		self.playback_marker.props.visibility = goocanvas.ITEM_VISIBLE

class Timeline(goocanvas.Canvas):
	__gproperties__ = {"mode":(gobject.TYPE_INT, "mode", "editing mode", 0, MODES_NUM-1, MODE_DEFAULT, gobject.PARAM_READWRITE)}

	def __init__(self, project, strings, **kwargs):
		goocanvas.Canvas.__gobject_init__(self)

		self.project = project

		if "scale" in kwargs: self.scale = kwargs["scale"]
		else: self.scale = 100

		if "width" in kwargs: self.width = kwargs["width"]
		else: self.width = 500

		# mode
		self.mode = MODE_DEFAULT

		# configure canvas
		height = self.get_pts(self.project.pipeline.duration)
		self.set_bounds(0,0,self.width,height)
		self.set_size_request(self.width,int(height))
		self.connect("button_press_event",self.canvas_button_press)

		root = self.get_root_item()

		# add ruler
		self.ruler = Ruler(self)

		# add rhythm marker space
		self.rhythm = Rhythm(self)
		self.rhythm.props.x = self.ruler.get_width()

		# position marker
		self.posmarker = goocanvas.polyline_new_line(root, 0, 0, self.width, 0)

		# items
		self.annotations = []
		self.markers = []
		self.tabulature = Tabulature(self, strings)
		self.tabulature.props.x = self.rhythm.props.x + self.rhythm.get_width() + 20

		# setup space
		self.space = goocanvas.Group(parent=root)
		self.space.props.x = self.tabulature.props.x + self.tabulature.get_width()+20

	# custom properties
	def do_get_property(self,pspec):
		return getattr(self, pspec.name)

	def do_set_property(self,pspec,value):
		setattr(self, pspec.name, value)

	# unit conversion
	def get_pts(self,*args):
		r = [1.*self.scale*seconds for seconds in args]
		if len(r)==1: return r[0]
		else: return r

	def get_seconds(self,*args):
		r = [1.*pts/self.scale for pts in args]
		if len(r)==1: return r[0]
		else: return r

	# position marker
	def set_position(self, pos):
		self.posmarker.props.y = self.get_pts(pos)

	# space events
	def canvas_button_press(self,widget,event):
		if self.props.mode==MODE_ANNOTATE:
			dialog = gtk.Dialog(title="Text", flags=gtk.DIALOG_DESTROY_WITH_PARENT|gtk.DIALOG_MODAL, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
			entry = gtk.Entry()
			dialog.vbox.add(entry)
			dialog.show_all()
			if dialog.run()==gtk.RESPONSE_ACCEPT:
				x,y,scale,rotation = self.space.get_simple_transform()
				ann = Annotation(self,text=entry.get_text(), x=event.x-x, y=event.y-y)
				self.annotations.append(ann)
				self.project.touch()
			dialog.destroy()

			self.props.mode=MODE_DEFAULT

			return True

gobject.type_register(Timeline)
