unit Maths;
{  Module: Maths.pas

   These procedures were added since they don't exist in Turbo Pascal

   Created:  9111.0518    Modified: 9111.2616    Version:  1.40

   ArcSin   -  0=ArcSin(Sin(0))
   ArcCos   -  0=ArcCos(Cos(0))
   Tan      -  Tan(0)
   ArcTan2  -  ArcTan(x,y)  Returns the proper quadrant.
   Cot      -  1/Tan(0)
   Cosec    -  1/Sin(0)
   Sec      -  1/Cos(0)
   DegToRad -  Converts degrees to radians
   RadToDeg -  Converts radians to degrees
   Reduce   -  Reduces the angle to the range +/- (0 to 360)
}
{$N+,E+}
interface

Function ArcSin(r:double):double;

Function ArcCos(r:double):double;

Function Tan(r:double):double;

Function ArcTan2(x,y:double):double;

Function Cot(r:double):double;

Function CoSec(r:double):double;

Function Sec(r:double):double;

Function DegToRad(r:double):double;

Function RadToDeg(r:double):double;

Function Reduce(r:double):double;

implementation

Function ArcSin(r:double):double;

 VAR asn : double;

 begin
    if ((1-ABS(r)) < 1E-5) then
      begin
        if (r > 0) then
          asn := Pi/2 - sqrt(1-r)
        else
          asn := -Pi/2 + sqrt(1+r)
      end
   else
     asn := ArcTan(r/(sqrt(1-r*r)));
   ArcSin := asn;
 end;

Function ArcCos(r:double):double;

 var ac : double;

 begin
   if ((1-ABS(r)) < 1E-5) then
     ac := 1 - ABS(r)
   else
     ac := ArcTan((1-r*r)/r);
   if (ac < 0) then
     ac := ac + Pi;
   ArcCos := ac;
 end;

Function Tan(r:double):double;
 begin
   tan:=sin(r)/cos(r);
 end;

Function ArcTan2(x,y:double):double;
 var t2:double;
 begin
   t2:=ArcTan(x/y);
   if (y < 0)  then
     t2:=t2+pi;
   if ((y > 0) and (x < 0)) then
     t2:=t2+2*pi;
   ArcTan2:=t2;
   end;

Function Cot(r:double):double;
 begin
   Cot:=1/Tan(r);
 end;

Function CoSec(r:double):double;
 begin
   CoSec:=1/Sin(r);
 end;

Function Sec(r:double):double;
 begin
   Sec:=1/Cos(r);
 end;

Function DegToRad(r:double):double;
 begin
   DegToRad:=(r/180)*pi;
 end;

Function RadToDeg(r:double):double;
 begin
   RadToDeg:=(r/pi)*180;
 end;

Function Reduce(r:double):double;
 var n:double;
 begin
   n:=trunc(r/360);
   r:=r-(n*360);
   If (r < 0) then
     Reduce:=r+360
   else
     Reduce:=r;
 end;

end.
