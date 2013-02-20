
"""This module defines the TimeRec and CalcPosition classes, containing attributes and
   methods for astrometric corrections (JD, LST, precession, nutation, refraction, etc).
"""

import time
import datetime
from math import sin,cos,tan,asin,acos,atan2,pi,sqrt,trunc,floor,modf

from globals import *

# Refraction correction constants:
N = 1.000297       #Index of refraction for air - apparently not actually used
R1 = 58.294
R2 = -0.0668



class TimeRec(object):
  """Class to store a date and time, in standard Python format (a datetime.datetime object,
     in the UTC timezone), a decimal Julian Day number, and the Local Sidereal Time associated
     with that JD and datetime for the current position (defined in the .ini file).
  """
  def __init__(self):
    """Create initial instance with the current date and time.
    """
    self.UT = datetime.datetime.utcnow()    #Current date and time, in UTC
    self.JD = 0.0                           #Fractional Julian Day
    self.LST = 0.0                          #Local Sidereal Time, in hours
    self.update()                        #Calculate JD and LST values

  def __getstate__(self):
    """Can't pickle the __setattr__ function when saving state
    """
    d = {}
    for n in ['UT','JD','LST']:
      d[n] = self.__dict__[n]
    return d

  def __repr__(self):
    return "<TimeRec: UT='%s', JD=%f, LST=%s >" % (self.UT.ctime(), self.JD, sexstring(self.LST))
    
  def __str__(self):
    return "[UT:%s LST:%s]" % (self.UT.time().isoformat()[:-7], sexstring(self.LST,fixed=True))

  def CalcJulDay(self):
    """Calculate full Julian Day for the time in self.UT
    """
    year, month = self.UT.year, self.UT.month
    if (month == 1) or (month == 2):
      year -= 1
      month += 12
    A = floor(year/100.0)
    B = 2 - A + floor(A/4.0)
    jd = floor(365.25 * year) + floor(30.6001 * (month + 1))
    jd = jd + self.UT.day + (self.UT.hour + (self.UT.minute/60.0) + (self.UT.second/3600.0) + self.UT.microsecond/3.6e9) / 24.0
    jd = jd + 1720994 + B + 0.5
    self.JD = jd

  def CalcLST(self):
    """Calculate the Local Sidereal Time from the objects .JD and .UT values.
    """
    if not self.JD:      #If JD hasn't been calculated yet, do it now
      self.CalcJulDay()
    T = ((int(self.JD-0.5)+0.5)-2415020)/36525        #Remove fractional day part of JD and convert to centuries since 1900.0
    LST = (modf(0.276919398+(100.0021359*T)+(0.000001075*T*T))[0])*24
    LST += MSOLDY*(self.UT.hour + self.UT.minute/60.0 + self.UT.second/3600.0 + self.UT.microsecond/3.6e9)

    L = 279.69668 + 36000.76892*T + 0.0003025*T*T     #Sun's mean longtitude
    Ld = 270.4342 + 481267.8831*T - 0.001133*T*T      #Moon's mean longtitude
    M = 358.47583 + 35999.04975*T - 0.000150*T*T - 0.0000033*T*T*T    #Sun's mean anomaly
    Md = 296.1046 + 477198.8491*T + 0.009192*T*T      #Moon's mean anomaly
    Omega = 259.1833 - 1934.1420*T + 0.002078*T*T     #Longtitude of Moon's ascending node
    L = DegToRad(Reduce(L))                  #Reduce to range 0-360, convert to radians
    Ld = DegToRad(Reduce(Ld))                #Reduce to range 0-360, convert to radians
    M = DegToRad(Reduce(M))                  #Reduce to range 0-360, convert to radians
    Md = DegToRad(Reduce(Md))                #Reduce to range 0-360, convert to radians
    Omega = DegToRad(Reduce(Omega))          #Likewise..
    dphi = ( -(17.2327+0.01737*T)*sin(Omega) - (1.2729+0.00013*T)*sin(2*L)
             + 0.2088*sin(2*Omega) - 0.2037*sin(2*Ld)
             + (0.1261-0.00031*T)*sin(M) + 0.0675*sin(Md)
             - (0.0497-0.00012*T)*sin(2*L+M) - 0.0342*sin(2*Ld-Omega)
             - 0.0261*sin(2*Ld+Md) + 0.0214*sin(2*L-M)
             - 0.0149*sin(2*L-2*Ld+Md) + 0.0124*sin(2*L-Omega)
             + 0.0114*sin(2*Ld-Md) )
    Epsi = 23.452294-0.0130125*T - 0.00000164*T*T + 0.000000503*T*T*T
    LST += (dphi*cos(DegToRad(Epsi)))/(15*3600)

    LST -= prefs.ObsLong/15.0    #Convert Sidereal Time at 0 longitude to real, local S.T.
    while LST > 24.0:
      LST -= 24
    while LST < 0:
      LST += 24
    self.LST = LST
     
  def update(self, now=True):
    """Update the time record. If now is True, get the current time, 
       otherwise update JD and LST fields for the value in self.UT
    """
    if now:
      self.UT = datetime.datetime.utcnow()
    self.CalcJulDay()
    self.CalcLST()



