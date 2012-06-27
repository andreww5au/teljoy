
# Uses: Dos, PC23io, Crt, Use32, VPUtils, Os2Def, Os2Base
#  globals, DigIO

import math
import threading
import sys
import time

from globals import *
import dummycon
import dbobj
import sqlint

MOTOR_ACCEL = 2.0*25000            #2.0 (revolutions/sec/sec) * 25000 (steps/rec)
PULSE = 0.05                   #50 milliseconds per 'tick'
POWERMSK = 0x01
HORIZMSK = 0x02
MESHMSK  = 0x04
EASTMSK  = 0x08
WESTMSK  = 0x10


"""
   Public variables:
   hexstr:array[0..15] of char

   RAsid:double
   RA_track:double    #RA Non-sidereal tracking velocity - steps/50ms
   DEC_track:double   #as for RA
   RA_jump:double     #jump velocity in RA - steps/50ms
   DEC_jump:double    #as for DEC
   RA_remain:double   #remainder in RA - used in telescope jump
   DEC_remain:double  #remainder in DEC - used in telescope jump
   int_RA:integer   #integer part of send_RA, the distance to move in this 50ms tick
   int_DEC:integer  #as for RA
   frac_RA:double     #fractional part of send_RA
   frac_DEC:double    #as for RA
   RA_hold:integer  #Used to delay one 50ms pulse value if direction changes
   DEC_hold:integer  #as for RA
   RA_up:longint    #number of 50ms ticks to ramp motor to max velocity
   RA_plateau:longint #number of 50ms ticks in the plateau of an RA jump
   RA_down:longint  #number of 50ms ticks to ramp motor down after RA jump
   DEC_up:longint     #as for RA
   DEC_plateau:longint  #as for RA
   DEC_down:longint     #as for RA
   max_vel:double     #maximum motor velocity in steps/50ms
   RA_max_vel:double  #plateau velocity in RA in steps/50ms
   DEC_max_vel:double #as for RA
   Paddle_start_RA:boolean  # true if RA paddle button pressed
   Paddle_stop_RA:boolean   # true if RA paddle button released
   Paddle_start_DEC:boolean   #as for RA
   Paddle_stop_DEC:boolean   #as for RA
   teljump:boolean     # true if telescope is jumping to new coords
   finish_RA:boolean   # true if move in RA axis is finished
   finish_DEC:boolean    #as for RA
   add_to_vel:double     #delta velocity ramp
   RA_add_vel:double     #delta velocity for ramp in RA axis
   DEC_add_vel:double      #as for RA
   sign_RA:boolean    #flag used to detected change in motor direction
   sign_DEC:boolean      #as above
   old_sign_RA:boolean   #as above
   old_sign_DEC:boolean  #as above
   DEC_scl:integer    #Correction to the down ramp on a jump
   RA_scl:integer       #as for Dec
   RA_max:double    #used for jump scaling
   DEC_max:double         #as above
   i:integer
   RA_Refraction:double       #real time refraction correction
   DEC_Refraction:double      #as above
   RA_padlog:double        #Log of paddle movements
   DEC_padlog:double       #as above
   RA_reflog:double        #Log of refraction movements
   DEC_reflog:double       #as above
   ticks:longint  #milliseconds since int. started (inc. by 300 evry 300msec)
   PosDirty:boolean   #true if telescope has just finished moving, and the
                    #position log file is out of date
   RA_Guide:integer           #Guide rate movement accumulator, in 'ticks'
   DEC_Guide:integer          #as above
   RA_Guidelog:double   #log of guide motion, in motor steps, zeroed on in each detevent loop
   DEC_Guidelog:double
   Watchdog:integer    #Incremented by DetermineEvent, zeroed by PC23 queue
                        #calculation loop if all is well
   GuideDebug:byte
   HRticktime:double   #Period, in milliseconds, of the HR timer tick
   HRlast, HRnow: QWord #Quad word, with .hi and .lo integer parts

   Plus internally only:

     IntExitSave:pointer
     OldInt3Vec:pointer
     fb,lb:byte
     CutFrac:0..10   #fraction of distance to cut for limit decelleration
                     #1=10%, 5=50%, etc. Normally 0, counts up to 10 after
                     #limit is hit
"""

