
"""
   This module contains the code needed to support higher-level telescope control, 
   including maintaining the current telescope coordinates, as well as checking and
   acting on external inputs (hand-paddle buttons, commanded actions via the SQL 
   'mailbox' table', etc) and publishing the state to the outside world (maintaining
   the current state in an SQL table and a position file).
   
   The core of the module is the 'DetermineEvent' function, which runs continuously,
   and never exits once called apart from non-recoverable errors. The init() function
   in this module will start this function in a seperate thread.

"""

import math
import time
import threading
import cPickle
import copy

from globals import *
import pdome
import correct
import motion
import digio
import sqlint


detthread = None     #Contains the thread object running DetermineEvent after the init() function is called


class PaddleStatus:
  """An instance of this class is used to store the state of the hand paddle
     buttons, current motion, and speed settings. 
     
     Note that for the Perth telescope:
       -The Fine paddle speed can be one of 'Guide' or 'Set'
       -The Coarse paddle speed can be one of 'Set' or 'Slew'
     For the NZ telescope:
       -There is no fine paddle
       -The Coarse paddle speed can be one of 'Guide', 'Set', or 'Slew'
  """
  def __init__(self):
    self.RA_GuideAcc = 0.0         #Accumulated guide motion, from motion.motors.RA_guidelog
    self.DEC_GuideAcc = 0.0
    self.ButtonPressedRA = False   #True if one of the RA direction buttons is pressed
    self.ButtonPressedDEC = False  #True if one of the DEC direction buttons is pressed
    self.FineMode = 'FSet'         #one of 'FSet' or 'FGuide', depending on 'Fine' paddle speed toggle switch
    self.CoarseMode = 'CSet'       #one of 'CSet' or 'CSlew' or 'CGuide', depending on 'Coarse' paddle speed toggle switch
    self.RAdir = ''                #one of 'fineEast',  'fineWest',  'CoarseEast', or  'CoarseWest'  
    self.DECdir = ''               #one of 'fineNorth', 'fineSouth', 'CoarseNorth', or 'CoarseSouth'
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
    s = "<PaddleStatus: GuideAcc=(%f,%f) " % (self.RA_GuideAcc, self.DEC_GuideAcc)
    if self.ButtonPressedRA:
      s += "(RA:%s) " % self.RAdir
    if self.ButtonPressedDEC:
      s += "(DEC:%s) " % self.DECdir
    s += " >"
    return s

  def check(self):
    """Read the actual handle paddle button and switch state, using the digio module, and 
       handle them appropriately. When the state of the direction buttons changes (press or
       release), set the appropriate motion control flags and velocity parameters, then
       start or stop the actual motors.
       
       This method is called at regular intervals by the DetermineEvent loop.
    """
    #Read the Hand-paddle inputs}
    cb = digio.ReadCoarse(motion.motors.Driver.inputs)
    fb = digio.ReadFine(motion.motors.Driver.inputs)

    #check the Fine paddle speed switches and set appropriate mode and velocity
    if ((fb & digio.FGuideMsk)==digio.FGuideMsk):
      self.FineMode = 'FGuide'
      FinePaddleRate = prefs.GuideRate
    else:
      self.FineMode = 'FSet'
      FinePaddleRate = prefs.FineSetRate

    #* Check the fine paddle by comparing fb to a set of masks}
    if ((fb & digio.FNorth)==digio.FNorth):        #Compare with the north mask}
      if not self.ButtonPressedDEC:          #The button has just been pressed}
        self.ButtonPressedDEC = True
        self.DECdir = 'fineNorth'
        Paddle_max_vel = FinePaddleRate
        motion.motors.start_motor('DEC', Paddle_max_vel) 
    elif self.ButtonPressedDEC and (self.DECdir=='fineNorth'):
      #Mask does not match but the motor is running}
      self.ButtonPressedDEC = False
      motion.motors.stop_motor('DEC')

    if ((fb & digio.FSouth)==digio.FSouth):            #Check with South Mask}
      if not self.ButtonPressedDEC:
        self.ButtonPressedDEC = True
        self.DECdir = 'fineSouth'
        Paddle_max_vel = -FinePaddleRate
        motion.motors.start_motor('DEC', Paddle_max_vel)
    elif self.ButtonPressedDEC and (self.DECdir=='fineSouth'):
      #Mask does not match but the motor is running}
      self.ButtonPressedDEC = False
      motion.motors.stop_motor('DEC')

    if ((fb & digio.FEast)==digio.FEast):              #Check the Eastmask}
      if (not self.ButtonPressedRA) and motion.limits.CanEast():
        self.ButtonPressedRA = True
        self.RAdir = 'fineEast'
        Paddle_max_vel = FinePaddleRate
        motion.motors.start_motor('RA', Paddle_max_vel)
    elif self.ButtonPressedRA and (self.RAdir=='fineEast'):
      #Mask does not match but the motor is running}
      self.ButtonPressedRA = False
      motion.motors.stop_motor('RA')

    if ((fb & digio.FWest)==digio.FWest):               #Check the West mask}
      if (not self.ButtonPressedRA) and motion.limits.CanWest():
        self.ButtonPressedRA = True
        self.RAdir = 'fineWest'
        Paddle_max_vel = -FinePaddleRate
        motion.motors.start_motor('RA', Paddle_max_vel)
    elif self.ButtonPressedRA and (self.RAdir=='fineWEST'):
      #Mask does not match but the motor is running}
      self.ButtonPressedRA = False
      motion.motors.stop_motor('RA')

    #check the Coarse paddle speed switches and set appropriate mode and velocity
