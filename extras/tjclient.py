"""Pyro4 RPC client library for Teljoy
"""

DEFHOST = 'cynosure.canterbury.ac.nz'
DEFPORT = 9696
DEFURL = 'PYRO:Teljoy@%s:%d' % (DEFHOST, DEFPORT)

import Pyro4

import datetime
import os
import time
import traceback

KEYFILE = '~mjuo/teljoy.pyrokey'

try:
  hmac = file(os.path.expanduser(KEYFILE), 'r').read().strip()
except IOError:
  print 'Pyro4 key file not found: %s' % KEYFILE
  hmac = ''

Pyro4.config.HMAC_KEY = hmac or Pyro4.config.HMAC_KEY

status = None
ShutterAction = None
FreezeAction = None


class StatusObj(object):
  def __repr__(self):
    return str(self.__dict__)


class DomeStatus(StatusObj):
  def __init__(self):
    self.DomeAzi = 0
    self.DomeInUse = False
    self.CommandSent = False
    self.Command = ''
    self.ShutterOpen = False
    self.AutoDome = False
    self.DomeTracking = False
    self.DomeLastTime = 0
    self.EncoderOffset = 0


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
    self.Autoguiding = False
    self.guidelog = (0,0)


class LimitStatus(object):
  def __init__(self):
    self.HWLimit = False          # True if any of the hardware limits are active. Should be method, not attribute
    self.OldLim = False           # ?
    self.PowerOff = False         # True if the telescope power is off (eg, switched off at the telescope)
    self.HorizLim = False         # True if the mercury switch 'nest' horizon limit has tripper
    self.MeshLim = False          # ?
    self.EastLim = False          # RA axis eastward limit reached
    self.WestLim = False          # RA axis westward limit reached
    self.LimitOnTime = 0          # Timestamp marking the last time we tripped a hardware limit.
    self.WantsOverride = False    # True if the user has requested an ovveride to the cable wrap limit
    self.LimOverride = False      # True if the limit has been overridden in software


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
    self.limits = LimitStatus()
    self.prefs = PrefsStatus()
    self.info = ''

  def update(self):
    with self.proxy:
      self.motors.__dict__.update(self.proxy.GetMotors())
      self.limits.__dict__.update(self.proxy.GetLimits())
      self.current.__dict__.update(self.proxy.GetCurrent())
      self.current.Time.__dict__.update(self.current.TimeDict)
      self.dome.__dict__.update(self.proxy.GetDome())
      self.prefs.__dict__.update(self.proxy.GetPrefs())
      self.info = self.proxy.GetInfo()

  def connect(self):
    self.connected = False
    ok = False
    msg = ''
    if self.proxy is not None:
      self.proxy._pyroRelease()

    try:
      self.proxy = Pyro4.Proxy(DEFURL)   # Use hardwired host/port first
      self.proxy.Ping()   # Check to see we can connect
      ok = True
    except Pyro4.errors.PyroError:
      msg += "Can't find teljoy using default URL, trying nameserver.\n"
      msg += "Local traceback: \n" + traceback.format_exc() + "\n"
      try:
        self.proxy = Pyro4.Proxy('PYRONAME:Teljoy')
        ok = True
      except Pyro4.errors.PyroError:
        self.proxy = None
        msg += "Can't find Teljoy service using nameserver"
        msg += "Local traceback: \n" + traceback.format_exc() + "\n"
        return msg
    if ok:
      try:
        self.update()
        self.connected = True
      except Pyro4.errors.PyroError:
        msg += "Local traceback: \n" + traceback.format_exc() + "\n"
        msg += "Remote Traceback: \n" + "".join(Pyro4.util.getPyroTraceback()) + "\n"
        return msg + "Can't connect to Teljoy Pyro4 service - is Teljoy running?"


def jump(*args, **kwargs):
  """Takes the arguments given, and sends a command to Teljoy
    to jump to that position.
    eg: jump('frog','12:34:56','-32:00:00',1998.5)
        jump(id='plref', ra='17:47:28', dec='-27:49:49', epoch=1998.5)
  """
  with status.proxy:
    return status.proxy.jump(*args, **kwargs)


def reset(*args, **kwargs):
  """Takes the arguments given, and sends a command to Teljoy
    to reset the telescope coordinates to that position.
    eg: reset('frog','12:34:56','-32:00:00',1998.5)
        reset(id='plref', ra='17:47:28', dec='-27:49:49', epoch=1998.5)
  """
  with status.proxy:
    return status.proxy.reset(*args, **kwargs)


def offset(offra=0, offdec=0):
  """Moves the telescope by offra,offdec arcseconds.
    Silently fails if Teljoy isn't ready to be remote-controlled.
    eg: jumpoff(2.45,-12.13)
  """
  with status.proxy:
    return status.proxy.offset(offra, offdec)


jumpoff = offset


def autoguide(on=True):
  """Turns autoguiding on (on=True) or off (on=False).
    eg: jumpoff(2.45,-12.13)
  """
  with status.proxy:
    return status.proxy.autoguide(on)


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
  with status.proxy:
    return status.proxy.dome(arg)


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
  with status.proxy:
    if action:
      return status.proxy.freeze()
      FreezeAction = True
    else:
      return status.proxy.unfreeze()
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
      with status.proxy:
        status.proxy.Ping()
  except KeyboardInterrupt:
    print "a keyboard interrupt in tjclient._background()"
  except Pyro4.errors.PyroError:
    msg = status.connect()
    if msg:
      print msg



def Init():
  """Connect to the Teljoy server process and create a proxy object to the
     real telescope object.
  """
  global status
  status = TelClient()
  return status.connect()   #Returns None for no errors, or an error message
