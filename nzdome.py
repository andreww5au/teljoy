
import math
import serial
import time

import digio
from globals import *

DOMEPORT = '/dev/ttyUSB0'   # Serial port for dome encoder
MAXDOMEMOVE = 180000     # Milliseconds of dome travel time before a dome-failure timeout occurs}
DENCODEROFFSET = 27    # Add this many counts to the encoder value (range 0-255) before converting to azimuth
                       # This value is the default, used if teljoy.ini is not found. The actual offset is taken
                       # from teljoy.ini.

#Dome parameters:
RD = 3.48                             #Dome radius, in metres
ABSP = 0.55/RD                        #Distance from centre of telescope tube to dome center, in metres
ETA = 0.2/RD                          #?

class Dome(object):
  """An instance of this class is used to store the current dome motion
     state, as well as some dome control preferences. Methods (open, close,
     move) allow control.
  """
  def __init__(self):
    self.DomeAzi = -10              #Current dome azimuth
    self.DomeInUse = False          #True if the dome is moving
    self.CommandSent = False        #True if the current command has been sent to the dome controller
    self.Command = None             #True if the dome movement has finished
    self.ShutterOpen = False        #True if the shutter is open (set after a successful open or close command)
    self.IsShutterOpen = False      #True if the shutter is open (set as a response from the actual dome controller)
    self.DomeFailed = False         #True if the controller has sent a 'Dome Failed' message, because rotation has failed.
    self.AutoDome = True            #True if the dome can be controlled, False if it's in 'Manual only' mode
    self.DomeTracking = False       #True if the dome should dynamically track the current telescope position.
                                    #   if false, the dome will only be moved if AutoDome is True, and detevent.Jump is called.
    self.DomeLastTime = 0           #Last time the dome was moved. Used for DomeTracking to prevent frequent small moves
    self.EncoderOffset = CP.getint('Dome', 'DomeEncoderOffset')   # How much to add to the raw enccoder value before converting to degrees
    self.queue = []
    try:
      self.ser = serial.Serial(DOMEPORT, baudrate=9600, stopbits=serial.STOPBITS_ONE, timeout=1.0, rtscts=False, xonxoff=False, dsrdtr=False)
    except:
      self.ser = None
      print "Error opening serial port, no dome communication"

  def __getstate__(self):
    """Can't pickle the __setattr__ function when saving state
    """
    d = {}
    for n in ['DomeAzi','DomeInUse','CommandSent','Command','IsShutterOpen','DomeFailed','AutoDome','DomeTracking','DomeLastTime','queue']:
      d[n] = self.__dict__[n]
    return d

  def __repr__(self):
    return str(self.__getstate__())

  def __call__(self, arg):
    """This method is run when an instance of this class is treated like a function, and called.
       Defining it allows the global 'dome' variable containing the current dome state to be
       treated like a function, so dome(123) would move the dome to Azi=123 degrees, and
       dome('open') or dome('close) would open and close the shutter.

       This is purely for the convenience of the human at the command line, you can
       also simply call dome.move(123), dome.open() or dome.close().
    """
    if type(arg)==int or type(arg)==float:
      self.move(arg)
    elif type(arg)==str:
      if arg.upper() in ['O','OPEN']:
        self.open()
      elif arg.upper() in ['C','CLOSE']:
        self.close()
      else:
        print "Unknown argument: specify an azimuth in degrees, or 'open', or 'close'"
    else:
      print "Unknown argument: specify an azimuth in degrees, or 'open', or 'close'"

  def getDomeAzi(self):   # Return current Dome azimuth from encoder
    self.ser.flushInput()      # Empty dome input buffer to get most recent position
    data = self.ser.read(1)
    if data:
      raw = ord(data) + self.EncoderOffset  # Value in range 0-255 for full circle
      if raw > 255:
        raw -= 256
      return (raw / 256.0) * 360    # Convert to degrees
    else:
      return -1

  def check(self):
    """Should be called repeatedly (eg by detevent loop) to manage communication
       with the dome controller.
    """
    if not self.AutoDome:
      return                 # Don't do anything if we aren't in automatic mode
    if self.queue and not self.Command: # If we aren't already processing a command, and there's one in the queue, do it now.
      self.Command = self.queue.pop(0)
      self.DomeLastTime = time.time()

    if self.Command:          # If we are currently processing a dome command:
      if self.Command == 'O':
        self.ShutterOpen = True
        self.Command = None
        self.DomeInUse = False     # Shutter opening not implemented
      elif self.Command == 'C':
        self.ShutterOpen = False
        self.Command = None
        self.DomeInUse = False     # Shutter closing not implemented
      elif self.Command == 'I':
        self.Command = None        # Shutter state query not implemented
        self.DomeInUse = False
      else:                        # Command is a new dome azimuth
        try:
          az = int(float(self.Command))
          if (az < 0) or (az > 360):
            logger.error('Invalid command in dome.Command: %s' % self.Command)
            az = 0
        except ValueError:
          logger.error('Invalid command in dome.Command: %s' % self.Command)
          az = 0

        self.DomeAzi = self.getDomeAzi()
        if ( (abs(self.DomeAzi - az) < 5) or
             (self.DomeAzi < 0) or
             (time.time() - self.DomeLastTime) > MAXDOMEMOVE ):
          digio.DomeStop()
          self.Command = None
          self.DomeInUse = False
        else:
          if az > self.DomeAzi:
            if (az - self.DomeAzi) < 180:
              digio.DomeRight()
            else:
              digio.DomeLeft()
          else:
            if (self.DomeAzi - az) < 180:
              digio.DomeLeft()
            else:
              digio.DomeRight()

  def move(self, az=None, force=False):
    """Add a 'move' command to the dome command queue, to be executed as soon as the dome is free.
       If a safety interlock is active, exit with an error unless the 'force' argument is
       True.

       The 'az' parameter defines the dome azimuth to move to - 0-360, where 0=North and
       90 is due East.
    """
    if not self.AutoDome:
      logger.error('nzdome.Dome.move: Dome not in auto mode.')
      return
    if type(az) == float or type(az) == int:
      if az < 0 or az > 360:
        logger.error("nzdome.Dome.move: argument must be an integer between 0 and 359, not %d" % az)
        return
    else:
      logger.error("nzdome.Dome.move: argument must be an integer between 0 and 359, not: %s" % az)
      return
    if safety.Active.is_set() or force:
      self.queue.append(str(int(az)))
    else:
      logger.error('nzdome.Dome.move: no dome activity until safety tags cleared.')

  def open(self, force=False):
    """If the safety interlock is not active, or the 'force' argument is true,
       add an 'open shutter' command to the dome command queue.
    """
    if not self.AutoDome:
      logger.error('nzdome.Dome.move: Dome not in auto mode.')
      return
    if safety.Active.is_set() or force:
      self.queue.append('O')
      self.queue.append('I')    #Check shutter status after the open command
    else:
      logger.error('nzdome.Dome.move: no dome activity until safety tags cleared.')

  def close(self, force=False):
    """If the safety interlock is not active, or the 'force' argument is true,
       add an 'close shutter' command to the dome command queue.
    """
    if not self.AutoDome:
      logger.error('nzdome.Dome.move: Dome not in auto mode.')
      return
    if safety.Active.is_set() or force:
      self.queue.append('C')
      self.queue.append('I')    #Check shutter status after the close command
    else:
      logger.error('System stopped, no dome activity until safety tags cleared.')

  def CalcAzi(self, Obj):
    """Calculates the dome azimuth for a given telescope position, passed as a
       correct.CalcPosition object. If that object has a DomePos attribute that is
       a valid number, use that instead of the calculated value.

       Because the telescope is mounted off-centre on the equatorial axis, and the
       dome radius is roughly the as the tube length, there is a considerable
       difference between telescope and dome azimuth.

       The correction is made by transforming the position of the centre of the
       telescope tube to cartesian coordinates (x0,y0,z0), projecting the direction
       of the telescope from that position to the surface of the dome sphere (Exx2, Why2, Zee2),
       and transforming that back to polar coordinates for the dome centre.

       Returns the calculated dome azimuth, in degrees.
    """
    if (type(Obj.DomePos) == float) or (type(Obj.DomePos) == int):
      return float(Obj.DomePos)     #Hard-wired dome azimuth in position record.
    if prefs.EastOfPier:
      p = -ABSP
    else:
      p = ABSP
    ObjRA = Obj.Ra/54000                     #in hours
    AziRad = DegToRad(Obj.Azi)
    AltRad = DegToRad(Obj.Alt)
    ha = DegToRad((Obj.Time.LST-ObjRA)*15)   #in rads

    y0 = -p*math.sin(ha)*math.sin(DegToRad(prefs.ObsLat))    #N-S component of scope centre displacement from dome centre
    x0 = p*math.cos(ha)                                      #E-W component of scope centre displacement from dome centre
    z0 = ETA-p*math.sin(ha)*math.cos(DegToRad(prefs.ObsLat)) #up-down component of scope centre displacement from dome centre
    a = -math.cos(AltRad)*math.sin(AziRad)
    b = -math.cos(AltRad)*math.cos(AziRad)
    c = math.sin(AltRad)
    Alpha = (a*a+c*c)/(b*b)
    Beta = 2*(a*x0+c*z0)/b
    Aye = Alpha + 1
    Bee = Beta - 2*Alpha*y0
    Cee = Alpha*y0*y0 - Beta*y0 + x0*x0 + z0*z0 - 1
    Why1 = ( -Bee + math.sqrt(Bee*Bee-4*Aye*Cee) )/(2*Aye)
    Exx1 = ((Why1-y0)*a/b + x0)
    Zee1 = (Why1-y0)*c/b + z0
    Why2 = ( -Bee - math.sqrt(Bee*Bee-4*Aye*Cee) )/(2*Aye)
    Exx2 = ((Why2-y0)*a/b + x0)
  #  Zee2 = (Why2-y0)*c/b + z0                         #Not necessary as we only want the corrected Azimuth, not elevation
    if Zee1>0:
      Azi = RadToDeg(math.atan2(Exx1,Why1))
    else:
      Azi = RadToDeg(math.atan2(Exx2,Why2))

    Azi += 180
    if Azi > 360:
      Azi -= 360

    return Azi




def DegToRad(r):    #Originally in MATHS.PAS
  """Given an argument in degrees, return the value converted to radians.
  """
  return (float(r)/180)*math.pi


def RadToDeg(r):    #Originally in MATHS.PAS
  """Given an argument in radians, return the value converted to degrees.
  """
  return (r/math.pi)*180


dome = Dome()

ConfigDefaults.update({'DomeTracking':'0', 'DomeEncoderOffset':DENCODEROFFSET, 'DefaultAutoDome':0})
CP,CPfile = UpdateConfig()

dome.DomeTracking = CP.getboolean('Toggles','DomeTracking')
dome.AutoDome = CP.getboolean('Toggles','DefaultAutoDome')
dome.EncoderOffset = CP.getint('Dome', 'DomeEncoderOffset')


