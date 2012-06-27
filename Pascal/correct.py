
unit Correct

#$N+,E+}
interface

uses Globals

Procedure AltAziConv(var Obj:ObjectRec)

Procedure Precess(var dRa,dDec:double var Obj:ObjectRec)

Procedure Refrac(var dRa,dDec:double var Obj:ObjectRec)

Procedure Nutation(var dPhi,dEpsi,T:double)

Procedure ApparentPlace(var dRa,dDec:double Obj:ObjectRec)

Function ArcDistance(Obj1,Obj2:ObjectRec):double

implementation

uses Dosini,Maths



Procedure AltAziConv(var Obj:ObjectRec)
var ObjRa,ObjDec,alt1,alt2,co,cd,ct,H:double
begin
     #This is taken from Astronomical Formulae for Calculators, Jean Meeus,
      3rd Ed. 1985.  P:43-48.                                              }
     ObjRa = Obj.RaA/54000
     ObjDec = Obj.DecA/3600
     if ObjDec<-90:
        ObjDec = -89.9999999
     alt1 = sin(DegToRad(ObsLat))
     alt1 = alt1*(sin(DegToRad(ObjDec)))
     co = cos(DegToRad(ObsLat))
     cd = cos(DegToRad(ObjDec))
     H = DegToRad((Obj.Time.LST-ObjRa)*15.0)
     ct = cos(H)
     alt2 = co*cd*ct
     Obj.Alt = RadToDeg(ArcSin(alt1+alt2))
     Obj.Azi = RadToDeg(ArcTan2(sin(H),(cos(H)*sin(DegToRad(ObsLat))-Tan(DegToRad(ObjDec))*co)))
     Obj.Azi = Obj.Azi+180    #stupid algorithm counts azi from south!}
     Obj.Azi = Reduce(Obj.Azi)
end-with-semicolon

Procedure Precess(var dRa,dDec:double var Obj:ObjectRec)
var JDz,tau,tauz,zeta,z,theta,A,B,C,t,ObjRA,ObjDEC:double
begin
     #This is taken from Astronomical Formulae for Calculators, Jean Meeus,
      3rd Ed. 1985.  P:65-67.                                              }
     dRa = 0
     dDec = 0

     ObjRa = (Obj.Ra/54000)*15
     ObjDec = Obj.Dec/3600
     tauz = (Obj.Epoch-1900)/100
     JDz = (tauz*36524.2199)+2415020.313
     tau = (Obj.Time.JD-JDz)/36524.2199
     zeta = ((2304.250+1.396*tauz)*tau+0.302*tau*tau+0.018*tau*tau*tau)/3600 #Convert to degrees}
     z = (zeta*3600+0.791*tau*tau+0.001*tau*tau*tau)/3600        #Likewise convert to degrees}
     theta = ((2004.682-0.853*tauz)*tau-0.426*tau*tau-0.042*tau*tau*tau)/3600
     A = cos(DegToRad(ObjDec))*sin(DegToRad(ObjRa+zeta))
     B = cos(DegToRad(theta))*cos(DegToRad(ObjDec))*cos(DegToRad(ObjRa+zeta))-sin(DegToRad(theta))*sin(DegToRad(ObjDec))
     C = sin(DegToRad(theta))*cos(DegToRad(ObjDec))*cos(DegToRad(ObjRa+zeta))+cos(DegToRad(theta))*sin(DegToRad(ObjDec))
     t = ArcTan2(A,B)
     dRa = ((RadToDeg(t+DegToRad(z))/15)*54000)  #in arcsec}
     if ObjDec>(-1000):
        dDec = (RadToDeg(ArcSin(C)))*3600
     else:
         begin
              dDec = RadToDeg(ArcCos(Sqrt(A*A+B*B)))*3600
              if c<0:
                 dDec = -dDec
         end-with-semicolon
     #Note: dRa and dDec are the CORRECTED Ra and Dec in arcseconds, NOT
            correction to the apparent Ra and Dec.                    }
