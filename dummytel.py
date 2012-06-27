#!/usr/bin/python

"""Client to monitor and display the state of the low-level dummy telescope controller.
   If dummycon.runtel isn't running, the updates will be paused until it (re)starts.
   
   Note that while the RA and DEC axes are displayed in hours/degrees, minutes and seconds,
   they are really just representations of the acumulated travel distance in each axis,
   in steps, since the runtel function was started. As such, they always count from zero
   when runtel is started, and will never reflect the actual RA and DEC values.
   
"""

import cPickle
import time

from globals import *
import dummycon

print __doc__

lasttime = 0

if __name__ == '__main__':
  while True:
    f = open('/tmp/dummy.status','r')
    s = cPickle.load(f)
    if s.savetime > lasttime:
      print s
      lasttime = s.savetime
    time.sleep(1)
