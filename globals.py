"""Constants, classes and utility functions used by most of the other
   modules in Teljoy. 
"""

import random
import threading
import time
import traceback

import ConfigParser
import logging

#SITE = 'PERTH'
SITE = 'NZ'

INIF = 'teljoy.ini'

if SITE == 'NZ':
  DOBSLAT = -43.9866666667               # Lat: -43 59.2
  DOBSLONG = -170.465                    # Long: -170 27.9
else:
  DOBSLAT = -32.008083333               # Lat: -32 00 29.1
  DOBSLONG = -116.13501944               # Long: -116 08 06.07

#These really are constant, unless this code is still being used thousands of years from now...
MSOLDY = 1.00273790931     # Mean solar day = MsolDy Mean sidereal days}
MSIDDY = 0.99726956637     # Mean sidereal day = MSidDy mean solar days}
DRASID = -15.04106868     # Sidereal rate, in arcseconds per SOLAR second

# Default telescope speeds. These are just fallback values if teljoy.ini is not found, the
# actual speeds used are taken from teljoy.ini.
# Note that unlike the numbers in teljoy.ini, these values are in
# STEPS per second, not arcseconds per second.
DFSLEWRATE = 108000                     # Default slew rate 1.5 deg/sec
DFCOARSESETRATE = 3600                  # Default set rate 3arcmin/sec
DFFINESETRATE = 1200                    # Default fine set rate 1arcmin/sec
DFGUIDERATE = 100                       # Default guide rate 5arcsec/sec

DFTEMP = 0                              # default (high altitude) air temp in deg C, for refraction calculation
DFPRESS = 1015.92                       # default atm. press. in mb, for refraction calculation

DEBUG = False    # If true, print extra debugging info - eg motion control activity

#DTABLE = 'ncurrent'      # Table to use for current position updates - 'ncurrent' for dummy, 'current' for real telescope.
DTABLE = 'current'      # Table to use for current position updates - 'ncurrent' for dummy, 'current' for real telescope.

PULSE = 0.05                       # 50 milliseconds per 'frame' (sometimes referred to as a 'tick')

REALMOTORS = True   # If true, we're driving the real telescope, if false, driving test motors.

if REALMOTORS:
  DIVIDER = 1   # Don't scale step values for real telescope
  MOTOR_ACCEL = 50000     # 2.0 (revs/sec/sec) * 25000 (steps/rev) = 50,000 steps/sec/sec = 125 steps/frame/frame
else:
  DIVIDER = 20   # Scale down step values for testing with non-microstepped driver boards
  MOTOR_ACCEL = 6000        # For test motors, this is 15 steps/frame/frame

# Which paddles to simulate using press, release functions
# DUMMYPADDLES = ['C','F']
DUMMYPADDLES = []
#DUMMY = ['C', 'F']  #List of paddles to  be simulated.

# Which paddle the test-rig should operate (using input bits 8-15)
TESTPADDLE = None
#TESTPADDLE = 'C'

FILTERS = ['Clear', 'Red', 'NCN', 'Blue', 'Visual', 'Infrared', 'Empty', 'Hole']

CPPATH = ['/usr/local/etc/teljoy.ini', './teljoy.ini', '/home/mjuo/teljoy/teljoy.ini']    # Initialisation file path

LOGLEVEL_CONSOLE = logging.INFO      # Logging level for console messages (INFO, DEBUG, ERROR, CRITICAL, etc)
LOGLEVEL_LOGFILE = logging.DEBUG      # Logging level for logfile
LOGFILE = "/tmp/teljoy.log"

# create global logger object for Facility Controller
logger = logging.getLogger("teljoy")
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages, formatted with timestamps
try:
  fh = logging.FileHandler(LOGFILE)
  fh.setLevel(LOGLEVEL_LOGFILE)
  ff = logging.Formatter("%(asctime)s: %(name)s-%(levelname)s  %(message)s")
  fh.setFormatter(ff)
except:
  fh = None    # This will fail if we don't have permission to write to an existing log file.

