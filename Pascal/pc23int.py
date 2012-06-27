
# Uses: Dos, PC23io, Crt, Use32, VPUtils, Os2Def, Os2Base
#  globals, DigIO

import math

from globals import *

MOTOR_ACCEL = 2.0
PULSE = 0.05
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
   paddle_start_RA:boolean  # true if RA paddle button pressed
   paddle_stop_RA:boolean   # true if RA paddle button released
   paddle_start_DEC:boolean   #as for RA
   paddle_stop_DEC:boolean   #as for RA
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

def KickStart():
  if not DUMMY:
    global motors
    motors = MotorControl()
    #TODO - create a new thread and call motors.Timeint()
    #**Enter time streaming mode**
    #SD  - generate the first interupt(pulse) toggle output 1 on PC23
    #Clear the output buffer
    #MSS - start the Master clock


def IntWriteCmd(cmd):
  """Write a character string to the controller. Returns None.
  """


def IntReadAnswer(Response):
  """Read a response from the controller and return it in 'Response'.
  """


def PCIntAck():
  """Acknowledge or reset status but indicating near-empty queue
  """
  if not DUMMY:
    pass
    #do something


class MotorControl():
  """An instance of this class handles all low-level motion control, with one method
     (TimeInt) running continuously in a background thread to keep the controller 
     queue full.
  """
  def __init__(self):
    print 'Initializing Global variables'
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
    self.RA_scl = 0             #How many ticks we have been decellerating for on the ramp down from a slew
    self.DEC_scl = 0            #How many ticks we have been decellerating for on the ramp down from a slew
    self.RA_refraction = 0.0
    self.DEC_refraction = 0.0
    self.RA_padlog = 0.0
    self.DEC_padlog = 0.0
    self.RA_reflog = 0
    self.Dec_reflog = 0
    self.RA_Guide = 0
    self.DEC_Guide = 0
    self.RA_Guidelog = 0
    self.DEC_Guidelog = 0
    self.CutFrac = 0
    self.ticks = 0
    self.Frozen = False
    print 'finished global vars'
    
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
    word_RA = 0            #Value containing the number to send to the RA motor this tick, should fit in signed 16-bit
    word_DEC = 0           #Value containing the number to send to the REC motor this tick, should fit in signed 16-bit
    old_sign_RA = False    #used to see if RA motor has changed direction since the last tick
    old_sign_DEC = False   #used to see if DEC motor has changed direction since the last tick
    
    while True:   #Replace with check of error status flag
      time.sleep(0.02)  #Check queue status every 20ms
      if not DUMMY and QueueEmpty():   #as yet undefined QueueEmpty function
        watchdog = 0   #Reset watchdog each time we get a signal from pc23 queue

        #This is the beginning of the SD loop. This loop sends 6 SD commands every
        # time an interupt is detected.
        for num_SD in range(6):
          self.ticks += 50
          
          self.CalcPaddle()

          #**MIX VELOCITIES for next pulse**
          if self.Teljump:
            self.CalcJump()
            self.send_RA = RAsid + self.RA_jump + self.RA_remain
            if NonSidOn:
              self.send_RA += self.RA_track

            self.send_DEC = self.DEC_jump + self.DEC_remain
            if NonSidOn:
              self.send_DEC += self.DEC_track
              #TODO - not sure why we want to include a non-sidereal track rate during slews - check.
          else:
            self.send_RA = self.RA_jump
            self.send_DEC = self.DEC_jump
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

              send_RA += RAsid + self.RA_refraction
              send_DEC += self.DEC_refraction
              self.RA_reflog += self.RA_refraction     #real-time bits
              self.Dec_reflog += self.DEC_refraction

              if NonSidOn:
                send_RA += self.RA_track
                send_DEC += self.DEC_track
                self.RA_padlog += self.RA_track
                self.DEC_padlog += self.DEC_track

              #end of if not Frozen
            else:
              self.RA_padlog -= RAsid    #If frozen, pretend we're slewing backwards at the sidereal rate

            #end of if teljump - else clause

          if RA_hold <> 0:
            send_RA += RA_hold
            RA_hold = 0
          if DEC_hold <> 0:
            send_DEC += DEC_hold
            DEC_hold = 0

          self.RA_padlog -= send_RA*(self.CutFrac/10)
          self.DEC_padlog -= send_DEC*(self.CutFrac/10)
          #Subtract the cut portion of motion from the paddle log
          #If no limits, cutfrac=0, if limit decel. finished cutfrac=10

          send_RA = send_RA * (1-self.CutFrac/10)
          send_DEC = send_DEC * (1-self.CutFrac/10)
          #Multiply send values by 1 if no limit, or 0.9, 0.8, .07 ... 0.0
          #successively if we hit a limit

          if EastOfPier:
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

          #**COMPUMOTOR SECTION**
          #send the number of steps for this pulse
          if int_RA < 0:
            word_RA = 32768 + abs(int_RA)
          else:
            word_RA = int_RA
          if int_DEC < 0:
            word_DEC = 32768 + abs(int_DEC)
          else:
            word_DEC = int_DEC

          #TODO - Now send word_RA and word_DEC to the controller queue here!


def InstallInt():
  """Start running the background thread to feed the controller queue
  """
  #Warning! Abort this if a hand-paddle button is pressed on startup...


def Deinstall():
  """Stop the queue-filler thread.
  """
  pass

#Main init routine for unit
#Set initial values

watchdog = -10
ticks = 0

