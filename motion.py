
"""This module handles the low-level motion control - velocity ramping in each axis and sending 
   velocity pairs to the motor queue for each 50ms time step. The core of this motion control
   system is the TimeInt method of the MotorControl class, which runs in a thread checking the
   motor queue and sending pairs of RA and DEC velocities for each 50ms 'tick' as required to 
   keep the motor queue filled.
"""

import math
import threading
import time

from globals import *
import usbcon

MOTOR_ACCEL = 2.0*25000            #2.0 (revolutions/sec/sec) * 25000 (steps/revolution)
PULSE = 0.05                       #50 milliseconds per 'tick'

#Bit masks for limit switches on the New Zealand telescope. No limit switches
#currently readable for Perth telescope.
POWERMSK = 0x01
HORIZMSK = 0x02
MESHMSK  = 0x04
EASTMSK  = 0x08
WESTMSK  = 0x10


intthread = None

def KickStart():
  """Initialise the hardware motor controller, and Start the motion
     control thread to keep the motor queue full.
  """
  motors.Driver.kickstart()



class LimitStatus():
  """Class to represent the hardware limit state/s. 
     
     Only used for New Zealand telescopes, no limit state can be read in Perth. This code largely
     ported as-is, and has never actually been used on the NZ telescope. It seems to have a few
     problems...
  """
  _reprf = ( '<LimitStatus: On: %(LimitOnTime)d, Off: %(LimitOffTime)d - ' +
             '%(HWLimit)s [Old=%(OldLim)s, PowerOff=%(PowerOff)s, ' + 
             'Horiz=%(HorizLim)s, Mesh=%(MeshLim)s, East=%(EastLim)s, West=%(WestLim)s, Override=%(LimOverride)s]>')
  _strf = ( 'HWLimits=%(HWLimit)s [Old=%(OldLim)s, PowerOff=%(PowerOff)s, ' + 
             'Horiz=%(HorizLim)s, Mesh=%(MeshLim)s, East=%(EastLim)s, West=%(WestLim)s, Override=%(LimOverride)s]' )

  def __repr__(self):
    """This is called by python itself when the object is converted
       to a string automatically, or using the `` operation.
    """
    return self._reprf % self.__dict__

  def __str__(self):
    """This is called by python itself when the object is converted to
       a string using the str() function.
    """
    return self._strf % self.__dict__

  def __init__(self):
    self.LimitOnTime = 0.0        #How long the limit has been active
    self.LimitOffTime = 0.0       #No idea, apparently never changed
    self.HWLimit = False          #True if any of the hardware limits are active. Should be method, not attribute
    self.OldLim = False           #?
    self.PowerOff = False         #True if the telescope power is off (eg, switched off at the telescope)
    self.HorizLim = False         #True if the mercury switch 'nest' horizon limit has tripper
    self.MeshLim = False          #? 
    self.EastLim = False          #RA axis eastward limit reached
    self.WestLim = False          #RA axis westward limit reached
    self.LimOverride = False      #True if the 'Limit Override' button on the telescope is pressed
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

  def CanEast(self):
    return (not self.HWLimit) or (self.LimOverride and self.WestLim)

  def CanWest(self):
    return (not self.HWLimit) or (self.LimOverride and self.EastLim)

  def check(self):
    if (not self.OldLim) and (self.HWLimit):
      motors.Frozen = True
      self.LimitOnTime = time.time()
      self.LimitOffTime = 2147483647    #sys.maxint
      self.OldLim = True
    if ( (not self.PowerOff) and (not self.HorizLim) and (not self.MeshLim) and
         (not motors.moving) and (not self.EastLim) and (not self.WestLim) and self.HWLimit ):
      motors.Frozen = False
      self.OldLim = False
      self.HWLimit = False
      self.LimOverride = False



