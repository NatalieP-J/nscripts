#!/usr/bin/env python

"""
correlate - correlate Dragonfly images against Herschel images

Expects a particular file system set up for Dragonfly images: 
<parent directory>/<object name>/<subdirectory>/
This may be followed by further subdirectories by date, or contain the files
themselves.

Requires the following software: sextractor, astrometry.net
Requires the following packages: numpy, scipy, astropy, docopt, matplotlib, os
Requires the following files:    photometry.py, resconvolve.py, maskdata.py
                                 regrid.py, backgroundplane.py

Usage:
correlate [-hvlgpcrmbnqw] [-d DIRECTORY] [-u DIRECTORIES] [-o OBJECTNAMES] 
		[-s DIRECTORY] [-f FILEPATHS] [-x DIRECTORY] [-a DIRECTORY]

Options:
    -h, --help                        	Show this screen
    -v, --verbose                     	Print processing steps and extra 
                                      	information
    -l, --lowmemory                   	If True, use a version of regridding code
                                      	that does not require high memory usage

    -d DIRECTORY, --IOdir DIRECTORY   	Location of input files (parent directory)
                                      	[default: /mnt/gfsproject/naiad/njones/moddragonflydata/]
    -u LIST, --unmod LIST             	A list of subdirectories of --IOdir 
					  	                containing raw files and calibration frames
					  	                [default: /raw_lights/, /calframes/]
    -o OBJECTS, --objects OBJECTS     	Provide a list of object subdirectory 
                                      	names as a string
                                      	[default: PGM_1_2, spi1_1]
    -s DIRECTORY, --sub DIRECTORY     	Subdirectory containing flat-fielded and
                                      	dark subtracted images
                                      	[default: /NCalibrated/] 
    -f FILES, --filelist FILES        	Provide a list of file paths to process
                                      	as a string. If empty, processes all file
                                      	in input directory
                                      	[default: ]
    -x DIRECTORY, --cross DIRECTORY   	Location of files to correlate with
					  	                [default: ../herschel/]
    -a DIRECTORY, --apass DIRECTORY   	Location of APASS catalogues
                                      	[default: APASS/]
Testing Options:
    -g, --generate                    	If False, do not generate data from
                                      	any of the following substeps unless that
                                      	data is missing
                                      	If True, force all data to be generated
    -q, --calibrate				  	    If False, do not dark subtract and flat field 
                                        them unless files are missing
    -w, --astro 					  	If False, do not do astrometry and create 
					  	                object catalogue
    -p, --photometry                  	If False, do not perform photometry on an
                                      	image unless photometry data is missing
                                      	If True, force photometry to be done
    -c, --convolve                    	If False, do not convolve an image unless
                                      	convolved image missing
                                      	If True, force photometry to be done
    -r, --regrid                      	If False, do not regrid an image unless
                                      	regridded image is missing
                                      	If True, force regridding to be done
    -m, --mask                        	If False, do not mask an image unless
                                      	masked image is missing
                                      	If True, force masking to be done
    -b, --backsub                     	If False, do not background plane subtract
                                      	an image unless subtracted is missing
                                      	If True, force background plane 
                                      	subtraction to be done


"""

########################### CONSTANTS ############################

# specify herschel resolution at each wavelength
SPIRE = {'PSW':17.6,'PMW':23.9,'PLW':35.2}
spirekeys = SPIRE.keys()

# master dark location
damdir = '/dark_masters/'
# master flat location
flmdir = '/flat_masters/'
# dark subtracted files
dsmdir = '/dark_subtracted/'

# source extractor object maps
objdir = '/objects/'
# source extractor background maps
bakdir = '/background/'
# source extractor catalogue
catdir = '/catalogue/'

# OUTPUT DIRECTORIES
# location of helper plots from zero point magnitude calculations
magdir = '/magnitudecalcs/'
# location of photometered fits files
phodir = '/photometered/'
# location of regridded images
regdir = '/regrid/'
# location of background plane subtracted images
bsudir = '/backgroundsub/'
# location of correlation plots
cordir = '/correlations/'

