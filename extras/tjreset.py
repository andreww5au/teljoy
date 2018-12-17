#!/usr/bin/python

__author__ = 'andrew'

"""
  Resets the telescope coordinates to the specified object or position.

  If one argument is given, it's assumed to be an object name. It's
  looked up (in the local database, solar system ephemeris, and
  SIMBAD/NED/Vizier online) and used as the current coordinates.

  If two arguments are given, they are assumed to be RA and Dec, in
  J2000 coordinates.

  If three arguments are given, the first two are RA and Dec, the third
  is the Epoch (strictly equinox) of the coordinates.

  If you want spaces in an argument, enclose it in quotes.

"""

import sys
import Pyro4

import tjclient

if __name__ == '__main__':
  if (len(sys.argv) < 2) or sys.argv[1] in ["-h", "--h", "--help"]:
    print "Usage: %s <objectname>    or" % sys.argv[0]
    print "       %s <ra> <dec>      or" % sys.argv[0]
    print "       %s <ra> <dec> <epoch>" % sys.argv[0]
    print
    print "Resets the telescope coordinates to the specified object or position."
    print
    print "If one argument is given, it's assumed to be an object name. It's"
    print "looked up (in the local database, solar system ephemeris, and "
    print "SIMBAD/NED/Vizier online) and used as the current coordinates."
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
    print "%s ngc104"  % sys.argv[0]
    print "%s 18:14:23 -27:43:22" % sys.argv[0]
    print '%s "alpha cantaurus"' % sys.argv[0]
    print '%s "12 34 56" "-43 21 09" 1950' % sys.argv[0]
    sys.exit()

  errmsg = tjclient.Init()    # Returns an error message there was a problem connecting to a running copy of Teljoy.

  if errmsg:
    sys.stderr.write(errmsg + '\n')
  else:
    s = tjclient.status

    try:
      print tjclient.reset(*sys.argv[1:])
    except:
      print "".join(Pyro4.util.getPyroTraceback())
