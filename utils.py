"""Utility functions, all intended to be called manually by users at the Teljoy command line.
   Also defines built in position constants like 'STOW', again to be used at the command line.
"""


import sys
import time
import urllib2

from globals import *
if SITE == 'PERTH':
  from pdome import dome
elif SITE == 'NZ':
  from nzdome import dome
import correct
import detevent
import motion
import sqlint
import pyephem

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
  """Given a string, look up that name in teljoy.objects, and
     anywhere else that seems reasonable. Return a position object for that name,
     or None if it can't be found. Try both the name as given, and if that fails,
     the name converted to all upper case.

     This function is intended to be called manually, by the user at the command line.
  """
  obj = sqlint.GetObject(name=objid)

  if SITE == 'PERTH':   # Old Perth Observatory supernova search galaxy catalogues
    if obj is None:
      obj = sqlint.GetRC3(gid=objid)
    if obj is None:
      obj = sqlint.GetRC3(gid=objid.upper())

  if obj is None:
    obj = pyephem.getObject(name=objid)
#  if obj is None:
#    obj = GetSesame(name=objid)
  return obj


def GetSesame(name=''):
  """Given an object name, use the Sesame web service to look up the object in
     SIMBAD, Vizier, and NED. Returns a position object.

     This function is intended to be called manually, by the user at the command line.
  """
  try:
    data = urllib2.urlopen('http://cdsweb.u-strasbg.fr/cgi-bin/nph-sesame/A?%s' % urllib2.quote(name)).read()
  except IOError:
    logger.error('IO error contacting Sesame web service')
    return None
  poslist = []
  source = '?'
  for l in data.split('\n'):
    if l.startswith('#='):
      try:
        source = l.split('=')[2].split(':')[0]
      except IndexError:
        source = '<' + l + '>'
    if l.startswith('%J '):
      try:
        ra = float(l.split()[1])
        dec = float(l.split()[2])
        poslist.append((source, ra, dec))
      except (IndexError,ValueError):
        pass  # Bad coordinates, ignore this line

  if poslist:
    print "Found positions:"
    for p in poslist:
      print "RA=%s, DEC=%s, Source=%s" % (sexstring(p[1]), sexstring(p[2]), p[0])
    print "Using position from '%s'" % poslist[0][0]
    return correct.CalcPosition(ra=poslist[0][1]/15.0, dec=poslist[0][2], epoch=2000.0, objid=name)
  else:
    return None


def ParseArgs(args, kws, pclass=correct.CalcPosition):
  """Take abitrary arguments stored in 'args' and 'kws' that hopefully specify coordinates, an object
     name to be looked up, or a position object, and return a position object representing that position.

     Normally that would be an instance of the correct.CalcPosition class, but you can pass an alternate
     base class in using the 'pclass' attribute.
  """
  ra, dec, epoch, objid, domepos, obj = None, None, None, None, None, None
  for n in ['ra', 'RA', 'Ra']:
    if n in kws.keys():
      ra = kws[n]
      break
  for n in ['dec', 'Dec', 'DEC']:
    if n in kws.keys():
      dec = kws[n]
      break
  for n in ['epoch', 'Epoch', 'EPOCH', 'ep', 'Ep', 'equinox', 'Equinox', 'eq', 'Eq']:
    if n in kws.keys():
      epoch = kws[n]
  for n in ['objid', 'Objid', 'ObjId', 'ObjID', 'objId', 'objID', 'id', 'Id', 'ID', 'name', 'Name']:
    if n in kws.keys():
      objid = kws[n]
  for n in ['domepos', 'Domepos', 'DomePos', 'domePos', 'DOMEPOS']:
    if n in kws.keys():
      domepos = kws[n]
  for n in ['o', 'O', 'obj', 'Obj', 'OBJ', 'pos', 'Pos', 'POS', 'position', 'Position']:
    if n in kws.keys():
      if isinstance(kws[n], correct.CalcPosition):
        obj = kws[n]
        break
  for o in args:
    if isinstance(o, correct.CalcPosition):
      obj = o
      break

  if obj is not None:
    if isinstance(obj, pclass):
      return obj
    else:
      return pclass(obj=obj, ra=ra, dec=dec, epoch=epoch, objid=objid, domepos=domepos)

  if (ra is not None) and (dec is not None):
    if epoch is None:
      epoch = 2000.0
    return pclass(ra=ra, dec=dec, epoch=epoch, objid=objid, domepos=domepos)

  if len(args) == 0:
    if type(objid) in [str, unicode]:
      return Lookup(objid=str(objid))
    else:
      return None
  elif len(args) == 1:
    if type(args[0]) in [str, unicode]:
      return Lookup(objid=str(args[0]))
    else:
      return None
  elif len(args) == 2:
    if epoch is None:
      epoch = 2000.0
    return pclass(ra=args[0], dec=args[1], epoch=epoch, objid=objid, domepos=domepos)
  elif len(args) == 3:
    try:
      epoch = float(args[2])
    except:
      epoch = 2000
    return pclass(ra=args[0], dec=args[1], epoch=epoch, objid=objid, domepos=domepos)

  return None