########################### IMPORT BASE PACKAGES ############################

import os
import docopt
import numpy as np
nmax = np.max
nmin = np.min
from numpy import *
import matplotlib.pyplot as plt
from astropy.io import fits
from matplotlib.colors import LogNorm

########################### COMMAND LINE ARGUMENTS #############################

arguments = docopt.docopt(__doc__)

# Non-mandatory options without arguments

VERBOSE = arguments['--verbose']
LOWMEMORY = arguments['--lowmemory']

# Non-mandatory options with arguments

directory = arguments['--IOdir']
rawdirs = arguments['--unmod']
rawdir = rawdirs.split(', ')[0]
caldir = rawdirs.split(', ')[1]
subdir = arguments['--sub']
APASSdir = arguments['--apass']
files = arguments['--filelist']
filelist = files.split(', ')
if filelist != ['']:
	files = True
elif filelist == ['']:
	files = False
objects = arguments['--objects']
herdir = arguments['--cross']

# Testing options

GENERATE = arguments['--generate']
CALIBRATE = arguments['--calibrate']
ASTROMETRY = arguments['--astro']
PHOTOMETRY = arguments['--photometry']
CONVOLVE = arguments['--convolve']
REGRID = arguments['--regrid']
MASK = arguments['--mask']
BACKSUB = arguments['--backsub']

########################### IMPORT FUNCTIONS ############################

from photometry import *
from resconvolve import resconvolve
from maskdata import maskdata
from regrid import reshape
from backgroundplane import subBGplane

if LOWMEMORY:
	from regrid import regrid_lowmemory as regrid
elif not LOWMEMORY:
	from regrid import regrid


#################################### FUNCTIONS #################################

def fexists(fname):
	if os.path.isfile(fname) == True:
		return True
	elif os.path.isfile(fname) != True:
		return False

def getsubdir(directory):
	"""
	Gets all immediate subdirectories of directory

	directory:	path to directory

	Returns a list of subdirectories
	"""
	subdir=[name for name in os.listdir(directory)
			if os.path.isdir(os.path.join(directory, name))]
	subdir=['/'+name+'/' for name in subdir if '.' not in name]
	return subdir


def sexcall(f,di,odi,cdi,bdi):
	"""
	Run source extractor on f, producing a catalogue, and object and background maps

	f:		file name to run source extractor on
	di:		directory path to f
	odi:	directory to save object map in
	cdi:	directory to save catalogue in
	bdi:	directory to save background map in

	Returns nothing explicitly, but runs source extractor on the file
	"""
	# Split to make file name for catalogue, object map and background map filenames
	fname = f.split('.fits')[0]
    # Construct source extractor call
	objsexcall = 'sex -PARAMETERS_NAME photo.param -CATALOG_NAME '+cdi+fname+'.cat'
	objsexcall += ' -CHECKIMAGE_TYPE OBJECTS, BACKGROUND -CHECKIMAGE_NAME '+odi+fname
	objsexcall += '_objects.fits, '+bdi+fname+'_background.fits '+di+f
	os.system(objsexcall)

