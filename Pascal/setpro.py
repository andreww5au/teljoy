
# uses Globals
# uses pc23int,Crt,PC23io,Time,Correct,Flexure

PULSE = 0.05   #seconds between interrupts


def relref(Obj):
  """Calculates a real time refraction correction for inclusion in INTPAS
     routine. The effect of refraction is calculated by
       (1) The effect of refraction is calculated at time+time_inc.
       (2) Divided by the number of interupts in the time interval and added
           to RA_send & DEC_send every time through the loop.
       (3) The next refract value is calculated and held ready for when
           a log decremented in INTPAS reaches zero.
           Global variables:
             RA_refraction    value passed to INTPAS to correct for refraction.
             DEC_refraction   as for RA.
             int_time         interupt time (50ms).
  """
  NUM_REF = 600                  # no of interrupts in time_inc time.
  TIME_INC = 30.0                # Update time
  SIDCORRECT = 30.08213727/3600  #number of siderial hours in update time
  # TODO - at some point in the past, the code was changed to calculate the
  # new refraction correction 30 _sidereal_ seconds in the future (SIDCORRECT)
  # instead of 30 seconds UT in the future (TIME_INC). This is then divided by 600, the number
  # of ticks in 30 seconds UT, to calculate a rate. I think this is wrong. Check... AW 2011/12/01

  #**Begin refraction correction**
  GetSidereal(Obj)       #Current sidereal time
  AltAziConv(obj)
  #TODO - Replace above with calls to methods of position object

  AltError = False
  if obj.alt < AltWarning:
    AltError = True

  if RefractionOn:
    refrac(oldRAref,oldDECref,Obj)
  else:
    oldRAref = 0
    oldDECref = 0

  if FlexureOn:
    Flex(oldRAflex,oldDECflex,Obj)
  else:
    oldRAflex = 0
    oldDECflex = 0

  if RealTimeOn:
    Obj.time.LST = Obj.time.LST + SIDCORRECT   #advance sid time TODO - check SIDCORRECT
    AltAziConv(Obj)               #Calculate the alt/az

    if RefractionOn:
      refrac(newRAref,newDECref,Obj)  #Calculate refraction for new time
    else:
      newRAref = 0
      newDECref = 0

    if FlexureOn:
      Flex(newRAflex,newDECflex,Obj)
    else:
      newRAflex = 0
      newDECflex = 0

    deltaRA = (newRAref-oldRAref) + (newRAflex-oldRAflex)
    deltaDEC = (newDECref-oldDECref) + (newDECflex-oldDECflex)

    #Start the refraction corrections
    RA_refraction = 20.0*(deltaRA/NUM_REF)    # TODO - check NUM_REF
    DEC_refraction = 20.0*(deltaDEC/NUM_REF)

    RefError = False
    if Abs(RA_refraction) > 200:
      RA_refraction = 200*(RA_refraction/Abs(RA_refraction))
      RefError = True
    if Abs(Dec_refraction) > 200:
      Dec_refraction = 200*(Dec_refraction/Abs(Dec_refraction))
      RefError = True
  else:
    #**Stop the refraction correction**
    RA_refraction = 0.0
    DEC_refraction = 0.0
    RefError = False

  #TODO - replace below with time.time() call, and calls to methods of position object.
  GetSysTime(Obj.Time.lthr,Obj.Time.ltm,Obj.Time.lts,Obj.Time.lthn)
  GetSysDate(Obj.Time.dy,Obj.Time.mnth,Obj.Time.yr)
  TimetoDec(Obj.Time)
  UTConv(Obj.Time)
  UTtoJD(Obj.Time)

  GetSidereal(Obj)       #Current sidereal time
  AltAziConv(obj)



