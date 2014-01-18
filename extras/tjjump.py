#!/usr/bin/python

__author__ = 'andrew'

import sys

if (len(sys.argv) < 2) or sys.argv[1] in ["-h", "--h", "--help"]:
  print "Usage: %s <objectname>    or"
  print "       %s <ra> <dec>      or"
  print "       %s <ra> <dec> <epoch>"
  print
  print "If one argument is given, it's looked up (in the local database, "
  print "solar system ephemeris, and SIMBAD/NED/Vizier) and used as a target."
  print
  print "If two arguments are given, they are assumed to be RA and Dec, in "
  print "J2000 coordinates."
  print
  print "If three arguments are given, the first two are RA and Dec, the third"
  print "is the Epoch (strictly equinox) of the coordinates."
  print
  print "If you want spaces in an argument, enclose it in quotes."
  print
  print "Examples:"
  print "%s ngc104"
  print "%s 18:14:23 -27:43:22"
  print '%s "alpha cantaurus"'
  print '%s "12 34 56" "-43 21 09" 1950' % [sys.argv[0]]*7


import tjclient

errmsg = tjclient.Init()    # Returns an error message there was a problem connecting to a running copy of Teljoy.

if errmsg:
  sys.stderr.write(errmsg + '\n')
else:
  s = tjclient.status

  tjclient.jump(*sys.argv[1:])