def hist2d(x,y,nbins,maskval = 0,saveloc = '',labels=[]):
	"""
	Creates a 2D histogram from data given by numpy's histogram

	x,y:		two 2D arrays to correlate, the second masked
	nbins:		number of bins
	maskval:	value that indicates masked areas
				(kwarg, default = 0)
	saveloc:	place to save histogram plot - if unspecified, do not
				save plot (kwarg, default = '')
	labels:		labels for histogram plot, with the following format
				[title,xlabel,ylabel,zlabel] - if unspecified, do 
				not label plot (kwarg, default = [])

	Returns the edges of the histogram bins and the 2D histogram

	"""
	# Remove NAN values
	a = where(isnan(x) == False)
	x = x[a]
	y = y[a]
	b = where(isnan(y) == False)
	x = x[b]
	y = y[b]
	# Remove masked areas
	c = where(y != maskval)
	x = x[c]
	y = y[c]
	# Create histogram
	H,xedges,yedges = histogram2d(x,y,bins=nbins)
	# Reorient appropriately
	H = rot90(H)
	H = flipud(H)
	# Mask zero value bins
	Hmasked = ma.masked_where(H==0,H)

	# Begin creating figure
	plt.figure(figsize=(12,10))
	# Use logscale
	plt.pcolormesh(xedges,yedges,Hmasked,
	               norm = LogNorm(vmin = Hmasked.min(),vmax = Hmasked.max()))
	cbar = plt.colorbar()
	# Add labels
	if labels != []:
	    title,xlabel,ylabel,zlabel = labels
	    plt.xlabel(xlabel)
	    plt.ylabel(ylabel)
	    plt.title(title)
	    cbar.ax.set_ylabel(zlabel)
	# Save plot
	if saveloc != '':
		plt.savefig(saveloc)
	plt.close()
	# Return histogram
	return xedges,yedges,Hmasked


######################### FIND FILES AND PREP FOR OUTPUT ######################
# if necessary, specify observation date subdirectory names for each object 
# in a dictionary
if files:
	fnames = []
	objectdates = {}
	datenames = {}
	objectherfiles = {}
	breakdown = filelist[0].split('/')
	fname = breakdown.pop(-1)
	date = breakdown.pop(-2)
	rawdir = breakdown.pop(-3)
	objects = breakdown.pop(-4)
	directory = '/'.join(breakdown)+'/'
	for f in filelist:
		breakdown = f.split('/')
		fname = breakdown.pop(-1)
		date = breakdown.pop(-2)
		newrawdir = breakdown.pop(-3)
		assert newrawdir == rawdir
		cloud = breakdown.pop(-4)
		newdirectory = '/'.join(breakdown)+'/'
		assert newdirectory == directory
		try:
			datenames[date].append(fname)
		except KeyError:
			datenames[date] = [fname]
		try:
			objectdates[cloud].append(date)
		except KeyError:
			objectdates[cloud] = [date]
		hdirec = herfir+'/'+cloud
		os.system('python rewriteherschel -d '+hdirec)
		herfiles = os.listdir(hdirec)
		objectherfiles[cloud] = [hdirec+'/'+i for i in herfiles if 'reindex' in i]


if not files:
	objectdates = {}
	datenames = {}
	objectherfiles = {}
	for cloud in objects:
		direc = directory+'/'+cloud+rawdir
		subdirs = getsubdir(direc)
		objectdates[cloud] = subdirs
		hdirec = herdir+'/'+cloud
		os.system('python rewriteherschel -d '+hdirec)
		herfiles = os.listdir(hdirec)
		objectherfiles[cloud] = [hdirec+'/'+i for i in herfiles if 'reindex' in i]
		for date in subdir:
			fnames = os.listdir(direc+'/'+date)
			datenames[date] = fnames

# if any of the output directories are missing, create them now
dirlist = [subdir,phodir,regdir,cordir,magdir,bsudir]
for d in dirlist:
    for key in keys:
        if os.path.isdir(directory+key+d) == False:
            os.system('mkdir '+directory+key+d)

################################ STEPS #####################################
keys = objectdates.keys()

for key in keys:
    print 'OBJECT '+key
    dates = objectdates[key]
    herfiles = objectherfiles[key]
    for date in dates:
        print 'DATE '+date

