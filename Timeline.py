#!/usr/bin/env python

import gtk
import goocanvas

# click modes
MODE_DEFAULT, MODE_ANNOTATE, MODE_DELETE = xrange(3)

class DraggableItem:
	def make_draggable(self, drag_item=None, draggable_x=True, draggable_y=True):
		if drag_item:
			self.drag_item = drag_item
		else:
			self.drag_item = self

		self.draggable_x = draggable_x
		self.draggable_y = draggable_y

		self.drag_item.connect("button_press_event", self.button_press)
		self.motion_handler_id = None
		self.release_handler_id = None

	def button_press(self, item, target, event):
		if not event.button==1: return

		if self.motion_handler_id:
			self.drag_item.handler_disconnect(self.motion_handler_id)
			self.motion_handler_id = None
		if self.release_handler_id:
			self.drag_item.handler_disconnect(self.release_handler_id)
			self.release_handler_id = None

		# grab pointer
		canvas = item.get_canvas()
		canvas.pointer_grab(item, gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.BUTTON_RELEASE_MASK, None, event.time)

		# connect callbacks
		self.motion_handler_id = self.drag_item.connect("motion_notify_event", self.motion_notify, event.x-self.props.x, event.y-self.props.y)
		self.release_handler_id = self.drag_item.connect("button_release_event", self.button_release)

		return True

	def motion_notify(self, item, target, event, offsetx, offsety):
		assert not self.motion_handler_id==None

		if self.draggable_x:
			self.props.x = event.x - offsetx
		if self.draggable_y:
			self.props.y = event.y - offsety

		self.on_drag()

		return True

	def button_release(self, item, target, event):
		assert not self.motion_handler_id==None
		assert not self.release_handler_id==None

		# ungrab pointer
		canvas = item.get_canvas()
		canvas.pointer_ungrab(item, event.time)

		# delete handlers
		self.drag_item.handler_disconnect(self.motion_handler_id)
		self.drag_item.handler_disconnect(self.release_handler_id)
		self.motion_handler_id = None
		self.release_handler_id = None

	def on_drag(self): pass

class Marker(goocanvas.Group, DraggableItem):
	def __init__(self,timeline,start,duration,text,**kwargs):
		self.timeline = timeline
		kwargs["parent"] = timeline.space

		kwargs["y"] = self.timeline.get_pts(start)

		goocanvas.Group.__init__(self,**kwargs)

		width = 20
		height = self.timeline.get_pts(duration)
		self.rect = goocanvas.Rect(parent=self,width=width,height=height,fill_color_rgba=0xaa0000aa)
		self.text = goocanvas.Text(parent=self,text=text, pointer_events=0)

		self.make_draggable(self.rect, True, False)

	def get_start(self):
		return self.timeline.get_seconds(self.props.y)

	def get_duration(self):
		return self.timeline.get_seconds(self.rect.props.height)

	def get_text(self):
		return self.text.props.text

	def on_drag(self):
		self.timeline.project.touched = True

class MarkerBak(goocanvas.Group):
	def __init__(self,timeline,start,duration,text,**kwargs):
		self.timeline = timeline
		kwargs["parent"] = timeline.space

		kwargs["y"] = self.timeline.get_pts(start)

		goocanvas.Group.__init__(self,**kwargs)

		width = 20
		height = self.timeline.get_pts(duration)
		self.rect = goocanvas.Rect(parent=self,width=width,height=height,fill_color_rgba=0xaa0000aa)
		self.text = goocanvas.Text(parent=self,text=text, pointer_events=0)

		self.rect.connect("button_press_event", self.button_press)
		self.motion_handler_id = None
		self.release_handler_id = None

	def get_start(self):
		return self.timeline.get_seconds(self.props.y)

	def get_duration(self):
		return self.timeline.get_seconds(self.rect.props.height)

	def get_text(self):
		return self.text.props.text

	# dragging
	def button_press(self, item, target, event):
		if not event.button==1: return

		if self.motion_handler_id:
			self.rect.handler_disconnect(self.motion_handler_id)
			self.motion_handler_id = None
		if self.release_handler_id:
			self.rect.handler_disconnect(self.release_handler_id)
			self.release_handler_id = None

		# grab pointer
		canvas = item.get_canvas()
		canvas.pointer_grab(item, gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.BUTTON_RELEASE_MASK, None, event.time)

		# connect callbacks
		self.motion_handler_id = self.rect.connect("motion_notify_event", self.motion_notify, event.x-self.props.x)
		self.release_handler_id = self.rect.connect("button_release_event", self.button_release)

		return True

	def motion_notify(self, item, target, event, offset):
		assert not self.motion_handler_id==None

		self.props.x = event.x - offset
		self.timeline.project.touched = True

		return True

	def button_release(self, item, target, event):
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

class Annotation(goocanvas.Text, DraggableItem):
	def __init__(self,timeline,**kwargs):
		self.timeline=timeline
		kwargs["parent"] = timeline.space

		if "time" in kwargs:
			kwargs["y"] = self.timeline.get_pts(kwargs["time"])
			del kwargs["time"]

		goocanvas.Text.__init__(self,**kwargs)

