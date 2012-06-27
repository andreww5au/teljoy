
import math

from globals import *
import correct
import detevent
import motion


def Reset(ra=None, dec=None, epoch=2000.0, objid=''):
  """Set the current RA and DEC to the values given. 
     'ra' and 'dec' can be sexagesimal strings (in hours:minutes:seconds for RA and degrees:minutes:seconds
     for DEC), or numeric values (fractional hours for RA, fractional degrees for DEC). Epoch is in decimal 
     years, and objid is an optional short string with an ID.
  """
  n = correct.CalcPosition(ra=ra, dec=dec, epoch=epoch, objid=objid)
  detevent.Current.Ra, detevent.Current.Dec, detevent.Current.Epoch = n.Ra, n.Dec, n.Epoch
  detevent.Current.update()


def offset(ora, odec):
  """Make a tiny slew from the current position, by ora,odec arcseconds.
  """
  DelRA = 20*ora/math.cos(Current.DecC/3600*math.pi/180)  #conv to motor steps
  DelDEC = 20*odec
  motion.motors.setprof(DelRA,DelDEC,prefs.SlewRate)  #Calculate the motor profile and jump
  if (not detevent.Current.posviolate):
    detevent.Current.Ra +=ora/math.cos(detevent.Current.DecC/3600*math.pi/180)
    detevent.Current.Dec += odec
  detevent.Current.RaA += ora/math.cos(detevent.Current.DecC/3600*math.pi/180)
  detevent.Current.DecA += odec
  detevent.Current.RaC += ora/math.cos(detevent.Current.DecC/3600*math.pi/180)
  detevent.Current.DecC += odec



