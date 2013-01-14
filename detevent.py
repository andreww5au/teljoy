
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
import sqlint
from handpaddles import paddles

TIMEOUT = 0   #Set to the number of seconds you want to wait without any contact from Prosp before closing down.


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
        logger.error("Error in EventLoop function %s: %s" % (name, error))
        #Later, maybe remove a function here if it throws exceptions too often?
  def runloop(self, looptime=0.2):
    """Loop forever iterating over the registered functions. Use time.sleep
       to make sure the loop is run no more often than once every 'looptime'
       seconds. Maintain 'self.runtime' as the measured time, in seconds,
       the last time the loop was run.

       Set self.exit to True to exit the loop
    """
    self.exit = False
    self.looptime = looptime
    logger.info("Event loop started")
    while not self.exit:
      self._Tlast = time.time()
      self.runall()
      self.runtime = time.time()-self._Tlast
      if self.runtime < self.looptime:
        time.sleep(self.looptime - self.runtime)
    logger.info("Event loop exited.")


class CurrentPosition(correct.CalcPosition):
  """A special position object that's used only to store the current telescope coordinates, and
     allow jumps from this position.
  """
  def __repr__(self):
    if self.posviolate:
      l1 = "Top RA:  %s      LST: %s         ObjID:   --" % (sexstring(self.RaC/15.0/3600,fixed=True), sexstring(self.Time.LST, fixed=True), self.ObjID)
      l2 = "Top Dec: %s     UT:  %s" %                      (sexstring(self.DecC/3600,fixed=True), self.Time.UT.time().isoformat()[:-4])
      l3 = "Alt:     %s      HA:  %s        ObjRA:   --" %  (sexstring(self.Alt, fixed=True), sexstring(self.RaC/15/3600-self.Time.LST, fixed=True))
      l4 = "Airmass: %6.4f        NonSidereal: %s      ObjDec:  --" % (1/math.cos((90-self.Alt)/180*math.pi), {False:"OFF", True:" ON"}[prefs.NonSidOn])
    else:
      l1 = "Top RA:  %s      LST: %s         ObjID:   %s" % (sexstring(self.RaC/15.0/3600,fixed=True), sexstring(self.Time.LST, fixed=True), self.ObjID)
      l2 = "Top Dec: %s     UT:  %s" %                      (sexstring(self.DecC/3600,fixed=True), self.Time.UT.time().isoformat()[:-4])
      l3 = "Alt:     %s      HA:  %s        ObjRA:   %s" % (sexstring(self.Alt, fixed=True), sexstring(self.RaC/15/3600-self.Time.LST, fixed=True),
                                                            sexstring(self.Ra/15/3600, fixed=True))
      l4 = "Airmass: %6.4f        NonSidereal: %s      ObjDec:  %s" % (1/math.cos((90-self.Alt)/180*math.pi), {False:"OFF", True:" ON"}[prefs.NonSidOn],
                                                                       sexstring(self.Dec/3600, fixed=True)
    l5 = "Moving:  %s           Frozen: %s           ObjEpoch:%6.1f" % ({False:" No", True:"Yes"}[motion.motors.Moving], {False:" No", True:"Yes"}[motion.motors.Frozen],
                                                                  self.Epoch)
    l6 = "Dome:  %s        Dome Tracking: %s" % ({False:"Inactive", True:"  Active"}[pdome.dome.DomeInUse or pdome.dome.ShutterInUse],
                                                {False:" No", True:"Yes"}[pdome.dome.DomeTracking])
    return '\n'.join([l1,l2,l3,l4,l5,l6])+'\n'

  def UpdatePosFile(self):
    """Save the current position to the 'saved position' file.

       The saved position file isn't actually used any more. It used to be the source of the
       initial position on startup, but now the current state from the database (saved by
       detevent.CheckDBUpdate and sqlint.UpdateSQLCurrent) is used instead.

       This method is called by CheckDirtyPos a set interval after a telescope move has finished.
    """
    t = correct.TimeRec()   #Defaults to 'now'
    d = t.UT
    try:
      pfile = open(poslog,'w')
    except:
      logger.error('detevent.UpdatePosFile: Path not found')
      return
    pfile.write('ID:      %s\n' % self.ObjID)
    pfile.write('Cor. RA: %f\n' % (self.RaC/15.0,))
    pfile.write('Cor. Dec:%f\n' % self.DecC)
    pfile.write('SysT:    %d %d %6.3f\n' % (d.hour,d.minute,d.second+d.microsecond/1e6) )  #Old file used hundredths of a sec
    pfile.write('Sys_Date:%d %d %d\n' % (d.day,d.month,d.year) )
    pfile.write('Jul Day: %f\n' % t.JD)
    pfile.write('LST:     %f\n' % (t.LST*3600,))
    pfile.close()

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

  def Jump(self, FObj, Rate=None):
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

    if (self.Alt < prefs.AltCutoffFrom) or (FObj.Alt < AltCutoffTo):
      logger.error('detevent.Jump: Invalid jump, too low for safety! Aborted! AltF=%4.1f, AltT=%4.1f' % (self.Alt,FObj.Alt))
      return True
    else:
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

        motion.motors.Jump(DelRA,DelDEC,Rate)  #Calculate the profile and start the actual slew
        LastObj = copy.deepcopy(self)                    #Save the current position
        self.RaC, self.DecC = FObj.RaC, FObj.DecC     #Copy the coordinates to the current position record
        self.RaA, self.DecA = FObj.RaA, FObj.DecA
        self.Ra, self.Dec = FObj.Ra, FObj.Dec
        self.Epoch = FObj.Epoch
        self.TraRA = FObj.TraRA                          #Copy the non-sidereal trackrate to the current position record
        self.TraDEC = FObj.TraDEC                        #   Non-sidereal tracking will only start when the profiled jump finishes
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
      pdome.dome.ShutterOpen = info.ShutterOpen
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

    pdome.dome.NewDomeAzi = pdome.dome.CalcAzi(self)
    pdome.dome.DomeLastTime = time.time()

  def Reset(self, obj):
    """Set the current RA and DEC to those in the specified object (must be an instance of correct.CalcPosition)
    """
    obj.update()
    self.Ra, self.Dec, self.Epoch = obj.Ra, obj.Dec, obj.Epoch
    self.update()

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



def SaveStatus():
  """Save the current state as pickled data in a status file, so clients can access it.

     This function is called at regular intervals by the DetermineEvent loop.
  """
  #TODO - replace with RPC calls to share state data  
  f = open('/tmp/teljoy.status','w')
  cPickle.dump((current,motion.motors,pdome.dome,errors,prefs),f)
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
    current.UpdatePosFile()
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
  if ( (abs(pdome.dome.CalcAzi(current)-pdome.dome.NewDomeAzi) > 6) and
       ((time.time()-pdome.dome.DomeLastTime) > prefs.MinWaitBetweenDomeMoves) and
       (not pdome.dome.DomeInUse) and
       (not pdome.dome.ShutterInUse) and
       pdome.dome.DomeTracking and
       (not motion.motors.Moving) and
       pdome.dome.AutoDome and
       (not motion.motors.PosDirty) ):
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
    foo.ShutterInUse = pdome.dome.ShutterInUse
    foo.ShutterOpen = pdome.dome.ShutterOpen
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
        AltErr = current.Jump(JObj, prefs.SlewRate)  #Goto new position}
        logger.info("detevent.DoTJbox: Remote control jump to object: %s" % JObj)
        if pdome.dome.AutoDome and (not AltErr):
          pdome.dome.move(pdome.dome.CalcAzi(JObj))
        if AltErr:
          logger.error("detevent.DoTJBox: Object in TJbox below Alt Limit")
        else:
          TJboxAction = other.action
      else:
        TJboxAction = 'none'
        sqlint.ClearTJbox(db=db)

    elif other.action == 'jumprd':
      AltErr = current.Jump(BObj, prefs.SlewRate)
      logger.info("detevent.DoTJbox: Remote control jump to object: %s" % BObj)
      if pdome.dome.AutoDome and (not AltErr):
        pdome.dome.move(pdome.dome.CalcAzi(BObj))
      if AltErr:
        logger.error('detevent.DoTJbox: Object in TJbox below Alt Limit')
      else:
        TJboxAction = other.action

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
        pdome.dome.open()           #True for open}
        logger.info("detevent.DoTJbox: remote control - shutter opened")
      else:
        pdome.dome.close()
        logger.info("detevent.DoTJbox: remote control - shutter closed")
      TJboxAction = other.action

    elif (other.action == 'freez') or (other.action == 'freeze'):
      if other.Freeze:
        motion.motors.Frozen = True
        logger.info("detevent.DoTJbox: remote control - telescope frozen")
      else:
        motion.motors.Frozen = False
        logger.info("detevent.DoTJbox: remote control - telescope un-frozen")
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
  if TIMEOUT == 0:
    return
  if ((time.time()-ProspLastTime) > TIMEOUT) and pdome.dome.ShutterOpen and (not pdome.dome.ShutterInUse):
    logger.critical('detevent.CheckTimeout: No communication with Prosp for over %d seconds!\nClosing Shutter, Freezing Telescope.' % TIMEOUT)
    pdome.dome.close()
    motion.motors.Frozen = True




def init():
  global db, eventloop, detthread, paddles, current, LastObj
  logger.debug('Detevent unit init started')

  db = sqlint.InitSQL()    #Get a new db object and use it for this detevent thread
  if db is None:
    logger.warn('detevent.DetermineEvent: Detevent loop started, but with no SQL access.')

  current = CurrentPosition()
  LastObj = correct.CalcPosition()
  current.IniPos()

  eventloop = EventLoop()
  eventloop.register('UpdateCurrent', current.UpdatePosition)         #add all motion to 'current' object coordinates
  eventloop.register('RelRef', current.RelRef)                       #calculate refraction+flexure correction velocities, check for
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



current = None
LastObj = None
poslog = prefs.LogDirName + '/teljoy.pos'
ProspLastTime = time.time()
DBLastTime = 0
TJboxAction = 'none'
LastError = ""                  #Meant to contain the last reported error string - #TODO - implement in the logger handler.

