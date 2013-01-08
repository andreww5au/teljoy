
import math

from globals import *
import correct
import detevent
import motion

STOW = correct.HADecPosition(ha=float(prefs.StowHourAngle),
                             dec=float(prefs.StowDec),
                             domepos=float(prefs.StowDomeAzi),
                             objid='Stowed')
CAP = correct.HADecPosition(ha=float(prefs.CapHourAngle),
                            dec=float(prefs.CapDec),
                            domepos=float(prefs.StowDomeAzi),
                            objid='Cap')
DOMEFLAT = correct.HADecPosition(ha=float(prefs.DomeFlatHourAngle),
                                 dec=float(prefs.DomeFlatDec),
                                 domepos=float(prefs.DomeFlatDomeAzi),
                                 objid='DomeFlat')
SKYFLAT = correct.HADecPosition(ha=float(prefs.SkyFlatHourAngle),
                                dec=float(prefs.SkyFlatDec),
                                domepos=None,
                                objid='SkyFlat')


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