#$IFDEF NZ}
#    if ((cb & digio.CspaMsk)==digio.CspaMsk) and ((cb & digio.CspbMsk)==digio.CspbMsk):
#      self.CoarseMode = 'CSet'
#      CoarsePaddleRate = prefs.CoarseSetRate
#    else:
#      if ((cb & digio.CspbMsk)==digio.CspbMsk):
#        self.CoarseMode = 'CGuide'
#        CoarsePaddleRate = prefs.GuideRate
#      else:
#        self.CoarseMode = 'CSlew'
#        CoarsePaddleRate = prefs.SlewRate
#$ELSE}
    if ((cb & digio.CSlewMsk)==digio.CSlewMsk):
      self.CoarseMode = 'CSlew'
      CoarsePaddleRate = prefs.SlewRate
    else:
      self.CoarseMode = 'CSet'
      CoarsePaddleRate = prefs.CoarseSetRate
#$ENDIF}

    #**Check the Coarse paddle by comparing cb to a set of masks}
    if ((cb & digio.CNorth)==digio.CNorth):
      if not self.ButtonPressedDEC:
        self.ButtonPressedDEC = True
        self.DECdir = 'CoarseNorth'
        Paddle_max_vel = CoarsePaddleRate
        motion.motors.start_motor('DEC', Paddle_max_vel)
    elif self.ButtonPressedDEC and (self.DECdir=='CoarseNorth'):
      #Mask does not match but the motor is running}
      self.ButtonPressedDEC = False
      motion.motors.stop_motor('DEC')

    if ((cb & digio.CSouth)==digio.CSouth):
      if not self.ButtonPressedDEC:
        self.ButtonPressedDEC = True
        self.DECdir = 'CoarseSouth'
        Paddle_max_vel = -CoarsePaddleRate
        motion.motors.start_motor('DEC', Paddle_max_vel)
    elif self.ButtonPressedDEC and (self.DECdir=='CoarseSouth'):
      #Mask does not match but the motor is running}
      self.ButtonPressedDEC = False
      motion.motors.stop_motor('DEC')

    if ((cb & digio.CEast)==digio.CEast):
      if (not self.ButtonPressedRA) and motion.limits.CanEast():
        self.ButtonPressedRA = True
        self.RAdir = 'CoarseEast'
        Paddle_max_vel = CoarsePaddleRate
        motion.motors.start_motor('RA', Paddle_max_vel)
    elif self.ButtonPressedRA and (self.RAdir=='CoarseEast'):
      #Mask does not match but the motor is running}
      self.ButtonPressedRA = False
      motion.motors.stop_motor('RA')

    if ((cb & digio.CWest)==digio.CWest):
      if (not self.ButtonPressedRA) and motion.limits.CanWest():
        self.ButtonPressedRA = True
        self.RAdir = 'CoarseWest'
        Paddle_max_vel = -CoarsePaddleRate
        motion.motors.start_motor('RA', Paddle_max_vel)
    elif self.ButtonPressedRA and (self.RAdir=='CoarseWest'):
      #Mask does not match but the motor is running}
      self.ButtonpressedRA = False
      motion.motors.stop_motor('RA')


