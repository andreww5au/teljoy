"""Pyro4 RPC client library for Teljoy
"""

from globals import *

import Pyro4
import time
import datetime

status = None
ShutterAction = None
FreezeAction = None

class StatusObj(object):
  def __repr__(self):
    return str(self.__dict__)


class DomeStatus(StatusObj):
  def __init__(self):
    self.DomeInUse = False
    self.ShutterInUse = False
    self.DomeMoved = False
    self.ShutterOpen = False
    self.DomeThere = False
    self.AutoDome = False
    self.DomeTracking = False
    self.DomeLastTime = 0
    self.NewDomeAzi = -10
    self.NewShutter = ''


class TimeStatus(StatusObj):
  def __init__(self):
    self.UT = datetime.datetime.utcnow()    #Current date and time, in UTC
    self.JD = 0.0                           #Fractional Julian Day
    self.LST = 0.0                          #Local Sidereal Time, in hours


class CurrentStatus(StatusObj):
  def __init__(self):
    self.Ra = None
    self.Dec = None
    self.Epoch = None
    self.RaA = None
    self.DecA = None
    self.RaC = None
    self.DecC = None
    self.Alt = None
    self.Azi = None
    self.ObjID = None
    self.TraRA = None
    self.TraDEC = None
    self.posviolate = None
    self.Time = TimeStatus()
    self.DomePos = None


class MotorsStatus(StatusObj):
  def __init__(self):
    self.Jumping = False
    self.Paddling = False
    self.Moving = False
    self.PosDirty = False
    self.ticks = 0
    self.Frozen = False


class PrefsStatus(StatusObj):
  def __init__(self):
    self.EastOfPier = False


class TelClient(StatusObj):
  """Client object, using a Pyro4 proxy of the remote telescope
     object to get status and send commands.
  """
  def __init__(self):
    """Set up the client object on creation
    """
    self.connected = False
    self.proxy = None
    self.dome = DomeStatus()
    self.current = CurrentStatus()
    self.motors = MotorsStatus()
    self.prefs = PrefsStatus()
    self.info = ''

  def update(self):
    self.motors.__dict__.update(self.proxy.GetMotors())
    self.current.__dict__.update(self.proxy.GetCurrent())
    self.current.Time.__dict__.update(self.current.TimeDict)
    self.dome.__dict__.update(self.proxy.GetDome())
    self.prefs.__dict__.update(self.proxy.GetPrefs())
    self.info = self.proxy.GetInfo()



def jump(*args, **kwargs):
  """Takes the arguments given, and sends a command to Teljoy
    to jump to that position.
    eg: jump('frog','12:34:56','-32:00:00',1998.5)
        jump(id='plref', ra='17:47:28', dec='-27:49:49', epoch=1998.5)
  """
  status.proxy.jump(*args, **kwargs)


def offset(offra=0, offdec=0):
  """Moves the telescope by offra,offdec arcseconds.
    Silently fails if Teljoy isn't ready to be remote-controlled.
    eg: jumpoff(2.45,-12.13)
  """
  status.proxy.offset(offra, offdec)

jumpoff = offset


def dome(arg=90):
  """Moves the dome (given an azimuth), or opens/shuts it, given
    a string that looks like 'open' or 'close'.
    Silently fails if Teljoy isn't ready to be remote-controlled.
    eg: dome(90)
  """
  global ShutterAction
  if type(arg) == str:
    if arg.upper() in ['O','OPEN']:
      ShutterAction = True
    elif arg.upper() in ['C','CLOSE']:
      ShutterAction = False
  status.proxy.dome(arg)


def freeze(action=True):
  """Freezes all telescope tracking if the argument is true, unfreezes
     if the argument is false. Silently fails if Teljoy isn't ready to be
     remote-controlled (waiting at a coordinate prompt or an older
     version of Teljoy). Check the 'Frozen' status flag to see if
     this command has worked.

     Usage: freeze(1)
            freeze(0)
  """
  global FreezeAction
  if action:
    status.proxy.freeze()
    FreezeAction = True
  else:
    status.proxy.unfreeze()
    FreezeAction = False


def unfreeze():
 """Unfreezes the telescope - utility function to match calls in new RPC protocol.
 """
 freeze(False)


def _background():
  """Function to be run in the background, updates the status object.
  """
  global ShutterAction, FreezeAction
  try:
    status.update()

    if (ShutterAction <> None) and (not status.dome.ShutterInUse) and (not status.dome.DomeInUse):
      if status.dome.ShutterOpen <> ShutterAction:
        dome(ShutterAction)
      else:
        ShutterAction = None
    elif FreezeAction <> None:
      if status.motors.Frozen <> FreezeAction:
        freeze(FreezeAction)
      else:
        FreezeAction = None
    else:
      status.proxy.Ping()
  except KeyboardInterrupt:
    logger.error("a keyboard interrupt in tjclient._background()")
  except Pyro4.errors.PyroError:
    Connect(status)


def Connect(s):
  s.connected = False
  try:
    s.proxy = Pyro4.Proxy('PYRONAME:Teljoy')
    s.connected = True
  except Pyro4.errors.PyroError:
    logger.error("Can't connect to Teljoy server - run teljoy.py to start the server")
  try:
    s.update()
  except Pyro4.errors.PyroError:
    s.connected = False


def Init():
  """Connect to the Teljoy server process and create a proxy object to the
     real telescope object.
  """
  global status
  status = TelClient()
  Connect(status)
  return status.connected   #True if we have a valid, working proxy