# create console handler with a higher log level, and without timestamps
ch = logging.StreamHandler()
ch.setLevel(LOGLEVEL_CONSOLE)
cf = logging.Formatter("%(name)s-%(levelname)s  %(message)s")
ch.setFormatter(cf)
# add the handlers to the logger
if fh is not None:
  logger.addHandler(fh)
logger.addHandler(ch)


class Position(object):
  """Base class used to store astronomical coordinates. Attributes are '.Ra' and
     '.Dec' in arcseconds, and '.Epoch', a decimal year containing the equinox
     for which that RA and DEC refer. The 'ObjID' attribute contains an optional short
     name for the object.

     While the 'ra' and 'dec' arguments for the constructor for new positions are
     in hours or degrees, the INTERNAL attributes (Ra and Dec, plus RaA, DecA, RaC, and DecC
     in the correct.CalcPosition subclass) are all in arcseconds.
     
     Note that RA and DEC attributes of this position class (.Ra, .Dec, .RaA, etc) should
     be the only identifiers for Right Ascension and Declination that are in mixed-case,
     in any of the teljoy code. This is to indicate the fact that they are in arcseconds, 
     not hours and degrees. All other coordinate attributes should be fully capitalised, as
     should the strings 'RA' and 'DEC' if they form part of another identifier (RA2000, etc).
     The only exceptions are the arguments to any function likely to be used on the
     command-line by a user, which should be fully lower case (ra, dec).
     
     Objects of this base class can't be used for telescope jumps, as they don't contain the 
     methods required to calculate apparent place - use the correct.CalcPosition subclass
     for most purposes.
     
     Note that for historical reasons, the equinox for the coordinates is stored in the 'Epoch'
     attribute. Strictly speaking, 'Epoch' refers to the time an observation or measurement
     was made, and NOT the coordinate reference frame used.
  """

  def __init__(self, ra=None, dec=None, epoch=2000.0, domepos=None, objid=''):
    """Accepts optional 'ra', 'dec' and 'objid' arguments. 'ra' and 'dec' can be sexagesimal 
       strings (in hours:minutes:seconds for RA and degrees:minutes:seconds for DEC), or
       numeric values (fractional hours for RA, fractional degrees for DEC).

       If 'domepos' (saved as self.DomePos) is None, then the dome azimuth is
       calculated automatically when the telescope is slewed, otherwise the given
       value (in degrees) is used for the dome azimuth when slewing to this position.
     
       objid is an optional identifier for the target specified.
    """
    self.ObjID = objid                     # Object ID
    if type(ra) == str:
      ra = stringsex(ra)
    if (ra is None) or (type(ra) != int and type(ra) != float):
      self.Ra = 0.0                        # mean RA in arcesc
    else:
      self.Ra = ra * 15.0 * 3600.0
    if type(dec) == str:
      dec = stringsex(dec)
    if (dec is None) or (type(dec) != int and type(dec) != float):
      self.Dec = 0.0                       # mean DEC in arcesc
    else:
      self.Dec = dec * 3600.0
    self.Epoch = epoch                     # Equinox for apparent Ra & Dec
    self.DomePos = domepos

  def __getstate__(self):
    """Can't pickle the __setattr__ function when saving state
    """
    d = {}
    for n in ['Ra', 'Dec', 'Epoch', 'ObjID', 'DomePos']:
      d[n] = self.__dict__[n]
    return d

  def __repr__(self):
    s = "<Position %s: Org=[%s, %s EQ %6.1f]>" % (self.ObjID, sexstring(self.Ra/15.0/3600, fixed=True), sexstring(self.Dec/3600, fixed=True), self.Epoch)
    return s

  def __str__(self):
    return "{%s}: Org=[%s, %s EQ %6.1f]" % (self.ObjID,
                                            sexstring(self.Ra/15.0/3600,fixed=True),
                                            sexstring(self.Dec/3600,fixed=True),
                                            self.Epoch )


