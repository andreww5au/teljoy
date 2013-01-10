
import sys
import time

from globals import *
from pdome import dome
import correct
import detevent
import motion
import sqlint

STOW = correct.HADecPosition(ha=prefs.StowHourAngle,
                             dec=prefs.StowDec,
                             domepos=prefs.StowDomeAzi,
                             objid='Stowed')
CAP = correct.HADecPosition(ha=prefs.CapHourAngle,
                            dec=prefs.CapDec,
                            domepos=prefs.StowDomeAzi,
                            objid='Cap')
DOMEFLAT = correct.HADecPosition(ha=prefs.DomeFlatHourAngle,
                                 dec=prefs.DomeFlatDec,
                                 domepos=prefs.DomeFlatDomeAzi,
                                 objid='DomeFlat')
SKYFLAT = correct.HADecPosition(ha=prefs.SkyFlatHourAngle,
                                dec=prefs.SkyFlatDec,
                                domepos=None,
                                objid='SkyFlat')


def Lookup(objid=''):
  """Given a string, look up that name in teljoy.objects, the RC3 catalog, and
     anywhere else that seems reasonable. Return a position object for that name,
     or None if it can't be found. Try both the name as given, and if that fails,
     the name converted to all upper case.

     Normally that would be an instance of the correct.CalcPosition class, but you can pass an alternate
     base class in using the 'pclass' attribute. This alternate class is NOT USED if the ID is used to look
     up an object in the database, either in teljoy.objects (when a correct.CalcPosition is returned) or in
     the RC3 catalog (when an sqlint.Galaxy object is returned).
  """
  obj = sqlint.GetObject(name=objid)
  if obj is None:
    obj = sqlint.GetObject(name=objid.upper())
  if obj is None:
    obj = sqlint.GetRC3(gid=objid)
  if obj is None:
    obj = sqlint.GetRC3(gid=objid.upper())
  return obj


def ParseArgs(args, kws, pclass=correct.CalcPosition):
  """Take abitrary arguments stored in 'args' and 'kws' that hopefully specify coordinates, an object
     name to be looked up, or a position object, and return a position object representing that position.

     Normally that would be an instance of the correct.CalcPosition class, but you can pass an alternate
     base class in using the 'pclass' attribute.
  """
  ra,dec,epoch,objid,domepos,obj = None,None,None,None,None,None
  for n in ['ra','RA','Ra']:
    if n in kws.keys():
      ra = kws[n]
      break
  for n in ['dec','Dec','DEC']:
    if n in kws.keys():
      dec = kws[n]
      break
  for n in ['epoch','Epoch','EPOCH','ep','Ep','equinox','Equinox','eq','Eq']:
    if n in kws.keys():
      epoch = kws[n]
  for n in ['objid','Objid','ObjId','ObjID','objId','objID','id','Id','ID']:
    if n in kws.keys():
      objid = kws[n]
  for n in ['domepos','Domepos','DomePos','domePos','DOMEPOS']:
    if n in kws.keys():
      domepos = kws[n]
  for n in ['o','O','obj','Obj','OBJ','pos','Pos','POS','position','Position']:
    if n in kws.keys():
      if isinstance(kws[n], correct.CalcPosition):
        obj = kws[n]
        break
  for o in args:
    if isinstance(o, correct.CalcPosition):
      obj = o
      break

  if obj is not None:
    return pclass(obj=obj, ra=ra, dec=dec, epoch=epoch, objid=objid, domepos=domepos)

  if (ra is not None) and (dec is not None):
    if epoch is None:
      epoch = 2000.0
    return pclass(ra=ra, dec=dec, epoch=epoch, objid=objid, domepos=domepos)

  if len(args) == 0:
    if type(objid) == str:
      return Lookup(objid=objid)
    else:
      return None
  elif len(args) == 1:
    if type(args[0]) == str:
      return Lookup(objid=args[0])
    else:
      return None
  elif len(args) == 2:
    if epoch is None:
      epoch = 2000.0
    return pclass(ra=args[0], dec=args[1], epoch=epoch, objid=objid, domepos=domepos)
  elif len(args) == 3:
    return pclass(ra=args[0], dec=args[1], epoch=args[2], objid=objid, domepos=domepos)

  return None


#Define a few convenience functions to take flexible arguments and return a position object.
def Pos(*args, **kws):
  return ParseArgs(args=args, kws=kws)
pos = Pos
position = Pos
p = Pos


def jump(*args, **kws):
  ob = Pos(*args, **kws)
  if ob is None:
    print "Can't parse those arguments to get a valid position"
    return
  print "Jumping to:", ob
  detevent.current.Jump(ob)
  if dome.AutoDome:
    print "Moving dome."
    dome.move(az=dome.CalcAzi(ob))

Jump = jump


def reset(*args, **kws):
  """Set the current RA and DEC to the values given. 
     'ra' and 'dec' can be sexagesimal strings (in hours:minutes:seconds for RA and degrees:minutes:seconds
     for DEC), or numeric values (fractional hours for RA, fractional degrees for DEC). Epoch is in decimal 
     years, and objid is an optional short string with an ID.
  """
  ob = Pos(*args, **kws)
  if ob is None:
    print "Can't parse those arguments to get a valid position"
    return
  print "Resetting current position to:", ob
  detevent.current.Reset(obj=ob)

Reset = reset


def offset(ora, odec):
  """Make a tiny slew from the current position, by ora,odec arcseconds.
  """
  detevent.current.Offset(ora=ora, odec=odec)
  logger.info("Moved small offset distance: %4.1f,%4.1f" % ora,odec)

Offset = offset


def freeze():
  """Freeze the telescope
  """
  motion.motors.Frozen = True
  logger.info("Telescope frozen")


def unfreeze():
  """Un-Freeze the telescope
  """
  motion.motors.Frozen = False
  logger.info("Telescope un-frozen")


def shutdown():
  """Go through a telescope and dome shutdown - move the telescope to the cap replacement
     position and rotate the dome to the park position.

     Then wait for a keypress indicating that the cap is on, and move the telescope to the
     STOW position, while closing the chutter.
  """
  print "About to shut down the system and close+park the dome - are you sure?"
  ans = raw_input()
  if 'y' not in ans.upper():
    print "Aborting."
    return
  if not dome.AutoDome:
    print "Dome not in automatic mode - can't park dome or close shutter"
  jump(CAP)
  print "Press 'ENTER' when cap is on, to stow the telescope at zenith"
  ans = raw_input()
  if dome.AutoDome:
    while dome.DomeInUse:
      print "Waiting for dome to finish moving..."
      time.sleep(2)
    print "Closing dome."
    dome.close()
  jump(STOW)
  sys.exit()

Shutdown = shutdown
ShutDown = shutdown