################################ CALIBRATE #####################################
        if GENERATE == True:
        	os.system('./calibratedata.sh {0} {1} {2} {3} {4} {5} {6} {7} {8}'.format(directory,key,date,caldir,rawdir,damdir,flmdir,dsmdir,subdir))
        # Directory containing raw image files
        di = directory+key+rawdir+date+'/'
        # Directory containing dark subtracted and flat fielded files
        ddi = directory+key+subdir+date+'/'
        # Directory containing source extractor object maps
        odi = directory+key+objdir+date+'/'
        # Directory containing source extractor catalogues
        cdi = directory+key+catdir+date+'/'
        # Directory containing source extractor background maps
        bdi = directory+key+bakdir+date+'/'
        # Directory containing photometered images
        pdi = directory+key+phodir+date+'/'
        # Directory containing regridded images
        rdi = directory+key+regdir+date+'/'
        # Directory containing masked images
        mdi = directory+key+magdir+date+'/'
        # Directory containing background subtracted images
        gdi = directory+key+bsudir+date+'/'
        # Directory containing correlation plots
        sdi = directory+key+cordir+date+'/'
        # Create output directories if any are missing
        dis = [odi,cdi,bdi,pdi,rdi,mdi,gdi,sdi]
        for d in dis:
            if os.path.isdir(d) == False:
                os.system('mkdir '+d)
        files = datenames[date]

################################ CYCLE FILES #####################################
        for f in files:
            print 'FILE '+ddi+f
            f = f.split('.fits')[0]+'_ds_ff.fits'
            # Confirm calibrated file exists
            assert os.path.isfile(ddi+f) == True
            spl = f.split('.fits')[0]

################################ ASTROMETRY #####################################
            if GENERATE==True or ASTROMETRY==True:
            	callastrometry(ddi+f,generate=True)
            else:
            	callastrometry(di+f)

################################ SEXTRACTOR #####################################
            if GENERATE==True or os.path.isfile(cdi+spl+'.cat')==False or os.path.isfile(odi+spl+'_objects.fits')==False or os.path.isfile(bdi+fname+'_background.fits')==False:
            	sexcall(f,ddi,odi,cdi,bdi)

################################ IMAGE PROPERTIES #####################################
            # Read in ds-ff data from file
            dflyimage = fits.open(di+f)
            dflydata = dflyimage[0].data
            dflyheader = dflyimage[0].header
            dflyimage.close()
            # Load catalogue data to find FWHM information
            catdata = loadtxt(cdi+spl+'.cat')
            # Find pixel scale from astrometry info
            pscalx = dflyheader['PSCALX']
            pscaly = dflyheader['PSCALY']
            pixscale = (pscalx+pscaly)/2.
            # Select for unflagged entries
            cheader = catheader(cdi+spl+'.cat')
            catdata = catdata[where(catdata[:,catheader['FLAGS']] == 0)]
            # Find the average FWHM and convert to arcseconds
            pfwhm = mean(catdata[:,catheader['FWHM_IMAGE']])
            dflybeam = pfwhm*pixscale
            # Add FWHM to header
            dflyheader['FWHM'] = (dflybeam, 'arcseconds')
            fits.writeto(ddi+f,dflyimage,dflyheader,clobber=True)
            # If polarization data, skip
            if dflyheader['FILTNAM'] == 'Pol':
                print 'Skipping polarization data'
                continue  

################################ PHOTOMETRY #####################################            
            # Choose photometered file name
            pname = spl+'_photo.fits'
            # Choose output location for photometry related plots
            outplots = mdi+spl
            # Run photometry
           	if os.path.isfile(pdi+pname) != True or GENERATE == True or PHOTOMETRY == True:
				pdata,dflyheader,zp = photometry(di+f,cdi+spl+'.cat',APASSdir,pdi+pname,
                                             	create = True,plot = outplots)
            elif os.path.isfile(pdi+pname) == True and GENERATE == False and PHOTOMETRY == False:
                pdata,dflyheader = fits.getdata(pdi+pname,header=True)
                zp = dflyheader['M0']
            # If photometry failed, quit
            if zp == 'N/A':
            	print 'Photometry failed, skipping file'
            	continue
            # Convert units in object and background map
            convert = dflyheader['kJpADU']
            pstar = fits.getdata(odi+spl+'_objects.fits')*convert
            pback = fits.getdata(bdi+spl+'_background.fits')*convert
            fits.writeto(odi+spl+'_photo_objects.fits',pstar,dflyheader)
            fits.writeto(bdi+spl+'_photo_background.fits',pback,dflyheader)
            