class Errors(object):
  """An instance of this class is created to store all internal software error states.
  """

  def __init__(self):
    self.RefError = False       # The refraction code failed (typically due to very low altitude)
    self.AltError = False       # Current altitude below defined threshold
    self.AltErrorTag = None     # Save the 'AltErr' safety interlock tag, if there is one
    self.CalError = False       # Current position is unknown
    self.CalErrorTag = None     # Save the 'CalErr' safety interlock tag, if there is one
    self.TimeoutError = False   # Haven't heard from Prosp for a while, not safe to continue

  def __getstate__(self):
    """Can't pickle the __setattr__ function when saving state
    """
    d = {}
    for n in ['RefError', 'AltError', 'CalError', 'TimeoutError']:
      d[n] = self.__dict__[n]
    return d

  def __repr__(self):
    errs = []
    if self.CalError:
      errs.append('**Teljoy Calibration Error - Reset Position!**')
    if self.RefError:
      errs.append('**Refrac velocity error**')
    if self.AltError:
      errs.append('**Object too LOW**')
    if self.TimeoutError:
      errs.append('**No contact with Prosp**')
    return '\n'.join(errs) + '\n'

  def __str__(self):
    errs = []
    if self.CalError:
      errs.append('CAL')
    if self.RefError:
      errs.append('REF')
    if self.AltError:
      errs.append('ALT')
    if self.TimeoutError:
      errs.append('PROSP')
    return "Errors:[%s]" % (','.join(errs))


class Prefs(object):
  """An instance of this class is created to store global preferences
     (from the .ini file) and operating modes.
  """

  def __init__(self):
    self.EastOfPier = CP.getboolean('Toggles', 'EastOfPier')
    self.RAsid = DRASID
    self.FlexureOn = CP.getboolean('Toggles', 'FlexureOn')          #flexure corrections on?
    self.HighHorizonOn = CP.getboolean('Toggles', 'HighHorizonOn')  #whether to use AltCutoffHi or AltCutoffLo
    self.RefractionOn = CP.getboolean('Toggles', 'RefractionOn')    #refraction corr. on?
    self.RealTimeOn = CP.getboolean('Toggles', 'RealTimeOn')      #real-time refraction and/or flexure corrections if on
    self.AltWarning = CP.getint('Alarms', 'AltWarning')
    self.AltCutoffFrom = CP.getint('Alarms', 'AltCutoffFrom')
    self.AltCutoffHi = CP.getint('Alarms', 'AltCutoffHi')
    self.AltCutoffLo = CP.getint('Alarms', 'AltCutoffLo')
    self.ObsLat = CP.getfloat('Environment', 'ObsLat')
    self.ObsLong = CP.getfloat('Environment', 'ObsLong')
    self.SlewRate = CP.getfloat('Rates', 'Slew') * 20
    self.CoarseSetRate = CP.getfloat('Rates', 'CoarseSet') * 20
    self.FineSetRate = CP.getfloat('Rates', 'FineSet') * 20
    self.GuideRate = CP.getfloat('Rates', 'Guide') * 20
    self.Temp = CP.getfloat('Environment', 'Temp')
    self.Press = CP.getfloat('Environment', 'Pressure')
    self.WaitBeforePosUpdate = CP.getfloat('Dome', 'WaitTime')
    self.MinWaitBetweenDomeMoves = CP.getfloat('Dome', 'MinBetween')
    self.LogDirName = CP.get('Paths', 'LogDirName')
    self.CapHourAngle = CP.getfloat('Presets', 'CapHourAngle')
    self.CapDec = CP.getfloat('Presets', 'CapDec')
    self.StowHourAngle = CP.getfloat('Presets', 'StowHourAngle')
    self.StowDec = CP.getfloat('Presets', 'StowDec')
    self.StowDomeAzi = CP.getfloat('Presets', 'StowDomeAzi')
    self.DomeFlatHourAngle = CP.getfloat('Presets', 'DomeFlatHourAngle')
    self.DomeFlatDec = CP.getfloat('Presets', 'DomeFlatDec')
    self.DomeFlatDomeAzi = CP.getfloat('Presets', 'DomeFlatDomeAzi')
    self.SkyFlatHourAngle = CP.getfloat('Presets', 'SkyFlatHourAngle')
    self.SkyFlatDec = CP.getfloat('Presets', 'SkyFlatDec')


