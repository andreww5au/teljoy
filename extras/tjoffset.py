#!/usr/bin/python

__author__ = 'andrew'

"""
  Given a pair of offsets in arcseconds (of plate scale east and
  west on the sky, not RA and DEC coordinates), shift the
  telescope by that small amount.

  Offsets are positive for East and North, Negative for West and South.

  Note that near the pole, a small offset in plate scale E/W
  can translate to a very large difference in the RA coordinate

"""

import sys
import Pyro4

if (len(sys.argv) < 3) or sys.argv[1] in ["-h", "--h", "--help"]:
  print "Usage: %s <EWoffset> <NSoffset>" % sys.argv[0]
  print
  print "Given a pair of offsets in arcseconds (of plate scale east and "
  print "west on the sky, not RA and DEC coordinates), shift the "
  print "telescope by that small amount."
  print 
  print "Offsets are positive for East and North, Negative for West and South."
  print
  print "Note that near the pole, a small offset in plate scale E/W "
  print "can translate to a very large difference in the RA coordinate."
  print 
  print "Examples:"
  print "%s 12.34 134.5"  % sys.argv[0]
  print "%s 203 12" % sys.argv[0]
  sys.exit()


import tjclient

errmsg = tjclient.Init()    # Returns an error message there was a problem connecting to a running copy of Teljoy.

if errmsg:
  sys.stderr.write(errmsg + '\n')
else:
  s = tjclient.status

  try:
    ew = float(sys.argv[1])
    ns = float(sys.argv[2])
  except ValueError:
    print "Arguments must be numbers - offsets in arcseconds."
    sys.exit()

  try:
    print tjclient.offset(ew,ns)
  except:
    print "Error communicating with Teljoy:"
    print "".join(Pyro4.util.getPyroTraceback())
