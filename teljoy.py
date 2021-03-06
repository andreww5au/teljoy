#!/usr/bin/python -i

"""Telescope control software using a 'velocity streaming' controller, where every frame
   (typically 50ms) a pair of integers are read by the control hardware, and the control hardware
   generates exactly that many motor steps over the next 50ms.

   This file is the main executable. It mports the relevant modules, puts
   useful functions into the global namespace to use on the command line, starts
   the appropriate background threads and drops into an interactive Python prompt. Signal
   handlers and cleanup functions are also set up, to shut down the motor controller cleanly
   when teljoy exits (either intentionally or unintentionally).

   All user control of the telescope is by typing functions at the Python command prompt,
   like 'jump()', 'reset()', etc.
   
   Most of the functions designed to be called directly by the user are in the 'utils.py' module.
   
   Typical use:
     >>> reset(ra='12:34:56', dec='-32:00:00')   #Set initial position
     >>> s = Pos(ra='23:50:0', dec='-32:00:00')
     >>> jump(s)
     >>> jump('NGC 2997')
     >>>

   Hit 'c' then enter to see the current telescope state.
"""

import libusb1
import sys
import time
import signal
import atexit
import traceback

from globals import *
import usbcon
import digio

if __name__ == '__main__':
  logger.info('* Resetting controller hardware with hardware_reset()')
  try:
    instance = usbcon.controller.Controller(None)
  except libusb1.USBError:
    logger.critical("Can't open USB device for telescope controller. Make sure that the controller " +
                    "is plugged in, and that there isn't another copy of teljoy running.")
    sys.exit(-1)
  instance.hardware_reset()
  time.sleep(0.5)
  del instance
  time.sleep(0.5)

import motion
import detevent
if SITE == 'PERTH':
  from pdome import dome
elif SITE == 'NZ':
  from nzdome import dome
#from digio import press, release, cslew, cset
from utils import *
import tjserver
if SITE == 'PERTH':
  import weather
import pyephem

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
    digio.DomeStop()
    while motion.motors.Moving or motion.motors.Paddling:
      logger.info("Waiting for slew and hand paddle motion to finish")
      time.sleep(5)
  finally:
    detevent.fastloop.shutdown()
    detevent.slowloop.shutdown()
    motion.motors.Driver.shutdown()
    detevent.fastthread.join()
    detevent.slowthread.join()
    time.sleep(1)
    logger.info("Teljoy shut down.")


def _safety_shutdown():
  """Called when the safety interlock is active. Save the dome and 'frozen' states, freeze the
     telescope and close the dome.
  """
  global LastDome, LastFrozen
  if LastDome is not None or LastFrozen is not None:
    logger.error("safety_shutdown called while the system is already shut down!")
  logger.info('Safety shutdown - freezing telescope')
  LastFrozen = motion.motors.Frozen
  freeze(force=True)
  logger.info('Safety shutdown - closing dome shutter')
  LastDome = dome.IsShutterOpen
  dome.close(force=True)


def _safety_startup():
  """Called when the safety interlock system has the last safety tag removed, to restart the
     system. If the dome was previously open, then re-open it. If the telescope was previously
     unfrozen, then unfreese it.
  """
  global LastDome, LastFrozen
  if LastDome is None or LastFrozen is None:
    logger.error("safety_startup called while the system is not shut down!")
  if LastDome:
    logger.info('Safety startup - re-opening dome shutter')
    dome.open(force=True)
  else:
    logger.info('Safety startup - dome  already closed when shut down, not re-opening')
  LastDome = None
  if not LastFrozen:
    logger.info('Safety startup - un-freezing telescope')
    unfreeze(force=True)
  else:
    logger.info('Safety startup - telescope already frozen when shut down, not un-freezing')
  LastFrozen = None


safety.register_stopfunction('Safety Shutdown', function=_safety_shutdown, args=[], kwargs={})

safety.register_startfunction('Safety Startup', function=_safety_startup, args=[], kwargs={})

#Convenience functions for the dummy hand paddle mode - delete once testing is complete.
#def n():
#  release('S', paddle='C')
#  press('N', paddle='C')

#def s():
#  release('N', paddle='C')
#  press('S', paddle='C')

#def r():
#  release('N', paddle='C')
#  release('S', paddle='C')

def i():
  print usbcon.binstring(d.inputs)

if __name__ == '__main__':
  LastDome = None    # State of the dome.IsShutterOpen boolean, saved during safety shutdowns
  LastFrozen = None  # State of the motion.motors.Frozen boolean, saved during safety shutdowns
  if SITE == 'PERTH':
    weather.Init()    #Initialise weather package, including SQL connection
  motion.KickStart()
  time.sleep(0.2)  # Wait for motion control to start up
  m = motion.motors
  d = m.Driver
  limits = motion.limits
  detevent.Init()
  RegisterCleanup(cleanup)
  current = detevent.current
  c = current
  tjserver.InitServer()