################################ CYCLE CORRELTION-FILES #########################
            for hfile in herfiles:
            	skey = [i for in in spirekeys if i in hfile][0]
                herbeam = SPIRE[skey]

################################ CONVOLUTION #####################################
                # Create output file names
                pspl = pname.split('.fits')[0]
                cname = pspl+'_convto'+str(herbeam)+'.fits'
                ocname = pspl+'_convto'+str(herbeam)+'_objects.fits'
                # Do convolution on sky image
                if os.path.isfile(pdi+cname) == True and GENERATE == False and CONVOLVE == False:
                    cdata,dflyheader = fits.getdata(pdi+cname,header=True)
                elif os.path.isfile(pdi+cname) != True or GENERATE == True or CONVOLVE == True:
                    cdata,dflyheader = resconvolve(pdi+pname,dflybeam,herbeam,
                                                   outfile = pdi+cname,
                                                   header = dflyheader)
                # Do convolution on object map
                if os.path.isfile(odi+ocname) == True and GENERATE == False and CONVOLVE == False:
                    ocdata,oheader = fits.getdata(odi+ocname,header=True)
                elif os.path.isfile(odi+ocname) != True or GENERATE == True or CONVOLVE == True:
                    ocdata,oheader = resconvolve(odi+spl+'_photo_objects.fits',
                    						     dflybeam,herbeam,
                                                 outfile = odi+ocname,
                                                 header = dflyheader)
                if dflyheader == 0:
                    print 'Convolution failed, skipping file'
                    continue

################################ MASK #####################################
                # Set cutoff for mask
                cutoff = 10*median(ocdata)
                # Create mask name
                mspl = cname.split('.fits')[0]
                mname = mspl+'_mask.fits'

                # Mask data
                if os.path.isfile(pdi+mname) == True and GENERATE == False and MASK == False:
                    mdata,dflyheader = fits.getdata(pdi+mname,header=True)
                    target = fits.getdata(hername)
                if os.path.isfile(pdi+mname) != True or GENERATE == True or MASK == True or dflyheader['MASKCUT'] - cutoff > 1e-3:
                    cdata,target = regrid(pdi+cname,hername)
                    ocdata,target = regrid(odi+ocname,hername)
                    mdata,dflyheader = maskdata(cdata,ocdata,cutoff,
                                                outfile = pdi+mname,
                                                header = dflyheader)

################################ RESHAPE #####################################                
                mspl = mname.split('.fits')[0]
                ress = sqrt((dflybeam/s2f)**2+(herbeam/s2f)**2)
                r = reshape(mdata,mdata,2*ress)
                t = reshape(target,mdata,2*ress)

################################ REGRID #####################################
                rname = mspl+'_regrid.fits'
                hname = hername.split('.fits')[0]
                hname = hname+'_reshaped.fits'
                fits.writeto(rdi+rname,r,dflyheader,clobber=True)

################################ BACK-SUB #####################################
                rspl = rname.split('.fits')[0]
                bname = rspl+'_backsub.fits'
                p0 = [2,1,1,1]
                newr,bg = subBGplane(r,t,p0)
                if isinstance(newr,float) != True:
                    dflyheader['BACKSUB'] = 'TRUE'
                    fits.writeto(gdi+bname,newr,dflyheader,clobber=True)
                    fits.writeto(bdi+spl+'_bgplane.fits',bg,dflyheader,clobber=True)
                    bspl = bname.split('.fits')[0]
                    saveloc = sdi+bspl+'_'+skey+'.png'
                    title = 'Correlation between Dragonfly and Herschel'
                    xlabel = 'Herschel [MJy/sr]'
                    ylabel = 'Dragonfly [kJy/sr]'
                    zlabel = 'Pixels'
                    labels = [title,xlabel,ylabel,zlabel]
                    pos = where(r > 0)
                    H = hist2d(t[pos],newr[pos],50,saveloc,labels = labels)
                elif isinstance(newr,float) == True:
                    print 'Failed background subtraction'
                    continue
                #fits.writeto(hname,t,clobber=True)
