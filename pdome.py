
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

ser = None   #Later instantiated as serial device


class DomeStatus:
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


def DomeAzi():
  """Return the current dome azimuth in degrees (or the destination azimuth if moving).
  """
  return status.NewDomeAzi


def DomeHalt():
  """Stop all dome motion. Can't be done using Perth dome (no effect).
  """
  pass
  
  
def DomeSetMode(mode=None):
  """Set the state of the AutoDome flag to the value given. If the argument is
     True, the dome will be moved by Teljoy. If False, Teljoy will not attempt to 
     move the dome under any condition.
     
     If no argument is given, ask the user on the command line for a Y/N response.
  """
  if type(mode)<>str and (mode is not None):
    status.AutoDome = bool(mode)
    return
  elif type(mode) == str:
    val = mode
  else:
    val = raw_input("Is dome in automatic mode? (Y/n): ")
  val = val.upper().strip()[:1]
  status.AutoDome = (val <> 'N')
  

def DomeCalcAzi(Obj):
  """Calculates the dome azimuth for a given telescope position, passed as a
     correct.CalcPosition object.
     
     Because the telescope is mounted off-centre on the equatorial axis, and the
     dome radius is roughly the as the tube length, there is a considerable
     difference between telescope and dome azimuth. 
     
     The correction is made by transforming the position of the centre of the 
     telescope tube to cartesian coordinates (x0,y0,z0), projecting the direction
     of the telescope from that position to the surface of the dome sphere (Exx2, Why2, Zee2), 
     and transforming that back to polar coordinates for the dome centre.
     
     Returns the calculated dome azimuth, in degrees.
  """
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

  Azi = Azi + 180
  if (Azi > 360):
    Azi = Azi - 360

  return Azi


def WaitPrompt():
  """If not busy, the dome controller will return a '?' prompt in response to a CR character.
     If it's busy, the dome controller will consume and ignore any input.
     
     This function will see if a prompt has been sent by the controller. If so, it returns True.
     If not, it sends a CR character to the controller and returns 'False'.
  """
  chars = []
  c = ''
  while c <> '':
    c = ser.read(1)
    chars.append(c)
  gots = ''.join(chars)

  if '?' not in gots:
    ser.write(chr(13))
    time.sleep(0.2)
    return False
  else:
    time.sleep(0.3)
    return True


def DomeInitialise():
  """Set up serial port, and initialise dome status flags.
  """
  global ser
  ser = serial.Serial('/dev/ttyS%d' % DOMEPORT, baudrate=1200, stopbits=serial.STOPBITS_TWO, timeout=0.1)
  status.DomeInUse = False
  status.DomeThere = True
  status.ShutterInUse = False
  status.NewShutter = ''


def DomeMove(az=None):
  """Move dome to the specified azimuth. Return immediately without waiting for the move to
     finish, or even guarantee that the move command has been sent - this function is likely to
     do nothing unless DomeCheckMove is being called repeatedly to actually manage the communications
     with the dome controller (eg by the detevent.DetermineEvent loop).
     
     If the dome or shutter is in use, this function exits with an error.
     
     If the dome controller is busy, and hasn't returned a prompt, set the desired azimuth and 
     let later calls to DomeCheckMove do the actual communication.
  """
  if not status.AutoDome:
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
  if status.DomeInUse or status.ShutterInUse:
    logger.error("pdome.DomeMove: Dome or shutter active - wait for it to finish...")
    return
  status.NewDomeAzi = az
  status.DomeInUse = True
  status.DomeThere = False
  status.DomeMoved = False
  if WaitPrompt():               #if the controller isn't busy, send the new azimuth
    status.DomeMoved = True
    ser.write('%d' % az)


def DomeCheckMove():
  """Should be called repeatedly (eg by detevent.DetermineEvent) to manage communication
     with the dome controller.
  """
  if status.DomeInUse:
    if status.DomeMoved:
      status.DomeThere = WaitPrompt()
    else:
      if WaitPrompt():
        status.DomeMoved = True
        ser.write('%d' % status.NewDomeAzi)
    if status.DomeThere:
      status.DomeInUse = False
      status.DomeLastTime = time.time()
  if status.ShutterInUse:
    if status.DomeMoved:
      status.DomeThere = WaitPrompt()
    else:
      if WaitPrompt():
        status.DomeMoved = True
        ser.write(status.NewShutter+chr(13))
    if status.DomeThere:
      status.ShutterInUse = False


