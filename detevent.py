
"""
   This module contains the code needed to support higher-level telescope control, 
   including maintaining the current telescope coordinates, as well as checking and
   acting on external inputs (hand-paddle buttons, commanded actions via the SQL 
   'mailbox' table', etc) and publishing the state to the outside world (maintaining
   the current state in an SQL table and a position file).
   
   The core of the module is the 'DetermineEvent' function, which runs continuously,
   and never exits once called apart from non-recoverable errors. The init() function
   in this module will start this function in a separate thread.

"""

import math
import time
import threading
import copy
import traceback

from globals import *
import pdome
import correct
import motion
import sqlint
import weather
from handpaddles import paddles

TIMEOUT = 0   #Set to the number of seconds you want to wait without any contact from Prosp before closing down.

FASTLOOP = 0.2     #How often the 'fast event loop' will call each of the registered functions
SLOWLOOP = 30      #How often the 'slow event loop' will call each of the registered functions

detthread = None     #Contains the thread object running DetermineEvent after the init() function is called


class EventLoop:
  """Allows a set of functions to be registered that must be called at
     regular intervals. One call to 'run' will iterate through all
     registered functions, catching and logging any errors.
  """
  def __init__(self, name='', looptime=1.0):
    self.name = name
    self.looptime = looptime
    self.Functions = {}
    self.Errors = {}
    self.exit = False
  def register(self, name, function):
    self.Functions[name] = function
    self.Errors[name] = {}
  def remove(self,name):
    if name in self.Functions:
      del self.Functions[name]
  def shutdown(self):
    self.exit = True
  def runall(self):
    for name,function in self.Functions.iteritems():
      try:
        function()
      except:
        now = time.time()
        error = traceback.format_exc()
        self.Errors[now] = error
        logger.error("Error in EventLoop '%s': function %s: %s" % (self.name, name, error))
        #Later, maybe remove a function here if it throws exceptions too often?
  def runloop(self):
    """Loop forever iterating over the registered functions. Use time.sleep
       to make sure the loop is run no more often than once every 'looptime'
       seconds. Maintain 'self.runtime' as the measured time, in seconds,
       the last time the loop was run.

       Set self.exit to True to exit the loop
    """
    self.exit = False
    logger.info("Event loop '%s' started" % self.name)
    while not self.exit:
      self._Tlast = time.time()
      self.runall()
      self.runtime = time.time()-self._Tlast
      sleeptime = self.looptime - self.runtime
      if sleeptime <= 0:
        pass
      elif sleeptime < 1.0:
        time.sleep(self.looptime - self.runtime)
      else:
        for i in range(int(sleeptime)):
          time.sleep(1.0)
          if self.exit:
            break
    logger.info("Event loop '%s' exited." % self.name)


