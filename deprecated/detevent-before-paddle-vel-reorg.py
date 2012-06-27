
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
    cb = digio.ReadCoarse()
    fb = digio.ReadFine()

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
        motion.motors.start_motor('DEC', Paddle_max_vel)      #TODO - change start_motor and stop_motor to use 'ra' and 'dec' instead of 'true' and 'false'
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

  #$IFDEF NZ}
  #    if ((cb & CspaMsk)==CspaMsk) and ((cb & CspbMsk)==CspbMsk):
  #      CoarseMode = CSet
  #    else:
  #      if ((cb & CspbMsk)==CspbMsk):
  #         CoarseMode = CGuide
  #      else:
  #          CoarseMode = CSlew
  #$ELSE}
    if ((cb & digio.CSlewMsk)==digio.CSlewMsk):
      self.CoarseMode = 'CSlew'
    else:
      self.CoarseMode = 'CSet'
  #$ENDIF}


    #**Check the Coarse paddle by comparing cb to a set of masks}
    if ((cb & digio.CNorth)==digio.CNorth):
      if not self.ButtonPressedDEC:
        self.ButtonPressedDEC = True
        self.DECdir = 'CoarseNorth'
        if (self.CoarseMode == 'CSlew'):
          Paddle_max_vel = prefs.SlewRate
        else:
          if (self.CoarseMode == 'CSet'):
            Paddle_max_vel = prefs.CoarseSetRate
          else:
            Paddle_max_vel = prefs.GuideRate
        motion.motors.start_motor('DEC', Paddle_max_vel)
    elif self.ButtonPressedDEC and (self.DECdir=='CoarseNorth'):
      #Mask does not match but the motor is running}
      self.ButtonPressedDEC = False
      motion.motors.stop_motor('DEC')

    if ((cb & digio.CSouth)==digio.CSouth):
      if not self.ButtonPressedDEC:
        self.ButtonPressedDEC = True
        self.DECdir = 'CoarseSouth'
        if (self.CoarseMode == 'CSlew'):
          Paddle_max_vel = -prefs.SlewRate
        else:
          if (self.CoarseMode == 'CSet'):
            Paddle_max_vel = -prefs.CoarseSetRate
          else:
            Paddle_max_vel = -prefs.GuideRate
        motion.motors.start_motor('DEC', Paddle_max_vel)
    elif self.ButtonPressedDEC and (self.DECdir=='CoarseSouth'):
      #Mask does not match but the motor is running}
      self.ButtonPressedDEC = False
      motion.motors.stop_motor('DEC')

    if ((cb & digio.CEast)==digio.CEast):
      if (not self.ButtonPressedRA) and motion.limits.CanEast():
        self.ButtonPressedRA = True
        self.RAdir = 'CoarseEast'
        if (self.CoarseMode == 'CSlew'):
          Paddle_max_vel = prefs.SlewRate
        else:
          if (self.CoarseMode == 'CSet'):
            Paddle_max_vel = prefs.CoarseSetRate
          else:
            Paddle_max_vel = prefs.GuideRate
        motion.motors.start_motor('RA', Paddle_max_vel)
    elif self.ButtonPressedRA and (self.RAdir=='CoarseEast'):
      #Mask does not match but the motor is running}
      self.ButtonPressedRA = False
      motion.motors.stop_motor('RA')

    if ((cb & digio.CWest)==digio.CWest):
      if (not self.ButtonPressedRA) and motion.limits.CanWest():
        self.ButtonPressedRA = True
        self.RAdir = 'CoarseWest'
        if (self.CoarseMode == 'CSlew'):
          Paddle_max_vel = -prefs.SlewRate
        else:
          if (self.CoarseMode == 'CSet'):
            Paddle_max_vel = -prefs.CoarseSetRate
          else:
            Paddle_max_vel = -prefs.GuideRate
        motion.motors.start_motor('RA', Paddle_max_vel)
    elif self.ButtonPressedRA and (self.RAdir=='CoarseWest'):
      #Mask does not match but the motor is running}
      self.ButtonpressedRA = False
      motion.motors.stop_motor('RA')

    

def UpdatePosFile():
  t = TimeRec()   #Defaults to 'now'
  d = t.UT
  try:
    pfile = open(poslog,'w')
  except:
    logger.error('detevent.UpdatePosFile: Path not found')
    return
  pfile.write('ID:      %s' % Current.ObjID)
  pfile.write('Cor. RA: %f' % (Current.RaC/15.0,))
  pfile.write('Cor. Dec:%f' % Current.DecC)
  pfile.write('SysT:    %d %d %6.3f' % (d.hour,d.minute,d.second+d.microsecond/1e6) )  #Old file used hundredths of a sec
  pfile.write('Sys_Date:%d %d %d' % (d.day,d.month,d.year) )
  pfile.write('Jul Day: %f' % t.JD)
  pfile.write('LST:     %f' % (t.LST*3600,))
  pfile.close()