def sexstring(value=0.0, sp=':', fixed=False, dp=None):
  """Convert the floating point 'value' into a sexagecimal string.
     The character in 'sp' is used as a spacer between components. Useful for
     within functions, not on its own.
     eg: sexstring(status.TJ.ObjRA,' ')
  """
  if fixed:
    dp = 0
  if dp is None:
    dp = 1
  else:
    if dp is None:
      dp = 1
    dp = int(dp)
  try:
    aval = abs(value)
    error = 0
  except TypeError:
    aval = 0.0
    error = 1
  if value < 0:
    outs = '-'
  else:
    outs = ''
  D = int(aval)
  M = int((aval - float(D)) * 60)
  S = (aval - float(D) - float(M)/60) * 3600
  Si = int(S)
  Sf = round(S-Si, dp)
  if Sf == 1.0:
    Si += 1
    if Si == 60:
      Si = 0
      M += 1
      if M == 60:
        M = 0
        D += 1
    Sf = 0.0
  outs += '%02i%s%02i%s%02i' % (D, sp, M, sp, Si)
  if dp > 0:
    fstr = ".%%0%id" % dp
    outs += fstr % int(Sf*(10**dp))
  if error:
    return ''
  else:
    return outs


def stringsex(value="", compressed=False):
  """Convert the sexagesimal coordinate 'value' into a floating point
     result. Handles either a colon or a space as seperator, but currently
     requires all three components (H:M:S not H:M or H:M.mmm).
     If 'compressed' is true, then no seperator is used, and the argument
     must have all three components, two digits for deg/minutes, and optional
     fractional seconds.
  """
  try:
    value = value.strip()
    if not compressed:
      components = value.split(':')
      if len(components) != 3:
        components = value.split(' ')
      if len(components) != 3:
        return None
      h, m, s = [c.strip() for c in components]
      sign = 1
      if h[0] == "-":
        sign = -1
      return float(h) + (sign*float(m)/60.0) + (sign*float(s)/3600.0)
    else:
      if value[0].isdigit():
        sign = 1
      elif value[0] == '-':
        value = value[1:]
        sign = -1
      else:
        return None
      h = value[:2]
      m = value[2:4]
      s = value[4:]
      return (sign*float(h)) + (sign*float(m)/60.0) + (sign*float(s)/3600.0)
  except:
    return None


