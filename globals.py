
"""Constants, classes and utility functions used by most of the other 
   modules in Teljoy. 
"""

import ConfigParser
import logging

INIF = 'teljoy.ini'   

#$IFDEF NZ}
  #DOBSLAT = -43.9866666667               #Lat: -43 59.2}
  #DOBSLONG = -170.465                     #Long: -170 27.9}
#$ELSE}
DOBSLAT = -32.008083333               #Lat: -32 00 29.1}
DOBSLONG = -116.13501944               #Long: -116 08 06.07}
#$ENDIF}

#These really are constant, unless this code is still being used thousands of years from now...
MSOLDY = 1.00273790931     #Mean solar day = MsolDy Mean sidereal days}
MSIDDY = 0.99726956637     #Mean sidereal day = MSidDy mean solar days}
DRASID = -15.04106868     #Default sidereal rate (multiplied by 'SidFudge' factor from ini file)

#Fiddle with the values in teljoy.ini, these are just fallback values
DFSLEWRATE = 144000                     #Default slew rate 2 deg/sec
DFCOARSESETRATE = 3600                  #Default set rate 3arcmin/sec
DFFINESETRATE = 1200                    #Default fine set rate 1arcmin/sec
DFGUIDERATE = 100                       #Default guide rate 5arcsec/sec

DFTEMP = 0                              #default (high altitude) air temp in deg C, for refraction calculation
DFPRESS = 1015.92                       #default atm. press. in mb, for refraction calculation

CLASSDEBUG = True    #If true, trap all classes to catch attributes created outside __init__ method

PULSE = 0.05                       #50 milliseconds per 'tick'

REALMOTORS = True   #If true, we're driving the real PLAT telescope, if false, driving test motors.

if REALMOTORS:
  DIVIDER = 1   #Don't scale step values for real telescope
  MOTOR_ACCEL = 6000     #2.0 (revs/sec/sec) * 25000 (steps/rev) = 50,000 steps/sec/sec = 125 steps/frame/frame
else:
  DIVIDER = 20   #Scale down step values for testing with non-microstepped driver boards
  MOTOR_ACCEL = 6000        #For test motors, this is 15 steps/frame/frame


FILTERS = ['Clear','Red','NCN','Blue','Visual','Infrared','Empty','Hole']

CPPATH = ['/usr/local/etc/teljoy.ini', './teljoy.ini']    #Initialisation file path

LOGLEVEL_CONSOLE = logging.INFO      #Logging level for console messages (INFO, DEBUG, ERROR, CRITICAL, etc)
LOGLEVEL_LOGFILE = logging.DEBUG      #Logging level for logfile
LOGFILE = "/tmp/teljoy.log"

# create global logger object for Facility Controller
logger = logging.getLogger("teljoy")
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages, formatted with timestamps
fh = logging.FileHandler(LOGFILE)
fh.setLevel(LOGLEVEL_LOGFILE)
ff = logging.Formatter("%(asctime)s: %(name)s-%(levelname)s  %(message)s")
fh.setFormatter(ff)
# create console handler with a higher log level, and without timestamps
ch = logging.StreamHandler()
ch.setLevel(LOGLEVEL_CONSOLE)
cf = logging.Formatter("%(name)s-%(levelname)s  %(message)s")
ch.setFormatter(cf)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)


