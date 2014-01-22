
"""
   Dome control module for  Perth telescope. All dome control is via a serial port to the
   dome controller.

   Arie's dome controller API for Perth telescope:

   interface is 1200 baud, 8 bits, two stop bits, no handshaking (HW or SW)

   Send a CR character to the dome. If it's busy, there will be no response.
   If it's ready for a command, it responds with three characters: CR, LF, '?'.

   Commands:
        'O',CR - opens the dome.
        'C',CR - closes the dome
        an integer azimuth in degrees, followed by a CR character - slews the dome
        'S',CR - recalibrate the dome encoders by slewing 175 degrees
        'I',CR - ask for the current dome shutter state. Returns CR,LF,'OD', or
                 CR,LF,'CD' depending on whether the dome is open (OD) or
                 closed (CD). This is followed by a return prompt (CR,LF,'?').

    Dome failure:
      If the dome fails to move when commanded, after 60 seconds, the controller will:
        -turn off the dome motors
        -close the shutter
        -repeat:
          -wait for 10 seconds
          -sound the alarm for 12 seconds
          -send CR, LF, and 'FD'
"""

import math
import serial
import time

from globals import *

#Dome parameters:
RD = 3.48                             #Dome radius, in metres
ABSP = 0.55/RD                        #Distance from centre of telescope tube to dome center, in metres
ETA = 0.2/RD                          #?

