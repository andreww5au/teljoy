#!/usr/bin/python

__author__ = 'andrew'

import sys

import tjclient

errmsg = tjclient.Init()    # Returns an error message there was a problem connecting to a running copy of Teljoy.

if errmsg:
  sys.stderr.write(errmsg + '\n')
else:
  s = tjclient.status
  if not s.current.posviolate:    # Original RA and Dec to standard epoch are valid
    print "RA:      %14.11f" % (s.current.Ra/15/3600,)   # RA stored in arcseconds, convert to hours
    print "DEC:     %14.11f" % (s.current.Dec/3600)      # Convert form arcseconds to degrees
    print "EPOCH:   %8.3f" % (s.current.Epoch)           # eg, 2000.0
  else:       # The hand-paddle has been used, or the telescope has been frozen or switched off since the last
              # jump or reset to coordinates with a valid, standard epoch.
    print "RA:      %14.11f" % (s.current.RaC/15/3600,)   # RA stored in arcseconds, convert to hours
    print "DEC:     %14.11f" % (s.current.DecC/3600,)     # Convert form arcseconds to degrees
    print "EPOCH:   0.0"                                  # Here, Epoch=0 means 'Epoch of Date', ie 'now'.

  print "ALT:     %4.1f" % (s.current.Alt,)
  print "AZI:     %5.1f" % (s.current.Azi,)
  print "LST:     %14.11f" % (s.current.Time.LST,)
  print "DomeAzi: %3d" % (s.dome.DomeAzi,)
  flags = []
  if s.current.posviolate:
    flags.append('PosViolate')
  if s.motors.Moving:
    if s.motors.Jumping:
      flags.append('Moving(Jump)')
    elif s.motors.Paddling:
      flags.append('Moving(Paddles)')
    else:
      flags.append('Moving(?)')
  if s.prefs.EastOfPier:
    flags.append('EastOfPier')
  if s.dome.DomeInUse:
    flags.append('DomeInUse')
  if s.dome.DomeTracking:
    flags.append('DomeTracking')
  if s.motors.Frozen:
    flags.append('Frozen')
  print "Flags:   %s" % (', '.join(flags))
  if s.limits.HWLimit:
    limits = []
    if s.limits.PowerOff:
      limits.append("PowerOff")
    else:
      if s.limits.EastLim:
        limits.append('EAST')
      if s.limits.WestLim:
        limits.append('WEST')
      if s.limits.HorizLim:
        limits.append('HORIZON')
      if s.limits.MeshLim:
        limits.append('MESH')
    print "Limits:  HW Limit ACTIVE: [%s]" % (', '.join(limits),)
  else:
    print "Limits:"
  print "UT:      %s" % (s.current.Time.UT,)

