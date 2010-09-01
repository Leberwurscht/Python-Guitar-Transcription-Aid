#!/usr/bin/env python

import gtk
import goocanvas

# click modes
MODE_DEFAULT, MODE_ANNOTATE, MODE_DELETE = xrange(3)

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

		if self.timeline.mode==MODE_DEFAULT:
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

		elif self.timeline.mode==MODE_DELETE:
			self.delete_item()
			self.remove()
			self.timeline.project.touch()
			self.timeline.mode=MODE_DEFAULT
			self.timeline.project.transcribe.builder.get_object("mode_default").set_active(True)

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
		self.timeline.project.transcribe.update_playback_marker_spinbuttons()
#		self.timeline.ruler.playback_marker_changed_cb()

class Annotation(TimelineItem):
	def __init__(self,timeline,text,**kwargs):
		TimelineItem.__init__(self,timeline,**kwargs)

		self.text = goocanvas.Text(parent=self,text=text)

	def get_text(self):
		return self.text.props.text

	def delete_item(self):
		self.timeline.annotations.remove(self)

class Ruler(goocanvas.Group):
	def __init__(self, timeline, project, **kwargs):
		self.timeline = timeline
		self.project = project

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

		self.timeline.project.transcribe.update_playback_marker_spinbuttons()

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

		# mode
		self.mode = MODE_DEFAULT
		self.project.transcribe.builder.get_object("mode_default").set_active(True)

		# configure canvas
		height = self.get_pts(self.project.pipeline.duration)
		self.set_bounds(0,0,self.width,height)
		self.set_size_request(self.width,height)
		self.connect("button_press_event",self.canvas_button_press)

		root = self.get_root_item()

		# add ruler
		self.ruler = Ruler(self, self.project, parent=root)

		# setup space
		self.space = goocanvas.Group(parent=root)
		self.space.translate(self.ruler.rect.props.width*1.3, 0)

		# position marker
		self.posmarker = goocanvas.polyline_new_line(root, 0, 0, self.width, 0)

		# items
		self.annotations = []
		self.markers = []

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
		if self.mode==MODE_ANNOTATE:
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

			self.mode=MODE_DEFAULT
			self.project.transcribe.builder.get_object("mode_default").set_active(True)

			return True