class SafetyInterlock(object):
  """Handles safety interlocks for a system. Any component, either locally or remotely, can
     call add_tag() on this object to add a safety interlock. The add_tag function returns a
     unique tag ID, which the calling process must save, and 'stops' the system - this is done by
     calling all of the functions registered using 'register_stopfunction()', one by one.

     By calling 'remove_tag(<tag>)', and passing the same tag value back, that safety tag can be
     removed.

     Any number of processes can add tags, but each tag can only be removed by passing back the
     unique tag ID value returned when that tag was added.

     The system is only re-started when _all_ tags have been removed, and that re-start
     process is carried out by calling all of the functions registered using the
     'register_startfunction()' method, one by one.

     There is a single threading.Event() attribute called 'Active', which is 'set' when the
     system is running/started, and clear when the system is stopped.
  """

  def __init__(self):
    self._lock = threading.RLock()
    self.Active = threading.Event()
    self.Active.set()
    self.Errors = {}
    self._tags = {}
    self._stopfunctions = {}     # Functions to call when the system is paused
    self._startfunctions = {}    # Functions to call when the system is un-paused

  def add_tag(self, comment=''):
    """Adds a safety tag, stops the system if it hasn't already been stopped, and returns
       a unique, random tag ID. That safety tag can only be removed by calling the
       remove_tag() method with that tag ID.
    """
    tag = random.getrandbits(31)
    with self._lock:
      assert tag not in self._tags.keys()
      self._tags[tag] = (time.time(), threading.current_thread(), comment)
      if self.Active.is_set():
        self.Active.clear()
        for name, action in self._stopfunctions.iteritems():
          try:
            logger.info("Calling safety stop function: %s" % name)
            function, args, kwargs = action
            function(*args, **kwargs)
          except:
            now = time.time()
            error = traceback.format_exc()
            self.Errors[name][now] = error
            logger.error(
              "Error in function called by safety interlock to stop the system: function %s: %s" % (name, error))
    return tag

  def remove_tag(self, tag=None):
    """Given a tag ID, removes that tag from the current tag set. If there are no tags remaining, and the system hasn't
       already been restarted, call all the start functions registered using register_startfunction().
    """
    with self._lock:
      if tag not in self._tags.keys():
        logger.error("Can't remove safety tag - invalid tag")
        return
      del self._tags[tag]
      if (not self._tags) and (not self.Active.is_set()):     # If no more tags, and the system hasn't already been started
        for name, action in self._startfunctions.iteritems():
          try:
            logger.info("Calling safety restart function: %s" % name)
            function, args, kwargs = action
            function(*args, **kwargs)
          except:
            now = time.time()
            error = traceback.format_exc()
            self.Errors[name][now] = error
            logger.error(
              "Error in function called by safety interlock to restart the system: function %s: %s" % (name, error))
        self.Active.set()

  def register_stopfunction(self, name, function, args=None, kwargs=None):
    if args is None:
      args = []
    if kwargs is None:
      kwargs = {}
    with self._lock:
      self._stopfunctions[name] = (function, args, kwargs)
      self.Errors[name] = {}

  def register_startfunction(self, name, function, args=None, kwargs=None):
    if args is None:
      args = []
    if kwargs is None:
      kwargs = {}
    with self._lock:
      self._startfunctions[name] = (function, args, kwargs)
      self.Errors[name] = {}

  def __repr__(self):
    mesg = []
    if self.Active.is_set():
      mesg.append("Safety Interlock - system ACTIVE")
    else:
      mesg.append("Safety Interlock - system STOPPED")
    if self._tags:
      mesg.append("Active safety tags:")
      for tme, thr, com in self._tags.values():
        mesg.append("Tag '%s' added at %s by thread %s" % (com, time.ctime(tme), thr))
    else:
      mesg.append('No tags.')
    return '\n'.join(mesg) + '\n'

  def __str__(self):
    return self.__repr__()


def UpdateConfig():
  lCP = ConfigParser.SafeConfigParser(defaults=ConfigDefaults)
  lCPfile = lCP.read(CPPATH)
  if not lCPfile:
    logger.error("None of the specified configuration files found by globals.py: %s" % (CPPATH,))
  return lCP, lCPfile


ConfigDefaults = {'FlexureOn':'True', 'HighHorizonOn':'False', 'RefractionOn':'True',
                  'RealTimeOn':'True', 'AltWarning':'10', 'AltCutoffFrom':'6',
                  'AltCutoffHi':'30', 'AltCutoffLo':'15', 'ObsLat':`DOBSLAT`, 'ObsLong':`DOBSLONG`,
                  'EastOfPier':'False', 'Slew':`DFSLEWRATE/20`,
                  'CoarseSet':`DFCOARSESETRATE/20`, 'FineSet':`DFFINESETRATE/20`, 'GUIDE':`DFGUIDERATE/20`,
                  'Temp':`DFTEMP`,'Press':`DFPRESS`}

ConfigDefaults.update( {'WaitTime':'0.5', 'MinBetween':'5', 'LogDirName':'/tmp'} )

CP, CPfile = UpdateConfig()

errors = Errors()
prefs = Prefs()

safety = SafetyInterlock()   # Create a safety interlock object

DirtyTime = 0


