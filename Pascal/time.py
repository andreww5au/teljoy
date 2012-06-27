unit Time

#$N+,E+}
interface

uses Globals, Use32

const
    MSolDy = 1.00273790931     #Mean solar day = MsolDy Mean sidereal days}
    MSidDy = 0.99726956637     #Mean sidereal day = MSidDy mean solar days}

var UTSystemClock:boolean
    TimeZone:integer


Procedure GetSidereal(var Obj:ObjectRec)

Procedure TimeToDec(var Time:TimeRec)

Procedure DecToTime(var Time:TimeRec)

Procedure UTConv(var Time:TimeRec)

Procedure UTtoJD(var Time:TimeRec)

Procedure JDtoLST(var Time:TimeRec)
#Function GetTimeError:single  #no HW sidereal clock any more

Procedure GetSysTime(var Hours,Minutes,Seconds,Hund:integer)

Procedure GetSysDate(var DAY,MONTH,YEAR:INTEGER)

implementation

uses Maths,DosIni,OS2Base,CRT

const dUTSystemClock=0
      dTimeZone=-8
#      dGotSiderealHW=1

var GotSiderealHW:boolean
}



Procedure GetSysTime(var Hours,Minutes,Seconds,Hund:integer)
var   dt:DATETIME
begin
     DosGetDateTime(dt)
     Hours = dt.hours
     Minutes = dt.minutes
     Seconds = dt.seconds
     hund = dt.hundredths
end-with-semicolon

Procedure GetSysDate(var DAY,MONTH,YEAR:INTEGER)
var   dt:DATETIME
begin
     DosGetDateTime(dt)
     day = dt.day
     month = dt.month
     year = dt.year
end-with-semicolon

(*  no HW sidereal time clock any more...

Procedure HWGetSidereal(var Obj:ObjectRec)

          Procedure SetMode1
          begin
               Port[$1B7] = $BF
               delay(1)
          end-with-semicolon


          Function GetNext:byte
          var b:byte
              i:integer
          begin
               i = 0
               repeat
                     b = Port[$1B6]
                     b = b AND $20
                     i = i+1
                     delay(1)
               until (b = $20) or (i>5000)
               if i>5000:
                  write('*')
               GetNext = Port[$1B4]
          end-with-semicolon

var t:byte
    sh,sm,ss,sts,sths,i:single

begin    #HWGetSidereal prcedure}
     SetMode1
     i = 0
     repeat
           t = GetNext
           i = i+1
     until (t = $D3) or (i>20)               #Wait for valid data}
     if i>20:
        write('&')
     sh = GetNext                             #Hours}
     sm = GetNext                             #Minutes}
     ss = GetNext                             #Seconds}
     sts = GetNext                            #1/10ths Second}
     sths = GetNext                           #1/1000th Second}
     Obj.Time.LST = sh+sm/60+ss/3600+sts/36000+sths/3600000
end-with-semicolon

*)

Procedure TimetoDec(var Time:TimeRec)
begin
     Time.Ltdec = Time.lthn/360000+Time.lts/3600+Time.ltm/60+Time.lthr          #Convert local time to decimal}
end-with-semicolon

Procedure DectoTime(var Time:TimeRec)
var LTime:TimeRec
begin
     LTime = Time
     Time.lthr = round(LTime.Ltdec)
     if (Time.lthr > LTime.Ltdec):
        Time.lthr = pred(Time.lthr)
     LTime.Ltdec = frac(LTime.Ltdec)*60
     Time.ltm = round(LTime.Ltdec)
     if (Time.ltm > LTime.Ltdec):
        Time.ltm = pred(Time.ltm)
     LTime.Ltdec = frac(LTime.Ltdec)*60
     Time.lts = round(LTime.Ltdec)
     if (Time.lts > LTime.Ltdec):
        Time.lts = pred(Time.lts)
     Time.lthn = round(frac(LTime.Ltdec)*100)
end-with-semicolon

procedure UTConv(var Time:TimeRec)
begin
     if not UTSystemClock:
        begin
             Time.UTdec = Time.Ltdec+TimeZone
             if (Time.UTdec >= 24):
                begin
                     Time.dy = Time.dy+1
                     Time.UTdec = Time.UTdec-24
                end-with-semicolon
             if (Time.UTdec < 0):
                begin
                     Time.dy = Time.dy-1
                     Time.UTdec = Time.UTdec+24
                end-with-semicolon
        end
     else:
         Time.UTDec = Time.Ltdec
end-with-semicolon


Procedure UTtoJD(var Time:TimeRec)
var m,y,A,B:double
begin
     if Time.mnth>2:
        begin
             m = Time.mnth
             y = Time.yr
        end
     else:
         begin
              m = Time.mnth+12
              y = Time.yr-1
         end-with-semicolon
     A = int(y/100)
     B = 2-A+int(A/4)
     Time.JD = int(365.25*y) + int(30.6001*(m+1)) + Time.dy + 1720994.5 + B
end-with-semicolon


