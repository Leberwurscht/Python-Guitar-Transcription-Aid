#!/usr/bin/env python

import numpy, cairo, gobject
import scipy.interpolate
import Math
from VisualizerControlBase import base as VisualizerControlBase

class VisualizerControl(VisualizerControlBase):
	__gproperties__ = {
		'autoupdate': (gobject.TYPE_BOOLEAN,'AutoUpdate','Whether to update visualizers while playback',False,gobject.PARAM_READWRITE)
	}

	__gsignals__ = {
		'new-data': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
		'add-tab-marker': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_INT, gobject.TYPE_INT)),
		'plot-evolution': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_INT,)),
		'find-onset': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_INT,)),
		'analyze-semitone': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_INT,))
	}

	""" holds data for visualizers, calculates and caches different scales """
	def __init__(self, pipeline, **kwargs):
		VisualizerControlBase.__init__(self, pipeline.spectrum, pipeline)
		self.autoupdate_handler = self.connect("magnitudes_available", self.autoupdate)
		self.handler_block(self.autoupdate_handler)
		self.autoupdate = False

		if "brightness_method" in kwargs:
			self.brightness_method = kwargs["brightness_method"]
		else:
			self.brightness_method = "from_magnitude"

		if self.brightness_method=="from_magnitude":
			if "min_magnitude" in kwargs:
				self.min_magnitude = kwargs["min_magnitude"]
			else:
				self.min_magnitude = None #-60.

			if "max_magnitude" in kwargs:
				self.max_magnitude = kwargs["max_magnitude"]
			else:
				self.max_magnitude = None #0.
		elif self.brightness_method=="from_power":
			if "min_power" in kwargs:
				self.min_power = kwargs["min_power"]
			else:
				self.min_power = None #0.0

			if "max_power" in kwargs:
				self.max_power = kwargs["max_power"]
			else:
				self.max_power = None #0.001
		else:
			raise Exception, "invalid method"

		self.clear()

	# custom properties
	def do_get_property(self,pspec):
		if pspec.name=="autoupdate":
			return self.autoupdate
		else:
			raise Exception, "Invalid property name"

	def do_set_property(self,pspec,value):
		if pspec.name=="autoupdate":
			if value and not self.autoupdate:
				self.handler_unblock(self.autoupdate_handler)
				self.autoupdate = True
			elif not value and self.autoupdate:
				self.handler_block(self.autoupdate_handler)
				self.autoupdate = False
		else:
			raise Exception, "Invalid property name"

	# callbacks
	def autoupdate(self, control, bands, rate, threshold, start, duration, magnitude):
		frequency = 0.5 * ( numpy.arange(bands) + 0.5 ) * rate / bands
		self.set_magnitude(start, duration, frequency, numpy.array(magnitude))

	# set data
	def clear(self):
		self.power = None
		self.magnitude = None
		self.brightness = None
		self.semitone = None
		self.power_spline = None
		self.powerfreq_spline = None
		self.gradient = None
		self.has_data = None
		self.start = None
		self.duration = None

	def set_magnitude(self, start, duration, frequency, magnitude):
		self.clear()
		self.start = start
		self.duration = duration
		self.frequency = frequency
		self.magnitude = magnitude
		self.has_data = True
		self.emit("new_data")
		
	def set_power(self, start, duration, frequency, power):
		self.clear()
		self.start = start
		self.duration = duration
		self.frequency = frequency
		self.power = power
		self.has_data = True
		self.emit("new_data")

	# get data
	def get_semitone(self):
		if self.semitone==None: self.semitone = Math.frequency_to_semitone(self.frequency)
		return self.semitone

	def get_magnitude(self):
		if self.magnitude==None: self.magnitude = Math.power_to_magnitude(self.power)
		return self.magnitude

	def get_power(self):
		if self.power==None: self.power = Math.magnitude_to_power(self.magnitude)
		return self.power

	def get_brightness_coefficients_for_magnitude(self):
		if self.max_magnitude==None:
			max_magnitude=numpy.max(self.get_magnitude())
		else:
			max_magnitude = self.max_magnitude

		if self.min_magnitude==None:
			min_magnitude=numpy.min(self.get_magnitude())
		else:
			min_magnitude = self.min_magnitude

		brightness_slope = - 1.0 / (max_magnitude - min_magnitude)
		brightness_const = 1.0 * max_magnitude / (max_magnitude - min_magnitude)

		return brightness_const, brightness_slope

	def get_brightness_coefficients_for_power(self):
		if self.max_power==None:
			max_power=numpy.max(self.get_power())
		else:
			max_power = self.max_power

		if self.min_power==None:
			min_power=numpy.min(self.get_power())
		else:
			min_power = self.min_power

		brightness_slope = - 1.0 / (max_power - min_power)
		brightness_const = 1.0 * max_power/ (max_power - min_power)

		return brightness_const, brightness_slope

	def get_brightness(self):
		if self.brightness==None:
			if self.brightness_method=="from_magnitude":
				brightness_const, brightness_slope = self.get_brightness_coefficients_for_magnitude()

				brightness = brightness_slope * self.get_magnitude() + brightness_const
				self.brightness = numpy.maximum(0.,numpy.minimum(1.,brightness))
			elif self.brightness_method=="from_power":
				brightness_const, brightness_slope = self.get_brightness_coefficients_for_power()

				brightness = brightness_slope * self.get_power() + brightness_const
				self.brightness = numpy.maximum(0.,numpy.minimum(1.,brightness))

		return self.brightness

	def get_gradient(self):
		if not self.gradient:
			semitones = self.get_semitone()
			semitonerange = semitones[-1]-semitones[0]
			brightness = self.get_brightness()

			self.gradient = cairo.LinearGradient(semitones[0], 0, semitones[-1], 0)

			for i in xrange(len(semitones)):
				b = brightness[i]
				self.gradient.add_color_stop_rgb( ( semitones[i]-semitones[0] ) / semitonerange, b,b,b)

		return self.gradient