intthread = None

def KickStart():
  global intthread

  dummycon.send(0,0)
  dummycon.send(0,0)
  dummycon.send(0,0)
  intthread = threading.Thread(target=motors.Timeint, name='Timeint-thread')
  intthread.daemon = True
  intthread.start()
  dummycon.init()
    


class LimitStatus(dbobj.dbObject):
  """Class to represent the hardware limit state/s. 
     Only one instance of this class should be created, unless the code is controlling
     two or more telescopes. Inherits from dbobj.dbObject to allow state to be saved to
     and an SQL database.
  """
  _table='teljoy.limits'
  _attribs = [('pkey','pkey',0),
              ('LimitOnTime','ontime',0.0),
              ('LimitOffTime','offtime',0.0),
              ('OldLim','oldlim',False),
              ('PowerOff','poweroff',False),
              ('HorizLim','horizlim',False),
              ('MeshLim','meshlim',False),
              ('EastLim','eastlim',False),
              ('WestLim','westlim',False),
              ('HWLimit','hwlimit',False),
              ('LimOverride','limoverride',False),
              ('ModTime','modtime',0) ]
  _readonly = ['ModTime']
  _key = ('pkey',)
  _reprf = ( '<LimitStatus: On: %(LimitOnTime)d, Off: %(LimitOffTime)d - ' +
             '%(HWLimit)s [Old=%(OldLim)s, PowerOff=%(PowerOff)s, ' + 
             'Horiz=%(HorizLim)s, Mesh=%(MeshLim)s, East=%(EastLim)s, West=%(WestLim)s, Override=%(LimOverride)s]>')
  _strf = ( 'HWLimits=%(HWLimit)s [Old=%(OldLim)s, PowerOff=%(PowerOff)s, ' + 
             'Horiz=%(HorizLim)s, Mesh=%(MeshLim)s, East=%(EastLim)s, West=%(WestLim)s, Override=%(LimOverride)s]' )
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname

  def __init__(self, db=None):
    self.db = db
    if db is not None:
      dbobj.dbObject.__init__(self, 'now', db=db)
    else:
      self.empty()
    if CLASSDEBUG:
      self.__setattr__ = self.debug
      
  def save(self, db=None, commit=True, verbose=False):
    if db is None:
      db = self.db
    if db is None:
      logger.warn('motion.LimitStatus.save: No SQL connection.')
      return None
    dbobj.dbObject.save(self, ask=False, force=True, db=db, commit=commit, verbose=verbose)

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

  def CanEast(self):
    return (not self.HWLimit) or (self.LimOverride and self.WestLim)

  def CanWest(self):
    return (not self.HWLimit) or (self.LimOverride and self.EastLim)

  def check(self):
    if (not self.OldLim) and (self.HWLimit):
      motors.Frozen = True
      self.LimitOnTime = time.time()
      self.LimitOffTime = sys.maxint
      self.OldLim = True
    if ( (not self.PowerOff) and (not self.HorizLim) and (not self.MeshLim) and
         (not motors.moving) and (not self.EastLim) and (not self.WestLim) and self.HWLimit ):
      motors.Frozen = False
      self.OldLim = False
      self.HWLimit = False
      self.LimOverride = False



