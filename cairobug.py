#!/usr/bin/env python

# https://bugs.freedesktop.org/show_bug.cgi?id=29470

import gtk, cairo

def expose(widget,event):
	ctx = widget.window.cairo_create()
	draw(ctx)

# should draw two lines, each consisting of a 6px gradient, at position 20px;
# the second line is drawn at 26px, however.
# derivation of the position formula:
#
# 
# |---------------------------|-----*---------------------|
# ^ -gradient_width           ^ 0   ^ 20px                ^ gradient_width
#
# percentual position of the 20px position is therefore
# (gradient_width+20) / (2*gradient_width) = .5*(gradient_width+pos)/gradient_width

def draw(ctx):
	pos = 20

	gradient_width = 300
	pattern = cairo.LinearGradient(-gradient_width, 0, gradient_width, 0)
	pattern.add_color_stop_rgb(.5*(gradient_width+pos-3)/gradient_width,1,1,1)
	pattern.add_color_stop_rgb(.5*(gradient_width+pos)/gradient_width,0,0,0)
	pattern.add_color_stop_rgb(.5*(gradient_width+pos+3)/gradient_width,1,1,1)
	ctx.rectangle(0,0,100,30)
	ctx.set_source(pattern)
	ctx.fill()

	gradient_width = 600
	pattern = cairo.LinearGradient(-gradient_width, 0, gradient_width, 0)
	pattern.add_color_stop_rgb(.5*(gradient_width+pos-3)/gradient_width,1,1,1)
	pattern.add_color_stop_rgb(.5*(gradient_width+pos)/gradient_width,0,0,0)
	pattern.add_color_stop_rgb(.5*(gradient_width+pos+3)/gradient_width,1,1,1)
	ctx.rectangle(0,30,100,30)
	ctx.set_source(pattern)
	ctx.fill()

	gradient_width = 20
	pattern = cairo.LinearGradient(0, 0, 2*gradient_width, 0)
	pattern.add_color_stop_rgb(.5*(pos/1000.-3)/gradient_width,1,1,1)
	pattern.add_color_stop_rgb(.5*(pos/1000.)/gradient_width,0,0,0)
	pattern.add_color_stop_rgb(.5*(pos/1000.+3)/gradient_width,1,1,1)
	ctx.rectangle(0,60,100,30)
	m = pattern.get_matrix()
	m.scale(1000.,1.)
	pattern.set_matrix(m)
	ctx.set_source(pattern)
	ctx.fill()

	gradient_width = 600
	pattern = cairo.LinearGradient(-gradient_width, 0, gradient_width, 0)
	pattern.add_color_stop_rgb(.5*(gradient_width+pos-3)/gradient_width,1,1,1)
	pattern.add_color_stop_rgb(.5*(gradient_width+pos)/gradient_width,0,0,0)
	pattern.add_color_stop_rgb(.5*(gradient_width+pos+3)/gradient_width,1,1,1)
	ctx.rectangle(0,90,100,30)
	ctx.set_source(pattern)
	ctx.fill()

surface = cairo.ImageSurface (cairo.FORMAT_ARGB32, 400,400)
context = cairo.Context(surface)
draw(context)
context.show_page()
surface.write_to_png("test.png")

w = gtk.Window()
d = gtk.DrawingArea()
d.connect("expose_event",expose)
w.add(d)
w.show_all()
w.connect("delete_event",gtk.main_quit)
gtk.main()