#	def get_total_power_in_semitone_range(self,lower,upper,overtones=10):
#		l = semitone_to_frequency(lower)
#		u = semitone_to_frequency(upper)
#		return self.get_total_power_in_frequency_range(l,u,overtones)
#
#	def get_total_power_in_frequency_range(self,lower,upper,overtones=10):
#		total = 0
#
#		for i in xrange(overtones+1):
##			total += integrate(self.frequency, self.get_power(), lower*(i+1), upper*(i+1))
#			total += self.get_power_in_frequency_range(lower*(i+1), upper*(i+1))
#
#		return total

#	def get_points_in_semitone_range(self,lower,upper,overtones=10):
#		l = semitone_to_frequency(lower)
#		u = semitone_to_frequency(upper)
#		return self.get_points_in_frequency_range(l,u,overtones)

	def get_peak_radius(self):
		bands = len(self.frequency)
		rate = 2.0 * bands * self.frequency[-1] / ( bands-0.5 )
		data_length = 2*bands - 2

		# http://mathworld.wolfram.com/HammingFunction.html: position of first root of apodization function
		peak_radius = 1.299038105676658 * rate / data_length

		return peak_radius

	def analyze_overtones(self,semitone,overtones=None):
		""" calculates power and peak center for each overtone and yields tuples (overtone, frequency, power, peak_center, difference_in_semitones) """
		frequency = Math.semitone_to_frequency(semitone)
		peak_radius = self.get_peak_radius()

		overtone=0

		while overtones==None or overtone<overtones:
			f = frequency*(overtone+1)
			s = Math.frequency_to_semitone(f)

			lower_frequency = f - peak_radius*1.65
			upper_frequency = f + peak_radius*1.65

			lower_frequency = min(lower_frequency, Math.semitone_to_frequency(s-0.5))
			upper_frequency = max(upper_frequency, Math.semitone_to_frequency(s+0.5))

			power = self.get_power_in_frequency_range(lower_frequency,upper_frequency)
			peak_center = self.get_powerfreq_spline().integral(lower_frequency,upper_frequency) / power

			difference_in_semitones = Math.frequency_to_semitone(peak_center) - s

			yield overtone, f, power, peak_center, difference_in_semitones

			overtone += 1

	def analyze_semitone(self,semitone,overtones=10, undertones=2, undertone_limit=80.):
		""" calculate total power, inharmonicity and independence coefficients """

		analysis = self.analyze_overtones(semitone,overtones)

		# fundamental tone
		overtone, fundamental_frequency, power, peak_center, difference_in_semitones = analysis.next()

		fundamental_power = power
		fundamental_diff_square = power * difference_in_semitones**2.
		fundamental_diff = power * difference_in_semitones

		# overtones
		overtone_power = 0
		overtone_diff_squares = 0
		overtone_diffs = 0

		for overtone, frequency, power, peak_center, difference_in_semitones in analysis:
			overtone_power += power
			overtone_diff_squares += power * difference_in_semitones**2.
			overtone_diffs += power * difference_in_semitones

		total_power = fundamental_power + overtone_power
		diff_squares = fundamental_diff_square + overtone_diff_squares
		diffs = fundamental_diff + overtone_diffs

		center = diffs/total_power
		variance = diff_squares/total_power - center**2.
		standard_deviation = numpy.sqrt(variance)

		# calculate upper_dependence
