#!/usr/bin/python -i

"""Crude command-line telescope control program.
   
   Imports the relevant modules, puts useful functions into the
   global namespace to use on the command line, starts the appropriate
   background threads (motion.TimeInt, dummycon.runtel and 
   detevent.DetermineEvent) and drops into an interactive Python prompt.
   
   The utils module contains functions that will probably only be used
   from the command line.
   
   Typical use:
     >>> Reset(ra='12:34:56', dec='-32:00:00')   #Set initial position
     >>> p = Pos(ra='23:50:0', dec='-32:00:00')
     >>> Jump(p)
     >>> g = GetRC3('NGC 2997')
     >>> Jump(g)
     >>> press('N','C')    #Press the N button on the coarse paddle
     >>> release()         #release the last button press
     >>> cslew()           #Change the coarse paddle speed to 'slew' (default is 'cset()')
     >>> press('S','C')    #Press the S button
     >>> release()
     >>>

   Run telclient.py in another window to see the current telescope state,
   updated every second.
"""

from globals import *
from correct import CalcPosition as Pos

import motion
import detevent
from pdome import dome
from sqlint import GetRC3, GetObject
from detevent import Jump
from digio import press, release, cslew, cset
from utils import *


def n():
  release('S', paddle='C')
  press('N', paddle='C')

def s():
  release('N', paddle='C')
  press('S', paddle='C')

def r():
  release('N', paddle='C')
  release('S', paddle='C')

if __name__ == '__main__':
  motion.KickStart()
  detevent.init()
  Current = detevent.Current


