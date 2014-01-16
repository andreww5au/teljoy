
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
import digio
import usbcon


intthread = None

log = []

def KickStart():
  """Start the motion control thread to keep the motor queue full.
  """
  global intthread
  print "Kickstarting motion control thread"
  #Start the queue handler thread to keep the queue full
  intthread = threading.Thread(target=RunQueue, name='USB-controller-thread')
  intthread.daemon = True
  intthread.start()






class Axis(object):
  """Represents the motor control flags and variables controlling motion on
     a single axis. Replaces RA_variable and DEC_variable type attributes of the
     MotorControl class.
  """
  def __init__(self, sidereal=0.0):
    """Set up empty attributes for a new axis record.
    """
    self.sidereal = sidereal   #Sidereal rate for this axis (prefs.RAsid for RA, 0.0 for DEC)
    self.up = 0                #number of 50ms ticks to ramp motor to max velocity for slew
    self.down = 0              #number of 50ms ticks to ramp motor down after slew
    self.plateau = 0           #number of 50ms ticks in the plateau of a slew
    self.track = 0.0           #Current Non-Sidereal tracking velocity for moving targets in steps/50ms
    self.add_vel = 0.0         #accelleration for slews in steps/50ms/50ms
    self.max_vel = 0.0         #plateau velocity in steps/50ms for current slew

    self.jump = 0.0            #Current slew velocity in steps/50ms, calculated by self.CalcJump or self.CalcPaddle for each tick
    self.remain = 0.0          #remainder after calculating ramp profile - used in telescope jump
    self.finish = True         #False if a jump (not paddle motion) is in progress for this axis
    self.Paddle_start = False  #True if hand-paddle motion for this axis is ramping up or or reached plateau velocity (button pressed)
    self.Paddle_stop = False   #True if hand-paddle motion for this axis is ramping down (button just released)
    self.scl = 0               #How many ticks we have been decelerating for on the ramp down from a slew in this axis
    self.refraction = 0.0      #Non sidereal trackrate used to correct for atmospheric refraction and telescope flexure - steps/50m
    self.padlog = 0.0          #Accumulated motion from hand paddle movement
    self.reflog = 0            #Accumulated motion from refraction tracking
    self.guidelog = 0          #Accumulated motion from autoguider
    self.hold = 0              #These are used to delay a velocity value by 50ms (so we can insert a zero velocity frame)
    self.frac = 0.0            #These store the accumulated fractional ticks, left over from previous frames
    self.Jumping = False       #True if a pre-calculated slew is in progress for this axis.
    self.Paddling = False      #True if hand-paddle motion is in progress for this axis
    self.lock = threading.RLock()

  def __repr__(self):
    mesg =  "  <Axis: Sidereal=%f\n" % self.sidereal
    flags = []
    if self.Paddling:
      if self.Paddle_start:
        flags.append("Paddling:Start")
      elif self.Paddle_stop:
        flags.append("Paddling:Stop")
      else:
        flags.append("Paddling")
    if self.Jumping:
      flags.append("Jumping")
    if not self.finish:
      flags.append("Jump not finished")
    mesg += "    Flags: [%s]\n" % (', '.join(flags))
    mesg += "    up/down/plateau = %d/%d/%d" % (self.up, self.down, self.plateau)
    mesg += '  >\n'

    return mesg

  def __getstate__(self):
    """Can't pickle the lock object when saving state
    """
    d = self.__dict__.copy()
    del d['lock']
    return d

  def CalcPaddle(self):
    """The paddle code in the 'Determine Event' loop communicates with the motor control object by
       calling StartPaddle and StopPaddle. These functions in turn set the motor control attributes:
          self.up, self.down                     #ramp up/down time in ticks
          Paddle_start, Paddle_stop              #Booleans
          self.max_vel                           #plateau velocity in steps/tick
          self.add_vel                           #ramp accel/decel in steps/tick/tick
       This function, called once per tick as the motion control values are calculated, uses the
       above flags to calculate the current velocity components for this tick due to a hand-paddle slew,
       stored in self.jump.

       Note that the 'jump' attribute (self.jump) are used for profiled 'jumps' as
       well as hand-paddle motion, so these actions can not be carried out simultaneously.
    """
    with self.lock:
      if self.Paddle_start:               #if RA Button pressed
        if self.up > 0:                   #if still accelerating
          self.jump += self.add_vel       #Increase current velocity
          self.up -= 1                    #Count down to the end of the acceleration time
          self.down += 1                  #Keep track of how many ticks we've accelerated for
        else:
          self.jump = self.max_vel        #Reached max velocity, continue till paddle button released

      if self.Paddle_stop:                #if RA Button has just been released
        if self.down > 0:                 #if still decelerating
          self.jump -= self.add_vel       #Decrease current velocity
          self.down -= 1                  #Count down to the end of the deceleration time
        else:
          self.jump = 0.0                 #Set velocity to zero
          self.Paddle_stop = False        #Flag that we have finished decelerating
          self.Paddle_start = False       #Flag that we aren't accelerating either
          self.Paddling = False

  def CalcJump(self):
    """A telescope slew is initiated by a call to MotorControl.Jump, with parameters delRA, delDEC, and Rate.
       That function sets up the actual motion by changing the motor control attributes:
          self.up, self.down       #ramp up/down time in ticks
          self.plateau             #time in ticks to stay at max velocity
          self.max_vel             #plateau velocity in steps/tick
          self.add_vel             #ramp accel/decel in steps/tick/tick
          self.remain              #Used to spread out 'leftover' slew pulses over entire slew duration
          self.Jumping             #Set to True to start slew
       This function, called once per tick as the motion control values are calculated, uses those
       parameters to calculate the current self.jump velocity for each tick.

       Note that the AXIS.jump attributes are used for profiled 'jumps' as
       well as hand-paddle motion, so these actions can not be carried out simultaneously.
    """
    with self.lock:
      if self.up > 0:                  #If we are ramping up
        self.jump += self.add_vel   # Increase current velocity
        self.max = self.jump        # Save maximum velocity so far, in case slew is too short to have plateau
        self.up -= 1                   # Count down to the end of the acceleration time
      else:
        if self.plateau > 0:           #If we've reached the plateau phase
          self.jump = self.max_vel  # Reached plateau, set constant velocity
          self.plateau -= 1            # Count down to the end of the plateau time
        else:                            #Not ramping up or plateauing
          if self.down > 0:            #if ramping down
            self.jump = self.max - self.scl*self.add_vel    #decrease velocity
            self.down -= 1             # count down to the end of the deceleration time
            self.scl += 1              # count the number of ticks we've been decelerating for
          else:                          #Finished jump in this axis
            self.jump = 0.0            #Set jump velocity to zero
            self.remain = 0            #Disable 'fudge velocity' used to store remainder of steps from profile during jump
            self.scl = 0               #Clear deceleration counter
            self.Jumping = False       #Flag end of jump in this axis

  def StartJump(self, delta, Rate):
    """This procedure calculates the profile parameters and starts a telescope jump
       for this axis.

       Inputs are delta, the (signed) offset in steps, and
       'Rate', the peak velocity in steps/second. Returns None.

       Outputs are the following attributes:
          self.up, self.down       #ramp up/down time in ticks
          self.plateau             #time in ticks to stay at max velocity
          self.max_vel             #plateau velocity in steps/tick
          self.add_vel             #ramp accell/decell in steps/tick/tick
          self.remain              #Used to spread out 'leftover' slew pulses over entire slew duration
          self.Jumping             #Set to True to start slew

       A jump has three components: the ramp up, the plateau and the ramp
       down. The size of the jump, the acceleration  and the maximum velocity
       determine the values for the three jump component. Components are described in terms
       of the number of pulses(interupts) and the number of motor steps per pulse.

       All parameters output from this procedure are in motor steps/time pulse.
    """
    if Rate <= 0:
      logger.error('StartJump called with zero or negative Rate')
      return True
    with self.lock:
      #calculate max_vel.
      max_vel = abs(Rate)*PULSE            #unsigned value steps/pulse

      #number of time pulses in the ramp up.
      ramp_time = abs(float(Rate))/MOTOR_ACCEL     #MOTOR_ACCEL is in steps/sec/sec
      num_pulses = math.trunc(ramp_time/PULSE)

      if num_pulses > 0:
        #speed increment per time pulse in motor steps/pulse:
        add_to_vel = max_vel/num_pulses
        #The number of motor steps in a ramp:
        num_ramp_steps = add_to_vel*(num_pulses*num_pulses/2.0+num_pulses/2.0)
      else:
        add_to_vel = max_vel
        num_ramp_steps = 0

      #Account for the direction of the jump.
      if delta < 0:
        self.add_vel = -add_to_vel
        self.max_vel = -max_vel
        sign = -1.0
      else:
        self.add_vel = add_to_vel
        self.max_vel = max_vel
        sign = 1.0

      #Calculate the ramp and plateau values.
      if delta == 0.0:
        #no jump
        self.up = 0
        self.down = 0
        self.plateau = 0
        self.remain = 0
        self.Jumping = False
      elif abs(delta) < 2.0*abs(self.add_vel):
        #Small jump - add delta to self.hold.
        self.up = 0
        self.down = 0
        self.plateau = 0
        self.remain = 0
        self.Jumping = False
        self.hold += delta
      elif abs(delta) > 2.0*num_ramp_steps:
        #Jump is large enough to reach max velocity - has a Plateau
        self.up = num_pulses
        self.down = num_pulses
        steps_plateau = delta - 2.0*num_ramp_steps*sign
        pulses_plateau = steps_plateau /self.max_vel
        self.plateau = math.trunc(pulses_plateau)      #number of pulses in the plateau
        sum_of_pulses = self.up*2 + self.plateau
        self.remain = (steps_plateau-self.plateau*self.max_vel)/sum_of_pulses
        self.Jumping = True
      else:
        #Jump is to short to reach max velocity - no plateau
        ramp_pulses_part = 0
        num_steps_hold = abs(delta)
        while True:
          steps_used = 2.0*add_to_vel*(ramp_pulses_part+1)
          num_steps_hold -= steps_used
          if num_steps_hold < 0.0:
            num_steps_hold += steps_used
            break
          else:
            ramp_pulses_part += 1
        self.up = ramp_pulses_part
        self.down = ramp_pulses_part
        self.plateau = 0
        sum_of_pulses = self.up*2
        self.remain = (num_steps_hold*sign)/sum_of_pulses
        self.Jumping = True

  def StartPaddle(self, Rate):
    """
       This procedure is used to start one of the motors for a hand-paddle move, where
       we don't know in advance when it will stop. Returns None.

       Inputs are:
        Rate is the peak velocity in steps/second (same units as self.StartJump)

       Outputs are the following attributes:
        self.up, self.down                     #ramp up/down time in ticks
        self.Paddle_start                      #True when button pressed - indicates ramp up or plateau
        self.Paddle_stop                       #True when button just released, indicates ramp down in progress
        self.max_vel                           #plateau velocity in steps/tick
        self.add_vel                           #ramp accel/decel in steps/tick/tick
        self.Paddling                          #True if the telescope is performing hand-paddle motion in this axis
    """
    with self.lock:
      #Test to see if the telescope is moving in this axis
      if self.Paddling or self.Jumping:
        logger.debug('motion.Axis.StartPaddle called when this axis is already in motion.')
        return False

      #number of pulses in ramp_up
      ramp_time = abs(float(Rate))/MOTOR_ACCEL
      num_pulses = math.trunc(ramp_time/PULSE)
      #maximum velocity in motor steps per pulse
      max_vel = Rate*PULSE

      #Increment velocity ramp by add_to_vel -  also error trap for num_pulses=0
      if num_pulses > 0:
        add_to_vel = max_vel/num_pulses
      else:
        add_to_vel = 0

      #Set motion values for the motor
      self.up = num_pulses
      self.down = 0
      self.Paddle_start = True
      self.Paddle_stop = False
      self.max_vel = max_vel
      self.add_vel = add_to_vel
      self.Paddling = True               #signal telescope in motion in this axis
      return True

  def StopPaddle(self):
    """
       This procedure is used to stop one of the motors for a hand-paddle move, when
       the hand-paddle button is released. Returns None.

       Outputs are the following attributes:
        self.Paddle_start                      #True when button pressed - indicates ramp up or plateau
        self.Paddle_stop                       #True when button just released, indicates ramp down in progress
    """
    with self.lock:
      self.Paddle_start = False
      self.Paddle_stop = True

  def getframe(self, Frozen):
    """Called by the controller thread when new data needs to be calculated to send to the
       controller queue for this axis.

       Returns the number of steps to travel in the next 50ms frame.
    """
    with self.lock:

      #MIX VELOCITIES for next pulse - sidereal rate, motion profile velocities, non-sidereal and refraction tracking
      #Start with sidereal rate, or zero if frozen
      if Frozen:
        send = 0.0                      #No sidereal motion, but:
        self.padlog -= self.sidereal    #Log fictitious backwards paddle motion instead of sidereal tracking (changes current sky coordinates)
      else:
        send = self.sidereal            #Start with sidereal rate in RA

      #Add in telescope jump or paddle motion velocities
      if self.Jumping:      #If currently moving in a profiled (ramp-up/plateau/ramp-down) jump
        self.CalcJump()      #Use jump profile attributes to calculate RA_jump and DEC_jump for this tick
        send += self.jump + self.remain
      elif self.Paddling:                  #We aren't in a profiled jump
        self.CalcPaddle()            #Use paddle move profile attributes to calculate RA_jump and DEC_jump for this tick, if any
        send += self.jump
        self.padlog += self.jump     #Log jump motion as paddle movement
      else:
        #If we're not slewing and not Frozen, add refraction motion, autoguider motion and non-sidereal tracking, for this tick
        if not Frozen:
          send += self.refraction         #Add in refraction correction velocity
          self.reflog += self.refraction     #Log refraction correction motion
          send += self.track            #Add in non-sidereal motion for moving targets
          self.padlog += self.track     #Log non-sidereal motion as paddle movement

      # TODO - handle autoguider log here, using counter data?

      send = send / DIVIDER     # TODO - remove this hack for use on the actual telescope, only needed for test motors.

      #Add any 'held' values for this axis, containing small offsets that can bypass the ramp calculations
      if self.hold <> 0:
        send += self.hold
        self.hold = 0

      #Break final velocity for this tick into integer & fraction
      fracpart, int_send = math.modf(send)
      self.frac += fracpart    #Accumulate the fractional part
      #if the absolute value of the accumulated self.frac is greater than 1.0, update int_send
      if abs(self.frac) > 1.0:
        int_send += math.trunc(self.frac)
        self.frac -= math.trunc(self.frac)

      #Now send it to the controller queue!
      return int_send