class CalcPosition(Position):        #Position class defined in globals.py
  """Subclass globals.Position to add astrometric calculation methods.
     Extra coordinate attributes (RaA, RaC, DecA, DecC) are all in arcseconds.
  """
  def __init__(self, obj=None, ra=None, dec=None, epoch=2000.0, domepos=None, objid=''):
    self.RaA,self.DecA = (0.0,0.0)        #Apparent sky position (not including refraction or flexure)
    self.RaC,self.DecC = (0.0,0.0)        #Fully Corrected Ra and Dec
    self.Alt,self.Azi = (0.0,0.0)         #Apparent Altitude and Azimuth
    self.TraRA,self.TraDEC = (0.0,0.0)         #Non-sidereal track rate for moving objects, in arcsec/second (which is identical to steps/50ms)
    self.posviolate = False               #False if RaC/DecC matches Ra/Dec/Epoch, True if moved since value calculated
    self.Time = TimeRec()                 #Time to use for the coordinate transforms
    if isinstance(obj,Position):
      if ra is None:
        ra = obj.Ra/15.0/3600
      if dec is None:
        dec = obj.Dec/3600.0
      if epoch is None:
        epoch = obj.Epoch
      if objid is None:
        objid = obj.ObjID
    Position.__init__(self, ra=ra, dec=dec, epoch=epoch, domepos=domepos, objid=objid)
    if (ra is not None) and (dec is not None):
      self.update()

  def __getstate__(self):
    """Can't pickle the __setattr__ function when saving state
    """
    d = {}
    for n in ['Ra','Dec','Epoch','RaA','DecA','RaC','DecC','Alt','Azi','ObjID','TraRA','TraDEC','posviolate','DomePos']:
      d[n] = self.__dict__[n]
    d['TimeDict'] = self.Time.__getstate__()
    return d

  def __repr__(self):
    if self.posviolate:
      s  = "<Position %s: Org=(INVALID , INVALID , INVALID),\n" % self.ObjID
    else:
      s  = "<Position %s: Org=(%s, %s, %6.1f),\n" % (self.ObjID, sexstring(self.Ra/15.0/3600,dp=3), sexstring(self.Dec/3600,dp=2), self.Epoch)
    s += "            App=(%s, %s),\n"  % (sexstring(self.RaA/15.0/3600,dp=3), sexstring(self.DecA/3600,dp=2) )
    s += "            Cor=(%s, %s),\n" % (sexstring(self.RaC/15.0/3600,dp=3), sexstring(self.DecC/3600,dp=2) )
    s += "            HA=%5.2f, Alt=%5.2f, Azi=%5.2f\n" % (self.RaC/54000-self.Time.LST, self.Alt, self.Azi)
    s += "      Time: %s >" % self.Time
    return s
    
  def __str__(self):
    if self.posviolate:
      return "{%s}: Time=%s, Pos=[INVALID,INVALID -> (%s,%s)]" % (self.ObjID,str(self.Time),
                                                                  sexstring(self.RaC/15.0/3600,dp=1),
                                                                  sexstring(self.DecC/3600,dp=0))
    else:
      return "{%s}: Time=%s, Pos=[%s,%s -> (%s,%s)]" % (self.ObjID,str(self.Time),
                                                  sexstring(self.Ra/15.0/3600,dp=1),
                                                  sexstring(self.Dec/3600,dp=0),
                                                  sexstring(self.RaC/15.0/3600,dp=1),
                                                  sexstring(self.DecC/3600,dp=0) )

  def AltAziConv(self):     #Originally in CORRECT.PAS
    """Calculate Altitude and Azimuth from .RaA, .DecA, and .Time.LST
    
       This method must be called after .RaA and .DecA have been calculated.
       
       #Taken from Astronomical Formulae for Calculators, Jean Meeus,
       #    3rd Ed. 1985.  P:43-48.
    """
    ObjRa = self.RaA/54000.0
    ObjDec = self.DecA/3600.0
    if ObjDec < -90:
      ObjDec = -89.9999999
    alt1 = sin(DegToRad(prefs.ObsLat))
    alt1 *= sin(DegToRad(ObjDec))
    co = cos(DegToRad(prefs.ObsLat))
    cd = cos(DegToRad(ObjDec))
    H = DegToRad((self.Time.LST-ObjRa)*15.0)
    ct = cos(H)
    alt2 = co*cd*ct
    self.Alt = RadToDeg(asin(alt1+alt2))
    self.Azi = RadToDeg(atan2(sin(H),(cos(H)*sin(DegToRad(prefs.ObsLat))-tan(DegToRad(ObjDec))*co)))
    self.Azi += 180.0    #stupid algorithm counts azi from south!}
    self.Azi = Reduce(self.Azi)

  def Precess(self):     #Originally in CORRECT.PAS
    """Correct for precession of coordinate reference frame from the equinox of the 
       original coordinates (.Ra, .Dec, and .Epoch) to the current date.
       
       Note that since the correction is for the reference frame itself, there's no 
       reason the destination epoch needs to be the current date - we just need the
       'current' and destination coordinates for any jumps to be in the same reference
       frame (equinox). 
       
       It might be more sensible to keep the 'current' coordinates (detevent.current)
       in J2000 equinox, and convert all targets to that equinox.

       Note that for historical reasons, the equinox for the coordinates is stored in the 'Epoch'
       attribute. Strictly speaking, 'Epoch' refers to the time an observation or measurement
       was made, and NOT the coordinate reference frame used.

       This method sets the RaA and DecA attributes to the precessed coordinates.
       
            #This is taken from Astronomical Formulae for Calculators, Jean Meeus,
            #    3rd Ed. 1985.  P:65-67.
    """
    if (self.Epoch is None) or (self.Epoch == 0.0):    #if the original equinox is zero, assume the
      now = time.gmtime()                              #   coordinates refer to equinox-of-date
      epoch = now.tm_year + now.tm_yday/365.0
    else:
      epoch = self.Epoch

    ObjRa = (self.Ra/54000.0)*15
    ObjDec = self.Dec/3600.0
    tauz = (epoch-1900.0)/100
    JDz = (tauz*36524.2199)+2415020.313
    tau = (self.Time.JD-JDz)/36524.2199
    zeta = ((2304.250+1.396*tauz)*tau+0.302*tau*tau+0.018*tau*tau*tau)/3600 #Convert to degrees}
    z = (zeta*3600+0.791*tau*tau+0.001*tau*tau*tau)/3600        #Likewise convert to degrees}
    theta = ((2004.682-0.853*tauz)*tau-0.426*tau*tau-0.042*tau*tau*tau)/3600
    A = cos(DegToRad(ObjDec))*sin(DegToRad(ObjRa+zeta))
    B = cos(DegToRad(theta))*cos(DegToRad(ObjDec))*cos(DegToRad(ObjRa+zeta)) - sin(DegToRad(theta))*sin(DegToRad(ObjDec))
    C = sin(DegToRad(theta))*cos(DegToRad(ObjDec))*cos(DegToRad(ObjRa+zeta)) + cos(DegToRad(theta))*sin(DegToRad(ObjDec))
    t = atan2(A,B)
    nRA = ((RadToDeg(t+DegToRad(z))/15)*54000)  #in arcsec}
    if nRA < 0:
      nRA += 360*3600
    if ObjDec > (-1000):
      nDEC = (RadToDeg(asin(C)))*3600
    else:
      nDEC = RadToDeg(acos(sqrt(A*A+B*B)))*3600
      if C < 0:
        nDEC = -nDEC
       #Note: nRA and nDEC are the NEW, CORRECTED RA and DEC in arcseconds, NOT
       #       offsets from the uncorrected RA and DEC.
    self.RaA,self.DecA = nRA, nDEC

  def Refrac(self):    #Originally in CORRECT.PAS
    """Calculate the correction for atmospheric refraction for the given coordinates.
                   
       Returns a tuple of dRA and dDEC, which are OFFSETS from the current position, in arcseconds.
    """
    ObjRa = self.RaA/54000.0       #Translate to hours from arcsec}
    ObjDec = self.DecA/3600.0      #Translate to degrees from arcsec}

    z = DegToRad(90-self.Alt)                      #Zenith distance in radians}
    if z <= 0:
      z = 1e-6
    h = DegToRad((self.Time.LST-ObjRa)*15)     #Hour angle in radians}
    dummy = trunc(h/(2*pi))
    h -= dummy*2*pi
    obs = DegToRad(prefs.ObsLat)                    #Observatory Lat in radians}
    R = -1
    NewR = 0
    twiggles = 0
    #Calculate the value R in arc seconds}
    while ((NewR-R)>=1e-8) and (twiggles<20):
      twiggles += 1
      R = NewR
      Tanof = tan(z-DegToRad(R/3600))
      NewR = R1*Tanof + R2*Tanof*Tanof*Tanof

    if twiggles>20:     #If we're very close to the horizon, the iterative solver can fail...
      logger.error('correct.CalcPosition.Refrac: Too many Twiggles in refraction code!')

    #Calculate dRA and dDEC in arcsec}
    R = NewR
    CurlR = R*17*(prefs.Press*30/1015.92)/(460+((prefs.Temp*9/5)+32))   #convert Temp and Press to F and "Hg for correction}
    dRA = CurlR * sin(h) * cosec(z) * cos(obs) * sec(DegToRad(ObjDec))
    dDEC = CurlR * ( sin(obs)*cosec(z)*sec(DegToRad(ObjDec)) - tan(DegToRad(ObjDec))*cot(z) )
    return dRA, dDEC

  def Nutation(self, T):   #Originally in CORRECT.PAS
    """var L,Ld,M,Md,Omega:double
       #This is taken from Astronomical Formulae for Calculators, Jean Meeus,
       # 3rd Ed. 1985.  P:69-70.

            NOTE - original Pascal function modified dPhi and dEpsi arguments in place
                   New Python function returns dRA and dDEC (in arcsec) as tuple!
    """
    L = 279.69668 + 36000.76892*T + 0.0003025*T*T   #Sun's mean longtitude
    Ld = 270.4342 + 481267.8831*T - 0.001133*T*T    #Moon's mean longtitude
    M = 358.47583 + 35999.04975*T - 0.000150*T*T - 0.0000033*T*T*T    #Sun's mean anomaly
    Md = 296.1046 + 477198.8491*T + 0.009192*T*T    #Moon's mean anomaly
    Omega = 259.1833 - 1934.1420*T + 0.002078*T*T   #Longtitude of Moon's ascending node
    L = DegToRad(Reduce(L))                         #Reduce to range 0-360, convert to radians
    Ld = DegToRad(Reduce(Ld))                       #Reduce to range 0-360, convert to radians
    M = DegToRad(Reduce(M))                         #Reduce to range 0-360, convert to radians
    Md = DegToRad(Reduce(Md))                       #Reduce to range 0-360, convert to radians
    Omega = DegToRad(Reduce(Omega))                 #Likewise..
    dPhi = ( -(17.2327+0.01737*T)*sin(Omega) - (1.2729+0.00013*T)*sin(2*L)
             +0.2088*sin(2*Omega) - 0.2037*sin(2*Ld)
             +(0.1261-0.00031*T)*sin(M) + 0.0675*sin(Md)
             -(0.0497-0.00012*T)*sin(2*L+M) - 0.0342*sin(2*Ld-Omega)
             -0.0261*sin(2*Ld+Md) + 0.0214*sin(2*L-M)
             -0.0149*sin(2*L-2*Ld+Md) + 0.0124*sin(2*L-Omega)
             +0.0114*sin(2*Ld-Md) )
    dEpsi = (  (9.2100+0.00091*T)*cos(Omega) + (0.5522-0.00029*T)*cos(2*L)
              -0.0904*cos(2*Omega) + 0.0884*cos(2*Ld)
              +0.0216*cos(2*L+M) + 0.0183*cos(2*Ld-Omega)
              +0.0113*cos(2*Ld+Md) - 0.0093*cos(2*L-M)
              -0.0066*cos(2*L-Omega) )
    #Note: dPhi and dEpsi are in arcsecs NOT degrees
    return dPhi, dEpsi
    
  def ApparentPlace(self):  #Originally in CORRECT.PAS
    """Calculate annual abberation (I think :-) 
    
       Returns dRA and dDEC corrections as a tuple, in arcseconds.
       
       #This is taken from Astronomical Formulae for Calculators, Jean Meeus,
       # 3rd Ed. 1985.  P:71-73.
    """
    Ra = DegToRad((self.RaA/54000.0)*15)     #Convert to degrees, and: radians}
    Dec = DegToRad(self.DecA/3600.0)         #Convert to degrees, and: radians}
    if abs(Dec/3600+90) < 1e-6:   
      Dec = -89.999999*3600      
    if abs(Dec/3600-90) < 1e-6:
      Dec = 89.999999
    T = (self.Time.JD-2415020)/36525
    dPhi, dEpsi = self.Nutation(T)
    L = 279.69668+36000.76892*T + 0.0003025*T*T         #Sun's mean longtitude}
    M = 358.47583+35999.04975*T - 0.000150*T*T - 0.0000033*T*T*T
    L = DegToRad(Reduce(L))                  #Reduce to 0-360, convert to radians}
    M = DegToRad(Reduce(M))
    Epsi = 23.452294-0.0130125*T - 0.00000164*T*T + 0.000000503*T*T*T
    Epsi = DegToRad(Epsi)                    #Convert to radians}
    C = ( (1.919460-0.004789*T-0.000014*T*T)*sin(M) +
          (0.020094-0.000100*T)*sin(2*M)+0.000293*sin(3*M) )
    Sun = L + DegToRad(C)                    #Sun's true longtitude, in radians}
    dRa1 = (cos(Epsi)+sin(Epsi)*sin(Ra)*tan(Dec))*dPhi - (cos(Ra)*tan(Dec))*dEpsi
    dDec1 = (sin(Epsi)*cos(Ra))*dPhi + sin(Ra)*dEpsi
    dRa2 = -20.49*((cos(Ra)*cos(Sun)*cos(Epsi)+sin(Ra)*sin(Sun))/cos(Dec))
    dDec2 = -20.49*(cos(Sun)*cos(Epsi)*(tan(Epsi)*cos(Dec)-sin(Ra)*sin(Dec))
                    +cos(Ra)*sin(Dec)*sin(Sun))
    dRA = dRa1 + dRa2                          #In arcsecs}
    dDEC = dDec1 + dDec2                       #Also in arcsecs}
    self.RaA += dRA
    self.DecA += dDEC

  def Flex(self):
    """Calculate the correction for telescope flexure, using the TPOINT flexure terms from
       the teljoy.ini file.
    """
    h  =  (self.Time.LST - self.RaC / 54000)/12*pi  #Hour angle in radians, +ve to West of meridian}
    d  =  self.DecC*pi/3600/180   #Dec in radians}
    sind = sin(d)
    cosd = cos(d)
    tand = tan(d)
    sinh = sin(h)     #We're not using any Hyperbolic trig functions, so don't worry about the name clashes
    cosh = cos(h)
    sinp = sin(prefs.ObsLat*pi/180)
    cosp = cos(prefs.ObsLat*pi/180)

    dr = 0
    dd = 0

    if abs(cosd) > 1e-3:                       #CH     {check for overflow on the division}
      dr += (FlexData.CH / cosd)

    dr -= (FlexData.MA * cosh * tand)      #MA
    dd += (FlexData.MA * sinh)

    dr += (FlexData.ME * sinh * tand)      #ME
    dd += (FlexData.ME * cosh)

    dr -= (FlexData.DAF * (cosp * cosh + sinp * tand) )    #DAF

    dr += (FlexData.HCEC * cosh)           #HCEC

    dr += (FlexData.HCES * sinh)           #HCES

    dd += (FlexData.DCEC * cosd)           #DCEC

    dd += (FlexData.DCES * sind)           #DCES

    dr += (FlexData.DNP * sinh * tand)     #DNP

    if abs(cosd) > 1e-3:                       #TF    {check for overflow on the division}
      dr += (FlexData.TF * cosp * sinh / cosd)
    dd += (FlexData.TF * (cosp * cosh * sind - sinp * cosd))

    dr += (FlexData.NP * tand)             #NP

    dr += (FlexData.HHSH2 * sin(2*h))      #HHSH2

    dr += (FlexData.HHSD * sind)           #HHSD

    dr += (FlexData.HHCD * cosd)           #HHCD

    return dr, -dd       # Invert dec offset to match default TPOINT output
    
  def update(self, now=True):
    """Use self.Ra and self.Dec to update the other position attributes (RaA,DecA,RaC,DecC,Alt,Azi).
       if 'now' is True, use the current time, otherwise use the time in self.Time.UT.
    """
    self.Time.update(now=now)
    self.Precess()
    self.ApparentPlace()
    self.RaC,self.DecC = self.RaA, self.DecA
    self.posviolate = False
    self.AltAziConv()
    if prefs.RefractionOn:
      dRA, dDEC = self.Refrac()
      self.RaC += dRA
      self.DecC += dDEC
    if prefs.FlexureOn:
      dRA,dDEC = self.Flex()
      self.RaC += dRA
      self.DecC += dDEC
      