def UpdatePosFile():
  """Save the current position to the 'saved position' file.
     
     The saved position file isn't actually used any more. It used to be the source of the
     initial position on startup, but now the current state from the database (saved by
     detevent.CheckDBUpdate and sqlint.UpdateSQLCurrent) is used instead.
     
     This function is called by CheckDirtyPos a set interval after a telescope move has finished.
  """
  t = correct.TimeRec()   #Defaults to 'now'
  d = t.UT
  try:
    pfile = open(poslog,'w')
  except:
    logger.error('detevent.UpdatePosFile: Path not found')
    return
  pfile.write('ID:      %s\n' % Current.ObjID)
  pfile.write('Cor. RA: %f\n' % (Current.RaC/15.0,))
  pfile.write('Cor. Dec:%f\n' % Current.DecC)
  pfile.write('SysT:    %d %d %6.3f\n' % (d.hour,d.minute,d.second+d.microsecond/1e6) )  #Old file used hundredths of a sec
  pfile.write('Sys_Date:%d %d %d\n' % (d.day,d.month,d.year) )
  pfile.write('Jul Day: %f\n' % t.JD)
  pfile.write('LST:     %f\n' % (t.LST*3600,))
  pfile.close()


def UpdateCurrent():  
  """Update Current sky coordinates from paddle and refraction motion

     This function is called at regular intervals by the DetermineEvent loop.
  """
  #TODO - add proper locking here, fiddling with motion.motors attributes not threadsafe
  #invalidate orig RA and Dec if frozen, or paddle move, or non-sidereal move}
  if motion.motors.Frozen or (motion.motors.RA_padlog<>0) or (motion.motors.DEC_padlog<>0):
    Current.posviolate = True

  #account for paddle and non-sid. motion, and limit encounters}
  Current.RaA = Current.RaA + motion.motors.RA_padlog/20
  Current.DecA = Current.DecA + motion.motors.DEC_padlog/20

  #above, plus real-time refraction+flexure+guide in the fully corrected coords}
  Current.RaC += motion.motors.RA_padlog/20 + motion.motors.RA_reflog/20 + motion.motors.RA_Guidelog/20
  Current.DecC += motion.motors.DEC_padlog/20 + motion.motors.DEC_reflog/20 + motion.motors.DEC_Guidelog/20
  paddles.RA_GuideAcc += motion.motors.RA_Guidelog/20
  paddles.DEC_GuideAcc += motion.motors.DEC_Guidelog/20

  motion.motors.RA_padlog = 0
  motion.motors.RA_reflog = 0
  motion.motors.DEC_padlog = 0
  motion.motors.DEC_reflog = 0
  motion.motors.RA_guidelog = 0
  motion.motors.DEC_guidelog = 0

  if Current.RaA > (24*60*60*15):
    Current.RaA -= (24*60*60*15)
  if Current.RaA < 0:
    Current.RaA += (24*60*60*15)

  if Current.RaC > (24*60*60*15):
    Current.RaC -= (24*60*60*15)
  if Current.RaC < 0:
    Current.RaC += (24*60*60*15)


def SaveStatus():
  """Save the current state as pickled data in a status file, so clients can access it.

     This function is called at regular intervals by the DetermineEvent loop.
  """
  #TODO - replace with RPC calls to share state data  
  f = open('/tmp/teljoy.status','w')
  cPickle.dump((Current,motion.motors,pdome.status,errors,prefs),f)
  f.close()


def CheckDirtyPos():
  """Check to see if we've just finished a move (hand paddle or profiled jump). If so, 
     record the time.
     
     If more than prefs.WaitBeforePosUpdate seconds have passed since the end of the last
     move, update the saved state file by calling UpdatePosFile.
     
     This function is called at regular intervals by the DetermineEvent loop.
  """
  global DirtyTime
  if motion.motors.PosDirty and (DirtyTime==0):
    DirtyTime = time.time()                 #just finished move}

  if (DirtyTime<>0) and (time.time()-DirtyTime > prefs.WaitBeforePosUpdate) and not motion.motors.moving:
    UpdatePosFile()
    DirtyTime = 0
    motion.motors.PosDirty = False
    paddles.RA_GuideAcc = 0.0
    paddles.DEC_GuideAcc = 0.0