class MotorControl():
  """An instance of this class handles all low-level motion control, with one method
     (TimeInt) running continuously in a background thread to keep the controller 
     queue full.
  """
  def __init__(self):
    logger.debug('motion.MotorControl.__init__: Initializing Global variables')
    self.RA_up = 0              #number of 50ms ticks to ramp motor to max velocity for slew
    self.RA_down = 0            #number of 50ms ticks to ramp motor down after slew
    self.DEC_up = 0             #number of 50ms ticks to ramp motor to max velocity for slew
    self.DEC_down = 0           #number of 50ms ticks to ramp motor down after slew
    self.RA_plateau = 0         #number of 50ms ticks in the plateau of a slew
    self.DEC_plateau = 0        #number of 50ms ticks in the plateau of a slew
    self.RA_track = 0.0         #RA Non-sidereal tracking velocity - steps/50ms
    self.DEC_track = 0.0        #Dec Non-sidereal tracking velocity - steps/50ms
    self.RA_add_vel = 0.0       #RA accelleration for slews
    self.DEC_add_vel = 0.0      #DEC accelleration for slews
    self.RA_max_vel = 0.0       #plateau velocity in RA in steps/50ms for current slew
    self.DEC_max_vel = 0.0      #plateau velocity in Dec in steps/50ms for current slew

    self.RA_jump = 0.0          #Current slew velocity in RA - steps/50ms
    self.DEC_jump = 0.0         #Current slew velocity in Dec - steps/50ms
    self.RA_remain = 0.0        #remainder in RA after calculating ramp profile - used in telescope jump
    self.DEC_remain = 0.0       #remainder in Dec after calculating ramp profile - used in telescope jump
    self.finish_RA = True
    self.finish_DEC = True
    self.Paddle_start_RA = False
    self.Paddle_stop_RA = False
    self.Paddle_start_DEC = False
    self.Paddle_stop_DEC = False
    self.Teljump = False
    self.moving = False
    self.PosDirty = False
    self.RA_scl = 0             #How many ticks we have been decellerating for on the ramp down from a slew
    self.DEC_scl = 0            #How many ticks we have been decellerating for on the ramp down from a slew
    self.RA_refraction = 0.0
    self.DEC_refraction = 0.0
    self.RA_padlog = 0.0
    self.DEC_padlog = 0.0
    self.RA_reflog = 0
    self.DEC_reflog = 0
    self.RA_Guide = 0
    self.DEC_Guide = 0
    self.RA_Guidelog = 0
    self.DEC_Guidelog = 0
    self.CutFrac = 0
    self.ticks = 0
    self.Frozen = False
    logger.debug('motion.MotorControl.__init__: finished global vars')
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
    
  def CalcPaddle(self):
    """The paddle code in the 'Determine Event' loop communicates with the motor control object by 
       calling start_motor and stop_motor. These functions in turn set the motor control attributes:
          AXIS_up, AXIS_down                     #ramp up/down time in ticks
          Paddle_start_AXIS, Paddle_stop_AXIS    #Booleans
          AXIS_max_vel                           #plateau velocity in steps/tick
          AXIS_add_vel                           #ramp accell/decell in steps/tick/tick
       This function, called once per tick as the motion control values are calculated, uses the 
       above flags to calculate the current velocity components for this tick due to a hand-paddle slew,
       stored in RA_jump and DEC_jump. 
    """
    if self.Paddle_start_RA:
      if self.RA_up > 0:
        self.RA_jump += self.RA_add_vel
        self.RA_up -= 1
        self.RA_down += 1
      else:
        self.RA_jump = self.RA_max_vel     #continue till paddle button released

    if self.Paddle_start_DEC:
      if self.DEC_up > 0:
        self.DEC_jump += self.DEC_add_vel
        self.DEC_up -= 1
        self.DEC_down += 1
      else:
        self.DEC_jump = self.DEC_max_vel   #continue till paddle button released

    if self.Paddle_stop_RA:
      if self.RA_down > 0:
        self.RA_jump -= self.RA_add_vel
        self.RA_down -= 1
      else:
        self.RA_jump = 0.0
        self.Paddle_stop_RA = False   #finished
        self.Paddle_start_RA = False

    if self.Paddle_stop_DEC:
      if self.DEC_down > 0:
        self.DEC_jump -= self.DEC_add_vel
        self.DEC_down -= 1
      else:
        self.DEC_jump = 0.0
        self.Paddle_stop_DEC = False   #finished
        self.Paddle_start_DEC = False
        
  def CalcJump(self):
    """A telescope slew is initiated by a call to setprof, with parameters delRA, delDEC, and Rate.
       That function sets up the actual motion by changing the motor control attributes:
          AXIS_up, AXIS_down       #ramp up/down time in ticks
          AXIS_plateau             #time in ticks to stay at max velocity
          AXIS_max_vel             #plateau velocity in steps/tick
          AXIS_add_vel             #ramp accell/decell in steps/tick/tick
          AXIS_remain              #Used to spread out 'leftover' slew pulses over entire slew duration
          finish_AXIS              #True if the slew has finished for that axis
          Teljump                  #Set to True to start slew            
       This function, called once per tick as the motion control values are calculated, uses those
       parameters to calculate the current AXIS_jump velocity for each tick.                   
    """
    if self.RA_up > 0:
      self.RA_jump += self.RA_add_vel
      self.RA_max = self.RA_jump
      self.RA_up -= 1
    else:
      if self.RA_plateau > 0:
        self.RA_jump = self.RA_max_vel
        self.RA_plateau -= 1
      else:
        if self.RA_down > 0:
          self.RA_jump = self.RA_max - self.RA_scl*self.RA_add_vel
          self.RA_down -= 1
          self.RA_scl += 1
        else:
          self.RA_jump = 0.0                #finished jump
          self.RA_remain = 0
          self.RA_scl = 0
          self.finish_RA = True

    if self.DEC_up > 0:
      self.DEC_jump += self.DEC_add_vel
      self.DEC_max = self.DEC_jump
      self.DEC_up -= 1
    else:
      if self.DEC_plateau > 0:
        self.DEC_jump = self.DEC_max_vel
        self.DEC_plateau -= 1
      else:
        if self.DEC_down > 0:
          self.DEC_jump = self.DEC_max - self.DEC_scl*self.DEC_add_vel
          self.DEC_down -= 1
          self.DEC_scl += 1
        else:
          self.DEC_jump = 0.0              #finished jump
          self.finish_DEC = True
          self.DEC_remain = 0.0
          self.DEC_scl = 0

    if self.finish_DEC and self.finish_RA:
      self.Teljump = False   #finished the telescope jump
      self.PosDirty = True   #Flag invalid position log file
      self.moving = False    #telescope no longer in motion
      self.RA_reflog = 0
      self.Dec_reflog = 0

  def setprof(self,delRA,delDEC,Rate):
    """This procedure calculates the profile parameters for a telescope jump.
    
       Inputs are delRA and delDEC, the (signed) offsets in steps, and
       'Rate', the peak velocity in steps/second.

       A jump has three components: the ramp up, the plateau and the ramp
       down. The size of the jump, the acceleration  and the maximum velocity
       determine the values for the three jump component. Components are described in terms
       of the number of pulses(interupts) and the number of motor steps per pulse.

       All parameters output from this procedure are in motor steps/time pulse.
    """
    #Determine motor speeds and displacements.
    #If teljump or paddle flags are true, loop until they go false.
    while (self.Teljump or self.Paddle_start_RA or self.Paddle_stop_RA or 
           self.Paddle_start_DEC or self.Paddle_stop_DEC):
      logger.debug('motion.MotorControl.setprof: Waiting for telescope to stop moving')
      time.sleep(1)   #TODO - fix this hack and replace with a proper lock

    #calculate max_vel.
    max_vel = abs(Rate)*PULSE            #unsigned value steps/pulse

    #number of time pulses in the ramp up.
    ramp_time = abs(float(Rate))/MOTOR_ACCEL     #MOTOR_ACCEL is in steps/sec/sec
    num_pulses = math.trunc(ramp_time/PULSE)

    #speed incrument per time pulse in motor steps/pulse.
    if num_pulses > 0:
      add_to_vel = max_vel/num_pulses
    else:
      add_to_vel = 0

    #The number of motor steps in a ramp is?
    num_ramp_steps = add_to_vel*(num_pulses*num_pulses/2.0+num_pulses/2.0)

    if add_to_vel == 0:
      add_to_vel = max_vel

  #Account for the direction of the jump.
    if delRA < 0:
      self.RA_add_vel = -add_to_vel
      self.RA_max_vel = -max_vel
      RA_sign = -1.0
    else:
      self.RA_add_vel = add_to_vel
      self.RA_max_vel = max_vel
      RA_sign = 1.0

    if delDEC < 0:
      self.DEC_add_vel = -add_to_vel
      self.DEC_max_vel = -max_vel
      DEC_sign = -1.0
    else:
      self.DEC_add_vel = add_to_vel
      self.DEC_max_vel = max_vel
      DEC_sign = 1.0

    #Calculate the ramp and plateau values for both axes.
    if delRA == 0.0:
      #no jump in RA axis
      self.RA_up = 0
      self.RA_down = 0
      self.RA_plateau = 0
      self.RA_remain = 0
      self.finish_RA = True
    elif abs(delRA) < abs(2.0*self.RA_add_vel):
      #Small jump - add delRA to frac_RA. #TODO - deal with the fact that frac_RA is private now.
      self.RA_up = 0
      self.RA_down = 0
      self.RA_plateau = 0
      self.RA_remain = 0
      self.finish_RA = True
      #frac_RA = frac_RA + delRA   #TODO - small jumps currently do nothing!
    elif abs(delRA) > 2.0*num_ramp_steps:
      #Jump is large enough to reach max velocity - has a Plateau
      self.RA_up = num_pulses
      self.RA_down = num_pulses
      steps_plateau = delRA - 2.0*(num_ramp_steps)*(RA_sign)
      pulses_plateau = steps_plateau/(self.RA_max_vel)
      self.RA_plateau = math.trunc(pulses_plateau)      #number of pulses in the plateau
      sum_of_pulses = self.RA_up*2 + self.RA_plateau
      self.RA_remain = (steps_plateau-self.RA_plateau*self.RA_max_vel)/sum_of_pulses
      self.finish_RA = False
    else:
      #Jump is to short to reach max velocity - no plateau
      ramp_pulses_part = 0
      num_steps_hold = abs(delRA)
      loop = True
      while loop:
        steps_used = 2.0*add_to_vel*(ramp_pulses_part+1)
        num_steps_hold = num_steps_hold - steps_used
        if num_steps_hold < 0.0:
          num_steps_hold = num_steps_hold + steps_used
          loop = False
        else:
          ramp_pulses_part = ramp_pulses_part + 1

      self.RA_up = ramp_pulses_part
      self.RA_down = ramp_pulses_part
      self.RA_plateau = 0
      sum_of_pulses = self.RA_up*2
      self.RA_remain = (num_steps_hold*RA_sign)/sum_of_pulses
      self.finish_RA = False

    if delDEC == 0:
      #no jump in DEC axis
      self.DEC_up = 0
      self.DEC_down = 0
      self.DEC_plateau = 0
      self.DEC_remain = 0
      self.finish_DEC = True
    elif abs(delDEC) < abs(2.0*self.DEC_add_vel):
      #Small jump - add delDEC to frac_DEC. #TODO - deal with the fact that frac_DEC is private now.
      self.DEC_UP = 0
      self.DEC_down = 0
      self.DEC_plateau = 0
      self.DEC_remain = 0
      self.finish_DEC = True
      #frac_DEC = frac_DEC + delDEC    #TODO - small jumps currently do nothing!
    elif abs(delDEC) > 2.0*num_ramp_steps:
      #Jump large enough to reach max velocity - has a Plateau.
      self.DEC_up = num_pulses
      self.DEC_down = num_pulses
      steps_plateau = delDEC - 2.0*(num_ramp_steps*DEC_sign)
      pulses_plateau = steps_plateau/(self.DEC_max_vel)
      self.DEC_plateau = math.trunc(pulses_plateau)
      sum_of_pulses = self.DEC_up*2 + self.DEC_plateau
      self.DEC_remain = (steps_plateau-self.DEC_plateau*self.DEC_max_vel)/sum_of_pulses
      self.finish_DEC = False
    else:
      #Jump is to small to reach max velocity- no Plateau.
      ramp_pulses_part = 0
      num_steps_hold = abs(delDEC)
      loop = True
      while loop:
        steps_used = 2.0*add_to_vel*(ramp_pulses_part+1)
        num_steps_hold = num_steps_hold - steps_used
        if num_steps_hold < 0.0:
          num_steps_hold = num_steps_hold + steps_used
          loop = False
        else:
          ramp_pulses_part = ramp_pulses_part + 1

      self.DEC_up = ramp_pulses_part
      self.DEC_down = ramp_pulses_part
      self.DEC_plateau = 0
      sum_of_pulses = self.DEC_up*2
      self.DEC_remain = (num_steps_hold*DEC_sign)/sum_of_pulses
      self.finish_DEC = False

    #inform the interupt that we have a telescope jump to execute
    #Check the paddles arent in use
    while (self.Teljump or self.Paddle_start_RA or self.Paddle_stop_RA or 
           self.Paddle_start_DEC or self.Paddle_stop_DEC):  #TODO - argh, even worse than the first hack!
      logger.debug('motion.MotorControl.setprof: Waiting for paddle motion to finish')
      time.sleep(1)

    if (not self.finish_RA or not self.finish_DEC):
      self.Teljump = True
      self.moving = True
    else:
      self.Teljump = False

  def start_motor(self, which_motor, Rate):
    """
       This procedure is used to start one of the compumotors for a hand-paddle move, where
       we don't know in advance when it will stop.

       which_motor must be 'ra' or 'dec' (case insensitive)
       Rate is the peak velocity in steps/second (same units as setprof)

    """
    if type(which_motor) <> str:
      logger.error("motion.MotorControl.start_motor: Use 'RA' or 'DEC' as which_motor argument")
      return True   #indicate error
    which_motor = which_motor.strip().upper()
    if which_motor <> 'RA' and which_motor <> 'DEC':
      logger.error("motion.MotorControl.start_motor: Use 'RA' or 'DEC' as which_motor argument")
      return True   #indicate error

    self.moving = True   #signal telescope in motion
    #Test that to see if the telescope is in jump mode
    while self.Teljump:
      logger.debug('motion.MotorControl.start_motor: Waiting for the telescope jump to end.')
      time.sleep(1)           #TODO - fix this hack and replace with a proper lock.

    if which_motor == 'RA': #Is the RA axis stationary?
      while (self.Paddle_start_RA or self.Paddle_stop_RA):
        logger.debug('motion.MotorControl.start_motor: Waiting for RA paddle motion to finish')
        time.sleep(0.5)
    else:     #Is the DEC axis stationary?
      while (self.Paddle_start_DEC or self.Paddle_stop_DEC):
        logger.debug('motion.MotorControl.start_motor: Waiting for DEC paddle motion to finish')
        time.sleep(0.5)

    #The following calculations are assumed to be the same for RA and DEC axis
    #number of pulses in ramp_up
    ramp_time = abs(float(Rate))/MOTOR_ACCEL
    num_pulses = math.trunc(ramp_time/PULSE)

    #maximum velocity in motor steps per pulse
    max_vel = Rate*PULSE

    #Incrument velocity ramp by add_to_vel -  also error trap for num_pulses=0
    if num_pulses > 0:
      add_to_vel = max_vel/num_pulses
    else:
      add_to_vel = 0

    #Set global values for the motor
    if which_motor == 'RA':
      self.RA_up = num_pulses
      self.RA_down = 0
      self.Paddle_start_RA = True
      self.Paddle_stop_RA = False
      self.RA_max_vel = max_vel
      self.RA_add_vel = add_to_vel
    else:                   #DEC axis
      self.DEC_up = num_pulses
      self.DEC_down = 0
      self.Paddle_start_DEC = True
      self.Paddle_stop_DEC = False
      self.DEC_max_vel = max_vel
      self.DEC_add_vel = add_to_vel

  def stop_motor(self,which_motor):
    """
       Ramp one of the compumotors down
         which_motor             'RA' or 'DEC'
         Paddle_start_RA         logical - if true then continue moving the RA motor
         Paddle_start_DEC        as for RA
         Paddle_stop_RA          logical - if true then ramp the RA motor down
         Paddle_stop_DEC         as for RA
    """
    if type(which_motor) <> str:
      logger.error("motion.MotorControl.stop_motor: Use 'RA' or 'DEC' as which_motor argument")
      return True   #indicate error
    which_motor = which_motor.strip().upper()
    if which_motor <> 'RA' and which_motor <> 'DEC':
      logger.error("motion.MotorControl.stop_motor: Use 'RA' or 'DEC' as which_motor argument")
      return True   #indicate error

    self.PosDirty = True    #flag pos log file as out of date
    self.moving = False     #no longer in motion
    if which_motor == 'RA':
      self.Paddle_start_RA = False
      self.Paddle_stop_RA = True
    else:             #DEC
      self.Paddle_start_DEC = False
      self.Paddle_stop_DEC = True


  def Timeint(self):
    """Loop forever when called, keeping controller queue full.

    MSB_RA,LSB_RA,MSB_DEC,LSB_DEC:string[2]
    word_RA,word_DEC:word
    sbyte,msbra,lsbra,msbdec,lsbdec:byte
    guidesteps:integer
    """
    global watchdog 

    RA_hold = 0            #Used to delay one 50ms pulse value if direction changes
    DEC_hold = 0           #Used to delay one 50ms pulse value if direction changes
    send_RA = 0.0          #Final floating point value for RA steps to send to the motor this tick
    send_DEC = 0.0         #Final floating point value for Dec steps to send to the motor this tick
    int_RA = 0             #integer part of send_RA, the distance to move in this 50ms tick
    int_DEC = 0            #integer part of send_Dec, the distance to move in this 50ms tick
    frac_RA = 0.0          #fractional part of send_RA, the distance to move in this 50ms tick
    frac_DEC = 0.0         #fractional part of send_Dec, the distance to move in this 50ms tick
    old_sign_RA = False    #used to see if RA motor has changed direction since the last tick
    old_sign_DEC = False   #used to see if DEC motor has changed direction since the last tick
    
    while True:   #Replace with check of error status flag
      time.sleep(0.02)  #Check queue status every 20ms
      if dummycon.QueueLow():   #as yet undefined QueueLow function
        watchdog = 0   #Reset watchdog each time we get a signal from pc23 queue

        #This is the beginning of the SD loop. This loop sends 6 SD commands every
        # time an interupt is detected.
        for num_SD in range(6):
          self.ticks += 50

