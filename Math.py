#!/usr/bin/env python

import numpy

REFERENCE_FREQUENCY = 440
note_names = ["a","ais","b","c","cis","d","dis","e","f","fis","g","gis"]

def note_name(semitone):
	semitone = int(round(semitone))

	if semitone<0:
		semitone += abs(semitone/12)*12

	assert not semitone<0

	semitone %= 12

	return note_names[semitone]

def power_to_magnitude(power, threshold=-60):
	magnitudes = numpy.maximum(threshold, 10.0*numpy.log10(power))
	return magnitudes

def magnitude_to_power(magnitude):
	power = 10.0**(magnitude/10.0)
	return power

def frequency_to_semitone(frequency):
	semitone = 12.*numpy.log2(frequency/REFERENCE_FREQUENCY)
	return semitone

def semitone_to_frequency(semitone):
	frequency = REFERENCE_FREQUENCY * (2.**(1./12.))**semitone
	return frequency

def windowed_fft(data):
	# apply window
	window = numpy.hamming(len(data))
	data *= window

	# fft
	power = numpy.abs(numpy.fft.rfft(data))**2. / len(data)**2.

	return power
