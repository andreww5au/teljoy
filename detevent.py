
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
import traceback

from globals import *
import pdome
import correct
import motion
import digio
import sqlint


detthread = None     #Contains the thread object running DetermineEvent after the init() function is called


class EventLoop:
  """Allows a set of functions to be registered that must be called at
     regular intervals. One call to 'run' will iterate through all
     registered functions, catching and logging any errors.
  """
  def __init__(self):
    self.looptime = 0.2
    self.Functions = {}
    self.Errors = {}
    self.exit = False
  def register(self, name, function):
    self.Functions[name] = function
    self.Errors[name] = {}
  def remove(self,name):
    if name in self.Functions:
      del self.Functions[name]
  def runall(self):
    for name,function in self.Functions.iteritems():
      try:
        function()
      except:
        now = time.time()
        error = traceback.format_exc()
        self.Errors[now] = error
        logger.error("Error in EventLoop function %s: %s" % (name, error))
        #Later, maybe remove a function here if it throws exceptions too often?
  def runloop(self, looptime=0.2):
    """Loop forever iterating over the registered functions. Use time.sleep
       to make sure the loop is run no more often than once every 'looptime'
       seconds. Maintain 'self.runtime' as the measured time, in seconds,
       the last time the loop was run.

       Set self.exit to True to exit the loop
    """
    self.looptime = looptime
    logger.info("Event loop started")
    while not self.exit:
      self._Tlast = time.time()
      self.runall()
      self.runtime = time.time()-self._Tlast
      if self.runtime < self.looptime:
        time.sleep(self.looptime - self.runtime)
    logger.info("Event loop exited.")


class Paddles:
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
        motion.motors.DEC.StartPaddle(Paddle_max_vel)
    elif self.ButtonPressedDEC and (self.DECdir=='fineNorth'):
      #Mask does not match but the motor is running}
      self.ButtonPressedDEC = False
      motion.motors.DEC.StopPaddle()

    if ((fb & digio.FSouth)==digio.FSouth):            #Check with South Mask}
      if not self.ButtonPressedDEC:
        self.ButtonPressedDEC = True
        self.DECdir = 'fineSouth'
        Paddle_max_vel = -FinePaddleRate
        motion.motors.DEC.StartPaddle(Paddle_max_vel)
    elif self.ButtonPressedDEC and (self.DECdir=='fineSouth'):
      #Mask does not match but the motor is running}
      self.ButtonPressedDEC = False
      motion.motors.DEC.StopPaddle()

    if ((fb & digio.FEast)==digio.FEast):              #Check the Eastmask}
      if (not self.ButtonPressedRA) and motion.limits.CanEast():
        self.ButtonPressedRA = True
        self.RAdir = 'fineEast'
        Paddle_max_vel = FinePaddleRate
        motion.motors.RA.StartPaddle(Paddle_max_vel)
    elif self.ButtonPressedRA and (self.RAdir=='fineEast'):
      #Mask does not match but the motor is running}
      self.ButtonPressedRA = False
      motion.motors.RA.StopPaddle()

    if ((fb & digio.FWest)==digio.FWest):               #Check the West mask}
      if (not self.ButtonPressedRA) and motion.limits.CanWest():
        self.ButtonPressedRA = True
        self.RAdir = 'fineWest'
        Paddle_max_vel = -FinePaddleRate
        motion.motors.RA.StartPaddle(Paddle_max_vel)
    elif self.ButtonPressedRA and (self.RAdir=='fineWest'):
      #Mask does not match but the motor is running}
      self.ButtonPressedRA = False
      motion.motors.RA.StopPaddle()

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
      logger.info('SLEW')
      CoarsePaddleRate = prefs.SlewRate
    else:
      self.CoarseMode = 'CSet'
      CoarsePaddleRate = prefs.CoarseSetRate