end-with-semicolon



Procedure Refrac(var dRa,dDec:double var Obj:ObjectRec)
const n=1.000297    #Index of refraction for air}
      R1=58.294
      R2=-0.0668
# Press=atm. press. in mb. (30in=1015.92mb) }
# Temp=temp in deg C }

var z,dummy,Tanof,h,obs,R,NewR,CurlR,ObjRA,ObjDec,ObjHour:double
    twiggles:integer

begin
     ObjRa = Obj.RaA/54000       #Translate to hours from arcsec}
     ObjDec = Obj.DecA/3600      #Translate to degrees from arcsec}

     z = DegToRad(90-Obj.Alt)                      #Zenith distance in radians}
     if z<=0:
        z = 1e-6
     h = DegToRad((Obj.Time.LST-ObjRa)*15)     #Hour angle in radians}
     dummy = Trunc(h/(2*pi))
     h = h-(dummy*2*pi)
     obs = DegToRad(ObsLat)                    #Observatory Lat in radians}
     NewR = 0
     twiggles = 0
     #Calculate the value R in arc seconds}
     repeat
           twiggles = twiggles+1
           R = NewR
           Tanof = tan(z-DegtoRad(R/3600))
           NewR = R1*Tanof + R2*Tanof*Tanof*Tanof
     until ((NewR-R)<1e-8) or (twiggles>20)

     if twiggles>20:
        writeln('Too many Twiggles in refraction code!')

     #Calculate dRA and dDEC in arcsec}
     R = NewR
     CurlR = R*17*(Press*30/1015.92)/(460+((Temp*9/5)+32))
                    #convert Temp and Press to F and "Hg for correction}

     dRA = CurlR * sin(h) * CoSec(z) * cos(obs) * Sec(DegToRad(ObjDec))
     dDec = CurlR * ( sin(obs)*CoSec(z)*Sec(DegToRad(ObjDec)) - tan(DegToRad(ObjDec))*Cot(z) )


     #dRa = (RadToDeg(dRa))*3600}             #LEAVE as seconds of arc!}
     #dDec = (RadToDeg(dDec))*3600}           #Likewise convert to arcsec}

end-with-semicolon


Procedure Nutation(var dPhi,dEpsi,T:double)
var L,Ld,M,Md,Omega:double
begin
     #This is taken from Astronomical Formulae for Calculators, Jean Meeus,
      3rd Ed. 1985.  P:69-70.                                              }
     L = 279.69668+36000.76892*T+0.0003025*T*T   #Sun's mean longtitude}
     Ld = 270.4342+481267.8831*T-0.001133*T*T #Moon's mean longtitude}
     M = 358.47583+35999.04975*T-0.000150*T*T-0.0000033*T*T*T#Sun's mean anomaly}
     Md = 296.1046+477198.8491*T+0.009192*T*T #Moon's mean anomaly}
     Omega = 259.1833-1934.1420*T+0.002078*T*T#Longtitude of Moon's ascending node}
     L = DegToRad(Reduce(L))                  #Reduce to range 0-360, convert to radians}
     Ld = DegToRad(Reduce(Ld))                #Reduce to range 0-360, convert to radians}
     M = DegToRad(Reduce(M))                  #Reduce to range 0-360, convert to radians}
     Md = DegToRad(Reduce(Md))                #Reduce to range 0-360, convert to radians}
     Omega = DegToRad(Reduce(Omega))          #Likewise..}
     dPhi = -(17.2327+0.01737*T)*sin(Omega)-(1.2729+0.00013*T)*sin(2*L)
            +0.2088*sin(2*Omega)-0.2037*sin(2*Ld)
            +(0.1261-0.00031*T)*sin(M)+0.0675*sin(Md)
            -(0.0497-0.00012*T)*sin(2*L+M)-0.0342*sin(2*Ld-Omega)
            -0.0261*sin(2*Ld+Md)+0.0214*sin(2*L-M)
            -0.0149*sin(2*L-2*Ld+Md)+0.0124*sin(2*L-Omega)
            +0.0114*sin(2*Ld-Md)
     dEpsi = (9.2100+0.00091*T)*cos(Omega)+(0.5522-0.00029*T)*cos(2*L)
            -0.0904*cos(2*Omega)+0.0884*cos(2*Ld)
            +0.0216*cos(2*L+M)+0.0183*cos(2*Ld-Omega)
            +0.0113*cos(2*Ld+Md)-0.0093*cos(2*L-M)
            -0.0066*cos(2*L-Omega)
     #Note: dPhi and dEpsi are in arcsecs NOT degrees}