#Serial port for communication with dome controller:
DOMEPORT = 0     #Python serial ports numbered 0,1,2,..., Pascal ports numbered 1,2,3,...



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
    self.queue = []
    try:
      self.ser = serial.Serial('/dev/ttyS%d' % DOMEPORT, baudrate=1200, stopbits=serial.STOPBITS_TWO, timeout=0.2, rtscts=False, xonxoff=False, dsrdtr=False)
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

  def __call__(self, arg, **kwargs):
    """This method is run when an instance of this class is treated like a function, and called.
       Defining it allows the global 'dome' variable containing the current dome state to be
       treated like a function, so dome(123) would move the dome to Azi=123 degrees, and
       dome('open') or dome('close) would open and close the shutter.

       This is purely for the convenience of the human at the command line, you can
       also simply call dome.move(123), dome.open() or dome.close().
    """
    if type(arg)==int or type(arg)==float:
      self.move(arg, **kwargs)
    elif type(arg)==str:
      if arg.upper() in ['O','OPEN']:
        self.open(**kwargs)
      elif arg.upper() in ['C','CLOSE']:
        self.close(**kwargs)
      else:
        print "Unknown argument: specify an azimuth in degrees, or 'open', or 'close'"
    else:
      print "Unknown argument: specify an azimuth in degrees, or 'open', or 'close'"

  def _waitprompt(self):
    """If not busy, the dome controller will return a '?' prompt in response to a CR character.
       If it's busy, the dome controller will consume and ignore any input.

       This method will see if a prompt has been sent by the controller. If so, it returns True.
       If not, it sends a CR character to the controller and returns 'False'.
    """
    chars = []
    c = 'X'
    while c <> '':
      c = self.ser.read(1)
      chars.append(c)
    gots = ''.join(chars)

    if gots:
      self._parse_response(gots)

    if '?' not in gots:
      self.ser.write(chr(13))
      time.sleep(0.2)
      return False
    else:
      time.sleep(0.3)
      return True

  def _parse_response(self, gots):
    """Look at the string returned from the dome controller, and if it's got a 'I' command response (either
       'OD' or 'CD', save that as the dome shutter state. If it contains 'FD', flag a dome failure error.
    """
    if 'OD' in gots:
      self.IsShutterOpen = True
    elif 'CD' in gots:
      self.IsShutterOpen = False
    elif 'FD' in gots:
      self.DomeFailed = True
      self.AutoDome = False
      self.Command = None
      self.CommandSent = False
      self.queue = []
      self.ShutterOpen = False
      safety.add_tag('Dome Failed to rotate, dome controller shutdown. Restart Teljoy to clear.')

  def check(self):
    """Should be called repeatedly (eg by detevent loop) to manage communication
       with the dome controller.
    """
    if not self.AutoDome:
      return
    if self.queue and not self.Command:  # If we aren't already processing a command, and there's one in the queue, do it now.
      self.Command = self.queue.pop(0)

    if self.Command:
      if self.CommandSent:
        if self._waitprompt():      #The command was sent earlier, and now a prompt has been received
          if self.Command == 'O':
            self.ShutterOpen = True
          elif self.Command == 'C':
            self.ShutterOpen = False
          elif self.Command == 'I':
            if self.IsShutterOpen is None:
              logger.error("'I' command to dome controller didn't return shutter state.")
            else:
              if self.IsShutterOpen <> self.ShutterOpen:
                logger.error("Shutter state from dome controller doesn't match desired shutter state. Resending command.")
                self.queue.append(self.Command)
                self.queue.append('I')
          else:
            try:
              az = int(float(self.Command))
              if (az < 0) or (az > 360):
                logger.error('Invalid command in dome.Command: %s' % self.Command)
              self.DomeAzi = az
              self.DomeLastTime = time.time()
            except ValueError:
              logger.error('Invalid command in dome.Command: %s' % self.Command)
          self.Command = None
          self.CommandSent = False
          self.DomeInUse = False
      else:
        self.DomeInUse = True       #There is a new command, but it hasn't been sent yet.
        if self._waitprompt():
          if self.Command == 'O':
            self.ShutterOpen = True
            self.CommandSent = True
            self.ser.write('O' + chr(13))
          elif self.Command == 'C':
            self.ShutterOpen = False
            self.CommandSent = True
            self.ser.write('C' + chr(13))
          elif self.Command == 'I':
            self.IsShutterOpen = None    #unknown until we receive the result
            self.CommandSent = True
            self.ser.write('I' + chr(13))
          else:
            try:
              az = int(self.Command)
              if (az < 0) or (az > 360):
                logger.error('Invalid command in dome command queue: %s' % self.Command)
              self.ser.write(self.Command + chr(13))
              self.CommandSent = True
            except ValueError:
              logger.error('Invalid command in dome command queue: %s' % self.Command)

  def move(self, az=None, force=False):
    """Add a 'move' command to the dome command queue, to be executed as soon as the dome is free.
       If a safety interlock is active, exit with an error unless the 'force' argument is
       True.

       The 'az' parameter defines the dome azimuth to move to - 0-360, where 0=North and
       90 is due East.
    """
    if not self.AutoDome:
      logger.error('pdome.Dome.move: Dome not in auto mode.')
      return
    if type(az) == float or type(az) == int:
      if az < 0 or az > 360:
        logger.error("pdome.Dome.move: argument must be an integer between 0 and 359, not %d" % az)
        return
    else:
      logger.error("pdome.Dome.move: argument must be an integer between 0 and 359, not: %s" % az)
      return
    if safety.Active.is_set() or force:
      self.queue.append(str(int(az)))
    else:
      logger.error('pdome.Dome.move: no dome activity until safety tags cleared.')

  def open(self, force=False):
    """If the safety interlock is not active, or the 'force' argument is true,
       add an 'open shutter' command to the dome command queue.
    """
    if not self.AutoDome:
      logger.error('pdome.Dome.move: Dome not in auto mode.')
      return
    if safety.Active.is_set() or force:
      self.queue.append('O')
      self.queue.append('I')    #Check shutter status after the open command
    else:
      logger.error('pdome.Dome.move: no dome activity until safety tags cleared.')

  def close(self, force=False):
    """If the safety interlock is not active, or the 'force' argument is true,
       add an 'close shutter' command to the dome command queue.
    """
    if not self.AutoDome:
      logger.error('pdome.Dome.move: Dome not in auto mode.')
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

ConfigDefaults.update({'DomeTracking':'0', 'AskDomeStatus':0, 'DefaultAutoDome':0})
CP,CPfile = UpdateConfig()

dome.DomeTracking = CP.getboolean('Toggles','DomeTracking')
dome.AutoDome = CP.getboolean('Toggles','DefaultAutoDome')