class MotorControl():
  """An instance of this class handles all low-level motion control, with one method
     (Timeint) running continuously in a background thread to keep the controller 
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
    self.RA_track = 0.0         #Current RA Non-sidereal tracking velocity for moving targets in steps/50ms
    self.DEC_track = 0.0        #Current DEC Non-sidereal tracking velocity for moving targets in steps/50ms
    self.RA_add_vel = 0.0       #RA accelleration for slews in steps/50ms/50ms
    self.DEC_add_vel = 0.0      #DEC accelleration for slews in steps/50ms/50ms
    self.RA_max_vel = 0.0       #plateau velocity in RA in steps/50ms for current slew
    self.DEC_max_vel = 0.0      #plateau velocity in Dec in steps/50ms for current slew

    self.RA_jump = 0.0          #Current slew velocity in RA in steps/50ms, calculated by self.CalcJump or self.CalcPaddle for each tick
    self.DEC_jump = 0.0         #Current slew velocity in DEC in steps/50ms, calculated by self.CalcJump or self.CalcPaddle for each tick
    self.RA_remain = 0.0        #remainder in RA after calculating ramp profile - used in telescope jump
    self.DEC_remain = 0.0       #remainder in Dec after calculating ramp profile - used in telescope jump
    self.finish_RA = True       #False if a jump (not paddle motion) is in progress for the RA axis
    self.finish_DEC = True      #False if a jump (not paddle motion) is in progress for the DEC axis
    self.Paddle_start_RA = False  #True if hand-paddle motion for the RA axis is ramping up or or reached plateau velocity (button pressed)
    self.Paddle_stop_RA = False   #True if hand-paddle motion for the RA axis is ramping down (button just released)
    self.Paddle_start_DEC = False #True if hand-paddle motion for the DEC axis is ramping up or or reached plateau velocity (button pressed)
    self.Paddle_stop_DEC = False  #True if hand-paddle motion for the DEC axis is ramping down (button just released)
    self.Teljump = False        #True if a 'Jump' (motion to desired endpoint coordinates) is in progress
    self.moving = False         #True if the telescope is moving (other than sidereal, non-sidereal offset, flexure and refraction tracking)
    self.PosDirty = False       #Set to True when a move (jump or paddle) finishes, to indicate move has finished. Reset to False by detevent.
    self.RA_scl = 0             #How many ticks we have been decellerating for on the ramp down from a slew in RA
    self.DEC_scl = 0            #How many ticks we have been decellerating for on the ramp down from a slew in DEC
    self.RA_refraction = 0.0    #Non sidereal RA trackrate used to correct for atmospheric refraction and telescope flexure - steps/50m
    self.DEC_refraction = 0.0   #Non sidereal DEC trackrate used to correct for atmospheric refraction and telescope flexure - steps/50m
    self.RA_padlog = 0.0        #Accumulated RA motion from hand paddle movement
    self.DEC_padlog = 0.0       #Accumulated RA motion from hand paddle movement
    self.RA_reflog = 0          #Accumulated RA motion from RA_refraction tracking
    self.DEC_reflog = 0         #Accumulated DEC motion from DEC_refraction tracking
    self.RA_GOffset = 0         #These store the total offset for a guide-correction movemement. Decremented to
    self.DEC_GOffset = 0        #    zero as the guide motion takes place, after which a new offset can be stored.
    self.RA_guide = 0           #These store the curent guide correction velocity, in steps/50ms
    self.DEC_guide = 0          #    used to perform autoguiding. Calculated by self.CalcGuide for each tick
    self.RA_Guidelog = 0        #Accumulated RA motion from autoguider (using RA_Guide and DEC_guide offsets described above)
    self.DEC_Guidelog = 0       #Accumulated DEC motion from autoguider (using RA_Guide and DEC_guide offsets described above)
    self.CutFrac = 0            # emergency ramp down on limit. Increases from 0 (no cut) to 10 (100% cut) over ten 50ms ticks
    self.ticks = 0              #Counts time since startup in ms. Increased by 50 as each velocity value is calculated and sent to the queue.
    self.Frozen = False         #If set to true, sidereal and non-sidereal tracking disabled. Slew and hand paddle motion not affected
    self.RA_hold = 0            #These are used to delay a velocity value by 50ms (so we can insert a zero velocity
    self.DEC_hold = 0           #   value in the queue between positive and negative values if the direction changes)
    self.frac_RA = 0.0          #These store the accumulated fractional ticks in RA and DEC, left over
    self.frac_DEC = 0.0         #    after the integer part of the velocity is sent for each tick
    self.old_sign_RA = False    #These are direction flags (False=negative) for the last velocity values sent,
    self.old_sign_DEC = False   #    used to see if each motor has changed direction since the last tick
    self.Driver = usbcon.Driver(getframe=self.getframe)
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
    del d['Driver']
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
       
       Note that the AXIS_jump attributes (RA_jump and DEC_jump) are used for profiled 'Jumps' as
       well as hand-paddle motion, so these actions can not be carried out simultaneously.
    """
    if self.Paddle_start_RA:               #if RA Button pressed
      if self.RA_up > 0:                   #if still accellerating
        self.RA_jump += self.RA_add_vel    #Increase current velocity
        self.RA_up -= 1                    #Count down to the end of the accelleration time
        self.RA_down += 1                  #Keep track of how many ticks we've accellerated for
      else:
        self.RA_jump = self.RA_max_vel     #Reached max velocity, continue till paddle button released

    if self.Paddle_start_DEC:               #if DEC Button pressed
      if self.DEC_up > 0:                   #if still accellerating
        self.DEC_jump += self.DEC_add_vel   #Increase current velocity
        self.DEC_up -= 1                    #Count down to the end of the accelleration time
        self.DEC_down += 1                  #Keep track of how many ticks we've accellerated for
      else:
        self.DEC_jump = self.DEC_max_vel   #Reached max velocity, continue till paddle button released

    if self.Paddle_stop_RA:                #if RA Button has just been released
      if self.RA_down > 0:                 #if still deccellerating
        self.RA_jump -= self.RA_add_vel    #Decrease current velocity
        self.RA_down -= 1                  #Count down to the end of the decelleration time
      else:
        self.RA_jump = 0.0                 #Set velocity to zero
        self.Paddle_stop_RA = False        #Flag that we have finished decellerating
        self.Paddle_start_RA = False       #Flag that we aren't acellerating either

    if self.Paddle_stop_DEC:               #if DEC Button has just been released
      if self.DEC_down > 0:                #if still deccellerating
        self.DEC_jump -= self.DEC_add_vel  #Decrease current velocity
        self.DEC_down -= 1                 #Count down to the end of the decelleration time
      else:
        self.DEC_jump = 0.0                #Set velocity to zero
        self.Paddle_stop_DEC = False       #Flag that we have finished decellerating
        self.Paddle_start_DEC = False      #Flag that we aren't acellerating either
        
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
       
       Note that the AXIS_jump attributes (RA_jump and DEC_jump) are used for profiled 'Jumps' as
       well as hand-paddle motion, so these actions can not be carried out simultaneously.
    """
    if self.RA_up > 0:                  #If we are ramping up
      self.RA_jump += self.RA_add_vel   # Increase current velocity
      self.RA_max = self.RA_jump        # Save maximum velocity so far, in case slew is too short to have plateau
      self.RA_up -= 1                   # Count down to the end of the accelleration time
    else:
      if self.RA_plateau > 0:           #If we've reached the plateau phase
        self.RA_jump = self.RA_max_vel  # Reached plateau, set constant velocity
        self.RA_plateau -= 1            # Count down to the end of the plateau time
      else:                            #Not ramping up or plateauing
        if self.RA_down > 0:            #if ramping down
          self.RA_jump = self.RA_max - self.RA_scl*self.RA_add_vel    #decrease velocity
          self.RA_down -= 1             # count down to the end of the decelleration time
          self.RA_scl += 1              # count the number of ticks we've been decellerating for
        else:                          #Finished jump in this axis
          self.RA_jump = 0.0            #Set jump velocity to zero
          self.RA_remain = 0            #Disable 'fudge velocity' used to store remainder of steps from profile during jump
          self.RA_scl = 0               #Clear decelleration counter
          self.finish_RA = True         #Flag end of jump in this axis

    if self.DEC_up > 0:                  #If we are ramping up
      self.DEC_jump += self.DEC_add_vel   # Increase current velocity
      self.DEC_max = self.DEC_jump        # Save maximum velocity so far, in case slew is too short to have plateau
      self.DEC_up -= 1                    # Count down to the end of the accelleration time
    else:
      if self.DEC_plateau > 0:           #If we've reached the plateau phase
        self.DEC_jump = self.DEC_max_vel  # Reached plateau, set constant velocity
        self.DEC_plateau -= 1             # Count down to the end of the plateau time
      else:                            #Not ramping up or plateauing
        if self.DEC_down > 0:            #if ramping down
          self.DEC_jump = self.DEC_max - self.DEC_scl*self.DEC_add_vel    #decrease velocity
          self.DEC_down -= 1              # count down to the end of the decelleration time
          self.DEC_scl += 1               # count the number of ticks we've been decellerating for
        else:                          #Finished jump in this axis
          self.DEC_jump = 0.0           #Set jump velocity to zero
          self.DEC_remain = 0.0         #Disable 'fudge velocity' used to store remainder of steps from profile during jump
          self.DEC_scl = 0              #Clear decelleration counter
          self.finish_DEC = True        #Flag end of jump in this axis

    if self.finish_DEC and self.finish_RA:    #If finished both axes
      self.Teljump = False                     #Flag that we have finished the telescope jump
      self.PosDirty = True                     #Flag that the log file position needs to be updated
      self.moving = False                      #Flag that the telescope is not in motion
      self.RA_reflog = 0                       #Zero the refraction/flexure tracking log
      self.Dec_reflog = 0                      #Zero the refraction/flexure tracking log

  def CalcGuide(self):
    """Telescope guide motion is initiated by code that calculates the difference in each axis
       between the current actual position and the desired telescope coordinates. The total offset,
       in steps, for each axis is stored in the AXIS_GOffset attributes. Returns None.

       This function, called once per tick as the motion control values are calculated, uses those
       parameters to calculate the current AXIS_guide velocity for each tick. The contents of
       AXIS_GOffset are decremented by the amount sent each 'tick' until they reach zero. 
       
       This 'Guide' motion is for small corrections initiated in software. It's distinct from, and
       complementary to, the external guide camera, which attempts to correct for drift by 
       physically toggling N,S,E and W digital inputs - that's going to be handled inside the USB
       controller.
       
       Note that prefs.GuideRate must be small enough that no accelleration/decelleration profile
       is required.
       
       Inputs are the attributes:
        AXIS_GOffset           #Total distance to correct, in steps, for each axis
        
       Outputs are the attributes:
        AXIS_guide             #Current guide correction rate, in steps/50ms, for this tick
    """
    if abs(self.RA_GOffset) > prefs.GuideRate/20:
      self.RA_guide = math.copysign(prefs.GuideRate/20, self.RA_GOffset)
      self.RA_GOffset -= self.RA_guide
    else:        #Use up remaining short guide motion
      self.RA_guide = self.RA_GOffset
      self.RA_GOffset = 0

    if abs(self.DEC_GOffset) > prefs.GuideRate/20:
      self.DEC_guide = math.copysign(prefs.GuideRate/20, self.DEC_GOffset)
      self.DEC_GOffset -= self.DEC_guide
    else:        #Use up remaining short guide motion
      self.DEC_guide = self.DEC_GOffset
      self.DEC_GOffset = 0

  def setprof(self,delRA,delDEC,Rate):
    """This procedure calculates the profile parameters for a telescope jump.
    
       Inputs are delRA and delDEC, the (signed) offsets in steps, and
       'Rate', the peak velocity in steps/second. Returns None.

       Outputs are the following attributes:
          AXIS_up, AXIS_down       #ramp up/down time in ticks
          AXIS_plateau             #time in ticks to stay at max velocity
          AXIS_max_vel             #plateau velocity in steps/tick
          AXIS_add_vel             #ramp accell/decell in steps/tick/tick
          AXIS_remain              #Used to spread out 'leftover' slew pulses over entire slew duration
          finish_AXIS              #True if the slew has finished for that axis
          Teljump                  #Set to True to start slew            

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
      time.sleep(1)   #TODO - fix this hack and replace with a lock

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
      #Small jump - add delRA to RA_GOffset.
      self.RA_up = 0
      self.RA_down = 0
      self.RA_plateau = 0
      self.RA_remain = 0
      self.finish_RA = True
      self.RA_GOffset += delRA
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
      #Small jump - add delDEC to DEC_GOffset.
      self.DEC_UP = 0
      self.DEC_down = 0
      self.DEC_plateau = 0
      self.DEC_remain = 0
      self.finish_DEC = True
      self.DEC_GOffset += delDEC 
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

    #inform the low-level loop that we have a telescope jump to execute
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
       we don't know in advance when it will stop. Returns None.

       Inputs are:
        which_motor must be 'ra' or 'dec' (case insensitive)
        Rate is the peak velocity in steps/second (same units as setprof)

       Outputs are the following attributes:
        AXIS_up, AXIS_down                     #ramp up/down time in ticks
        Paddle_start_AXIS                      #True when button pressed - indicates ramp up or plateau
        Paddle_stop_AXIS                       #True when button just released, indicates ramp down in progress
        AXIS_max_vel                           #plateau velocity in steps/tick
        AXIS_add_vel                           #ramp accell/decell in steps/tick/tick
        moving                                 #True if the telescope is slewing (jump or paddle)

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
      time.sleep(1)           #TODO - fix these hacks and replace with proper locks.

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
       This procedure is used to stop one of the compumotors for a hand-paddle move, when
       the hand-paddle button is released. Returns None.

       Inputs are:
        which_motor         must be 'ra' or 'dec' (case insensitive)

       Outputs are the following attributes:
        AXIS_up, AXIS_down                     #ramp up/down time in ticks
        Paddle_start_AXIS                      #True when button pressed - indicates ramp up or plateau
        Paddle_stop_AXIS                       #True when button just released, indicates ramp down in progress
        AXIS_max_vel                           #plateau velocity in steps/tick
        AXIS_add_vel                           #ramp accell/decell in steps/tick/tick
        moving                                 #True if the telescope is slewing (jump or paddle)
        PosDirty                               #Set True when move finished to trigger position logfile update
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


  def getframe(self):
    """
    """
    global watchdog        #Watchdog counter used by external code to make sure the motor queue is active

    send_RA = 0.0          #Final floating point value for RA steps to send to the motor this tick
    send_DEC = 0.0         #Final floating point value for DEC steps to send to the motor this tick
    int_RA = 0             #integer part of send_RA, the distance to send for this 50ms tick
    int_DEC = 0            #integer part of send_Dec, the distance to send for this 50ms tick
    self.ticks += 50

    #MIX VELOCITIES for next pulse - sidereal rate, motion profile velocities, non-sidereal and refraction tracking
    #Start with sidereal rate, or zero if frozen
    if self.Frozen:
      send_RA = 0.0                    #No sidereal motion, but:
      send_DEC = 0.0
      self.RA_padlog -= prefs.RAsid    #Log fictitious backwards paddle motion instead of sidereal tracking (changes current sky coordinates)
    else:
      send_RA = prefs.RAsid            #Start with sidereal rate in RA
      send_DEC = 0.0

    #Add in telescope jump or paddle motion velocities
    if self.Teljump:      #If currently moving in a profiled (ramp-up/plateau/ramp-down) jump
      self.CalcJump()      #Use jump profile attributes to calculate RA_jump and DEC_jump for this tick
      send_RA += self.RA_jump + self.RA_remain
      send_DEC += self.DEC_jump + self.DEC_remain
    else:                  #We aren't in a profiled jump
      self.CalcPaddle()            #Use paddle move profile attributes to calculate RA_jump and DEC_jump for this tick, if any
      send_RA += self.RA_jump
      send_DEC += self.DEC_jump
      self.RA_padlog += self.RA_jump     #Log jump motion as paddle movement
      self.DEC_padlog += self.DEC_jump

      #If we're not in a profiled jump, add refraction motion, autoguider motion and non-sidereal tracking, for this tick
      if not self.Frozen:
        send_RA += self.RA_refraction         #Add in refraction correction velocity
        send_DEC += self.DEC_refraction
        self.RA_reflog += self.RA_refraction     #Log refraction correction motion
        self.DEC_reflog += self.DEC_refraction
        send_RA += self.RA_guide             #Add in autoguider correction velocity
        send_DEC += self.DEC_guide
        self.RA_Guidelog += self.RA_guide    #Log autoguider correction motion
        self.DEC_Guidelog += self.DEC_guide
        if prefs.NonSidOn:
          send_RA += self.RA_track            #Add in non-sidereal motion for moving targets
          send_DEC += self.DEC_track
          self.RA_padlog += self.RA_track     #Log non-sidereal motion as paddle movement
          self.DEC_padlog += self.DEC_track

    #Add the 'held' values for each axis, from a previous tick where a zero was sent when the axis direction changed
    #This was a hardware requirement for PC23, probably not for USB controller.
    if self.RA_hold <> 0:
      send_RA += self.RA_hold
      self.RA_hold = 0
    if self.DEC_hold <> 0:
      send_DEC += self.DEC_hold
      self.DEC_hold = 0

    #Subtract the cut portion of motion from the paddle log for emergency stop after hitting a limit
    #If no limits, cutfrac=0, if limit decel. finished cutfrac=10
    #Only applicable to NZ telescope, and will not apply for new USB controller which handles
    #emergency stops internally.
    send_RA = send_RA * (1-self.CutFrac/10.0)         #Multiply send values by 1 if no limit, or 0.9, 0.8, .07 ... 0.0
    send_DEC = send_DEC * (1-self.CutFrac/10.0)       #    successively if we hit a limit
    self.RA_padlog -= send_RA*(self.CutFrac/10.0)     #Log the cut fraction of motor travel as fictitious paddle motion in the
    self.DEC_padlog -= send_DEC*(self.CutFrac/10.0)   #    other direction, so position accuracy is preserved.

    if prefs.EastOfPier:
      send_DEC = -send_DEC      #Invert DEC direction if tel. east of pier

    #Break final RA velocity for this tick into integer & fraction
    fracpart, int_RA = math.modf(send_RA)
    self.frac_RA += fracpart    #Accumulate the fractional part
    #if the absolute value of the accumulated frac_RA is greater than 1.0, update int_RA
    if abs(self.frac_RA) > 1.0:
      int_RA += math.trunc(self.frac_RA)
      self.frac_RA -= math.trunc(self.frac_RA)

    #Break final DEC velocity for this tick into integer & fraction
    fracpart, int_DEC = math.modf(send_DEC)
    self.frac_DEC += fracpart      #accumulate residuals
    #if the accumulated frac_DEC is greater than 1 update int_DEC
    if abs(self.frac_DEC) > 1.0:
      int_DEC += math.trunc(self.frac_DEC)
      self.frac_DEC -= math.trunc(self.frac_DEC)

    #**CHECKS**
    #if the sign of either send_RA or send_DEC has changed since the last
    # pulse add int_** to frac_** and reset int_** to 0.0
    sign_RA = (int_RA >= 0)
    if sign_RA <> self.old_sign_RA:     #Set an initial value for old_sign_RA
      self.old_sign_RA = sign_RA
      self.RA_hold = int_RA             #include this velocity in the next pulse
      int_RA = 0

    sign_DEC = (int_DEC >= 0)
    if sign_DEC <> self.old_sign_DEC:   #as for old_sign_RA
      self.old_sign_DEC = sign_DEC
      self.DEC_hold = int_DEC
      int_DEC = 0

    #Now send word_RA and word_DEC to the controller queue!
    return(int_RA, int_DEC)



#Main init routine for unit
#Set initial values

watchdog = -10
ticks = 0

limits = LimitStatus()
motors = MotorControl()