def CheckDirtyDome():
  """When prefs.DomeTracking is on, make sure that the dome is moved to the current
     telescope azimuth after each telescope more, or if the telescope has tracked
     far enough since the last dome move that the dome azimuth is more than 6 degrees
     off. 

     This function is called at regular intervals by the DetermineEvent loop.
  """
  if ( (abs(pdome.DomeCalcAzi(Current)-pdome.status.NewDomeAzi) > 6) and
       ((time.time()-pdome.status.DomeLastTime) > prefs.MinWaitBetweenDomeMoves) and
       (not pdome.status.DomeInUse) and
       (not pdome.status.ShutterInUse) and
       pdome.status.DomeTracking and
       (not motion.motors.moving) and
       pdome.status.AutoDome and
       (not motion.motors.PosDirty) ):
    pdome.DomeMove(pdome.DomeCalcAzi(Current))


def CheckDBUpdate(db=None):
  """Make sure that the current state is saved to the SQL database approximately once 
     every second. Exits without an error if the SQL connection isn't available.
     
     The state data is used by external clients (eg Prosp, the CCD camera controller)
     and also used by Teljoy to set the initial position on startup, using the last
     recorded RA, DEC and LST.

     This function is called at regular intervals by the DetermineEvent loop.
  """
  global DBLastTime
  if db is None:
    return
  if (time.time()-DBLastTime) > 1.0:
    foo = sqlint.Info() 
    foo.posviolate = Current.posviolate
    foo.moving = motion.motors.moving
    foo.EastOfPier = prefs.EastOfPier
    foo.NonSidOn = prefs.NonSidOn
    foo.DomeInUse = pdome.status.DomeInUse
    foo.ShutterInUse = pdome.status.ShutterInUse
    foo.ShutterOpen = pdome.status.ShutterOpen
    foo.DomeTracking = pdome.status.DomeTracking
    foo.Frozen = motion.motors.Frozen
    foo.RA_guideAcc = paddles.RA_GuideAcc
    foo.DEC_guideAcc = paddles.DEC_GuideAcc
    foo.LastError = LastError
    sqlint.UpdateSQLCurrent(Current, foo, db)
    DBLastTime = time.time()


def DoTJbox(db=None):
  """Read the tjbox database table and carry out any commanded actions.
     Exits without an error if the SQL connection isn't available.

     This function is called by CheckTJBox.
  """
  #TODO - add an RPC interface for external commands
  global ProspLastTime, TJboxAction
  if db is None:
    return
  BObj, other = sqlint.ReadTJbox(db=db)
  if BObj is None or other is None:
    return
  ProspLastTime = time.time()
  if (other.LastMod<0) or (other.LastMod>5) or motion.motors.moving:
    other.action = 'none'
    sqlint.ClearTJbox(db=db)
    TJboxAction = 'none'
  else:
    if other.action in ['error','none']:
      sqlint.ClearTJbox(db=db)
      TJboxAction = 'none'
    elif other.action == 'jumpid':
      found = False
      JObj = sqlint.GetObject(BObj.ObjID, db=db)
      if JObj is not None:
        found = True
      else:
        JObj = sqlint.GetRC3(BObj.ObjID, 0, db=db)
        if (JObj is not None) and JObj.numfound == 1:
          found = True
      if found and (not motion.limits.HWLimit):
        AltErr = Jump(JObj, prefs.SlewRate)  #Goto new position}
        if pdome.status.AutoDome and (not AltErr):
          pdome.DomeMove(pdome.DomeCalcAzi(JObj))
        if AltErr:
          logger.error('detevent.DoTJBox: Object in TJbox below Alt Limit')
        else:
          TJboxAction = other.action
      else:
        TJboxAction = 'none'
        sqlint.ClearTJbox(db=db)
    elif other.action == 'jumprd':
      AltErr = Jump(BObj, prefs.SlewRate)
      if pdome.status.AutoDome and (not AltErr):
        pdome.DomeMove(pdome.DomeCalcAzi(BObj))
      if AltErr:
        logger.error('detevent.DoTJbox: Object in TJbox below Alt Limit')
      else:
        TJboxAction = other.action

    elif other.action == 'jumpaa':
      sqlint.ClearTJbox(db=db)
      logger.error("detevent.DoTJbox: Remote control command 'jumpaa' not supported.")

    elif other.action == 'nonsid':
      sqlint.ClearTJbox(db=db)
      logger.error("detevent.DoTJbox: Remote control command 'nonsid' not supported.")

    elif other.action == 'offset':
      RAOffset = other.OffsetRA
      DECOffset = other.OffsetDEC
      DelRA = 20*RAOffset/math.cos(Current.DecC/3600*math.pi/180)  #conv to motor steps}
      DelDEC = 20*DECOffset
      motion.motors.setprof(DelRA,DelDEC,prefs.SlewRate)  #Calculate the motor profile and jump}
      if (not Current.posviolate):
        Current.Ra += RAOffset/math.cos(Current.DecC/3600*math.pi/180)
        Current.Dec += DECOffset
      Current.RaA += RAOffset/math.cos(Current.DecC/3600*math.pi/180)
      Current.DecA += DECOffset
      Current.RaC += RAOffset/math.cos(Current.DecC/3600*math.pi/180)
      Current.DecC += DECOffset
      TJboxAction = other.action

    elif other.action == 'dome':
      if other.DomeAzi < 0:
        pdome.DomeMove(pdome.DomeCalcAzi(Current))
      else:
        pdome.DomeMove(other.DomeAzi)
      TJboxAction = other.action

    elif other.action == 'shutter':
      if other.Shutter:
        pdome.DomeOpen()           #True for open}
      else:
        pdome.DomeClose()
      TJboxAction = other.action

    elif (other.action == 'freez') or (other.action == 'freeze'):
      if other.Freeze:
        motion.motors.Frozen = True
      else:
        motion.motors.Frozen = False
      TJboxAction = 'none'    #Action complete}
      sqlint.ClearTJbox(db=db)


