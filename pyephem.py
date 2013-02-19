"""Module to wrap some convenient features from the 'PyEphem' package.

"""

from globals import *
import correct
import ephem


def herenow():
  c = ephem.Observer()
  c.lat = prefs.ObsLat
  c.long = prefs.ObsLong
  c.pressure = 1013.0
  c.temp = 20.0
  c.epoch = ephem.J2000
  return c


class EphemTime(correct.TimeRec):
  def __init__(self):
    self.observer = herenow()
    self.update()

  def update(self, now=True):
    if now:
      self.observer.date = ephem.now()
    self.UT = self.observer.date.datetime()
    self.CalcJulDay()        #set self.JD
    self.JDo = self.JD       #and move old hand-calculated JD to self.JDo
    self.JD = ephem.julian_date(self.observer)    #Use ephem to calculate self.JD
    self.CalcLST()
    self.LSTo = self.LST
    self.LST = self.observer.sidereal_time() * 12 / ephem.pi


class EphemPos(correct.CalcPosition):
  def __init__(self, obj=None, ra=None, dec=None, epoch=2000.0, domepos=None, objid=''):
    if isinstance(obj,ephem.Body):
      self.body = obj
      if self.body.name:
        objid = self.body.name
    #TODO - all the rest of the setup
    self.Time = EphemTime()
    self.observer = self.Time.observer

  def update(self, now=True):
    self.Time.update(now=now)
    self.body.compute(self.observer)
    self.Ra = self.body.a_ra*180/(15*ephem.pi)       #radians to hours
    self.Dec = self.body.a_dec*180/ephem.pi          #radians to degrees
    self.Epoch = 2000.0 + (self.body.a_epoch-ephem.J2000)/365.246
    self.RaA = self.body.g_ra*180/(15*ephem.pi)       #radians to hours
    self.DecA = self.body.g_dec*180/ephem.pi          #radians to degrees
    self.RaC = self.body.ra*180/(15*ephem.pi)       #radians to hours
    self.DecC = self.body.dec*180/ephem.pi          #radians to degrees
    self.Alt = float(self.body.alt)
    self.Azi = float(self.body.azi)
    self.TraRA,self.TraDEC = (0.0,0.0)         #Non-sidereal track rate for moving objects, in arcsec/second (which is identical to steps/50ms)
    self.posviolate = False               #False if RaC/DecC matches Ra/Dec/Epoch, True if moved since value calculated