#$ENDIF}

    #**Check the Coarse paddle by comparing cb to a set of masks}
    if ((cb & digio.CNorth)==digio.CNorth):
      logger.info('N')
      if not self.ButtonPressedDEC:
        self.ButtonPressedDEC = True
        self.DECdir = 'coarseNorth'
        Paddle_max_vel = CoarsePaddleRate
        motion.motors.DEC.StartPaddle(Paddle_max_vel)
    elif self.ButtonPressedDEC and (self.DECdir=='coarseNorth'):
      #Mask does not match but the motor is running}
      self.ButtonPressedDEC = False
      motion.motors.DEC.StopPaddle()

    if ((cb & digio.CSouth)==digio.CSouth):
      logger.info('S')
      if not self.ButtonPressedDEC:
        self.ButtonPressedDEC = True
        self.DECdir = 'coarseSouth'
        Paddle_max_vel = -CoarsePaddleRate
        motion.motors.DEC.StartPaddle(Paddle_max_vel)
    elif self.ButtonPressedDEC and (self.DECdir=='coarseSouth'):
      #Mask does not match but the motor is running}
      self.ButtonPressedDEC = False
      motion.motors.DEC.StopPaddle()

    if ((cb & digio.CEast)==digio.CEast):
      logger.info('E')
      if (not self.ButtonPressedRA) and motion.limits.CanEast():
        self.ButtonPressedRA = True
        self.RAdir = 'coarseEast'
        Paddle_max_vel = CoarsePaddleRate
        motion.motors.RA.StartPaddle(Paddle_max_vel)
    elif self.ButtonPressedRA and (self.RAdir=='coarseEast'):
      #Mask does not match but the motor is running}
      self.ButtonPressedRA = False
      motion.motors.RA.StopPaddle()

    if ((cb & digio.CWest)==digio.CWest):
      logger.info('W')
      if (not self.ButtonPressedRA) and motion.limits.CanWest():
        self.ButtonPressedRA = True
        self.RAdir = 'coarseWest'
        Paddle_max_vel = -CoarsePaddleRate
        motion.motors.RA.StartPaddle(Paddle_max_vel)
    elif self.ButtonPressedRA and (self.RAdir=='coarseWest'):
      #Mask does not match but the motor is running}
      self.ButtonPressedRA = False
      motion.motors.RA.StopPaddle()


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
  #invalidate orig RA and Dec if frozen, or paddle move, or non-sidereal move}
  if motion.motors.Frozen or (motion.motors.RA.padlog<>0) or (motion.motors.DEC.padlog<>0):
    Current.posviolate = True

  #account for paddle and non-sid. motion, and limit encounters}
  Current.RaA += motion.motors.RA.padlog/20
  Current.DecA += motion.motors.DEC.padlog/20

  #above, plus real-time refraction+flexure+guide in the fully corrected coords}
  Current.RaC += motion.motors.RA.padlog/20 + motion.motors.RA.reflog/20 + motion.motors.RA.guidelog/20
  Current.DecC += motion.motors.DEC.padlog/20 + motion.motors.DEC.reflog/20 + motion.motors.DEC.guidelog/20
  paddles.RA_GuideAcc += motion.motors.RA.guidelog/20
  paddles.DEC_GuideAcc += motion.motors.DEC.guidelog/20

  with motion.motors.RA.lock:
    motion.motors.RA.padlog = 0
    motion.motors.RA.reflog = 0
    motion.motors.RA.guidelog = 0
  with motion.motors.DEC.lock:
    motion.motors.DEC.padlog = 0
    motion.motors.DEC.reflog = 0
    motion.motors.DEC.guidelog = 0

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
  cPickle.dump((Current,motion.motors,pdome.dome,errors,prefs),f)
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

  if (DirtyTime<>0) and (time.time()-DirtyTime > prefs.WaitBeforePosUpdate) and not motion.motors.Moving:
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
  if ( (abs(pdome.CalcAzi(Current)-pdome.dome.NewDomeAzi) > 6) and
       ((time.time()-pdome.dome.DomeLastTime) > prefs.MinWaitBetweenDomeMoves) and
       (not pdome.dome.DomeInUse) and
       (not pdome.dome.ShutterInUse) and
       pdome.dome.DomeTracking and
       (not motion.motors.Moving) and
       pdome.dome.AutoDome and
       (not motion.motors.PosDirty) ):
    pdome.dome.move(pdome.CalcAzi(Current))


