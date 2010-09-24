
### http://gist.github.com/250860

import sys
from numpy import NaN, Inf, arange, isscalar, asarray

import numpy
import scipy.ndimage

def find_peaks(frq,power,max_window=3,min_window=3,height=0.0001):
#	delta_frq = frq[1]-frq[0]
#	delta_ind = fwhm/delta_frq
#	maximum_filter(power,size=delta_ind)
	max_filtered = scipy.ndimage.maximum_filter1d(power,size=max_window)
	min_filtered = scipy.ndimage.minimum_filter1d(power,size=min_window)
	maxima = numpy.logical_and(max_filtered==power, max_filtered-min_filtered>height)
	maxima_indices = numpy.nonzero(maxima)[0]
	return maxima_indices

def mypeakdet(v,delta,x):
	ind=find_peaks(x,v,3,3,delta)
	print "ind",
	return [(x[i],v[i]) for i in ind], []

def peakdet(v, delta, x = None):
    """
    Converted from MATLAB script at http://billauer.co.il/peakdet.html
    
    Currently returns two lists of tuples, but maybe arrays would be better
    
    function [maxtab, mintab]=peakdet(v, delta, x)
    %PEAKDET Detect peaks in a vector
    %        [MAXTAB, MINTAB] = PEAKDET(V, DELTA) finds the local
    %        maxima and minima ("peaks") in the vector V.
    %        MAXTAB and MINTAB consists of two columns. Column 1
    %        contains indices in V, and column 2 the found values.
    %      
    %        With [MAXTAB, MINTAB] = PEAKDET(V, DELTA, X) the indices
    %        in MAXTAB and MINTAB are replaced with the corresponding
    %        X-values.
    %
    %        A point is considered a maximum peak if it has the maximal
    %        value, and was preceded (to the left) by a value lower by
    %        DELTA.
    
    % Eli Billauer, 3.4.05 (Explicitly not copyrighted).
    % This function is released to the public domain; Any use is allowed.
    
    """
    maxtab = []
    mintab = []
       
    if x is None:
        x = arange(len(v))
    
    v = asarray(v)
    
    if len(v) != len(x):
        sys.exit('Input vectors v and x must have same length')
    
    if not isscalar(delta):
        sys.exit('Input argument delta must be a scalar')
    
    if delta <= 0:
        sys.exit('Input argument delta must be positive')
    
    mn, mx = Inf, -Inf
    mnpos, mxpos = NaN, NaN
    
    lookformax = True
    
    for i in arange(len(v)):
        this = v[i]
        if this > mx:
            mx = this
            mxpos = x[i]
        if this < mn:
            mn = this
            mnpos = x[i]
        
        if lookformax:
            if this < mx-delta:
                maxtab.append((mxpos, mx))
                mn = this
                mnpos = x[i]
                lookformax = False
        else:
            if this > mn+delta:
                mintab.append((mnpos, mn))
                mx = this
                mxpos = x[i]
                lookformax = True

    return maxtab, mintab
