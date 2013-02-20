"""Module to wrap some convenient features from the 'PyEphem' package.

"""

import copy

from globals import *
import correct
import ephem


def herenow():
  c = ephem.Observer()
  c.lat = prefs.ObsLat*ephem.pi/180
  c.long = -prefs.ObsLong*ephem.pi/180
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
    Position.__init__(self, ra=ra, dec=dec, epoch=epoch, domepos=domepos, objid=objid)
    self.Time = EphemTime()
    self.observer = self.Time.observer
    if isinstance(obj,ephem.Body):
      self.body = obj
      if self.body.name:
        self.ObjID = self.body.name
    else:
      self.body = ephem.FixedBody()
      self.body._ra = self.Ra*ephem.pi/(180*3600)
      self.body._dec = self.Dec*ephem.pi/(180*3600)
      self.body._epoch = (self.Epoch-2000.0)*365.246 + ephem.J2000
    self.body.compute(self.observer)
    self.update()

  def updatePM(self):
    """Sets TraRA and TraDEC: Non-sidereal track rates for moving objects, in arcsec/second
       (which is identical to steps/50ms)

       Use copies of body and observer objects, to avoid corrupting real ones. Will still work
       if self.observ
    """
    b = copy(self.body)
    o = copy(self.observer)
    o.pressure = 0.0     #Don't include refraction in proper motion, we account for that elsewhere
    o.date -= 1.0/48   #Half an hour before the current date/time
    b.compute(o)
    ra1,dec1 = b.ra,b.dec
    o.date += 1.0/24    #Half an hour _after_ the current date/time
    b.compute(o)
    ra2,dec2 = b.ra,b.dec
    self.TraRA = (ra2-ra1)*3600*180*3600/ephem.pi     #_radians_ per _hour_ to _arcsec_ per _second_ = *3600*180*3600
    self.TraDEC = (dec2-dec1)*3600*180*3600/ephem.pi
    return self.TraRA, self.TraDEC

  def update(self, now=True):
    self.Time.update(now=now)
    self.body.compute(self.observer)
    self.Ra = self.body.a_ra*180*3600/ephem.pi      #radians to arcsec
    self.Dec = self.body.a_dec*180*3600/ephem.pi    #radians to arcsec
    self.Epoch = 2000.0 + (self.body.a_epoch-ephem.J2000)/365.246
    self.RaA = self.body.g_ra*180*3600/ephem.pi     #radians to arcsec
    self.DecA = self.body.g_dec*180*3600/ephem.pi   #radians to arcsec
    self.RaC = self.body.ra*180*3600/ephem.pi       #radians to arcsec
    self.DecC = self.body.dec*180*3600/ephem.pi     #radians to arcsec
    self.Alt = self.body.alt*180/ephem.pi           #radians to degrees
    self.Azi = self.body.azi*180/ephem.pi           #radians to degrees
    self.updatePM()
    self.posviolate = False               #False if RaC/DecC matches Ra/Dec/Epoch, True if moved since value calculated