class Position:
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
  def __init__(self, ra=None, dec=None, epoch=2000.0, objid=''):
    """Accepts optional 'ra', 'dec' and 'objid' arguments. 'ra' and 'dec' can be sexagesimal 
       strings (in hours:minutes:seconds for RA and degrees:minutes:seconds for DEC), or
       numeric values (fractional hours for RA, fractional degrees for DEC).
     
       objid is an optional identifier for the target specified.
    """
    self.ObjID = objid                     #Object ID
    if type(ra) == str:
      ra = stringsex(ra)
    if (ra is None) or (type(ra)<>int and type(ra)<>float):
      self.Ra = 0.0                        #mean RA in arcesc
    else:
      self.Ra = ra * 15.0 * 3600.0
    if type(dec) == str:
      dec = stringsex(dec)
    if (dec is None) or (type(dec)<>int and type(dec)<>float):
      self.Dec = 0.0                       #mean DEC in arcesc
    else:
      self.Dec = dec * 3600.0
    self.Epoch = epoch                     #Equinox for apparent Ra & Dec
    if CLASSDEBUG:
      self.__setattr__ = self.debug

  def debug(self,name,value):
    """Trap all attribute writes, and raise an error if the attribute
       wasn't defined in the __init__ method. Debugging code to catch all
       the identifier mismatches due to the fact that Pascal isn't case
       sensitive for identifier names.
    """
    if name in self.__dict__.keys():
      self.__dict__[name] = value
    else:
      raise AssertionError, "Setting attribute %s=%s for the first time."

  def __getstate__(self):
    """Can't pickle the __setattr__ function when saving state
    """
    d = self.__dict__.copy()
    del d['__setattr__']
    return d

  def __repr__(self):
    s  = "<Position %s: Org=[%s, %s EQ %6.1f]>" % (self.ObjID, sexstring(self.Ra/15.0/3600,fixed=True), sexstring(self.Dec/3600,fixed=True), self.Epoch)
    return s
    
  def __str__(self):
    return "{%s}: Org=[%s, %s EQ %6.1f]" % (self.ObjID,
                                            sexstring(self.Ra/15.0/3600,fixed=True),
                                            sexstring(self.Dec/3600,fixed=True),
                                            self.Epoch )


class Errors:
  """An instance of this class is created to store all internal software error states.
  """
  def __init__(self):
    self.RefError = False       #The refraction code failed (typically due to very low altitude)
    self.AltError = False       #Current altitude below defined threshold
    self.CalError = CP.getboolean('Alarms','OrigPosWarn')      #Current position is unknown
    self.TimeoutError = False   #Motion control queue handler not running (motion.motors.Timeint)
    self.watchdog = 0           #Reset to zero every 20ms by motion control queue handler
    if CLASSDEBUG:
      self.__setattr__ = self.debug

  def debug(self,name,value):
    """Trap all attribute writes, and raise an error if the attribute
       wasn't defined in the __init__ method. Debugging code to catch all
       the identifier mismatches due to the fact that Pascal isn't case
       sensitive for identifier names.
    """
    if name in self.__dict__.keys():
      self.__dict__[name] = value
    else:
      raise AssertionError, "Setting attribute %s=%s for the first time."

  def __getstate__(self):
    """Can't pickle the __setattr__ function when saving state
    """
    d = self.__dict__.copy()
    del d['__setattr__']
    return d

  def update(self):
    """Checks the watchdog counter and sets the TimeoutError attribute if the
       queue handler isn't running. Called by detevent.DetermineEvent.
    """
    pass
#    self.watchdog += 1        #increment watchdog timer
#    if self.watchdog>100:
#      self.TimoutError = True

  def __repr__(self):
    errs = []
    if self.CalError:
      errs.append('**Teljoy Calibration Error - Reset Position!**')
    if self.RefError:
      errs.append('**Refrac velocity error**')
    if self.AltError:
      errs.append('**Object too LOW**')
    if self.TimeoutError:
      errs.append('**Interrupt lost**')
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
      errs.append('INT')
    return "Errors:[%s]" % (','.join(errs))
  
    
    