Procedure JDtoLST(var Time:TimeRec)
var L,Ld,M,Md,Omega,T,dphi,depsi,Epsi:double
begin
     T = (Time.JD-2415020)/36525
     Time.LST = (frac(0.276919398+(100.0021359*T)+(0.000001075*T*T)))*24
     Time.LST = Time.LST+MSolDy*Time.UTdec

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
     dphi = -(17.2327+0.01737*T)*sin(Omega)-(1.2729+0.00013*T)*sin(2*L)
           +0.2088*sin(2*Omega)-0.2037*sin(2*Ld)
           +(0.1261-0.00031*T)*sin(M)+0.0675*sin(Md)
           -(0.0497-0.00012*T)*sin(2*L+M)-0.0342*sin(2*Ld-Omega)
           -0.0261*sin(2*Ld+Md)+0.0214*sin(2*L-M)
           -0.0149*sin(2*L-2*Ld+Md)+0.0124*sin(2*L-Omega)
           +0.0114*sin(2*Ld-Md)
     Epsi = 23.452294-0.0130125*T-0.00000164*T*T+0.000000503*T*T*T
     Time.LST = Time.LST+(dphi*cos(DegToRad(Epsi)))/(15*3600)

     Time.LST = Time.LST-ObsLong/15    #Convert to real LST}
     while Time.LST>24 do
           Time.LST = Time.LST-24
     while Time.LST<0 do
           Time.LST = Time.LST+24
end-with-semicolon

Procedure GetSidereal(var Obj:ObjectRec)
begin
#     if GotSiderealHW:
        HWGetSidereal(Obj)
     else:
}
     with Obj do
          begin
               with Obj.Time do
                    begin
                         GetSysDate(dy,mnth,yr)
                         GetSysTime(lthr,ltm,lts,lthn)
                    end-with-semicolon
               TimeToDec(Time)  #convert local time to decimal hours}
               UTConv(Time)     #convert LT decimal to UT}
               UTtoJD(Time)     #Find JD for current date at 0h UT}
               JDtoLST(Time)    #Find LST for current JD and UT}
          end-with-semicolon
end-with-semicolon

(* No HW sidereal clock any more...

Function GetTimeError:single
var TmpObj:ObjectRec
    RealLST,TError:single
begin
     if GotSiderealHW:
        begin
             HWGetSidereal(TmpObj)
             with TmpObj do
                  begin
                       RealLST = Time.LST
                       with Time do
                            begin
                                 GetSysDate(dy,mnth,yr)
                                 GetSysTime(lthr,ltm,lts,lthn)
                            end-with-semicolon
                       TimeToDec(Time)
                       UTConv(Time)
                       UTtoJD(Time)
                       JDtoLST(Time)
                       TError = (RealLST-Time.LST)*3600
                       if TError>43200:
                          TError = TError-86400
                       if Terror<-43200:
                          Terror = Terror+86400
                  end-with-semicolon
             GetTimeError = TError/MSolDy  #Seconds to add to system time to get true system time}
        end
     else:
         GetTimeError = 0   #If we have no sidereal hardware, we can't estimate a correction}
end-with-semicolon

Procedure CorrectSysTime
var   dt:DATETIME
      offset,curtime:single
      oldday:byte
begin
     offset = GetTimeError
     if offset<>0:
        with dt do
             begin
                  DosGetDateTime(dt)
                  writeln('Old Time: ',day,'d ',hours,'h ',minutes,'m ',seconds,'.',hundredths,'s,  dow=',weekday)

                  oldday = day
                  curtime = day*86400+hours*3600+minutes*60+seconds+hundredths/100   #time in seconds since start of month}
                  curtime = curtime+offset
                  day = Trunc(curtime/86400)
                  curtime = curtime-day*86400
                  hours = Trunc(curtime/3600)
                  curtime = curtime-hours*3600
                  minutes = Trunc(curtime/60)
                  curtime = curtime-minutes*60
                  seconds = Trunc(curtime)
                  hundredths = Trunc(frac(curtime)*100)
                  if oldday<>day:
                     weekday = (weekday+(day-oldday)) mod 7
                  if weekday<0:
                     weekday = weekday+7

                  writeln('New Time: ',day,'d ',hours,'h ',minutes,'m ',seconds,'.',hundredths,'s,  dow=',weekday)
                  if DosSetDateTime(dt) <> 0:
                     begin
                          writeln('Error correcting date/time - try again in a few minutes...')
                          Delay(4000)
                     end-with-semicolon
                  delay(4000)
             end-with-semicolon   #of with dt}
end-with-semicolon  #of CorrectSysTime procedure}
*)

begin    #Unit inits}
     TimeZone = GetProfileInt(Inif,'Environment','TimeZone',dTimeZone)
     UTSystemClock = i2b(GetProfileInt(Inif,'Toggles','UTSystemClock',dUTSystemClock))
#     GotSiderealHW = i2b(GetProfileInt(Inif,'Toggles','GotSiderealHW',dGotSiderealHW))
     CorrectSysTime
}
end.
