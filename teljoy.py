#!/usr/bin/python -i

"""Crude command-line telescope control program.
   
   Imports the relevant modules, puts useful functions into the
   global namespace to use on the command line, starts the appropriate
   background threads (motion.TimeInt, dummycon.runtel and 
   detevent.DetermineEvent) and drops into an interactive Python prompt.
   
   The utils module contains functions that will probably only be used
   from the command line.
   
   Typical use:
     >>> reset(ra='12:34:56', dec='-32:00:00')   #Set initial position
     >>> s = Pos(ra='23:50:0', dec='-32:00:00')
     >>> jump(s)
     >>> jump('NGC 2997')
     >>>

   Hit 'c' then enter to see the current telescope state.
"""

import sys
import time
import signal
import atexit
import traceback

from globals import *
import usbcon
import motion
import detevent
from pdome import dome
from digio import press, release, cslew, cset
from utils import *
import tjserver

SIGNAL_HANDLERS = {}
CLEANUP_FUNCTION = None


def SignalHandler(signum=None,frame=None):
  """Called when a signal is received that would result in the programme exit, if the
     RegisterCleanup() function has been previously called to set the signal handlers and
     define an exit function using the 'atexit' module.

     Note that exit functions registered by atexit are NOT called when the programme exits due
     to a received signal, so we must trap signals where possible. The cleanup function will NOT
     be called when signal 9 (SIGKILL) is received, as this signal cannot be trapped.
  """
  logger.error("Signal %d received." % signum)
  sys.exit(-signum)    #Called by signal handler, so exit with a return code indicating the signal received


def RegisterCleanup(func):
  """Traps a number of signals that would result in the program exit, to make sure that the
     function 'func' is called before exit. The calling process must define its own cleanup
     function - typically this would shut down anything that needs to be stopped cleanly.

     We don't need to trap signal 2 (SIGINT), because this is internally handled by the python
     interpreter, generating a KeyboardInterrupt exception - if this causes the process to exit,
     the function registered by atexit.register() will be called automatically.
  """
  global SIGNAL_HANDLERS, CLEANUP_FUNCTION
  CLEANUP_FUNCTION = func
  for sig in [3,15]:
    SIGNAL_HANDLERS[sig] = signal.signal(sig,SignalHandler)   #Register a signal handler
  SIGNAL_HANDLERS[1] = signal.signal(1,signal.SIG_IGN)
  atexit.register(CLEANUP_FUNCTION)       #Register the passed CLEANUP_FUNCTION to be called on
  #  normal programme exit, with no arguments.


def cleanup():
  """Registers to be called just before exit by the exit handler.
     Waits for any hand paddle motion or slews to finish before exiting.
  """
  logger.info("Exiting teljoy.py program - here's why: %s" % traceback.print_exc())
  try:
    while motion.motors.Moving or motion.motors.Paddling:
      logger.info("Waiting for slew and hand paddle motion to finish")
      time.sleep(5)
  finally:
    detevent.eventloop.shutdown()
    motion.motors.Driver.host.shutdown()
    logger.info("Teljoy shut down.")


#Convenience functions for the dummy hand paddle mode - delete once testing is complete.
def n():
  release('S', paddle='C')
  press('N', paddle='C')

def s():
  release('N', paddle='C')
  press('S', paddle='C')

def r():
  release('N', paddle='C')
  release('S', paddle='C')

m = motion.motors
d = m.Driver

def i():
  print usbcon.binstring(d.inputs)

if __name__ == '__main__':
  RegisterCleanup(cleanup)
  motion.KickStart()
  detevent.init()
  current = detevent.current
  c = current
  tjserver.InitServer()