def CheckTJbox(db=None):
  """Check the command table in the database and carry out any commanded actions.
     Check the progress of any previous commands still being acted on.
     Exits without an error if the SQL connection isn't available.     

     This function is called at regular intervals by the DetermineEvent loop.
  """
  #TODO - add an RPC interface for external commands
  global TJboxAction
  if db is None:
    return
  if TJboxAction == 'none':
    if sqlint.ExistsTJbox(db=db):
      DoTJbox(db=db)
  elif TJboxAction in ['jumpid','jumprd','jumpaa','offset']:
    if (not motion.motors.moving) and (not pdome.status.DomeInUse):
      TJboxAction = 'none'
      sqlint.ClearTJbox(db=db)
  elif TJboxAction == 'dome':
    if not pdome.status.DomeInUse:
      TJboxAction = 'none'
      sqlint.ClearTJbox(db=db)
  elif TJboxAction == 'shutter':
    if not pdome.status.ShutterInUse:
      TJboxAction = 'none'
      sqlint.ClearTJbox(db=db)


def CheckTimeout():
  """This function checks the time since the last command received via the database from the command table.
     If it exceeds ten minutes, the shutter is closed and the telescope is frozen.
     
     This is a safety mechanism, as the CCD camera control software (Prosp) also currently handles 
     weather and sunrise detection. If that isn't running, we need to make sure the roof is closed.
     
     When this Python Teljoy code is stable, the weather and end-of-night handling can be moved here,
     and this function removed.
     
     This function is called at regular intervals by the DetermineEvent loop.
  """
  #TODO - make timeout configurable via teljoy.ini and globals.prefs, with 0 to disable.
  if ((time.time()-ProspLastTime) > 600) and pdome.status.ShutterOpen and (not pdome.status.ShutterInUse):
    logger.critical('detevent.CheckTimeout: No communication with Prosp for over 10 minutes!\nClosing Shutter, Freezing Telescope.')
    pdome.DomeClose()
    motion.motors.Frozen = True