#Define a few convenience functions to take flexible arguments and return a position object.
def Pos(*args, **kws):
  return ParseArgs(args=args, kws=kws)


pos = Pos
position = Pos
p = Pos


def jump(*args, **kws):
  """Jump the telescope to a new object, specified by an obect name string, or ra=, dec= and epoch= arguments,
     where ra and dec can be strings (containing H:M:S or D:M:S values) or numbers.


       This function is intended to be called manually, by the user at the command line.
  """
  if 'force' in kws.keys():
    force = kws['force']
  else:
    force = None
  ob = Pos(*args, **kws)
  if ob is None:
    print "Can't parse those arguments to get a valid position"
    return
  if not safety.Active.is_set():
    if not force:
      logger.error("safety interlock, can't jump the telescope")
      return
    else:
      logger.info("safety interlock FORCED, jumping telescope")
  print "Jumping to:", ob
  detevent.current.Jump(ob, force=force)
  if dome.AutoDome:
    print "Moving dome."
    dome.move(az=dome.CalcAzi(ob))


Jump = jump


def reset(*args, **kws):
  """Set the current RA and DEC to the values given. 
     'ra' and 'dec' can be sexagesimal strings (in hours:minutes:seconds for RA and degrees:minutes:seconds
     for DEC), or numeric values (fractional hours for RA, fractional degrees for DEC). Epoch is in decimal 
     years, and objid is an optional short string with an ID.

     This function is intended to be called manually, by the user at the command line.

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

       This function is intended to be called manually, by the user at the command line.
  """
  oldRA, oldDEC = sexstring(detevent.current.Ra / 15 / 3600, sp=' '), sexstring(detevent.current.Dec / 3600, sp=' ')
  if detevent.current.Dec > 0:
    oldDEC = '+' + oldDEC
  detevent.current.Offset(ora=ora, odec=odec)
  logger.info("Moved small offset distance: %4.1f,%4.1f" % (ora, odec))
  time.sleep(0.5)
  newRA, newDEC = sexstring(detevent.current.Ra / 15 / 3600, sp=' '), sexstring(detevent.current.Dec / 3600, sp=' ')
  if detevent.current.Dec > 0:
    newDEC = '+' + newDEC
  lst = sexstring(detevent.current.Time.LST, sp=' ')[:5]
  print "TPoint input data: oldRA, oldDEC, newRA, newDEC, LST"
  print "%s   %s   %s   %s   %s" % (oldRA, oldDEC, newRA, newDEC, lst)


Offset = offset


def freeze(force=False):
  """Freeze the telescope. Stops all sidereal and non-sidereal tracking, but maintain position accuracy.

       This function is intended to be called manually, by the user at the command line.
  """
  motion.motors.Frozen = True
  logger.info("Telescope frozen")


def unfreeze(force=False):
  """Un-Freeze the telescope. Resume tracking.

       This function is intended to be called manually, by the user at the command line.
  """
  if not safety.Active.is_set():
    if not force:
      logger.error("safety interlock, can't unfreeze the telescope")
      return
    else:
      logger.info("safety interlock FORCED, unfreezing telescope")
  motion.motors.Frozen = False
  logger.info("Telescope un-frozen")


if SITE == 'NZ':
  def domecal():
    """Call this function when the dome is pointing due North. It will calculate a
       current value for the dome encoder offset, and set the current encoder offset
       in the dome object.

         This function is intended to be called manually, by the user at the command line.
    """
    print "Assuming dome is due north!"
    azi = dome.getDomeAzi()
    enc = int(azi*256.0/360.0)
    enc -= dome.EncoderOffset
    if enc < 0:
      enc += 256
    if enc > 255:
      enc -= 256
    print "Raw dome encoder value = %d" % enc
    newoff = -enc
    if newoff > 128:
      newoff -= 256
    if newoff < -128:
      newoff += 256
    print "Setting dome encoder offset to %d" % newoff
    dome.EncoderOffset = newoff


def shutdown():
  """Go through a telescope and dome shutdown - move the telescope to the cap replacement
     position and rotate the dome to the park position.

     Then wait for a keypress indicating that the cap is on, and move the telescope to the
     STOW position, while closing the chutter.

       This function is intended to be called manually, by the user at the command line.
  """
  print "About to shut down the system and close+park the dome - are you sure?"
  ans = raw_input()
  if 'Y' not in ans.upper():
    print "Aborting."
    return
  if not dome.AutoDome:
    print "Dome not in automatic mode - can't park dome or close shutter"
  if SITE == 'PERTH':
    jump(CAP, force=True)
    print "Press 'ENTER' when cap is on, to stow the telescope at zenith"
    ans = raw_input()
    if dome.AutoDome:
      while dome.DomeInUse:
        print "Waiting for dome to finish moving..."
        time.sleep(2)
      print "Closing dome."
      dome.close(force=True)
  jump(STOW, force=True)
  time.sleep(2)
  while motion.motors.Moving or dome.DomeInUse:
    print "Waiting for telescope to park and dome to finish moving."
    time.sleep(5)
  sys.exit()


Shutdown = shutdown
ShutDown = shutdown