class CurrentPosition(correct.CalcPosition):
  """A special position object that's used only to store the current telescope coordinates, and
     allow jumps from this position.
  """
  def __repr__(self):
    if self.posviolate:
      l1 = "Top RA:  %s      LST: %s         ObjID:   --" % (sexstring(self.RaC/15.0/3600,fixed=True), sexstring(self.Time.LST, fixed=True))
      l2 = "Top Dec: %s     UT:  %s" %                      (sexstring(self.DecC/3600,fixed=True), self.Time.UT.time().isoformat()[:-4])
      l3 = "Alt:     %s      HA:  %s        ObjRA:   --" %  (sexstring(self.Alt, fixed=True), sexstring(self.RaC/15/3600-self.Time.LST, fixed=True))
      l4 = "Airmass: %6.4f        NonSidereal: %s      ObjDec:  --" % (1/math.cos((90-self.Alt)/180*math.pi), {False:"OFF", True:" ON"}[prefs.NonSidOn])
      l5 = "Moving:  %s           Frozen: %s           ObjEpoch: --" % ({False:" No", True:"Yes"}[motion.motors.Moving], {False:" No", True:"Yes"}[motion.motors.Frozen])
    else:
      l1 = "Top RA:  %s      LST: %s         ObjID:   %s" % (sexstring(self.RaC/15.0/3600,fixed=True), sexstring(self.Time.LST, fixed=True), self.ObjID)
      l2 = "Top Dec: %s     UT:  %s" %                      (sexstring(self.DecC/3600,fixed=True), self.Time.UT.time().isoformat()[:-4])
      l3 = "Alt:     %s      HA:  %s        ObjRA:   %s" % (sexstring(self.Alt, fixed=True), sexstring(self.RaC/15/3600-self.Time.LST, fixed=True),
                                                            sexstring(self.Ra/15/3600, fixed=True))
      l4 = "Airmass: %6.4f        NonSidereal: %s      ObjDec:  %s" % (1/math.cos((90-self.Alt)/180*math.pi), {False:"OFF", True:" ON"}[prefs.NonSidOn],
                                                                       sexstring(self.Dec/3600, fixed=True))
      l5 = "Moving:  %s           Frozen: %s           ObjEpoch:%6.1f" % ({False:" No", True:"Yes"}[motion.motors.Moving], {False:" No", True:"Yes"}[motion.motors.Frozen],
                                                                          self.Epoch)
    l6 = "Dome:  %s        Dome Tracking: %s           %s" % ({False:"Inactive", True:"  Active"}[pdome.dome.DomeInUse],
                                                              {False:" No", True:"Yes"}[pdome.dome.DomeTracking],
                                                              str(errors))
    return '\n'.join([l1,l2,l3,l4,l5,l6])+'\n'

  def UpdatePosition(self):
    """Update Current sky coordinates from paddle and refraction motion

       This function is called at regular intervals by the DetermineEvent loop.
    """
    #invalidate orig RA and Dec if frozen, or paddle move, or non-sidereal move}
    if motion.motors.Frozen or (motion.motors.RA.padlog<>0) or (motion.motors.DEC.padlog<>0):
      self.posviolate = True

    with motion.motors.RA.lock:
      #account for paddle and non-sid. motion, and limit encounters}
      self.RaA += motion.motors.RA.padlog/20
      #above, plus real-time refraction+flexure+guide in the fully corrected coords}
      self.RaC += motion.motors.RA.padlog/20 + motion.motors.RA.reflog/20 + motion.motors.RA.guidelog/20
      paddles.RA_GuideAcc += motion.motors.RA.guidelog/20
      motion.motors.RA.padlog = 0
      motion.motors.RA.reflog = 0
      motion.motors.RA.guidelog = 0

    with motion.motors.DEC.lock:
      #account for paddle and non-sid. motion, and limit encounters}
      self.DecA += motion.motors.DEC.padlog/20
      #above, plus real-time refraction+flexure+guide in the fully corrected coords}
      self.DecC += motion.motors.DEC.padlog/20 + motion.motors.DEC.reflog/20 + motion.motors.DEC.guidelog/20
      paddles.DEC_GuideAcc += motion.motors.DEC.guidelog/20
      motion.motors.DEC.padlog = 0
      motion.motors.DEC.reflog = 0
      motion.motors.DEC.guidelog = 0

    if self.RaA > (24*60*60*15):
      self.RaA -= (24*60*60*15)
    if self.RaA < 0:
      self.RaA += (24*60*60*15)

    if self.RaC > (24*60*60*15):
      self.RaC -= (24*60*60*15)
    if self.RaC < 0:
      self.RaC += (24*60*60*15)

  def RelRef(self):
    """Calculates real time refraction and flexure correction velocities for the current position.
       These velocities are mixed into the telescope motion by the low-level control loop
       in motion.motors.TimeInt.

       This function is called at regular intervals by the DetermineEvent loop.
    """
    NUM_REF = 600                  # no of interrupts in time_inc time.
    SIDCORRECT = 30.08213727/3600  #number of siderial hours in update time

    #**Begin refraction correction**
    self.Time.update()
    self.AltAziConv()           #Calculate Alt/Az now

    errors.AltError = False
    if self.Alt < prefs.AltWarning:
      errors.AltError = True

    if prefs.RefractionOn:
      oldRAref,oldDECref = self.Refrac()   #Calculate and save refraction correction now
    else:
      oldRAref = 0
      oldDECref = 0

    if prefs.FlexureOn:
      oldRAflex,oldDECflex = self.Flex()   #Calculate and save flexure correction now
    else:
      oldRAflex = 0
      oldDECflex = 0

    if prefs.RealTimeOn:
      self.Time.LST += SIDCORRECT   #advance sidereal time by 30 solar seconds
      self.AltAziConv()             #Calculate the alt/az at that future LST

      if prefs.RefractionOn:
        newRAref,newDECref = self.Refrac()  #Calculate refraction for future time
      else:
        newRAref = 0.0
        newDECref = 0.0

      if prefs.FlexureOn:
        newRAflex,newDECflex = self.Flex()  #Calculate flexure for new time
      else:
        newRAflex = 0.0
        newDECflex = 0.0

      self.Time.update()     #Return to the current time
      self.AltAziConv()      #Recalculate Alt/Az for now

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

  def Jump(self, FObj, Rate=None, force=False):
    """Jump to new position.

       Inputs:
         FObj - a correct.CalcPosition object containing the destination position
         Rate - the motor speed, in steps/second

       Slews in RA by (FObj.RaC-Current.RaC), and slews in DEC by (FObj.DecC-Current.DecC).
       Returns 'True' if Alt of initial or final object is too low, 'False' if the slew proceeded OK.

       This method is called by DoTJBox (that handles external commands) as well as by
       the user from the command line.
    """
    global LastObj
    if Rate is None:
      Rate = prefs.SlewRate
    self.UpdatePosition()             #Apply accumulated paddle and guide movement to current position
    FObj.update()                      #Correct final object coordinates

    if prefs.HighHorizonOn:
      AltCutoffTo = prefs.AltCutoffHi
    else:
      AltCutoffTo = prefs.AltCutoffLo

    if errors.CalError:
      logger.error('Teljoy uncalibrated! - do a Reset() to set the position before slewing')
      return True
    elif (self.Alt < prefs.AltCutoffFrom) or (FObj.Alt < AltCutoffTo):
      logger.error('detevent.Jump: Invalid jump, too low for safety! Aborted! AltF=%4.1f, AltT=%4.1f' % (self.Alt,FObj.Alt))
      return True
    elif (not safety.Active.is_set()) and (not force):
      logger.error('detevent.Jump: safety interlock - no jumping allowed.')
      return True
    else:
      if force:
        logger.info('detevent.Jump: safety interlock forced - jumping anyway')
      DelRA = FObj.RaC - self.RaC

      if abs(DelRA) > (3600*15*12):
        if DelRA < 0:
          DelRA += (3600*15*24)
        else:
          DelRA -= (3600*15*24)
      DelDEC = FObj.DecC - self.DecC

      DelRA = DelRA*20        #Convert to number of motor steps}
      DelDEC = DelDEC*20

      with motion.motors.lock:
        if motion.motors.Moving or motion.motors.Paddling:
          logger.error('detevent.Jump called while telescope in motion!')
          return True

        jumperror = motion.motors.Jump(DelRA,DelDEC,Rate, force=force)  #Calculate the profile and start the actual slew
        if jumperror:
          return True
        else:
          LastObj = copy.deepcopy(self)                    #Save the current position
          self.RaC, self.DecC = FObj.RaC, FObj.DecC     #Copy the coordinates to the current position record
          self.RaA, self.DecA = FObj.RaA, FObj.DecA
          self.Ra, self.Dec = FObj.Ra, FObj.Dec
          self.Epoch = FObj.Epoch
          self.TraRA = FObj.TraRA                          #Copy the non-sidereal trackrate to the current position record
          self.TraDEC = FObj.TraDEC                        #   Non-sidereal tracking will only start when the profiled jump finishes
          self.ObjID = FObj.ObjID
          with motion.motors.RA.lock:
            motion.motors.RA.track = self.TraRA              #Set the actual hardware trackrate in the motion controller
          with motion.motors.DEC.lock:
            motion.motors.DEC.track = self.TraDEC            #   Non-sidereal tracking will only happen if prefs.NonSidOn is True
          self.posviolate = False    #signal a valid original RA and Dec

  def IniPos(self):
    """This function is called on startup to set the 'Current' position
       and other data to something reasonable on startup.

       Uses the RA, DEC and LST in the state information saved by
       detevent.ChecKDBUpdate and sqlint.UpdateSQLCurrent approximately
       once per second.
    """
    info, HA, LastMod = sqlint.ReadSQLCurrent(self)
    if info is None:            #Flag a Calibration Error if there was no valid data in the table
      errors.CalError = True
      #If there's no saved position, assume telescope is pointed straight up
      HA = 0
      self.DecC = prefs.ObsLat*3600
    else:
      errors.CalError = False
      pdome.dome.IsShutterOpen = info.ShutterOpen
      prefs.EastOfPier = info.EastOfPier

    motion.motors.Frozen = False    #Always start out not frozen

    self.Time.update()
    rac = (self.Time.LST+HA)*15*3600
    if rac > 24*15*3600:
      rac -= 24*15*3600
    elif rac < 0.0:
      rac += 24*15*3600
    self.RaC = rac

    self.Ra = self.RaC
    self.Dec = self.DecC
    self.RaA = self.RaC
    self.DecA = self.DecC
    self.Epoch = 0.0

    logger.debug('detevent.IniPos: Old Alt/Azi: %4.1f, %4.1f' % (self.Alt, self.Azi))
    self.AltAziConv()
    logger.debug('detevent.IniPos: New Alt/Azi: %4.1f, %4.1f' % (self.Alt, self.Azi))

    pdome.dome.DomeAzi = pdome.dome.CalcAzi(self)
    pdome.dome.DomeLastTime = time.time()

  def Reset(self, obj):
    """Set the current RA and DEC to those in the specified object (must be an instance of correct.CalcPosition)
    """
    obj.update()
    self.Ra, self.Dec, self.Epoch, self.ObjID = obj.Ra, obj.Dec, obj.Epoch, obj.ObjID
    self.update()
    errors.CalError = False

  def Offset(self, ora, odec):
    """Make a tiny slew from the current position, by ora,odec arcseconds.
    """
    DelRA = 20*ora/math.cos(self.DecC/3600*math.pi/180)  #conv to motor steps
    DelDEC = 20*odec
    with motion.motors.lock:
      if motion.motors.Moving or motion.motors.Paddling:
        logger.error('detevent.Jump called while telescope in motion!')
        return True
      motion.motors.Jump(DelRA,DelDEC,prefs.SlewRate)  #Calculate the motor profile and jump
      if not self.posviolate:
        self.Ra +=ora/math.cos(self.DecC/3600*math.pi/180)
        self.Dec += odec
      self.RaA += ora/math.cos(self.DecC/3600*math.pi/180)
      self.DecA += odec
      self.RaC += ora/math.cos(self.DecC/3600*math.pi/180)
      self.DecC += odec


