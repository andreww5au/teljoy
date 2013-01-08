
import math

from globals import *
import correct
import detevent
import motion

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


#TODO - add some arg processing here that allows the user to pass on object, an RA/dec string or
#       floats, an objid string, etc, for a human-oriented 'Jump' function. Ditto for 'Reset'.
#Actually, a single function that took an arbitrary arglist and returned an object would save
#a lot of code re-use.
def jump(ob):
  detevent.current.Jump(ob)
  if dome.AutoDome:
    dome.move(az=dome.CalcAzi(ob))


def reset(ra=None, dec=None, epoch=2000.0, objid=''):
  """Set the current RA and DEC to the values given. 
     'ra' and 'dec' can be sexagesimal strings (in hours:minutes:seconds for RA and degrees:minutes:seconds
     for DEC), or numeric values (fractional hours for RA, fractional degrees for DEC). Epoch is in decimal 
     years, and objid is an optional short string with an ID.
  """
  n = correct.CalcPosition(ra=ra, dec=dec, epoch=epoch, objid=objid)
  detevent.current.Reset(obj=n)


def offset(ora, odec):
  """Make a tiny slew from the current position, by ora,odec arcseconds.
  """
  detevent.current.Offset(ora=ora, odec=odec)



