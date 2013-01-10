
"""
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
DOMEPORT = 1     #Python serial ports numbered 0,1,2,..., Pascal ports numbered 1,2,3,...



class Dome:
  """An instance of this class is used to store the current dome motion 
     state, as well as some dome control preferences.
  """
  def __init__(self):
    self.DomeInUse = False          #True if the dome is moving
    self.ShutterInUse = False       #True if the shutter is moving
    self.DomeMoved = False          #True if the 'move' command has been sent to the dome already
    self.ShutterOpen = False        #True if the shutter is open
    self.DomeThere = True           #True if the dome movement has finished
    self.AutoDome = True            #True if the dome can be controlled, False if it's in 'Manual only' mode
    self.DomeTracking = False       #True if the dome should dynamically track the current telescope position.
                                    #   if false, the dome will only be moved if AutoDome is True, and detevent.Jump is called.
    self.DomeLastTime = 0           #Last time the dome was moved. Used for DomeTracking to prevent frequent small moves
    self.NewDomeAzi = 0             #Desired dome azimuth for move, or current dome azimuth if move has finished
    self.NewShutter = ''            #Desired shutter state ('O' or 'C') for open/close
    self.ser = serial.Serial('/dev/ttyS%d' % DOMEPORT, baudrate=1200, stopbits=serial.STOPBITS_TWO, timeout=0.1)
    if CLASSDEBUG:
      self.__setattr__ = self.debug

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

  def _waitprompt(self):
    """If not busy, the dome controller will return a '?' prompt in response to a CR character.
       If it's busy, the dome controller will consume and ignore any input.

       This method will see if a prompt has been sent by the controller. If so, it returns True.
       If not, it sends a CR character to the controller and returns 'False'.
    """
    chars = []
    c = ''
    while c <> '':
      c = self.ser.read(1)
      chars.append(c)
    gots = ''.join(chars)

    if '?' not in gots:
      self.ser.write(chr(13))
      time.sleep(0.2)
      return False
    else:
      time.sleep(0.3)
      return True

  def move(self, az=None):
    """Move dome to the specified azimuth. Return immediately without waiting for the move to
       finish, or even guarantee that the move command has been sent - this function is likely to
       do nothing unless self.check is being called repeatedly to actually manage the communications
       with the dome controller (eg by the detevent.DetermineEvent loop).

       If the dome or shutter is in use, this function exits with an error.

       If the dome controller is busy, and hasn't returned a prompt, set the desired azimuth and
       let later calls to DomeCheckMove do the actual communication.
    """
    if not self.AutoDome:
      logger.error('pdome.DomeMove: Dome not in auto mode.')
      return
    if type(az) == float or type(az) == int:
      if az < 0 or az > 360:
        logger.error("pdome.DomeMove: argument must be an integer between 0 and 359, not %d" % az)
        return
    elif az is None:
      try:
        val = raw_input("Enter new dome azimuth(0-359): ")
        az = int(val)
        if az < 0 or az > 359:
          assert ValueError
      except ValueError:
        print "Must be an integer between 0 and 359, not %d" % az
        return
    if abs(az-self.NewDomeAzi) < 2.0:
      logger.debug('pdome.DomeMove: no dome slew required')
      return
    if self.DomeInUse or self.ShutterInUse:
      logger.error("pdome.DomeMove: Dome or shutter active - wait for it to finish...")
      return
    self.NewDomeAzi = az
    self.DomeInUse = True
    self.DomeThere = False
    self.DomeMoved = False
    if self._waitprompt():               #if the controller isn't busy, send the new azimuth
      self.DomeMoved = True
      self.ser.write('%d' % az)

  def check(self):
    """Should be called repeatedly (eg by detevent.DetermineEvent) to manage communication
       with the dome controller.
    """
    if self.DomeInUse:
      if self.DomeMoved:
        self.DomeThere = self._waitprompt()
      else:
        if self._waitprompt():
          self.DomeMoved = True
          self.ser.write('%d' % self.NewDomeAzi)
      if self.DomeThere:
        self.DomeInUse = False
        self.DomeLastTime = time.time()
    if self.ShutterInUse:
      if self.DomeMoved:
        self.DomeThere = self._waitprompt()
      else:
        if self._waitprompt():
          self.DomeMoved = True
          self.ser.write(self.NewShutter+chr(13))
      if self.DomeThere:
        self.ShutterInUse = False

  def open(self):
    """Open dome shutter. Return immediately without waiting for the shutter to finish opening, or even
       guarantee that the open command has been sent - this function is likely to
       do nothing unless DomeCheckMove is being called repeatedly to actually manage the communications
       with the dome controller (eg by the detevent.DetermineEvent loop).

       If the dome or shutter is in use, this function exits with an error.

       If the dome controller is busy, and hasn't returned a prompt, set the desired shutter state and
       let later calls to DomeCheckMove do the actual communication.
    """
    if not self.AutoDome:
      logger.error('pdome.DomeOpen: Dome not in auto mode.')
      return
    if self.DomeInUse or self.ShutterInUse:
      logger.error('pdome.DomeOpen: Dome or shutter active - wait for it to finish...')
      return

    self.NewShutter = 'O'
    self.ShutterOpen = True
    self.ShutterInUse = True
    self.DomeThere = False
    self.DomeMoved = False
    if self._waitprompt():              #if the controller isn't busy, send the new shutter state
      self.DomeMoved = True
      self.ser.write('O'+chr(13))

  def close(self):
    """Close dome shutter. Return immediately without waiting for the shutter to finish closing, or even
       guarantee that the close command has been sent - this function is likely to
       do nothing unless DomeCheckMove is being called repeatedly to actually manage the communications
       with the dome controller (eg by the detevent.DetermineEvent loop).

       If the dome or shutter is in use, this function exits with an error.

       If the dome controller is busy, and hasn't returned a prompt, set the desired shutter state and
       let later calls to DomeCheckMove do the actual communication.
    """
    if not self.AutoDome:
      logger.error('pdome.DomeClose: Dome not in auto mode.')
      return
    if self.DomeInUse or self.ShutterInUse:
      logger.error('pdome.DomeClose: Dome or shutter active - wait for it to finish...')
      return

    self.NewShutter = 'C'
    self.ShutterOpen = False
    self.ShutterInUse = True
    self.DomeThere = False
    self.DomeMoved = False
    if self._waitprompt():               #if the controller isn't busy, send the new shutter state
      self.DomeMoved = True
      self.ser.write('C'+chr(13))

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
  return (float(r)/180)*math.pi

def RadToDeg(r):    #Originally in MATHS.PAS
  return (r/math.pi)*180


dome = Dome()

ConfigDefaults.update({'DomeTracking':'0', 'AskDomeStatus':0, 'DefaultAutoDome':0})
CP,CPfile = UpdateConfig()

dome.DomeTracking = CP.getboolean('Toggles','DomeTracking')
dome.AutoDome = CP.getboolean('Toggles','DefaultAutoDome')