def CheckDirtyPos():
  """Check to see if we've just finished a move (hand paddle or profiled jump).
     
     The motion.motors.PosDirty flag is true if the telescope while the telescope
     is moving, AND for a few seconds after it finishes moving. It is reset to False
     by this function. Other code uses this flag to delay costly actions like
     moving the dome until it's clear that another movement (eg, paddle button) isn't
     about to occur).

     If more than prefs.WaitBeforePosUpdate seconds have passed since the end of the last
     move, flag the current position as new and stable by clearing the PosDirty flag.
     
     This function is called at regular intervals by the DetermineEvent loop.
  """
  global DirtyTime
  if motion.motors.PosDirty and (DirtyTime==0):
    DirtyTime = time.time()                 #just finished move}

  if ( (DirtyTime<>0) and
       (time.time()-DirtyTime > prefs.WaitBeforePosUpdate) and
       not motion.motors.Moving and
       not errors.CalError):
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
  if ( (abs(pdome.dome.CalcAzi(current)-pdome.dome.DomeAzi) > 6) and
       ((time.time()-pdome.dome.DomeLastTime) > prefs.MinWaitBetweenDomeMoves) and
       (not pdome.dome.DomeInUse) and
       pdome.dome.DomeTracking and
       (not motion.motors.Moving) and
       pdome.dome.AutoDome and
       (not motion.motors.PosDirty) and
       not errors.CalError ):
    pdome.dome.move(pdome.dome.CalcAzi(current))


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
    foo.posviolate = current.posviolate
    foo.moving = motion.motors.Moving
    foo.EastOfPier = prefs.EastOfPier
    foo.NonSidOn = prefs.NonSidOn
    foo.DomeInUse = pdome.dome.DomeInUse
    foo.ShutterInUse = pdome.dome.DomeInUse
    foo.ShutterOpen = pdome.dome.IsShutterOpen
    foo.DomeTracking = pdome.dome.DomeTracking
    foo.Frozen = motion.motors.Frozen
    foo.RA_guideAcc = paddles.RA_GuideAcc
    foo.DEC_guideAcc = paddles.DEC_GuideAcc
    foo.LastError = LastError
    sqlint.UpdateSQLCurrent(current, foo, db)
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
        JObj = sqlint.GetRC3(BObj.ObjID, num=0, db=db)
        if (JObj is not None) and JObj.numfound == 1:
          found = True
      if found and (not motion.limits.HWLimit):
        if safety.Active.is_set():
          AltErr = current.Jump(JObj, prefs.SlewRate)  #Goto new position}
          logger.info("detevent.DoTJbox: Remote control jump to object: %s" % JObj)
          if pdome.dome.AutoDome and (not AltErr):
            pdome.dome.move(pdome.dome.CalcAzi(JObj))
          if AltErr:
            logger.error("detevent.DoTJBox: Object in TJbox below Alt Limit")
          else:
            TJboxAction = other.action
        else:
          logger.error('detevent.DoTJbox: ERROR - safety interlock, NO jumping')
          TJboxAction = 'none'
          sqlint.ClearTJbox(db=db)
      else:
        TJboxAction = 'none'
        sqlint.ClearTJbox(db=db)

    elif other.action == 'jumprd':
      if safety.Active.is_set():
        AltErr = current.Jump(BObj, prefs.SlewRate)
        logger.info("detevent.DoTJbox: Remote control jump to object: %s" % BObj)
        if pdome.dome.AutoDome and (not AltErr):
          pdome.dome.move(pdome.dome.CalcAzi(BObj))
        if AltErr:
          logger.error('detevent.DoTJbox: Object in TJbox below Alt Limit')
        else:
          TJboxAction = other.action
      else:
        logger.error('detevent.DoTJbox: ERROR - safety interlock, NO jumping')
        TJboxAction = 'none'
        sqlint.ClearTJbox(db=db)

    elif other.action == 'reset':
      current.Reset(BObj)
      logger.info("detevent.DoTJbox: Remote control reset current position to %s" % BObj)

    elif other.action == 'jumpaa':
      sqlint.ClearTJbox(db=db)
      logger.error("detevent.DoTJbox: Remote control command 'jumpaa' not supported.")

    elif other.action == 'nonsid':
      sqlint.ClearTJbox(db=db)
      logger.error("detevent.DoTJbox: Remote control command 'nonsid' not supported.")

    elif other.action == 'offset':
      current.Offset(other.OffsetRA, other.OffsetDEC)
      logger.info("detevent.DoTJbox: Remote small offset shift by %4.1f,%4.1f arcsec" % (other.OffsetRA, other.OffsetDEC))
      TJboxAction = other.action

    elif other.action == 'dome':
      if other.DomeAzi < 0:
        pdome.dome.move(pdome.dome.CalcAzi(current))
        logger.info("detevent.DoTJbox: Dome aligned to current telescope position")
      else:
        pdome.dome.move(other.DomeAzi)
        logger.info("detevent.DoTJbox: Dome moved to %d" % other.DomeAzi)
      TJboxAction = other.action

    elif other.action == 'shutter':
      if other.Shutter:
        if safety.Active.is_set():
          pdome.dome.open()           #True for open}
          logger.info("detevent.DoTJbox: remote control - shutter opened")
          TJboxAction = other.action
        else:
          logger.error('detevent.DoTJbox: ERROR - safety interlock, shutter NOT opened')
          TJboxAction = 'none'
          sqlint.ClearTJbox(db=db)
      else:
        pdome.dome.close()
        logger.info("detevent.DoTJbox: remote control - shutter closed")
        TJboxAction = other.action

    elif (other.action == 'freez') or (other.action == 'freeze'):
      if other.Freeze:
        motion.motors.Frozen = True
        logger.info("detevent.DoTJbox: remote control - telescope frozen")
      else:
        if safety.Active.is_set():
          motion.motors.Frozen = False
          logger.info("detevent.DoTJbox: remote control - telescope un-frozen")
        else:
          logger.error('detevent.DoTJbox: ERROR - safety interlock, telescope NOT un-frozen')
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
    if not pdome.dome.DomeInUse:
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
  #TODO - make timeout configurable via teljoy.ini and globals.prefs.
  if TIMEOUT == 0:
    errors.TimeoutError = False
  elif ((time.time()-ProspLastTime) > TIMEOUT) and pdome.dome.IsShutterOpen and (not pdome.dome.DomeInUse):
    logger.critical('detevent.CheckTimeout: No communication with Prosp for over %d seconds!\nClosing Shutter, Freezing Telescope.' % TIMEOUT)
    errors.TimeoutError = True
    safety.add_tag('Prosp communications time out - shutting down')  #Discard tag, we don't want to try to recover from this
  else:
    errors.TimeoutError = False


