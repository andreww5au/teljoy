{$N+,E+}
unit ObjInfo;

{  Module: ObjInfo.pas

   This module deals with the gathering of object information from the user.

}

interface

uses Globals;

Procedure GetInfo(const Title:string80; var Obj:ObjectRec;var abort:boolean);

Procedure Convert(var Obj:ObjectRec);

implementation

uses Crt,Dos,Correct,ReadIn,Maths,Time,Flexure;

{header line:
procedure rddat(dattype:dtype;var val:double;defval:double;var msg:string;xpos,ypos:integer;var abort:boolean);
 }


Procedure GetInfo(const Title:string80; var Obj:ObjectRec;var abort:boolean);
var ct:char;
    an:char;
begin
     repeat
           ClrScr;
           writeln(Title);
           abort:=false;
           repeat
                 msg:='Object Ra  (Hr, Min, Sec):';
                 RdDat(dms,Obj.RA,Obj.RA/15,msg,1,2,abort);
                 Obj.RA:=Obj.RA*15;                {convert to ARC sec}
                 if abort then
                    Exit;
                 ConvDMS(Obj.RA/15,Obj.RaH,Obj.RaM,Obj.RaS);
           until (Obj.Ra>=0) and (Obj.Ra<=24*15*3600);

           repeat
                 msg:='Object Dec  (Deg, Min, Sec):';
                 RdDat(dms,Obj.Dec,Obj.Dec,msg,1,3,abort);
                 if abort then
                    Exit;
                 ConvDMS(Obj.Dec,Obj.DecD,Obj.DecM,Obj.DecS);
           until (Obj.Dec>=-90*3600) and (Obj.Dec<=90*3600);

           msg:='Epoch (0 for epoch of date):';
           RdDat(num,Obj.Epoch,Obj.Epoch,msg,1,4,abort);
           if abort then
              Exit;

           GotoXY(1,5);
           write('Object ID: ');
           readln(Obj.ID);

           Obj.Comp:=true;

           Convert(Obj);
           writeln;
           Writeln('The above coordinates are offset by:');
           write('    RA: ');

           if (Abs(Obj.RaC-IObj.RaC) < 15*12*3600) then
              WriteDMS((Obj.RaC-IObj.RaC)/15)
           else
               WriteDMS((Obj.RaC-IObj.RaC)/15 -
                  24*3600*( (Obj.RaC-IObj.RaC)/Abs(Obj.RaC-IObj.RaC) ) );

           writeln(' hours,');
           write('   Dec: ');
           WriteDMS((Obj.DecC-IObj.DecC));
           writeln(' degrees.');
           writeln('From the current position.');

           writeln;
           write('Is the above information correct (y)? ');

           repeat
           until keypressed;
           an:=ReadKey;

           an:=Upcase(an);
           if Ord(an)=27 then
              abort:=true;
     until (an = 'Y') or (Ord(an)=13) or abort;
     ClrScr;
end;


Procedure Convert(var Obj:ObjectRec);
 var delra,deldec,HourC,DecCd,dr,dd:double;
     ndays,mnthday,i:integer;
     IsLeapyr:boolean;
 begin
      GetSysTime(Obj.Time.lthr,Obj.Time.ltm,Obj.Time.lts,Obj.Time.lthn);
      GetSysDate(Obj.Time.dy,Obj.Time.mnth,Obj.Time.yr);
      TimetoDec(Obj.Time);
      UTConv(Obj.Time);
      UTtoJD(Obj.Time);
      GetSidereal(Obj);
      if (Obj.Epoch=0) then
         begin
              IsLeapyr:=(Obj.Time.yr-1900) mod 4 = 0;   {Need this to determine the number of
                                                  days so far this year}
              ndays:=0;
              for i:=1 to Obj.Time.mnth do              {Add up the number of days}
                  begin                               {for the year so far}
                       if (i < Obj.Time.mnth) then
                          case i of
                               1,3,5,7,8,10,12: mnthday:=31;
                               2: if IsLeapyr then
                                     mnthday:=29
                                  else
                                      mnthday:=28;
                               4,6,9,11: mnthday:=30;
                          end
                       else
                           mnthday:=Obj.Time.dy;
                       ndays:=ndays+mnthday;
                  end;
              ndays:=ndays-1;
              Obj.Epoch:=Obj.Time.yr+ndays/365;
         end;

{      writeln;
      write('Init Co-ords:    RA: ');
      WriteDMS(Obj.RA/15);
      write('     Dec: ');
      WriteDMS(Obj.Dec);
      writeln;                 }

      Precess(dr,dd,Obj);
      Obj.RaA:=dr;
      Obj.DecA:=dd;

{      write('Prec. Co_rods:   RA: ');
      WriteDMS(dr/15);
      write('     Dec: ');
      writeDMS(dd);
      writeln;                 }

      ApparentPlace(dr,dd,Obj);
      Obj.RaA:=Obj.RaA+dr;                 {Add in corrections for apparent}
      Obj.DecA:=Obj.DecA+dd;               {place.                         }

{      write('App. place:      RA: ');
      writeDMS(Obj.RaA/15);
      write('     Dec: ');
      WriteDMS(Obj.DecA);
      writeln;                 }

      AltAziConv(Obj);

      { *********** The Flexure Correction ************}

      Obj.RaC:=Obj.RaA;
      Obj.DecC:=Obj.DecA;

      if RefractionOn then
         begin
              Refrac(dr,dd,Obj);
              Obj.RaC:=Obj.RaC+dr;        {Add in corrections for refraction}
              Obj.DecC:=Obj.DecC+dd;
         end;

      if FlexureOn then
         begin
              Flex(dr,dd,Obj);
              Obj.RaC:=Obj.RaC+dr;
              Obj.DecC:=Obj.DecC+dd;
         end;



{      write('Final Co-ords:   RA: ');
      writeDMS(Obj.RaC/15);
      write('     Dec: ');
      writeDMS(Obj.DecC);
      writeln;                   }

 end;

end.
