#!/usr/bin/env python

import numpy, pylab, sys
import peakdetect
import scipy.ndimage.filters

semitone_factor = 2**(1/12.)
tones=['a','ais (german b)','b (german h)','c','cis','d','dis','e','f','fis','g','gis']

def level_to_power(level):
	power = 10.0 ** (level/10.0)
	return power

def power_to_level(power):
	level = 10.0 * numpy.log10(power)
	return level

def get_tones(frq,power):
	maxtab,mintab = peakdetect.peakdet(power, .000005, frq)

	if len(maxtab)<2: return
#	print "max"
	for i in maxtab:
#		print i
		pylab.axvline(i[0])

	pylab.plot(frq, power)
#	pylab.show()

	ffrq_candidates = [i for i in maxtab]

	ffrq = []

	for f,p in ffrq_candidates:
#		print f,"could be fundamental frequency, checking..."
		# check if this is a overtone
		is_overtone=False
		for o in xrange(2,20):
			overtone_f = f/o
			lower = overtone_f / semitone_factor**.5
			upper = overtone_f * semitone_factor**.5
			for i in maxtab:
				if i[0]>lower and i[0]<upper and i[1]>p:
					is_overtone=True
					break
		if is_overtone:
#			print "is overtone."
			continue

		power_found=0
		for o in xrange(2,20):
			overtone_f = f*o
			lower = overtone_f / semitone_factor**.5
			upper = overtone_f * semitone_factor**.5
			for i in maxtab:
#				diff_in_semitones = numpy.log(i[0]/overtone_f)/numpy.log(semitone_factor)
				if i[0]>lower and i[0]<upper and i[1]<p:
#					print "found candidate for overtone",o,":",i[0],diff_in_semitones
					power_found += i[1]
#		print "power with overtones",power_found

	#	if power_found > 3.*p:
	#		print "excluded because overtones have much more power than fundamental frequency"
	#		continue

		power_total = p+power_found
#		if power_total>0.001:
		if True:
			ffrq.append((power_total,f))

	ffrq.sort(None,None,True)
	maximum=0
	try:
		maximum = ffrq[0][0]
	except:pass

	st = {}

	for p,f in ffrq:
		if p<maximum/4: continue
		semitone = numpy.log(f/440.)/numpy.log(semitone_factor)
		semitone = int(numpy.round(semitone))
		semitone12 = (semitone + 12*1000) % 12
		print "Power",p,"Frq",f,tones[semitone12],semitone
		st[semitone]=p

#	return ffrq
	return st

if __name__=="__main__":
	f = open("spectrumgriff2.txt")

	frq = []
	level = []

	for i in f:
		try:
			s = i.split()
			line_frq = float(s[0].replace(",","."))
			line_level = float(s[1].replace(",","."))
			frq.append(line_frq)
			level.append(line_level)
		except Exception,e:
			print >>sys.stderr, "Exception: ",e

	frq = numpy.array(frq)
	level = numpy.array(level)

	power = level_to_power(level)

	maxtab,mintab = peakdetect.mypeakdet(power, .000005, frq)

	for st in xrange(-29,8):
		f = semitone_factor**st * 440.
		pylab.axvline(f, color="k")

	print "max"
	for i in maxtab:
		print i
		pylab.axvline(i[0], color="r")

	maxf=scipy.ndimage.filters.maximum_filter(power,size=3)
	minf=scipy.ndimage.filters.minimum_filter(power,size=3)
	pylab.plot(frq,maxf, color='g')
	pylab.plot(frq,minf, color='g')
	pylab.plot(frq, numpy.logical_and(maxf==power, maxf-minf>0.0001), color='g')
#	print maxf==power 
#	print maxf-minf > 0.0001

	#print "min"
	#for i in mintab:
	#	print i
	#	pylab.axvline(i[0])

	ffrq_candidates = [i for i in maxtab]

	ffrq = []

	for f,p in ffrq_candidates:
		print 
		print f,"could be fundamental frequency, checking..."

		# check if this is a overtone
		is_overtone=False
		for o in xrange(2,20):
			overtone_f = f/o
			lower = overtone_f / semitone_factor**.5
			upper = overtone_f * semitone_factor**.5
			for i in maxtab:
				diff_in_semitones = numpy.log(i[0]/overtone_f)/numpy.log(semitone_factor)
				if i[0]>lower and i[0]<upper and i[1]>p:
					print "this is a overtone of",i[0],":",diff_in_semitones
					is_overtone=True
		if not is_overtone:
			print "it's no overtone -> fundamental frequency"
		else:
			print "it's a overtone -> exclude"
			continue

		power_found=0
		for o in xrange(2,20):
			overtone_f = f*o
			lower = overtone_f / semitone_factor**.5
			upper = overtone_f * semitone_factor**.5
			for i in maxtab:
				diff_in_semitones = numpy.log(i[0]/overtone_f)/numpy.log(semitone_factor)
				if i[0]>lower and i[0]<upper and i[1]<p:
					print "found candidate for overtone",o,":",i[0],diff_in_semitones
					power_found += i[1]
		print "power with overtones",power_found

	#	if power_found > 3.*p:
	#		print "excluded because overtones have much more power than fundamental frequency"
	#		continue

		ffrq.append((p+power_found,f))

	ffrq.sort()


	print
	print "=== result ==="
	for p,f in ffrq:
		if p>0.001:
			semitone = numpy.log(f/440.)/numpy.log(semitone_factor)
			semitone = (numpy.round(semitone) + 12*1000) % 12
			semitone = int(semitone)
			print "Power",p,"Frq",f,tones[semitone]

	pylab.plot(frq, power,color="b")
	pylab.show()
