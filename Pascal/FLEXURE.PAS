unit flexure;

interface

uses Globals,Dosini,Maths;


Procedure Flex(var dr,dd:double; Obj:ObjectRec);

Procedure GetFlexConstants;


implementation

var CH, MA, ME, DAF, HCEC, HCES, DCEC, DCES, DNP, TF, NP, HHSH2, HHSD, HHCD  : double;  {Flexure constants from TPOINT}

Procedure GetFlexConstants;
var section:string[20];
begin
     if EastOfPier then
        Section:='FlexureEast'
     else
         Section:='FlexureWest';

      CH:=GetProfileReal(Inif,Section,'CH',0);
      MA:=GetProfileReal(Inif,Section,'MA',0);
      ME:=GetProfileReal(Inif,Section,'ME',0);
      DAF:=GetProfileReal(Inif,Section,'DAF',0);
      HCEC:=GetProfileReal(Inif,Section,'HCEC',0);
      HCES:=GetProfileReal(Inif,Section,'HCES',0);
      DCEC:=GetProfileReal(Inif,Section,'DCEC',0);
      DCES:=GetProfileReal(Inif,Section,'DCES',0);
      DNP:=GetProfileReal(Inif,Section,'DNP',0);
      TF:=GetProfileReal(Inif,Section,'TF',0);
      NP:=GetProfileReal(Inif,Section,'NP',0);
      HHSH2:=GetProfileReal(Inif,Section,'HHSH2',0);
      HHSD:=GetProfileReal(Inif,Section,'HHSD',0);
      HHCD:=GetProfileReal(Inif,Section,'HHCD',0);

end;


Procedure Flex(var dr,dd:double; Obj:ObjectRec);

var h,d:double;
    cosh,sinh,cosd,sind,tand,cosp,sinp:double;


begin
     h := (Obj.Time.LST - Obj.RaC / 54000)/12*Pi;  {Hour angle in radians, +ve to West of meridian}
     d := Obj.DecC*Pi/3600/180;   {Dec in radians}

     sind:=sin(d);
     cosd:=cos(d);
     tand:=tan(d);

     sinh:=sin(h);
     cosh:=cos(h);

     sinp:=sin(ObsLat*Pi/180);
     cosp:=cos(ObsLat*Pi/180);

     dr:=0;
     dd:=0;

{CH}
     if abs(cosd) > 1e-3 then       {check for overflow on the division}
        dr := dr   + CH / cosd;

{MA}
     dr := dr   - MA * cosh * tand;
     dd := dd   + MA * sinh;

{ME}
     dr := dr   + ME * sinh * tand;
     dd := dd   + ME * cosh;

{DAF}
     dr := dr   - DAF * (cosp * cosh + sinp * tand);

{HCEC}
     dr := dr   + HCEC * cosh;

{HCES}
     dr := dr   + HCES * sinh;

{DCEC}
     dd := dd   + DCEC * cosd;

{DCES}
     dd := dd   + DCES * sind;

{DNP}
     dr := dr   + DNP * sinh * tand;

{TF}
     if abs(cosd) > 1e-3 then       {check for overflow on the division}
        dr := dr   + TF * cosp * sinh / cosd;
     dd := dd   + TF * (cosp * cosh * sind - sinp * cosd);

{NP}
     dr := dr   + NP * tand;

{HHSH2}
     dr := dr   + HHSH2 * sin(2*h);

{HHSD}
     dr := dr   + HHSD * sind;

{HHCD}
     dr := dr   + HHCD * cosd;

{
     dr:=-dr;
}
     dd:=-dd;  { Invert to match default TPOINT output }


{      Writeln ('Flexure:   dRA: ',dr,'"  dDEC:',dd,'"    ");
}

   end;    {Proc. Flex}

end.  {Unit Flexure
