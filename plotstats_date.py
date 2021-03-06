import numpy as np
from numpy import *
import matplotlib.pyplot as plt
plt.ion()

outlierremove = True

stats = loadtxt('stats/stats.txt',dtype = 'str')

objects = stats[:,0]
times = stats[:,1].astype(float)
serials = stats[:,2]
colours = stats[:,3]
expns = stats[:,4]
altitudes = stats[:,5].astype(float)
airmasses = stats[:,6].astype(float)
m0s = stats[:,7].astype(float)
fwhms = stats[:,8].astype(float)
dates = stats[:,9]
slopes = stats[:,10].astype(float)
fslopes = stats[:,11].astype(float)
freqs = stats[:,12].astype(float)

order = times.argsort()
objects = objects[order]
times = times[order]
serials = serials[order]
colours = colours[order]
expns = expns[order]
altitudes = altitudes[order]
airmasses = airmasses[order]
m0s = m0s[order]
fwhms = fwhms[order]
dates = dates[order]
slopes = slopes[order]
fslopes = fslopes[order]
freqs = freqs[order]

spi = where(objects == 'spi1_1')
dra = where(objects == 'PGM_1_2')

inds = {}
inds['spi'] = spi
inds['dra'] = dra

names = {}
names['spi'] = 'Spider'
names['dra'] = 'Draco'

figinds = {}
figinds['spi'] = 0
figinds['dra'] = 7

reds = ['r','lightcoral','darkred','darkorange','indianred']
greens = ['g','lime','darkgreen','darkseagreen','greenyellow']