def CheckDBUpdate():
  """Make sure that the current state is saved to the SQL database approximately once 
     every second. Exits without an error if the SQL connection isn't available.
     
     The state data is used by external clients (eg Prosp, the CCD camera controller)
     and also used by Teljoy to set the initial position on startup, using the last
     recorded RA, DEC and LST.

     This function is called at regular intervals by the DetermineEvent loop.
  """
  global db, DBLastTime
  if (time.time()-DBLastTime) > 1.0:
    foo = sqlint.Info() 
    foo.posviolate = Current.posviolate
    foo.moving = motion.motors.Moving
    foo.EastOfPier = prefs.EastOfPier
    foo.NonSidOn = prefs.NonSidOn
    foo.DomeInUse = pdome.dome.DomeInUse
    foo.ShutterInUse = pdome.dome.ShutterInUse
    foo.ShutterOpen = pdome.dome.ShutterOpen
    foo.DomeTracking = pdome.dome.DomeTracking
    foo.Frozen = motion.motors.Frozen
    foo.RA_guideAcc = paddles.RA_GuideAcc
    foo.DEC_guideAcc = paddles.DEC_GuideAcc
    foo.LastError = LastError
    sqlint.UpdateSQLCurrent(Current, foo, db)
    DBLastTime = time.time()


def DoTJbox():
  """Read the tjbox database table and carry out any commanded actions.
     Exits without an error if the SQL connection isn't available.

     This function is called by CheckTJBox.
  """
  #TODO - add an RPC interface for external commands
  global db, ProspLastTime, TJboxAction
  BObj, other = sqlint.ReadTJbox(db=db)
  if BObj is None or other is None:
    return
  ProspLastTime = time.time()
  if (other.LastMod<0) or (other.LastMod>5) or motion.motors.Moving:
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
        if pdome.dome.AutoDome and (not AltErr):
          pdome.dome.move(pdome.CalcAzi(JObj))
        if AltErr:
          logger.error('detevent.DoTJBox: Object in TJbox below Alt Limit')
        else:
          TJboxAction = other.action
      else:
        TJboxAction = 'none'
        sqlint.ClearTJbox(db=db)
    elif other.action == 'jumprd':
      AltErr = Jump(BObj, prefs.SlewRate)
      if pdome.dome.AutoDome and (not AltErr):
        pdome.dome.move(pdome.CalcAzi(BObj))
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
      motion.motors.Jump(DelRA,DelDEC,prefs.SlewRate)  #Calculate the motor profile and jump}
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
        pdome.dome.move(pdome.CalcAzi(Current))
      else:
        pdome.dome.move(other.DomeAzi)
      TJboxAction = other.action

    elif other.action == 'shutter':
      if other.Shutter:
        pdome.dome.open()           #True for open}
      else:
        pdome.dome.close()
      TJboxAction = other.action

    elif (other.action == 'freez') or (other.action == 'freeze'):
      if other.Freeze:
        motion.motors.Frozen = True
      else:
        motion.motors.Frozen = False
      TJboxAction = 'none'    #Action complete}
      sqlint.ClearTJbox(db=db)


