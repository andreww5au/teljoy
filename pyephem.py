"""Module to wrap some convenient features from the 'PyEphem' package.
   Subclasses TimeRec and CalcPosition from correct.py and duplicates a
   lot of the functionality - at some point, these classes could be merged, and
   the code in correct.py replaced with the calls to the ephem library.
"""

import copy

from globals import *
import correct
import ephem


def herenow():
    """Find and return an observer for the current location (as set in the .ini file) and the
       current time.
    """
    c = ephem.Observer()
    c.lat = prefs.ObsLat * ephem.pi / 180
    c.long = -prefs.ObsLong * ephem.pi / 180
    if prefs.RefractionOn:
        c.pressure = prefs.Press
        c.temp = prefs.Temp
    else:
        c.pressure = 0.0  # Set pressure to zero to disable PyEphem refraction
        c.temp = 20.0
    c.epoch = ephem.J2000
    return c


class EphemTime(correct.TimeRec):
    """Subclasses and could largely replace correct.TimeRec.
    """

    def __init__(self):
        self.observer = herenow()
        self.JDo = None  # Place to save JD calculated by old code in correct.py
        self.LSTo = None  # Place to save LST calculated by old code in correct.py
        correct.TimeRec.__init__(self)

    def update(self, now=True):
        """Update the time objects attributes to be correct for the current time (if now=True) or
           for the time set in self.observer.date otherwise.
        """
        if now:
            self.observer.date = ephem.now()
        self.UT = self.observer.date.datetime()
        self.CalcJulDay()  # set self.JD
        self.JDo = self.JD  # and move old hand-calculated JD to self.JDo
        self.JD = ephem.julian_date(self.observer)  # Use ephem to calculate self.JD
        self.CalcLST()
        self.LSTo = self.LST
        self.LST = self.observer.sidereal_time() * 12 / ephem.pi


class EphemPos(correct.CalcPosition):
    """A Position class where the astrometric calculations use Elwood P Downey's 'ephem' library
       (wrapped in python) instead of the astrometry routines in correct.py.

       Unlike correct.CalcPosition(), this class also handles ephemeris calculations for Solar
       System objects, or from orbital elements, as well as fixed bodies.
    """

    def __init__(self, obj=None, ra=None, dec=None, epoch=2000.0, domepos=None, objid=''):
        """Create a new instance. If passed any kind of Position object in the 'obj' attribute,
           extract its coordinates and use them to initialise the object, otherwise use the
           ra, dec, epoch, etc parameters.
        """
        Position.__init__(self, ra=ra, dec=dec, epoch=epoch, domepos=domepos, objid=objid)
        self.Time = EphemTime()
        self.observer = self.Time.observer
        if (isinstance(obj, ephem.Body) or
                isinstance(obj, ephem.Planet) or
                isinstance(obj, ephem.PlanetMoon) or
                isinstance(obj, ephem.EllipticalBody) or
                isinstance(obj, ephem.ParabolicBody) or
                isinstance(obj, ephem.HyperbolicBody) or
                isinstance(obj, ephem.EarthSatellite)):
            self.body = obj
            if self.body.name:
                self.ObjID = self.body.name
        else:
            self.body = ephem.FixedBody()
            self.body._ra = self.Ra * ephem.pi / (180 * 3600)
            self.body._dec = self.Dec * ephem.pi / (180 * 3600)
            self.body._epoch = (self.Epoch - 2000.0) * 365.246 + ephem.J2000
        self.body.compute(self.observer)
        self.update()

    def updatePM(self):
        """Sets TraRA and TraDEC: Non-sidereal track rates for moving objects, in arcsec/second
           (which is identical to steps/50ms)

           Use copies of body and observer objects, to avoid corrupting real ones. Will still work
           if self.observer has a time in the past or future.

           If TraRA or TraDEC is less than 0.0001 arcsec/sec, return exactly zero instead
        """
        b = self.body.copy()
        o = self.observer.copy()
        o.pressure = 0.0  # Don't include refraction in proper motion, we account for that elsewhere
        o.date -= 1.0 / 48  # Half an hour before the current date/time
        b.compute(o)
        ra1, dec1 = b.ra, b.dec
        o.date += 1.0 / 24  # Half an hour _after_ the current date/time
        b.compute(o)
        ra2, dec2 = b.ra, b.dec
        self.TraRA = (ra2 - ra1) * 180 / ephem.pi  # _radians_ to degrees, then degrees per _hour_ to _arcsec_ per _second_ (*3600/3600)
        if self.TraRA < 1e-4:
            self.TraRA = 0.0
        self.TraDEC = (dec2 - dec1) * 180 / ephem.pi
        if self.TraDEC < 1e-4:
            self.TraDEC = 0.0
        return self.TraRA, self.TraDEC

    def update(self, now=True):
        """Update the position objects attributes to be correct for the current time (if now=True) or
           for the time set in self.observer.date otherwise.
        """
        self.Time.update(now=now)
        self.body.compute(self.observer)
        self.Ra = self.body.a_ra * 180 * 3600 / ephem.pi  # radians to arcsec
        self.Dec = self.body.a_dec * 180 * 3600 / ephem.pi  # radians to arcsec
        try:
            self.Epoch = 2000.0 + (self.body.a_epoch - ephem.J2000) / 365.246
        except AttributeError:  # For some reason, ephem.PlanetMoon objects don't have an a_epoch attribute
            self.Epoch = 2000.0
        self.RaA = self.body.g_ra * 180 * 3600 / ephem.pi  # radians to arcsec
        self.DecA = self.body.g_dec * 180 * 3600 / ephem.pi  # radians to arcsec
        self.RaC = self.body.ra * 180 * 3600 / ephem.pi  # radians to arcsec
        self.DecC = self.body.dec * 180 * 3600 / ephem.pi  # radians to arcsec
        self.Alt = self.body.alt * 180 / ephem.pi  # radians to degrees
        self.Azi = self.body.az * 180 / ephem.pi  # radians to degrees
        if prefs.FlexureOn:
            dRA, dDEC = self.Flex()
            self.RaC += dRA
            self.DecC += dDEC
        if isinstance(self.body, ephem.FixedBody):  # If it's a fixed body, non-sidereal track rates must be zero
            self.TraRA = 0
            self.TraDEC = 0
        else:  # If this isn't a fixed body, update the proper motion parameters
            self.updatePM()
        self.posviolate = False  # False if RaC/DecC matches Ra/Dec/Epoch, True if moved since value calculated


def isdark():
    """Returns True if the Sun is more than 12 degrees below the horizon, False otherwise.
    """
    h = herenow()
    sun = ephem.Sun()
    sun.compute(h)
    if (float(sun.alt) * 180 / ephem.pi) > -12:
        return False
    else:
        return True


def getObject(name):
    """If name is in the set of predefined objects in PyEphem, return an EphemPos object for that name,
       otherwise return nothing.
    """
    byname = ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
              'ariel', 'callisto', 'deimos', 'dione', 'enceladus', 'europa', 'ganymede', 'hyperion', 'iapetus',
              'io', 'mimas', 'miranda', 'oberon', 'phobos', 'rhea', 'tethys', 'titan', 'titania', 'umbriel']
    if name.strip().lower() in byname:
        obj = ephem.__dict__[name.title()]()
        return EphemPos(obj)