def setprof (delRA,delDEC,Rate):
  """This procedure calculates the profile parameters for a telescope jump.

     A jump has three components they are the ramp up, the plateau and the ramp
     down. The size of the jump, the acceleration  and the maximum velocity
     determine the values for the three jump component. Components are described in terms
     of the number of pulses(interupts) and the number of motor steps per pulse.

     All parameters output from this procedure are in motor steps/time pulse.
  """
  #Determine motor speeds and displacements.
  #If teljump or paddle flags are true, loop until they go false.
  while (Teljump or Paddle_start_RA or Paddle_stop_RA or Paddle_start_DEC or Paddle_stop_DEC):
    print 'Waiting for telescope to stop moving:'
    time.sleep(1)

  #calculate max_vel.
  motor_max_vel = Rate/25000            #revs/sec
  max_vel = Rate*PULSE                  #unsigned value steps/pulse

  #number of time pulses in the ramp up.
  ramp_time = motor_max_vel/motor_accel
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
    RA_add_vel = -add_to_vel
    RA_max_vel = -max_vel
    RA_sign = -1.0
  else:
    RA_add_vel = add_to_vel
    RA_max_vel = max_vel
    RA_sign = 1.0

  if delDEC < 0:
    DEC_add_vel = -add_to_vel
    DEC_max_vel = -max_vel
    DEC_sign = -1.0
  else:
    DEC_add_vel = add_to_vel
    DEC_max_vel = max_vel
    DEC_sign = 1.0

  #Calculate the ramp and plateau values for both axes.
  if delRA == 0.0:
    #no jump in RA axis
    RA_up = 0
    RA_down = 0
    RA_plateau = 0
    RA_remain = 0
    finish_RA = True
  elif abs(delRA) < abs(2.0*RA_add_vel):
    #Small jump - add delRA to frac_RA. #TODO - deal with the fact that frac_RA is private now.
    RA_up = 0
    RA_down = 0
    RA_plateau = 0
    RA_remain = 0
    finish_RA = True
    frac_RA = frac_RA + delRA
  elif abs(delRA) > 2.0*num_ramp_steps:
    #Jump is large enough to reach max velocity - has a Plateau
    RA_up = num_pulses
    RA_down = num_pulses
    steps_plateau = delRA - 2.0*(num_ramp_steps)*(RA_sign)
    pulses_plateau = steps_plateau/(RA_max_vel)
    RA_plateau = math.trunc(pulses_plateau)      #number of pulses in the plateau
    sum_of_pulses = RA_up*2 + RA_plateau
    RA_remain = (steps_plateau-RA_plateau*RA_max_vel)/sum_of_pulses
    finish_RA = False
  else:
    #Jump is to short to reach max velocity - no plateau
    ramp_pulses_part = 0
    num_steps_hold = abs(delRA)
    loop = True
    while loop:
      steps_used = 2.0*add_to_vel*(ramp_pulses_part+1)
      num_steps_hold = num_steps_hold - steps_used
      if num_steps_hold<0.0:
        num_steps_hold = num_steps_hold + steps_used
        loop = False
      else:
        ramp_pulses_part = ramp_pulses_part + 1

    RA_up = ramp_pulses_part
    RA_down = ramp_pulses_part
    RA_plateau = 0
    sum_of_pulses = RA_up*2
    RA_remain = (num_steps_hold*RA_sign)/sum_of_pulses
    finish_RA = False

  if delDEC == 0:
    #no jump in DEC axis
    DEC_up = 0
    DEC_down = 0
    DEC_plateau = 0
    DEC_remain = 0
    finish_DEC = True
  elif abs(delDEC) < abs(2.0*DEC_add_vel):
    #Small jump - add delDEC to frac_DEC. #TODO - deal with the fact that frac_DEC is private now.
    DEC_UP = 0
    DEC_down = 0
    DEC_plateau = 0
    DEC_remain = 0
    finish_DEC = True
    frac_DEC = frac_DEC + delDEC
  elif abs(delDEC) > 2.0*num_ramp_steps:
    #Jump large enough to reach max velocity - has a Plateau.
    DEC_up = num_pulses
    DEC_down = num_pulses
    steps_plateau = delDEC - 2.0*(num_ramp_steps*DEC_sign)
    pulses_plateau = steps_plateau/(DEC_max_vel)
    DEC_plateau = math.trunc(pulses_plateau)
    sum_of_pulses = DEC_up*2 + DEC_plateau
    DEC_remain = (steps_plateau-DEC_plateau*DEC_max_vel)/sum_of_pulses
    finish_DEC = False
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

    DEC_up = ramp_pulses_part
    DEC_down = ramp_pulses_part
    DEC_plateau = 0
    sum_of_pulses = DEC_up*2
    DEC_remain = (num_steps_hold*DEC_sign)/sum_of_pulses
    finish_DEC = False

  #inform the interupt that we have a telescope jump to execute
  #Check the paddles arent in use
  while Teljump or Paddle_start_RA or Paddle_stop_RA or Paddle_start_DEC or Paddle_stop_DEC:
    print ','

  if (not finish_RA or not finish_DEC):
    Teljump = True
    Moving = True
  else:
    Teljump = False