def init():
  global db, fastloop, slowloop, fastthread, slowthread, paddles, current, LastObj
  logger.debug('Detevent unit init started')

  db = sqlint.InitSQL()    #Get a new db object and use it for this detevent thread
  if db is None:
    logger.warn('detevent.DetermineEvent: Detevent loop started, but with no SQL access.')

  current = CurrentPosition()
  LastObj = correct.CalcPosition()
  current.IniPos()

  fastloop = EventLoop(name='FastLoop', looptime=FASTLOOP)
  fastloop.register('UpdateCurrent', current.UpdatePosition)         #add all motion to 'current' object coordinates
  fastloop.register('CheckDBUpdate', CheckDBUpdate)              #Update database at intervals with saved state information
  fastloop.register('CheckDirtyPos', CheckDirtyPos)         #Check to see if the PosDirty flag needs to be cleared
  fastloop.register('CheckDirtyDome', CheckDirtyDome)       #Check to see if dome needs moving if DomeTracking is on
  fastloop.register('pdome.dome.check', pdome.dome.check)  #Check to see if dome has reached destination azimuth
  fastloop.register('motion.limits.check', motion.limits.check)  #Test to see if any hardware limits are active (doesn't do much for Perth telescope)
  fastloop.register('CheckTJbox', CheckTJbox)               #Look for a new database record in the command table for automatic control events
  fastloop.register('CheckTimeout', CheckTimeout)           #Check to see if Prosp (CCD camera controller) is still alive and monitoring weather
  fastloop.register('paddles.check', paddles.check)         #Check and act on changes to hand-paddle buttons and switch state.

  weather.Init()    #Initialise weather package, including SQL connection
  slowloop = EventLoop(name='SlowLoop', looptime=SLOWLOOP)
  slowloop.register('RelRef', current.RelRef)              #calculate refraction+flexure velocities, check alt, set 'AltError' if low
  slowloop.register('Weather', weather._background)

  logger.debug('Detevent unit init finished')
  fastthread = threading.Thread(target=fastloop.runloop, name='detevent-fastloop-thread')
  fastthread.daemon = True
  fastthread.start()
  logger.debug('detevent.init: Detevent fast loop thread started.')
  slowthread = threading.Thread(target=slowloop.runloop, name='detevent-slowloop-thread')
  slowthread.daemon = True
  slowthread.start()
  logger.debug('detevent.init: Detevent slow loop thread started.')


current = None
LastObj = None
ProspLastTime = time.time()
DBLastTime = 0
TJboxAction = 'none'
LastError = ""                  #Meant to contain the last reported error string - #TODO - implement in the logger handler.