end-with-semicolon

Procedure ApparentPlace(var dRa,dDec:double Obj:ObjectRec)
var dRa1,dRa2,dDec1,dDec2,Epsi,dPhi,dEpsi,T,L,M,e,C,Sun:double
begin
     #This is taken from Astronomical Formulae for Calculators, Jean Meeus,
     3rd Ed. 1985.  P:71-73.                                              }

     if Abs(Obj.Dec/3600+90)<1e-6:
        Obj.Dec = -89.999999*3600
     if Abs(Obj.Dec/3600-90)<1e-6:
        Obj.Dec = 89.999999

     Obj.Ra = DegToRad((Obj.RaA/54000)*15)     #Convert to degrees, and: radians}
     Obj.Dec = DegToRad(Obj.DecA/3600)         #Convert to degrees, and: radians}
     T = (Obj.Time.JD-2415020)/36525
     Nutation(dPhi,dEpsi,T)
     L = 279.69668+36000.76892*T+0.0003025*T*T#Sun's mean longtitude}
     M = 358.47583+35999.04975*T-0.000150*T*T-0.0000033*T*T*T
     L = DegToRad(Reduce(L))                  #Reduce to 0-360, convert to radians}
     M = DegToRad(Reduce(M))
     Epsi = 23.452294-0.0130125*T-0.00000164*T*T+0.000000503*T*T*T
     Epsi = DegToRad(Epsi)                    #Convert to radians}
     C = (1.919460-0.004789*T-0.000014*T*T)*sin(M)
        +(0.020094-0.000100*T)*sin(2*M)+0.000293*sin(3*M)
     Sun = L+DegToRad(C)                      #Sun's true longtitude, in radians}
     dRa1 = (cos(Epsi)+sin(Epsi)*sin(Obj.Ra)*tan(Obj.Dec))*dPhi-(cos(Obj.Ra)*tan(Obj.Dec))*dEpsi
     dDec1 = (sin(Epsi)*cos(Obj.Ra))*dPhi+sin(Obj.Ra)*dEpsi
     dRa2 = -20.49*((cos(Obj.Ra)*cos(Sun)*cos(Epsi)+sin(Obj.Ra)*sin(Sun))/cos(Obj.Dec))
     dDec2 = -20.49*(cos(Sun)*cos(Epsi)*(tan(Epsi)*cos(Obj.Dec)-sin(Obj.Ra)*sin(Obj.Dec))
            +cos(Obj.Ra)*sin(Obj.Dec)*sin(Sun))
     dRa = dRa1+dRa2                          #In arcsecs}
     dDec = dDec1+dDec2                       #Also in arcsecs}
                                              #dRa is MEANT to be in arcsec}
end-with-semicolon

Function ArcDistance(Obj1,Obj2:ObjectRec):double
var  Ra1,Dec1,Ra2,Dec2,dRa,dDec,d:double
begin
   Ra1 = DegToRad(Obj1.Ra/54000)
   Dec1 = DegToRad(Obj1.Dec/3600)
   Ra2 = DegToRad(Obj2.Ra/54000)
   Dec2 = DegToRad(Obj2.Dec/3600)
   d = ArcCos(sin(Dec1)*sin(Dec2)+cos(Dec1)*cos(Dec2)*cos(Ra1-Ra2))
   ArcDistance = RadToDeg(d)
end-with-semicolon

end.