#IFDEF NZ
#          #When a limit trips in or out, ramp the speed in each axis up and down over
#          #ten 50ms 'tick' values.
#          if limits.HWLimit and (not limits.LimOverride) and (CutFrac<10):
#            CutFrac += 1
#          if ((not HWLimit) or LimOverride) and (CutFrac>0):
#            CutFrac -= 1
#No hardware limits readable from Perth at the moment, so CutFrac is always zero.

          
          #**MIX VELOCITIES for next pulse**
          if self.Teljump:
            self.CalcJump()
            send_RA = prefs.RAsid + self.RA_jump + self.RA_remain
            if prefs.NonSidOn:
              send_RA += self.RA_track

            send_DEC = self.DEC_jump + self.DEC_remain
            if prefs.NonSidOn:
              send_DEC += self.DEC_track
              #TODO - not sure why we want to include a non-sidereal track rate during slews - check.
          else:
            self.CalcPaddle()

            send_RA = self.RA_jump
            send_DEC = self.DEC_jump
            self.RA_padlog += self.RA_jump
            self.DEC_padlog += self.DEC_jump

            if not self.Frozen:
              #This section sends guide motion, can be deleted and replaced with code to log the 
              #guide motion from the controller.
  #            if abs(RA_Guide) > GuideRate/20:
  #              send_RA = send_RA + Sgn(RA_Guide)*GuideRate/20
  #              RA_Guidelog = RA_Guidelog + Sgn(RA_Guide)*GuideRate/20
  #              RA_Guide = RA_Guide - Round(Sgn(RA_Guide)*GuideRate/20)
  #            else:        #Use up remaining short guide motion
  #              send_RA = Send_RA + RA_Guide
  #              RA_GuideLog = RA_GuideLog + RA_Guide
  #              RA_Guide = 0
  #
  #            if abs(DEC_Guide) > GuideRate/20:
  #              send_DEC = send_DEC + Sgn(DEC_Guide)*GuideRate/20
  #              DEC_Guidelog = DEC_Guidelog + Sgn(DEC_Guide)*GuideRate/20
  #              DEC_Guide = DEC_Guide - Round(Sgn(DEC_Guide)*GuideRate/20)
  #            else:        #Use up remaining short guide motion
  #              send_DEC = send_DEC + DEC_Guide
  #             DEC_Guidelog = DEC_Guidelog + DEC_Guide
  #              DEC_Guide = 0
              #End of guider section

              send_RA += prefs.RAsid + self.RA_refraction
              send_DEC += self.DEC_refraction
              self.RA_reflog += self.RA_refraction     #real-time bits
              self.DEC_reflog += self.DEC_refraction

              if prefs.NonSidOn:
                send_RA += self.RA_track
                send_DEC += self.DEC_track
                self.RA_padlog += self.RA_track
                self.DEC_padlog += self.DEC_track

              #end of if not Frozen
            else:
              self.RA_padlog -= prefs.RAsid    #If frozen, pretend we're slewing backwards at the sidereal rate

            #end of if teljump - else clause

          if RA_hold <> 0:
            send_RA += RA_hold
            RA_hold = 0
          if DEC_hold <> 0:
            send_DEC += DEC_hold
            DEC_hold = 0

          self.RA_padlog -= send_RA*(self.CutFrac/10.0)
          self.DEC_padlog -= send_DEC*(self.CutFrac/10.0)
          #Subtract the cut portion of motion from the paddle log
          #If no limits, cutfrac=0, if limit decel. finished cutfrac=10

          send_RA = send_RA * (1-self.CutFrac/10.0)
          send_DEC = send_DEC * (1-self.CutFrac/10.0)
          #Multiply send values by 1 if no limit, or 0.9, 0.8, .07 ... 0.0
          #successively if we hit a limit

          if prefs.EastOfPier:
            send_DEC = -send_DEC      #Invert dec direction if tel. east of pier

          #Break into integer & fraction
          fracpart, int_RA = math.modf(send_RA)
          frac_RA += fracpart    #Accumulate the fractional part
          #if the absolute value of the accumulated frac_RA is greater than 1.0, update int_RA
          if abs(frac_RA) > 1.0:
            int_RA += math.trunc(frac_RA)
            frac_RA -= math.trunc(frac_RA)

          #Break into integer & fraction
          fracpart, int_DEC = math.modf(send_DEC)
          frac_DEC += fracpart      #accumulate residuals
          #if the accumulated frac_DEC is greater than 1 update int_DEC
          if abs(frac_DEC) > 1.0:
            int_DEC += math.trunc(frac_DEC)
            frac_DEC -= math.trunc(frac_DEC)

          #**CHECKS**
          #if the sign of either send_RA or send_DEC has changed since the last
          # pulse add int_** to frac_** and reset int_** to 0.0 
          sign_RA = (int_RA >= 0)
          if sign_RA <> old_sign_RA:     #Set an initial value for old_sign_RA
            old_sign_RA = sign_RA
            RA_hold = int_RA             #include this velocity in the next pulse
            int_RA = 0

          sign_DEC = (int_DEC >= 0)
          if sign_DEC <> old_sign_DEC:   #as for old_sign_RA
            old_sign_DEC = sign_DEC
            DEC_hold = int_DEC
            int_DEC = 0

          #TODO - Now send word_RA and word_DEC to the controller queue here!
          dummycon.send(int_RA, int_DEC)



#Main init routine for unit
#Set initial values

watchdog = -10
ticks = 0

db, GotSQL = sqlint.InitSQL()
status = dummycon.status
limits = LimitStatus(db=db)
motors = MotorControl()