def CheckTJbox():
  """Check the command table in the database and carry out any commanded actions.
     Check the progress of any previous commands still being acted on.
     Exits without an error if the SQL connection isn't available.     

     This function is called at regular intervals by the DetermineEvent loop.
  """
  #TODO - add an RPC interface for external commands
  global db, TJboxAction
  if TJboxAction == 'none':
    if sqlint.ExistsTJbox(db=db):
      DoTJbox()
  elif TJboxAction in ['jumpid','jumprd','jumpaa','offset']:
    if (not motion.motors.Moving) and (not pdome.dome.DomeInUse):
      TJboxAction = 'none'
      sqlint.ClearTJbox(db=db)
  elif TJboxAction == 'dome':
    if not pdome.dome.DomeInUse:
      TJboxAction = 'none'
      sqlint.ClearTJbox(db=db)
  elif TJboxAction == 'shutter':
    if not pdome.dome.ShutterInUse:
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
  if ((time.time()-ProspLastTime) > 600) and pdome.dome.ShutterOpen and (not pdome.dome.ShutterInUse):
    logger.critical('detevent.CheckTimeout: No communication with Prosp for over 10 minutes!\nClosing Shutter, Freezing Telescope.')
    pdome.dome.close()
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
    with motion.motors.RA.lock:
      motion.motors.RA.refraction = RA_ref
    with motion.motors.DEC.lock:
      motion.motors.DEC.refraction = DEC_ref
  else:
    #**Stop the refraction correction**
    with motion.motors.RA.lock:
      motion.motors.RA.refraction = 0.0
    with motion.motors.DEC.lock:
      motion.motors.DEC.refraction = 0.0
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
  if motion.motors.Moving:
    logger.error('detevent.Jump called while telescope in motion!')
    return True
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
    motion.motors.Jump(DelRA,DelDEC,Rate)  #Calculate the profile and start the actual slew

    LastObj = copy.deepcopy(Current)                    #Save the current position
    Current.RaC, Current.DecC = FObj.RaC, FObj.DecC     #Copy the coordinates to the current position record
    Current.RaA, Current.DecA = FObj.RaA, FObj.DecA
    Current.Ra, Current.Dec = FObj.Ra, FObj.Dec
    Current.Epoch = FObj.Epoch
    Current.TraRA = FObj.TraRA                          #Copy the non-sidereal trackrate to the current position record
    Current.TraDEC = FObj.TraDEC                        #   Non-sidereal tracking will only start when the profiled jump finishes
    with motion.motors.RA.lock:
      motion.motors.RA.track = Current.TraRA              #Set the actual hardware trackrate in the motion controller
    with motion.motors.DEC.lock:
      motion.motors.DEC.track = Current.TraDEC            #   Non-sidereal tracking will only happen if prefs.NonSidOn is True
    Current.posviolate = False    #signal a valid original RA and Dec




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
    pdome.dome.ShutterOpen = info.ShutterOpen
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

  pdome.dome.NewDomeAzi = pdome.CalcAzi(Current)
  pdome.dome.DomeLastTime = time.time()


def init():
  global db, eventloop, detthread, paddles, Current, LastObj
  logger.debug('Detevent unit init started')

  db = sqlint.InitSQL()    #Get a new db object and use it for this detevent thread
  if db is None:
    logger.warn('detevent.DetermineEvent: Detevent loop started, but with no SQL access.')

  paddles = Paddles()
  Current = correct.CalcPosition()
  LastObj = correct.CalcPosition()
  IniPos()

  eventloop = EventLoop()
  eventloop.register('UpdateCurrent', UpdateCurrent)         #add all motion to 'Current' object coordinates
  eventloop.register('RelRef', RelRef)                       #calculate refraction+flexure correction velocities, check for
                                                             #    altitude too low and set 'AltError' if true
  eventloop.register('SaveStatus', SaveStatus)               #Save the current state as pickled data to a status file
  eventloop.register('errors.update', errors.update)         #Increment and check watchdog timer to detect low-level motor control failure
  eventloop.register('CheckDirtyPos', CheckDirtyPos)         #Check to see if dynamic 'saved position' file needs updating after a move
  eventloop.register('CheckDirtyDome', CheckDirtyDome)       #Check to see if dome needs moving if DomeTracking is on
  eventloop.register('pdome.dome.check', pdome.dome.check)  #Check to see if dome has reached destination azimuth
  eventloop.register('motion.limits.check', motion.limits.check)  #Test to see if any hardware limits are active (doesn't do much for Perth telescope)
  eventloop.register('CheckDBUpdate', CheckDBUpdate)              #Update database at intervals with saved state information
  eventloop.register('CheckTJbox', CheckTJbox)               #Look for a new database record in the command table for automatic control events
  eventloop.register('CheckTimeout', CheckTimeout)           #Check to see if Prosp (CCD camera controller) is still alive and monitoring weather
  eventloop.register('paddles.check', paddles.check)         #Check and act on changes to hand-paddle buttons and switch state.

  logger.debug('Detevent unit init finished')
  detthread = threading.Thread(target=eventloop.runloop, name='detevent-thread')
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