def DomeOpen():
  """Open dome shutter. Return immediately without waiting for the shutter to finish opening, or even
     guarantee that the open command has been sent - this function is likely to
     do nothing unless DomeCheckMove is being called repeatedly to actually manage the communications
     with the dome controller (eg by the detevent.DetermineEvent loop).
     
     If the dome or shutter is in use, this function exits with an error.
     
     If the dome controller is busy, and hasn't returned a prompt, set the desired shutter state and 
     let later calls to DomeCheckMove do the actual communication.
  """
  if not status.AutoDome:
    logger.error('pdome.DomeOpen: Dome not in auto mode.')
    return
  if status.DomeInUse or status.ShutterInUse:
    logger.error('pdome.DomeOpen: Dome or shutter active - wait for it to finish...')
    return

  status.NewShutter = 'O'
  status.ShutterOpen = True
  status.ShutterInUse = True
  status.DomeThere = False
  status.DomeMoved = False
  if WaitPrompt():              #if the controller isn't busy, send the new shutter state
    status.DomeMoved = True
    ser.write('O'+chr(13))


def DomeClose():
  """Close dome shutter. Return immediately without waiting for the shutter to finish closing, or even
     guarantee that the close command has been sent - this function is likely to
     do nothing unless DomeCheckMove is being called repeatedly to actually manage the communications
     with the dome controller (eg by the detevent.DetermineEvent loop).
     
     If the dome or shutter is in use, this function exits with an error.
     
     If the dome controller is busy, and hasn't returned a prompt, set the desired shutter state and 
     let later calls to DomeCheckMove do the actual communication.
  """
  if not status.AutoDome:
    logger.error('pdome.DomeClose: Dome not in auto mode.')
    return
  if status.DomeInUse or status.ShutterInUse:
    logger.error('pdome.DomeClose: Dome or shutter active - wait for it to finish...')
    return

  status.NewShutter = 'C'
  status.ShutterOpen = False
  status.ShutterInUse = True
  status.DomeThere = False
  status.DomeMoved = False
  if WaitPrompt():               #if the controller isn't busy, send the new shutter state
    status.DomeMoved = True
    ser.write('C'+chr(13))


def DomeOpenWait():
  """Open dome shutter, and return when the shutter is fully open.
     This function is likely to do nothing unless DomeCheckMove is being
     called repeatedly to actually manage the communications
     with the dome controller (eg by the detevent.DetermineEvent loop).
     
     If the dome or shutter is in use, this function gives an error and
     doesn't open the dome shutter.
  """
  DomeOpen()
  logger.debug('pdome.DomeOpenWait: Waiting for shutter')
  while status.ShutterInUse:
    time.sleep(1)
  

def DomeCloseWait():
  """Close dome shutter, and return when the shutter is fully closed.
     This function is likely to do nothing unless DomeCheckMove is being
     called repeatedly to actually manage the communications
     with the dome controller (eg by the detevent.DetermineEvent loop).
     
     If the dome or shutter is in use, this function gives an error and
     doesn't close the dome shutter.
  """
  DomeClose()
  logger.debug('pdome.DomeCloseWait: Waiting for shutter:')
  while status.ShutterInUse:
    time.sleep(1)
  
  
def DomeMoveWait(Azi):
  """Move dome to the specified azimuth, and return when the dome has reached the desired position.
     This function is likely to do nothing unless DomeCheckMove is being called repeatedly to actually manage the communications
     with the dome controller (eg by the detevent.DetermineEvent loop).
     
     If the dome or shutter is in use, this function gives an error and doesn't move the dome.
  """
  DomeMove(Azi)
  logger.debug('pdome.DomeMoveWait: Waiting for dome:')
  while status.DomeInUse:
    time.sleep(1)


def DegToRad(r):    #Originally in MATHS.PAS
  return (float(r)/180)*math.pi

def RadToDeg(r):    #Originally in MATHS.PAS
  return (r/math.pi)*180


status = DomeStatus()

ConfigDefaults.update({'DomeTracking':'0', 'AskDomeStatus':0, 'DefaultAutoDome':0})
CP,CPfile = UpdateConfig()

status.DomeTracking = CP.getboolean('Toggles','DomeTracking')
ask = CP.getboolean('Toggles','AskDomeStatus')
status.AutoDome = CP.getboolean('Toggles','DefaultAutoDome')
if ask:
  DomeSetMode()
  
