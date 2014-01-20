#!/usr/bin/python

__author__ = 'andrew'

import sys
import Pyro4

if (len(sys.argv) < 2) or sys.argv[1] in ["-h", "--h", "--help"]:
  print "Usage: %s <action>" % sys.argv[0]
  print
  print "Turns the autoguide mode on or off, depending on the argument"
  print "If the argument is '1', 'on', 'ON', 'y', etc, turn autoguiding on."
  print "If the argument is '0', 'off', 'OFF', 'n', etc, turn autoguiding off."
  print 
  sys.exit()


import tjclient

errmsg = tjclient.Init()    # Returns an error message there was a problem connecting to a running copy of Teljoy.

if errmsg:
  sys.stderr.write(errmsg + '\n')
else:
  s = tjclient.status

  arg = sys.argv[1]
  if arg.strip().lower() in ['1', 'on', 'y', 'yes']:
    on = True
  elif arg.strip().lower() in ['0', 'off', 'n', 'no']:
    on = False
  else:
    print "Unknown argument: %s" % arg
    sys.exit()

  try:
    print tjclient.autoguide(on)
  except:
    print "Error communicating with Teljoy:"
    print "".join(Pyro4.util.getPyroTraceback())