class HADecPosition(CalcPosition):
  """Subclass CalcPosition to handle fixed (HourAngle/Dec positions, for tasks like
     pointing at the flatfielding screen, parking the telescope, etc. Source attributes
     and arguments to __init__ are ha (in hours, dec (in degrees), and domepos (in degrees).

     The update() method is overridden to first calculate .Ra and .Dec from the
  """
  def __init__(self, ha=None, dec=None, epoch=0.0, domepos=None, objid=''):
    self.HA = ha
    self.Time = TimeRec()                 #Time to use for the coordinate transforms
    ra = self.Time.LST + self.HA
    if ra < 0.0:
      ra += 24.0
    if ra > 24.0:
      ra -= 24.0
    CalcPosition.__init__(self, ra=ra, dec=dec, epoch=epoch, domepos=domepos, objid=objid)
    self.update()

  def update(self, now=True):
    """Override normal position update to calculate the current ra/dec from the fixed hour-angle/dec position
       before doing the astropmetric calculations.
    """
    self.Time.update(now=now)
    self.Ra = (self.Time.LST + self.HA)*15*3600
    CalcPosition.update(self)


class FlexureProfile(object):
  """Class to load and store the TPOINT flexure terms from the .ini file
  """
  def __init__(self):
    self.GetFlexConstants()
  def GetFlexConstants(self): 
    """Load the terms from the .ini file
    """
    if prefs.EastOfPier:
      Section = 'FlexureEast'
    else:
      Section = 'FlexureWest'
    self.CH  =  CP.getfloat(Section,'CH')
    self.MA  =  CP.getfloat(Section,'MA')
    self.ME  =  CP.getfloat(Section,'ME')
    self.DAF  = CP.getfloat(Section,'DAF')
    self.HCEC = CP.getfloat(Section,'HCEC')
    self.HCES = CP.getfloat(Section,'HCES')
    self.DCEC = CP.getfloat(Section,'DCEC')
    self.DCES = CP.getfloat(Section,'DCES')
    self.DNP  = CP.getfloat(Section,'DNP')
    self.TF  =  CP.getfloat(Section,'TF')
    self.NP  =  CP.getfloat(Section,'NP')
    self.HHSH2= CP.getfloat(Section,'HHSH2')
    self.HHSD = CP.getfloat(Section,'HHSD')
    self.HHCD = CP.getfloat(Section,'HHCD')



def DegToRad(r):    #Originally in MATHS.PAS
  return (float(r)/180)*pi

def RadToDeg(r):    #Originally in MATHS.PAS
  return (r/pi)*180

def cosec(r):       #Originally in MATHS.PAS
  return 1/sin(r)
  
def sec(r):         #Originally in MATHS.PAS
  return 1/cos(r)
  
def cot(r):         #Originally in MATHS.PAS
  return 1/tan(r)

def Reduce(r):      #Originally in MATHS.PAS
  n = trunc(r/360.0)
  r -= n*360
  if r < 0:
    return r + 360
  else:
    return r



ConfigDefaults.update( {'CH':'0.0', 'MA':'0.0', 'ME':'0.0', 'DAF':'0.0', 'HCEC':'0.0',
                        'HCES':'0.0', 'DCEC':'0.0', 'DCES':'0.0', 'DNP':'0.0', 'TF':'0.0',
                        'NP':'0.0', 'HHSH2':'0.0', 'HHSD':'0.0', 'HHCD':'0.0'} )

CP,CPfile = UpdateConfig()

FlexData = FlexureProfile()