#		if fundamental_frequency<150.: fp = fundamental_power*15.	# exception for low-pitched tones
#		else: fp = fundamental_power
#		alien_power = max(0, overtone_power - 0.5*fp)
		alien_power = max(0, overtone_power - 0.5*fundamental_power)
		upper_dependence = alien_power / total_power
		print "upperdependence of %d is %f" % (semitone, upper_dependence)

		# calculate lower_dependence
		peak_radius = self.get_peak_radius()

		undertone_power = 0

		for undertone in xrange(2,undertones+2):
			undertone_frequency = fundamental_frequency / undertone
			if undertone_frequency < undertone_limit: break

			s = Math.frequency_to_semitone(undertone_frequency)

			lower_frequency = undertone_frequency - peak_radius*1.65
			upper_frequency = undertone_frequency + peak_radius*1.65

			lower_frequency = min(lower_frequency, Math.semitone_to_frequency(s-0.5))
			upper_frequency = max(upper_frequency, Math.semitone_to_frequency(s+0.5))

			power = self.get_power_in_frequency_range(lower_frequency,upper_frequency)

			power /= undertone**2.

#			if undertone_frequency>150.: power *= 15

			undertone_power += power

		lower_dependence = undertone_power / total_power
		print "lowerdependence of %d is %f (%f/%f)" % (semitone, lower_dependence, undertone_power, total_power)

		return fundamental_power, total_power, center, standard_deviation, upper_dependence, lower_dependence

	def get_power_spline(self):
		if not self.power_spline:
			self.power_spline = scipy.interpolate.InterpolatedUnivariateSpline(self.frequency, self.get_power(), None, [None, None], 1)

		return self.power_spline

	def get_powerfreq_spline(self):
		if not self.powerfreq_spline:
			self.powerfreq_spline = scipy.interpolate.InterpolatedUnivariateSpline(self.frequency, self.get_power()*self.frequency, None, [None, None], 1)

		return self.powerfreq_spline

	def get_power_in_frequency_range(self,lower,upper):
		return self.get_power_spline().integral(lower, upper)

	def get_points_in_frequency_range(self,lower,upper,overtones=10):
		# string 6: consider range of 3 semitones for key and 1st overtone
		# string 5: consider range of 3 semitones for key tone
		## better: estimate peak width through window function and use range of one semitone
		## or, if greater, peak width

		# low-pitched tones have more overtones (up to 9) and have them most of the time
		# key tone often lower-toned than first overtone for low-pitched notes

		# high-pitched tones tend to have less, but can have up to 6

		# calculate variance of peak center among overtones, should be small (inharmonicity)

		# return total power, inharmonicity, and perhaps some "independence" coefficients that
		# say how probable it is that this total power is just overtones of other notes or whether
		# the power belongs to an overtone of this note.
		# the second one can be seen by -X-X-X-X-X-X or --X--X--X--X patterns
		# the first one can be seen by checking for alternative key tones explaining these peaks

		#1> ~total power in mother tones with some weights
		# to get a big number, we need more power in one mother tone(except for low-pitched ones->amplify them).
		# -> ALGORITHM:
		#	weights = 1/frequency**2
		#	weights[0 Hz : 150 Hz] = weights[150 Hz] (exception for low-pitched tones)
		#	weighted_power = weights * power
		#	lower_dependence = sum[weighted_power(f/i) for i in xrange()] * f**2

		#2> if one overtone has much greater power, subtract it from total power (except for low-pitched tones)
		# [   1 + 1/4 + 1/9 + 1/16 + ... ~= 1.5 ]
		# 1 1/4 1/9
		# so overtones should have same power or less as fundamental tone*.5
		# (if fundamental frequency < 150Hz, fundamental frequency is given a bonus *= 15)
		# if not, an overtone note is also played.
		## find position of this overtone note (maximum?)
		## => subtract overtone note power from total power, divide by total power
		## => this is the percentage of power that belongs to this tone
		# so clip total power to fundamental_power * 1.5
		# upper_dependence is percentage of power not belonging to fundamental tone.
		# -> ALGORITHM:
		#	if fundamental_frequency<150Hz: fundamental_power *= 15
		#	alien_power = max(0, overtone_power - .5*fundamental_power)
		#	total power = overtone_power + fundamental_power
		#	upper_dependence = alien_power / total_power
		#
		#	( => upper_dependence = (overtone_power - .5*fundamental_power) / (overtone_power+fundamental_power) < 1 )

		# problem: if only one overtone exists, inharmonicity is 0 but this is not necessarily a note

		points = 0
		power = 0

		power = self.get_total_power_in_frequency_range(lower,upper,overtones)

		return points

gobject.type_register(VisualizerControl)