def RelRef():
  """Calculates real time refraction and flexure correction velocities for the current position.
     These velocities are mixed into the telescope motion by the low-level control loop
     in motion.motors.TimeInt.

     This function is called at regular intervals by the DetermineEvent loop.
  """
  NUM_REF = 600                  # no of interrupts in time_inc time.
  SIDCORRECT = 30.08213727/3600  #number of siderial hours in update time

  #**Begin refraction correction**
  Current.Time.update()
  Current.AltAziConv()           #Calculate Alt/Az now

  errors.AltError = False
  if Current.Alt < prefs.AltWarning:
    errors.AltError = True

  if prefs.RefractionOn:
    oldRAref,oldDECref = Current.Refrac()   #Calculate and save refraction correction now
  else:
    oldRAref = 0
    oldDECref = 0

  if prefs.FlexureOn:
    oldRAflex,oldDECflex = Current.Flex()   #Calculate and save flexure correction now
  else:
    oldRAflex = 0
    oldDECflex = 0

  if prefs.RealTimeOn:
    Current.Time.LST += SIDCORRECT   #advance sidereal time by 30 solar seconds
    Current.AltAziConv()             #Calculate the alt/az at that future LST

    if prefs.RefractionOn:
      newRAref,newDECref = Current.Refrac()  #Calculate refraction for future time
    else:
      newRAref = 0.0
      newDECref = 0.0

    if prefs.FlexureOn:
      newRAflex,newDECflex = Current.Flex()  #Calculate flexure for new time
    else:
      newRAflex = 0.0
      newDECflex = 0.0

    Current.Time.update()     #Return to the current time
    Current.AltAziConv()      #Recalculate Alt/Az for now

    deltaRA = (newRAref-oldRAref) + (newRAflex-oldRAflex)
    deltaDEC = (newDECref-oldDECref) + (newDECflex-oldDECflex)

    #Calculate refraction/flexure correction velocities in steps/50ms
    RA_ref = 20.0*(deltaRA/NUM_REF)
    DEC_ref = 20.0*(deltaDEC/NUM_REF)

    #Cap refraction/flexure correction at 200 arcsec/second (~ 3.3 deg/minute)
    #and flag RefError if we've reached that cap.
    errors.RefError = False
    if abs(RA_ref) > 200:
      RA_ref = 200*(RA_ref/abs(RA_ref))
      errors.RefError = True
    if abs(DEC_ref) > 200:
      DEC_ref = 200*(DEC_ref/abs(DEC_ref))
      errors.RefError = True

    #Set the actual refraction/flexure correction velocities in steps/50ms
    motion.motors.RA_refraction = RA_ref
    motion.motors.DEC_refraction = DEC_ref
  else:
    #**Stop the refraction correction**
    motion.motors.RA_refraction = 0.0
    motion.motors.DEC_refraction = 0.0
    errors.RefError = False


def Jump(FObj, Rate=None):
  """Jump to new position.
  
     Inputs:
       FObj - a correct.CalcPosition object containing the destination position
       Rate - the motor speed, in steps/second
       
     Slews in RA by (FObj.RaC-Current.RaC), and slews in DEC by (FObj.DecC-Current.DecC).
     Returns 'True' if Alt of initial or final object is too low, 'False' if the slew proceeded OK.
     
     This function is called by the DoTJBox (that handles external commands) as well as by
     the user from the command line.
  """
  global Current, LastObj
  if Rate is None:
    Rate = prefs.SlewRate
  #TODO - handle locking properly so we don't slew during a slew, or during paddle motion
  UpdateCurrent()             #Apply accumulated paddle and guide movement to current position
  FObj.update(FObj)                      #Correct final object

  if prefs.HighHorizonOn:
    AltCutoffTo = prefs.AltCutoffHi
  else:
    AltCutoffTo = prefs.AltCutoffLo

  if (Current.Alt < prefs.AltCutoffFrom) or (FObj.Alt < AltCutoffTo):
    logger.error('detevent.Jump: Invalid jump, too low for safety! Aborted! AltF=%4.1f, AltT=%4.1f' % (Current.Alt,FObj.Alt))
    return True
  else:
    DelRA = FObj.RaC - Current.RaC

    if abs(DelRA) > (3600*15*12):
      if DelRA < 0:
        DelRA += (3600*15*24)
      else:
        DelRA -= (3600*15*24)
    DelDEC = FObj.DecC - Current.DecC

    DelRA = DelRA*20        #Convert to number of motor steps}
    DelDEC = DelDEC*20
    motion.motors.setprof(DelRA,DelDEC,Rate)  #Calculate the profile and start the actual slew

    LastObj = copy.deepcopy(Current)                    #Save the current position
    Current.RaC, Current.DecC = FObj.RaC, FObj.DecC     #Copy the coordinates to the current position record
    Current.RaA, Current.DecA = FObj.RaA, FObj.DecA
    Current.Ra, Current.Dec = FObj.Ra, FObj.Dec
    Current.Epoch = FObj.Epoch
    Current.TraRA = FObj.TraRA                          #Copy the non-sidereal trackrate to the current position record
    Current.TraDEC = FObj.TraDEC                        #   Non-sidereal tracking will only start when the profiled jump finishes
    motion.motors.RA_track = Current.TraRA              #Set the actual hardware trackrate in the motion controller
    motion.motors.DEC_track = Current.TraDEC            #   Non-sidereal tracking will only happen if prefs.NonSidOn is True
    Current.posviolate = False    #signal a valid original RA and Dec