class MotorControl(object):
  """An instance of this class handles all low-level motion control, with one background thread running
     self.Driver.run to keep the controller queue full. This thread is started when the 'KickStart()' function
     is called by the main program.
  """
  def __init__(self, limits=None):
    logger.debug('motion.MotorControl.__init__: Initializing Global variables')
    self.Jumping = False        #True if a 'Jump' (precalculated slew) is in progress for either axis
    self.Paddling = False       #True if hand-paddle movement is in progress for either axis
    self.Moving = False         #True if the telescope is moving (other than sidereal, non-sidereal offset, flexure and refraction tracking)
    self.PosDirty = False       #Set to True when a move (jump or paddle) finishes, to indicate move has finished. Reset to False by detevent.
    self.ticks = 0              #Counts time since startup in ms. Increased by 50 as each velocity value is calculated and sent to the queue.
    self.Frozen = False         #If set to true, sidereal and non-sidereal tracking disabled. Slew and hand paddle motion not affected
    self.RA = Axis(sidereal=prefs.RAsid)
    self.DEC = Axis()
    self.limits = limits
    self.lock = threading.RLock()
    self.Driver = None
    logger.debug('motion.MotorControl.__init__: finished global vars')

  def __getstate__(self):
    """Can't pickle the __setattr__ function when saving state
    """
    d = {}
    for n in ['Jumping','Paddling','Moving','PosDirty','ticks','Frozen']:
      d[n] = self.__dict__[n]
    return d

  def __repr__(self):
    mesg = "<Motors: ticks=%d" % self.ticks
    flags = []
    if self.Jumping:
      flags.append("Jumping")
    if self.Moving:
      flags.append("Moving")
    if self.Paddling:
      flags.append("Paddling")
    if self.Frozen:
      flags.append("Frozen")
    if self.PosDirty:
      flags.append("PosDirty")
    mesg += "  Flags: [%s]\n" % (', '.join(flags))
    mesg += "RA:\n%s" % self.RA
    mesg += "Dec:\n%s" % self.DEC
    mesg += '>\n'
    return mesg

  def Jump(self, delRA, delDEC, Rate, force=False):
    """This procedure calculates the profile parameters for a telescope jump.
    
       Inputs are delRA and delDEC, the (signed) offsets in steps, and
       'Rate', the peak velocity in steps/second. Returns None.

       Calls RA.StartJump() and DEC.StartJump to start the slews in each axis
    """
    #Determine motor speeds and displacements.
    #If slewing (paddle or Jump) exit and return True as an error
    if (self.Jumping or self.Paddling):
      logger.debug('motion.MotorControl.Jump called while telescope is already moving')
      return True
    if safety.Active.is_set() or force:
      with self.lock:
        self.RA.StartJump(delRA, Rate)
        self.DEC.StartJump(delDEC, Rate)
        return False
    else:
      logger.error('ERROR: motion.motors.Jump called when safety interlock is on')

  def getframe(self):
    """
    """
    self.ticks += 50

    was_moving = self.Moving
    int_RA = self.RA.getframe(self.Frozen)
    int_DEC = self.DEC.getframe(self.Frozen)

    self.Paddling = (self.RA.Paddling or self.DEC.Paddling)
    self.Jumping = (self.RA.Jumping or self.DEC.Jumping)
    self.Moving = (self.Paddling or self.Jumping)

    if was_moving and (not self.Moving):
      self.PosDirty = True                     #Flag that the log file position needs to be updated
      with self.RA.lock:
        self.RA.reflog = 0                       #Zero the refraction/flexure tracking log
      with self.DEC.lock:
        self.DEC.reflog = 0                      #Zero the refraction/flexure tracking log

    if prefs.EastOfPier:
      int_DEC = -int_DEC      #Invert DEC direction if tel. east of pier

    #Now send word_RA and word_DEC to the controller queue!
    return (int_RA, int_DEC)



def RunQueue():
  """Starts the motion control queue running.

     This function only exits if stop() was called with an exception, indicating an
     unrecoverable error that means the main program must exit.
  """
  global motors
  global limits
  limits = usbcon.LimitStatus()
  while True:
    try:
      motors = MotorControl(limits=limits)
      motors.Driver = usbcon.Driver(getframe=motors.getframe, limits=limits)
      motors.Driver.run()
    except:
      print "controller.Controller.stop() was called with an exception:"
      traceback.print_exc()
      break
    logger.info("Restarting controller.run().")


#Main init routine for unit

limits = None
motors = None