def start_motor(which_motor, paddle_max_vel):
  """
     #This procedure is used to start one of the compumotors

     paddle_max_vel           the max speed of the paddles in revs/sec (does this describe direction????)
     MOTOR_ACCEL              the acceleration of the motors in revs/sec
     PULSE                    the duration of a time pulse (interupt)
     num_steps_rev            the number of motor steps in 1 rev
     Which_motor              logical - true then this call refers to the RA motor else DEC motor
     RA_up                    the number of pulses in the up ramp
     DEC_up                   as for RA
     Paddle_start_RA          logical - if true then start the Ra motor
     Paddle_start_DEC         as for RA

     var ramp_time:double
         num_pulses:longint
  """
  #TODO - change from using boolean to select axis, use something like 'ra' or 'dec'

  Moving = True   #signal telescope in motion
  #Test that to see if the telescope is in jump mode
  while teljump:
    print 'Waiting for the telescope jump to end.'
    time.sleep(1)
  if which_motor: #Is the RA axis stationary?
    while (Paddle_start_RA or Paddle_stop_RA):
      time.sleep(0.1)
  else:     #Is the DEC axis stationary?
    while (Paddle_start_DEC or Paddle_stop_DEC):
      time.sleep(0.1)

  #The following calculations are assumed to be the same for RA and DEC axis
  #number of pulses in ramp_up
  ramp_time = abs(paddle_max_vel)/MOTOR_ACCEL
  num_pulses = math.trunc(ramp_time/PULSE)

  #maximum velocity in motor steps per pulse
  max_vel = paddle_max_vel*25000*PULSE

  #Incrument velocity ramp by add_to_vel -  also error trap for num_pulses=0
  if num_pulses > 0:
    add_to_vel = max_vel/num_pulses
  else:
    add_to_vel = 0

  #Set global values for the motor
  if which_motor:    #RA axis
    RA_up = num_pulses
    RA_down = 0
    Paddle_start_RA = True
    Paddle_stop_RA = False
    RA_max_vel = max_vel
    RA_add_vel = add_to_vel
  else:                   #DEC axis
    DEC_up = num_pulses
    DEC_down = 0
    Paddle_start_DEC = True
    Paddle_stop_DEC = False
    DEC_max_vel = max_vel
    DEC_add_vel = add_to_vel



def stop_motor(which_motor):
  """
     Ramp one of the compumotors down
       which_motor             logical - if true then stop RA motor else: stop DEC motor
       paddle_start_RA         logical - if true then continue moving the RA motor
       paddle_start_DEC        as for RA
       paddle_stop_RA          logical - if true then ramp the RA motor down
       paddle_stop_DEC         as for RA

  TODO - change from using boolean to select axis, use something like 'ra' or 'dec'
  """
  PosDirty = True    #flag pos log file as out of date
  Moving = False     #no longer in motion
  if which_motor:
    paddle_start_RA = False
    paddle_stop_RA = True
  else:
    paddle_start_DEC = False
    paddle_stop_DEC = True



def resetPC23():
  """
     This Procedure resets the PC23 card. The card is is assumed to be
     running in Time Data(TD) mode.
  """
  print 'Starting resetPC23'
  print 'Finished initialization of the board'
  print 'About to Kickstart!'
  pc23int.KickStart()           #Set up axes in streaming mode, send first data
  print 'wheeee!!!!'



def setup():
  if not DUMMY:
    resetPC23()        #Call the procedure to initialize the PC23 card