def DetermineEvent():
  """The main loop that handles housekeeping tasks - communications, status updates,
     hand-paddle switch sensing, etc.
  """
  db = sqlint.InitSQL()    #Get a new db object and use it for this detevent thread
  if db is None:
    logger.warn('detevent.DetermineEvent: Detevent loop started, but with no SQL access.')
  while True:
    UpdateCurrent()        #add all motion to 'Current' object coordinates
    RelRef()               #calculate refraction+flexure correction velocities, check for
                           #    altitude too low and set 'AltError' if true
    SaveStatus()           #Save the current state as pickled data to a status file
    errors.update()        #Increment and check watchdog timer to detect low-level motor control failure
    CheckDirtyPos()        #Check to see if dynamic 'saved position' file needs updating after a move
    CheckDirtyDome()       #Check to see if dome needs moving if DomeTracking is on
    pdome.DomeCheckMove()  #Check to see if dome has reached destination azimuth
    motion.limits.check()  #Test to see if any hardware limits are active (doesn't do much for Perth telescope)
    CheckDBUpdate(db=db)   #Update database at intervals with saved state information
    CheckTJbox(db=db)      #Look for a new database record in the command table for automatic control events
    CheckTimeout()         #Check to see if Prosp (CCD camera controller) is still alive and monitoring weather
    paddles.check()        #Check and act on changes to hand-paddle buttons and switch state.

    time.sleep(0.1)        #Loop approximately 10 times per second


def IniPos():
  """This function is called on startup to set the 'Current' position
     and other data to something reasonable on startup.
     
     Uses the RA, DEC and LST in the state information saved by
     detevent.ChecKDBUpdate and sqlint.UpdateSQLCurrent approximately
     once per second.
  """
  info, HA, LastMod = sqlint.ReadSQLCurrent(Current)
  if info is None:            #Flag a Calibration Error if there was no valid data in the table
    errors.CalError = True
    #If there's no saved position, assume telescope is pointed straight up
    HA = 0
    Current.DecC = prefs.ObsLat*3600
  else:
    errors.CalError = False
    pdome.status.ShutterOpen = info.ShutterOpen
    prefs.EastOfPier = info.EastOfPier

  motion.motors.Frozen = False    #Always start out not frozen

  Current.Time.update()
  rac = (Current.Time.LST+HA)*15*3600
  if rac > 24*15*3600:
    rac -= 24*15*3600
  elif rac < 0.0:
    rac += 24*15*3600
  Current.RaC = rac

  Current.Ra = Current.RaC
  Current.Dec = Current.DecC
  Current.RaA = Current.RaC
  Current.DecA = Current.DecC
  Current.Epoch = 0.0

  logger.debug('detevent.IniPos: Old Alt/Azi: %4.1f, %4.1f' % (Current.Alt, Current.Azi))
  Current.AltAziConv()
  logger.debug('detevent.IniPos: New Alt/Azi: %4.1f, %4.1f' % (Current.Alt, Current.Azi))

  pdome.status.NewDomeAzi = pdome.DomeCalcAzi(Current)
  pdome.status.DomeLastTime = time.time()


def init():
  global detthread, paddles, Current, LastObj
  logger.debug('Detevent unit init started')
  paddles = PaddleStatus()
  Current = correct.CalcPosition()
  LastObj = correct.CalcPosition()
  IniPos()
  logger.debug('Detevent unit init finished')
  detthread = threading.Thread(target=DetermineEvent, name='detevent-thread')
  detthread.daemon = True
  detthread.start()
  logger.debug('detevent.init: Detevent thread started.')

paddles = None
Current = None
LastObj = None
poslog = prefs.LogDirName + '/teljoy.pos'
ProspLastTime = time.time()
DBLastTime = 0
TJboxAction = 'none'
LastError = ""                  #Meant to contain the last reported error string - #TODO - implement in the logger handler.

