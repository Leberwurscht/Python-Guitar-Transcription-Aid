#!/usr/bin/env python

import gtk
import goocanvas

class Timeline(goocanvas.Canvas):
	def __init__(self, duration, **kwargs):
		goocanvas.Canvas.__init__(self)

		self.duration = duration

		if "scale" in kwargs: self.scale = kwargs["scale"]
		else: self.scale = 50

		if "width" in kwargs: self.width = kwargs["width"]
		else: self.width = 400

		if "timelinewidth" in kwargs: timelinewidth = kwargs["timelinewidth"]
		else: timelinewidth = 40

		# mode
		self.mode = None
		self.dragging=False

		# configure canvas
		self.set_bounds(0,0,self.width,self.duration*self.scale)
		self.connect("button_press_event",self.canvas_button_press)

		root = self.get_root_item()

		# setup space
		self.space = goocanvas.Group(parent=root)
		self.space.translate(timelinewidth,0)

		# setup timeline
		self.timeline = goocanvas.Group(parent=root)
		self.timerect = goocanvas.Rect(parent=self.timeline,width=timelinewidth,height=self.duration*self.scale,fill_color="blue")
		self.marker = goocanvas.Rect(parent=self.timeline,width=timelinewidth,height=0,visibility=goocanvas.ITEM_INVISIBLE, fill_color_rgba=0x00000044)
		self.marker.props.pointer_events = 0
		self.timerect.connect("motion_notify_event", self.timerect_on_motion_notify)
        	self.timerect.connect("button_press_event", self.timerect_on_button_press)
		self.timerect.connect("button_release_event", self.timerect_on_button_release)

		for i in xrange(int(duration)):
			goocanvas.Text(parent=self.timeline, text=str(i), y=i*self.scale)

	# marker
	def get_marker(self):
		if self.marker.props.visibility==goocanvas.ITEM_INVISIBLE:
			return None
		else:
			return (1.*self.marker.props.y/self.scale, 1.*self.marker.props.height/self.scale)

	# marker events
	def timerect_on_motion_notify (self, item, target, event):
		if (self.dragging == True) and (event.state & gtk.gdk.BUTTON1_MASK):
			if self.drag_y<0:
				self.marker.props.y=0
			if event.y>self.drag_y:
				self.marker.props.y=self.drag_y
				self.marker.props.height=event.y-self.drag_y
			else:
				self.marker.props.y=event.y
				self.marker.props.height=self.drag_y-event.y
				
		return True
    
	def timerect_on_button_press (self, item, target, event):
		if event.button == 1:
			self.drag_y = event.y

			canvas = item.get_canvas()
			canvas.pointer_grab (item, gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.BUTTON_RELEASE_MASK, None, event.time)
        	        self.dragging = True

			self.marker.props.visibility = goocanvas.ITEM_VISIBLE
			self.marker.props.y=event.y
			self.marker.props.height=0
	        return True

	def timerect_on_button_release (self, item, target, event):
		canvas = item.get_canvas()
		canvas.pointer_ungrab(item, event.time)
		self.dragging = False

	# drag and drop
	def enable_dragging(self,item):
		item.connect("motion_notify_event", self.on_motion_notify)
        	item.connect("button_press_event", self.on_button_press)
		item.connect("button_release_event", self.on_button_release)

	def on_motion_notify (self, item, target, event):
		if (self.dragging == True) and (event.state & gtk.gdk.BUTTON1_MASK):
			new_x = event.x
			new_y = event.y
			item.translate (new_x - self.drag_x, new_y - self.drag_y)
		return True
    
	def on_button_press (self, item, target, event):
		if event.button == 1:
			self.drag_x = event.x
			self.drag_y = event.y

			canvas = item.get_canvas()
			canvas.pointer_grab (item, gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.BUTTON_RELEASE_MASK, None, event.time)
        	        self.dragging = True
	        return True

	def on_button_release (self, item, target, event):
		canvas = item.get_canvas()
		canvas.pointer_ungrab(item, event.time)
		self.dragging = False

	# space events
	def canvas_button_press(self,widget,event):
		if self.mode=="insert_text":
			dialog = gtk.Dialog(title="Text", flags=gtk.DIALOG_DESTROY_WITH_PARENT|gtk.DIALOG_MODAL, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
			entry = gtk.Entry()
			dialog.vbox.add(entry)
			dialog.show_all()
			if dialog.run()==gtk.RESPONSE_ACCEPT:
				x,y,scale,rotation = self.space.get_simple_transform()
				text = goocanvas.Text(parent=self.space, text=entry.get_text(), x=event.x-x, y=event.y-y)
				self.enable_dragging(text)
			dialog.destroy()
			self.mode=None