class Prefs:
  """An instance of this class is created to store global preferences
     (from the .ini file) and operating modes.
  """
  def __init__(self):
    self.EastOfPier = CP.getboolean('Toggles','EastOfPier')
    self.RAsid = DRASID * CP.getfloat('Rates','SidFudge')
    self.FlexureOn = CP.getboolean('Toggles','FlexureOn')          #flexure corrections on?
    self.HighHorizonOn = CP.getboolean('Toggles','HighHorizonOn')  #whether to use AltCutoffHi or AltCutoffLo
    self.RefractionOn = CP.getboolean('Toggles','RefractionOn')    #refraction corr. on?
    self.RealTimeOn = CP.getboolean('Toggles','RealTimeOn')      #real-time refraction and/or flexure corrections if on
    self.AltWarning = CP.getint('Alarms','AltWarning')
    self.AltCutoffFrom = CP.getint('Alarms','AltCutoffFrom')
    self.AltCutoffHi = CP.getint('Alarms','AltCutoffHi')
    self.AltCutoffLo = CP.getint('Alarms','AltCutoffLo')
    self.ObsLat = CP.getfloat('Environment','ObsLat')
    self.ObsLong = CP.getfloat('Environment','ObsLong')
    self.SlewRate = CP.getfloat('Rates','Slew')*20
    self.CoarseSetRate = CP.getfloat('Rates','CoarseSet')*20
    self.FineSetRate = CP.getfloat('Rates','FineSet')*20
    self.GuideRate = CP.getfloat('Rates','Guide')*20
    self.Temp = CP.getfloat('Environment','Temp')
    self.Press = CP.getfloat('Environment','Pressure')
    self.NonSidOn = False
    self.WaitBeforePosUpdate = CP.getint('Dome','WaitTime')
    self.MinWaitBetweenDomeMoves = CP.getint('Dome','MinBetween')
    self.LogDirName = CP.get('Paths','LogDirName')  
    if CLASSDEBUG:
      self.__setattr__ = self.debug

  def debug(self,name,value):
    """Trap all attribute writes, and raise an error if the attribute
       wasn't defined in the __init__ method. Debugging code to catch all
       the identifier mismatches due to the fact that Pascal isn't case
       sensitive for identifier names.
    """
    if name in self.__dict__.keys():
      self.__dict__[name] = value
    else:
      raise AssertionError, "Setting attribute %s=%s for the first time."

  def __getstate__(self):
    """Can't pickle the __setattr__ function when saving state
    """
    d = self.__dict__.copy()
    del d['__setattr__']
    return d


def sexstring(value=0,sp=':',fixed=False):
  """Convert the floating point 'value' into a sexagecimal string.
     The character in 'sp' is used as a spacer between components. Useful for
     within functions, not on its own.
     eg: sexstring(status.TJ.ObjRA,' ')
  """
  try:
    aval = abs(value)
    error = 0
  except:
    aval = 0.0
    error = 1
  if value < 0:
    outs = '-'
  else:
    outs = ''
  D = int(aval)
  M = int((aval-float(D))*60)
  S = float(int((aval-float(D)-float(M)/60)*36000))/10
  if fixed:
    outs += '%02i%s%02i%s%02i' % (D,sp,M,sp,S)
  else:
    outs += '%02i%s%02i%s%4.1f' % (D,sp,M,sp,S)
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
      if len(components) <> 3:
        components = value.split(' ')
      if len(components) <> 3:
        return None
      h,m,s = [c.strip() for c in components]
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


def UpdateConfig():
  lCP = ConfigParser.SafeConfigParser(defaults=ConfigDefaults)
  lCPfile = lCP.read(CPPATH)
  if not lCPfile:
    logger.error("None of the specified configuration files found by globals.py: %s" % (CPPATH,))
  return lCP,lCPfile


ConfigDefaults = {'OrigPosWarn':'True', 'FlexureOn':'True', 'HighHorizonOn':'False', 'RefractionOn':'True',
                  'RealTimeOn':'True', 'AltWarning':'10', 'AltCutoffFrom':'6',
                  'AltCutoffHi':'30', 'AltCutoffLo':'15', 'ObsLat':`DOBSLAT`, 'ObsLong':`DOBSLONG`,
                  'SidFudge':'-15.04106868', 'EastOfPier':'False', 'Slew':`DFSLEWRATE/20`,
                  'CoarseSet':`DFCOARSESETRATE/20`, 'FineSet':`DFFINESETRATE/20`, 'GUIDE':`DFGUIDERATE/20`,
                  'Temp':`DFTEMP`,'Press':`DFPRESS`}
                  
ConfigDefaults.update( {'WaitTime':'100', 'MinBetween':'5', 'LogDirName':'/tmp'} )


CP,CPfile = UpdateConfig()

errors = Errors()
prefs = Prefs()

DirtyTime = 0

logger.info('globals.py init finished')
print 'Globals init finished'