def UpdateCurrent():  
  """Update Current RA and Dec from paddle and refraction motion
  """
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
  """Original used position calls to write data in top few lines of screen, 
     this first draft simply dumps values to stdout
  """
  f = open('/tmp/teljoy.status','w')
  cPickle.dump((Current,motion.motors,pdome.status,errors,prefs),f)
  f.close()


def CheckDirtyPos():
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
  global DBLastTime
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
  """Read the tjbox database table and carry out any commanded actions
  
   DObj:ObjectRec
   other:TJboxrec
   RAOffset,DecOffset:double
   AltErr:boolean
  """
  global ProspLastTime, TJboxAction
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
        JObj = sqlint.GetRC3ByName(BObj.ObjID, 0, db=db)
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
  global TJboxAction
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
  if ((time.time()-ProspLastTime) > 600) and pdome.status.ShutterOpen and (not pdome.status.ShutterInUse):
    logger.critical('detevent.CheckTimeout: No communication with Prosp for over 10 minutes!\nClosing Shutter, Freezing Telescope.')
    pdome.DomeClose()
    motion.motors.Frozen = True


def RelRef():
  """Calculates a real time refraction correction for inclusion in INTPAS
     routine. 
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
    oldRAref,oldDECref = Current.Refrac()
  else:
    oldRAref = 0
    oldDECref = 0

  if prefs.FlexureOn:
    oldRAflex,oldDECflex = Current.Flex()
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


def Reset(ra=None, dec=None, epoch=2000.0, objid=''):
  """Set the current RA and DEC to the values given. 
     'ra' and 'dec' can be sexagesimal strings (in hours:minutes:seconds for RA and degrees:minutes:seconds
     for DEC), or numeric values (fractional hours for RA, fractional degrees for DEC). Epoch is in decimal 
     years, and objid is an optional short string with an ID.
  """
  n = correct.CalcPosition(ra=ra, dec=dec, epoch=epoch, objid=objid)
  Current.Ra, Current.Dec, Current.Epoch = n.Ra, n.Dec, n.Epoch
  Current.update()
  

def Jump(FObj, Rate=None):
  """Takes initial and final object records. Slews in RA by (FObj.RaC-Current.RaC), and
     slews in DEC by (FObj.DecC-Current.DecC). Returns 'True' if Alt of initial or final object
     is too low, 'False' if the slew proceeded OK.
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
    motion.motors.setprof(DelRA,DelDEC,Rate)  #Calculate the motor profile for the RA and DEC axis}

    LastObj = copy.deepcopy(Current)
    Current.RaC, Current.DecC = FObj.RaC, FObj.DecC
    Current.RaA, Current.DecA = FObj.RaA, FObj.DecA
    Current.Ra, Current.Dec = FObj.Ra, FObj.Dec
    Current.Epoch = FObj.Epoch
    Current.posviolate = False    #signal a valid original RA and Dec


def DetermineEvent():
  """The new version of determine event
  """
  db, gotSQL = sqlint.InitSQL()    #Get a new db object and use it for this detevent thread
  if gotSQL:
    while True:
      UpdateCurrent()      #add all motion to 'Current' object coordinates
      RelRef()         #calculate refrac velocity correction, check for
                          # altitude too low and set 'AltError' if true
      SaveStatus()     #Update status window at top of screen
      errors.update()  #Increment and check watchdog timer
      CheckDirtyPos()  #Check to see if dynamic position file needs updating
      CheckDirtyDome() #Check to see if dome needs moving if DomeTracking is on
      pdome.DomeCheckMove()  #Check to see if dome has reached destination azimuth
      motion.limits.check()    #Test to see if any hardware limits are active
      CheckDBUpdate(db=db)  #Update database at intervals
      CheckTJbox(db=db)     #Look for a TJbox entry for automatic control events
      CheckTimeout()   #Check to see if Prosp is still alive and monitoring weather
      paddles.check()

      time.sleep(0.1)
  else:
    logger.critical('detevent.DetermineEvent: Detevent loop aborting, no SQL access.')


def IniPos():    #set 'Current' position and other data to something reasonable on startup
  info, HA, LastMod = sqlint.ReadSQLCurrent(Current)

  pdome.status.ShutterOpen = info.ShutterOpen
  prefs.EastOfPier = info.EastOfPier
  motion.motors.Frozen = False    #Always start out not frozen}

  if LastMod == 0:
    errors.CalError = True
  else:
    errors.CalError = False

  Current.Time.update()
  rac = (Current.Time.LST+HA)*15*3600  #1800 arcsec fudge factor offset}
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


bg = None
def init():
  global bg
  bg = threading.Thread(target=DetermineEvent, name='detevent-thread')
  bg.daemon = True
  bg.start()
  logger.debug('detevent.init: Detevent thread started.')


paddles = PaddleStatus()


#begin  #Unit initialisation}
logger.debug('Detevent unit init started')

poslog = prefs.LogDirName + '/teljoy.pos'
ProspLastTime = time.time()
DBLastTime = 0
TJboxAction = 'none'
LastError = None
Current = correct.CalcPosition()
LastObj = correct.CalcPosition()
IniPos()
logger.debug('Detevent unit init finished')