for key in names.keys():
	k = 0
	if key == 'dra':
		uplim = 6
		daydiv = 0.1
	if key == 'spi':
		uplim = 7
		daydiv = 0.05
	colors = plt.get_cmap('cool')(linspace(0, 1.0, uplim))
	serial = serials[inds[key]]
	colour = colours[inds[key]]
	m0 = m0s[inds[key]]
	am = airmasses[inds[key]]
	fwhm = fwhms[inds[key]]
	time = times[inds[key]]
	time -= np.min(time)
	date = dates[inds[key]]
	expn = expns[inds[key]]
	slope = slopes[inds[key]]
	fslope = fslopes[inds[key]]
	freq = freqs[inds[key]]
	diff = abs(roll(time,1)-time)
	transition = where(diff > 0.1)
	transition = delete(transition, 0)
	daysplits = []
	for t in transition:
		indstochange = arange(t,len(time))
		for j in indstochange:
			time[j] -= diff[t]
			time[j] += daydiv
		try:
			daysplits.append(0.5*(time[t]-time[t-1])+time[t-1])
		except IndexError:
			continue
	if outlierremove:
		good = where((fwhm < 30) & (m0 > 26.5))
		serial = serial[good]
		colour = colour[good]
		m0 = m0[good]
		am = am[good]
		fwhm = fwhm[good]
		time = time[good]
		expn = expn[good]
		date = date[good]
		slope = slope[good]
		freq = freq[good]
		fslope = fslope[good]
	ds = unique(date)
	cams = unique(serial)
	cr = 0
	cg = 0
	plt.figure(1+figinds[key],figsize = (10,8))
	plt.title(names[key])
	plt.xlabel('Time')
	plt.ylabel('$m_0$',fontsize = 20)
	plt.figure(2+figinds[key],figsize = (10,8))
	plt.title(names[key])
	plt.xlabel('Time')
	plt.ylabel('FWHM ["]')
	plt.figure(3+figinds[key],figsize = (10,8))
	plt.title(names[key])
	plt.xlabel('FWHM ["]')
	plt.ylabel('$m_0$',fontsize = 20)	
	plt.figure(4+figinds[key],figsize = (10,8))
	plt.title(names[key])	
	plt.xlabel('Airmass')
	plt.ylabel('FWHM ["]')	
	plt.figure(5+figinds[key],figsize = (10,8))
	plt.title(names[key])	
	plt.xlabel('Airmass')
	plt.ylabel('$m_0$',fontsize = 20)
	plt.figure(6+figinds[key],figsize = (10,8))
	plt.title(names[key])	
	plt.xlabel('Time')
	plt.ylabel('Slope')
	plt.figure(7+figinds[key],figsize = (10,8))
	plt.title(names[key])
	plt.xlabel(r'$\nu [GHz]$',fontsize = 20)
	plt.ylabel(r'$\nu|_{\nu} W m^{-2} sr^{-1}$',fontsize = 20)
	for d in ds:
		potinds = where(date==d)
		expntemp = expn[potinds]
		m0temp = m0[potinds]
		timetemp = time[potinds]
		fwhmtemp = fwhm[potinds]
		amtemp = am[potinds]
		serialtemp = serial[potinds]
		slopetemp = slope[potinds]
		freqtemp = freq[potinds]
		num = unique(expntemp)
		plt.figure(1+figinds[key])
		plt.plot(timetemp,m0temp,color = colors[k],linewidth = 3)
		plt.figure(2+figinds[key])
		plt.plot(timetemp,fwhmtemp,color = colors[k],linewidth = 3)
		plt.figure(3+figinds[key])
		plt.plot(fwhmtemp,m0temp,color = colors[k],linewidth = 3)
		plt.figure(4+figinds[key])
		plt.plot(amtemp,fwhmtemp,color = colors[k],linewidth = 3)
		plt.figure(5+figinds[key])
		plt.plot(amtemp,m0temp,color = colors[k],linewidth = 3)
		plt.figure(6+figinds[key])
		plt.plot(timetemp,slopetemp,color = colors[k],linewidth = 3)
		k+=1
	for cam in cams:
		i = where(cam == serial)
		c = colour[i][0]
		if c == 'SloanG':
			color = greens[cg]
			cg += 1
		elif c == 'SloanR':
			color = reds[cr]
			cr += 1
		plt.figure(1+figinds[key])
		plt.plot(time[i],m0[i],'o',color = color,markersize = 10,label = cam)
		plt.figure(2+figinds[key])
		plt.plot(time[i],fwhm[i],'o',color = color,markersize = 10,label = cam)
		plt.figure(3+figinds[key])
		plt.plot(fwhm[i],m0[i],'o',color = color,markersize = 10,label = cam)
		plt.figure(4+figinds[key])
		plt.plot(am[i],fwhm[i],'o',color = color,markersize = 10,label = cam)
		plt.figure(5+figinds[key])
		plt.plot(am[i],m0[i],'o',color = color,markersize = 10,label = cam)
		plt.figure(6+figinds[key])
		plt.plot(time[i],slope[i],'o',color = color, markersize = 10,label = cam)
		plt.figure(7+figinds[key])
		plt.loglog(freq[i],fslope[i],'o',color = color, markersize = 10,label = cam)
	for day in daysplits:
		plt.figure(1+figinds[key])
		plt.axvline(day,color='k',linewidth = 4)
		plt.figure(2+figinds[key])
		plt.axvline(day,color='k',linewidth = 4)
		plt.figure(6+figinds[key])
		plt.axvline(day,color='k',linewidth = 4)
	plt.figure(1+figinds[key])
	plt.legend(loc = 'best',fontsize = 10)
	if not outlierremove:
		plt.savefig('datestats/{0}_m0_time.png'.format(names[key]))
	if outlierremove:
		plt.savefig('datestats/no_out_{0}_m0_time.png'.format(names[key]))
	plt.figure(2+figinds[key])
	plt.legend(loc = 'best',fontsize = 10)
	if not outlierremove:
		plt.savefig('datestats/{0}_FWHM_time.png'.format(names[key]))
	if outlierremove:
		plt.savefig('datestats/no_out_{0}_FWHM_time.png'.format(names[key]))
	plt.figure(3+figinds[key])
	plt.legend(loc = 'best',fontsize = 10)
	if not outlierremove:
		plt.savefig('datestats/{0}_FWHM_m0.png'.format(names[key]))
	if outlierremove:
		plt.savefig('datestats/no_out_{0}_FWHM_m0.png'.format(names[key]))
	plt.figure(4+figinds[key])
	plt.legend(loc = 'best',fontsize = 10)
	if not outlierremove:
		plt.savefig('datestats/{0}_airmass_FWHM.png'.format(names[key]))
	if outlierremove:
		plt.savefig('datestats/no_out_{0}_airmass_FWHM.png'.format(names[key]))
	plt.figure(5+figinds[key])
	plt.legend(loc = 'best',fontsize = 10)
	if not outlierremove:
		plt.savefig('datestats/{0}_airmass_m0.png'.format(names[key]))
	if outlierremove:
		plt.savefig('datestats/no_out_{0}_airmass_m0.png'.format(names[key]))
	plt.figure(6+figinds[key])
	plt.legend(loc = 'best',fontsize = 10)
	if not outlierremove:
		plt.savefig('datestats/{0}_slope_time.png'.format(names[key]))
	if outlierremove:
		plt.savefig('datestats/no_out_{0}_slope_time.png'.format(names[key]))
	plt.figure(7+figinds[key])
	plt.xlim(1e2,1e7)
	plt.ylim(1e-10,1e-6)
	plt.legend(loc = 'best',fontsize = 10)
	if not outlierremove:
		plt.savefig('datestats/{0}_fslope.png'.format(names[key]))
	if outlierremove:
		plt.savefig('datestats/no_out_{0}_fslope.png'.format(names[key]))
