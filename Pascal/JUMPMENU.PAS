unit JumpMenu;
interface

Procedure JumpTo;
Procedure Freeze;
Procedure TogEast;

implementation

uses Globals,Crt,JumpCont,DetEvent,Menutext,ObjList,ObjInfo,ReadIn,
     SetPro,PC23int,DataBase,Flexure,
{$IFDEF NZ}
NZdome;
{$ELSE}
Pdome;
{$ENDIF}

var LastRAOffset,LastDecOffset:double;

Procedure Freeze;     {Freezes sidereal & non-sid tracking motion}
var key:char;
begin
     if HWlimit then
        Exit;

     ClrScr;
     writeln;

     Frozen:=true;

     writeln;
     Writeln('Sidereal motion and non-sidereal tracking now frozen.');
     writeln('Paddle control will function normally.');
     writeln('Press any key to exit, and resume tracking:');

     repeat
           DetermineEvent;
     until keypressed;
     key:=ReadKey;

     Frozen:=false;

     ClrScr;
     writeln;
     writeln('Normal tracking resumed');
end;

Procedure ResetPosition(var Obj:ObjectRec;var abort:boolean);
begin
     clrscr;
     writeln;
     GetInfo('Define current telescope position to be:',Obj,abort);
     if abort then
        System.Exit;
     Convert(Obj);
     RA_padlog:=0;
     DEC_padlog:=0;
     RA_reflog:=0;
     Dec_reflog:=0;
     CalError:=false;
     PosDirty:=True;
     posviolate:=false;   {signal valid org RA and Dec}
end;

procedure TogEast;
begin
     EastOfPier:=not EastOfPier;
     writeln('                                                                           ');
     write('EastOfPier is now:');
     if EastOfPier then
        writeln('ON                                                      ')
     else
         writeln('OFF                                                    ');
     GetFlexConstants;
     writeln('                                                                           ');
     writeln('Do a "Reset Position" now, to ensure flexure correction accuracy!          ');
     writeln('                                                                           ');
     delay(1000);
end;



Procedure JumpTo;
var AltErr,abort:boolean;
    DObj:ObjectRec;
    RAOffset,DecOffset:double;
    key:char;
    obname:string10;
begin
     MenuJump;
     key:=' ';
     repeat
           if keypressed and not (ButtonPressedRA or ButtonPressedDec) then
              begin
                   key:=readkey;
                   key:=Upcase(key);
                   case ord(key) of

                        ord('G'):
                                 begin
                                      clrscr;
                                      DObj:=FObj;
                                      GetInfo('Goto new coordinates:',DObj,abort);
                                      if (not abort) and (not HWlimit) then
                                         begin
                                              FObj:=DObj;
                                              Jump(IObj,FObj,SlewRate,AltErr);  {Goto new position}
                                              if AutoDome and (not AltErr) then
                                                 DomeMove(DomeCalcAzi(FObj));
                                              if AltErr then
                                                 begin
                                                      writeln('Object below Alt Limit');
                                                      { Sound(1000); }
                                                      Delay(1000);
                                                      { NoSound; }
                                                 end
                                              else
                                                  begin
                                                       DObj:=IObj;
                                                       IObj:=FObj;
                                                       FObj:=DObj;
                                                  end;
                                         end
                                      else
                                          MenuJump;
                                 end;

                        ord('N'):
                                 begin
                                      clrscr;
                                      Writeln('Goto Object by name in database:');
                                      DObj:=FObj;
                                      write('Enter Object name:');
                                      readln(obname);
                                      if DataLookup(obname,DObj,true) and (not HWlimit) then
                                         begin
                                              FObj:=DObj;
                                              Jump(IObj,FObj,SlewRate,AltErr);  {Goto new position}
                                              if AutoDome and (not AltErr) then
                                                 DomeMove(DomeCalcAzi(FObj));
                                              if AltErr then
                                                 begin
                                                      writeln('Object below Alt Limit');
                                                      { Sound(1000); }
                                                      Delay(1000);
                                                      { NoSound; }
                                                 end
                                              else
                                                  begin
                                                       DObj:=IObj;
                                                       IObj:=FObj;
                                                       FObj:=DObj;
                                                  end;
                                         end
                                      else
                                          MenuJump;
                                 end;

                        Ord('O'):
                                 begin
                                      clrscr;
                                      writeln;
                                      writeln('Offset by a given distance in arcseconds on the sky:');
                                      writeln('Enter East/West and North/South offsets:');
                                      msg:='East/West offset in arc-seconds, East = negative :  ';
                                      abort:=false;
                                      rddat(num,RAOffset,-LastRAOffset,msg,1,6,abort);
                                      if Abs(RAOffset)>7200 then
                                         abort:=true;
                                      if not abort then
                                         begin
                                              msg:='North/South offset in arc-seconds, South = negative:  ';
                                              rddat(num,DecOffset,-LastDecOffset,msg,1,7,abort);
                                              if Abs(DecOffset)>7200 then
                                                 abort:=true;
                                         end;
                                      if not abort and (not HWlimit) then
                                         begin
                                              DelRA:=20*RAOffset/Cos(IObj.DecC/3600*Pi/180);  {conv to motor steps}
                                              DelDec:=20*DecOffset;
                                              setprof(DelRA,DelDEC,SlewRate);  {Calculate the motor profile and jump}
                                              if (not posviolate) then
                                                 begin
                                                      IObj.RA:=IObj.RA+RAOffset/Cos(IObj.DecC/3600*Pi/180);
                                                      IObj.Dec:=IObj.Dec+DecOffset;
                                                 end;
                                              IObj.RaA:=IObj.RaA+RAOffset/Cos(IObj.DecC/3600*Pi/180);
                                              IObj.DecA:=IObj.DecA+DecOffset;
                                              IObj.RaC:=IObj.RaC+RAOffset/Cos(IObj.DecC/3600*Pi/180);
                                              IObj.DecC:=IObj.DecC+DecOffset;
                                              LastRAOffset:=RAOffset;
                                              LastDecOffset:=DecOffset;
                                         end
                                      else
                                          MenuJump;
                                 end;

                        ord('F'): Freeze;       {freeze tracking}
{$IFDEF NZ}
                        ord('H'): DomeHalt;     {Stop dome spinning}
{$ENDIF}
                        ord('M'): DomeAskMove;  {Move Dome to given position}
                        ord('A'):
                                 if (AutoDome and not ShutterInUse) then
                                    DomeMove(DomeCalcAzi(IObj))
                                 else
                                     begin
                                          writeln('Unable to Move Dome');
                                          { Sound(1000); }
                                          Delay(1000);
                                          { NoSound; }
                                     end;
                        ord('R'):
                                 begin
                                      DObj:=IObj;
                                      ResetPosition(DObj,abort);
                                      if not abort then
                                         IObj:=DObj;  {Reset initial position}
                                      if abort then
                                         MenuJump;
                                 end;
                        ord('S'): NonSidOn:=not NonSidOn;
                        ord('I'): TogEast;
{$IFDEF NZ}
                        ord('L'): LimOverride:=true;
{$ENDIF}
                   end; {of case}

                   MenuJump;

              end;   {of 'if keypressed...'}

           DetermineEvent;

     until (key = chr(27));   {Esc key pressed}
end;

begin
     lastRAOffset:=0;
     lastDecOffset:=0;
end.