#		self.timeline.enable_dragging(self)
		self.make_draggable()

	def get_time(self):
		return self.timeline.get_seconds(self.props.y)

	def on_drag(self):
		self.timeline.project.touched = True

class Ruler(goocanvas.Group):
	def __init__(self, timeline, project, **kwargs):
		self.timeline = timeline
		self.project = project
		self.playback_marker_changed_cb = None

		if "width" in kwargs:
			width = kwargs["width"]
			del kwargs["width"]
		else:
			width = 50

		goocanvas.Group.__init__(self,**kwargs)

		self.rect = goocanvas.Rect(parent=self, width=width, height=timeline.get_pts(project.pipeline.duration), fill_color="blue")
		self.rect.connect("button_press_event", self.button_press)
		self.motion_handler_id = None
		self.release_handler_id = None

		# labelling
		for i in xrange(int(project.pipeline.duration)):
			goocanvas.Text(parent=self, text=str(1.0*i), y=timeline.get_pts(i))

		# playback_marker
		self.playback_marker = goocanvas.Rect(parent=self, width=width, height=0, visibility=goocanvas.ITEM_INVISIBLE, fill_color_rgba=0x00000044)
		self.playback_marker.props.pointer_events = 0 # let self.rect receive pointer events

	# set callback
	def set_playback_marker_changed_cb(self, cb):
		self.playback_marker_changed_cb = cb

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

		# make marker visible
		self.playback_marker.props.visibility = goocanvas.ITEM_VISIBLE

		if self.playback_marker_changed_cb: self.playback_marker_changed_cb()

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

		start,duration = self.timeline.get_seconds(self.playback_marker.props.y, self.playback_marker.props.height)

		return start, duration

	def set_playback_marker(self,start,duration):
		self.playback_marker.props.y = self.timeline.get_pts(start)
		self.playback_marker.props.height = self.timeline.get_pts(duration)
		self.playback_marker.props.visibility = goocanvas.ITEM_VISIBLE

class Timeline(goocanvas.Canvas):
	def __init__(self, project, **kwargs):
		goocanvas.Canvas.__init__(self)

		self.project = project

		if "scale" in kwargs: self.scale = kwargs["scale"]
		else: self.scale = 100

		if "width" in kwargs: self.width = kwargs["width"]
		else: self.width = 400

		if "timelinewidth" in kwargs: timelinewidth = kwargs["timelinewidth"]
		else: timelinewidth = 40

		# mode
		self.mode = None
#		self.dragging=False

		# configure canvas
		self.set_bounds(0,0,self.width,self.get_pts(self.project.pipeline.duration))
		self.connect("button_press_event",self.canvas_button_press)

		root = self.get_root_item()

		# setup space
		self.space = goocanvas.Group(parent=root)
		self.space.translate(timelinewidth,0)

		# position marker
		self.posmarker = goocanvas.polyline_new_line(root, 0, 0, self.width, 0)

		# items
		self.annotations = []
		self.markers = []

		self.ruler = Ruler(self, self.project, parent=root)

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

	# drag and drop
	def enable_dragging(self,item):
		item.connect("motion_notify_event", self.on_motion_notify)
		item.connect("button_press_event", self.on_button_press)
		item.connect("button_release_event", self.on_button_release)

	def on_motion_notify (self, item, target, event):
		if (self.dragging == True) and (event.state & gtk.gdk.BUTTON1_MASK):
			new_x = event.x
			new_y = event.y
#			item.translate (new_x - self.drag_x, new_y - self.drag_y)
			item.props.x = new_x - self.drag_x
			item.props.y = new_y - self.drag_y
			self.project.touched=True
		return True
    
	def on_button_press (self, item, target, event):
		if event.button == 1:
			self.drag_x = event.x - item.props.x
			self.drag_y = event.y - item.props.y
#			self.drag_x = event.x
#			self.drag_y = event.y

			canvas = item.get_canvas()
			canvas.pointer_grab (item, gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.BUTTON_RELEASE_MASK, None, event.time)
			self.dragging = True
	        return True

	def on_button_release (self, item, target, event):
		canvas = item.get_canvas()
		canvas.pointer_ungrab(item, event.time)
		self.dragging = False
#		print item.props.x,item.props.y,item.props.text,item.get_time()
#		print item.get_simple_transform()

	# space events
	def canvas_button_press(self,widget,event):
		if self.mode==MODE_ANNOTATE:
			dialog = gtk.Dialog(title="Text", flags=gtk.DIALOG_DESTROY_WITH_PARENT|gtk.DIALOG_MODAL, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
			entry = gtk.Entry()
			dialog.vbox.add(entry)
			dialog.show_all()
			if dialog.run()==gtk.RESPONSE_ACCEPT:
				x,y,scale,rotation = self.space.get_simple_transform()
				ann = Annotation(self,text=entry.get_text(), x=event.x-x, y=event.y-y)
				self.annotations.append(ann)
				self.project.touched=True
			dialog.destroy()
			self.mode=MODE_DEFAULT
