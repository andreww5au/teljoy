unit PDome;

{  Module: DomeControl.pas

   This module deals with the control and operation of the dome when
   running in either manual or automatic modes of operation.

   Created: 9201.1322          Modified: 9201.1322         Version: 1.00

   Written by: Malcolm Evans (Surak) for the Perth Observatory

   The source code below cannot be distributed without the authors or the
   Perth Observatory's permission.  All rights are retained by the
   aforementioned.

   The following procedures are contained within:

   DomeInitialise  -  Initialise dome control.
   DomeCheck       -  Check status of dome operation, and state of shutters.
   OpenDome        -  Open the dome's shutters.
   CloseDome       -  Close the domes shutters.
   MoveDome        -  Move the dome to the `desired' postion.

   Revision History
   ----------------
   Version       Modified            Reason for Modification
    1.00          9201.13         Initial procedures written.

}

{$N+ $E+}                                   {Use doubles, longint etc...}

interface


uses Globals;

const DomePort=2;

var DomeMoved,DomeInUse,ShutterInUse,ShutterOpen,DomeThere:boolean;
    AutoDome:boolean;
    DomeTracking:boolean;
    DomeStartTicks,DomeLastTicks:longint;
    NewDomeAzi:double;
    NewShutter:string[10];


Function DomeAzi:double;

Procedure DomeSetMode(var DomeMode:boolean); {Ask if dome on manual or auto mode}

Procedure DomeAskMove;   {Ask for new dome azimuth and go there}

Procedure DomeInitialise;

Procedure DomeOpen;

Procedure DomeClose;

Procedure DomeOpenWait(var OK:boolean);

Procedure DomeCloseWait(var OK:boolean);

Procedure DomeMove(Azi:double);   {Start dome move to given Azimuth}

Procedure DomeMoveWait(Azi:double);  {Move dome and wait for it to arrive}

Procedure DomeCheckMove;  {Check to see if dome has reached final pos.}

Procedure DomeCleanUp;

Procedure DomeHalt;    {allow external code to halt the dome motion}

Function DomeCalcAzi(Obj:ObjectRec):double; {returns dome Azi given object rec.}



implementation

uses Maths,DetEvent,CRT,Comm_vp,ReadIn,PC23int,DosIni;

Function DomeAzi:double;
begin
     DomeAzi:=NewDomeAzi;
end;

Procedure DomeHalt;
begin
end;

Procedure DomeSetMode(var DomeMode:boolean); {Ask if dome on manual or auto mode}
var an:char;
begin
     repeat
           clrscr;
           writeln;
           writeln('                     Dome Mode Inquiry');
           writeln;
           writeln(' Please check the state of the key switch for dome control.');
           writeln;
           write(' Is it set for  AUTOMATIC (y/n) ? ');
           readln(an);
           writeln;
           if (an = 'y') then
              begin
                   writeln('Dome Mode : AUTOMATIC');
                   DomeMode:=true;
              end
           else
               begin
                    writeln('Dome Mode : MANUAL');
                    DomeMode:=false;
               end;
           writeln;
           writeln;
           write('Is this information correct (y/n) ? ');
           readln(an);
     until (an='y');
end;


Procedure DomeAskMove;   {Ask for new dome azimuth and go there}
var  Azi:integer;
     tmpAzi,tmpDef:double;
     abort:boolean;

begin
     clrscr;
     msg:='Move to (Dome Azimuth) (0-360):';
     tmpDef:=DomeCalcAzi(IObj);
     repeat
           rddat(num,tmpAzi,tmpDef,msg,1,3,abort);
           if abort then
              System.Exit;
           Azi:=Round(tmpAzi);
     until ((Azi >=0 ) and (Azi <=360));
     if (AutoDome and not (DomeInUse or ShutterInUse)) then
        DomeMove(Azi)
     else
         begin
              writeln('Unable to Move Dome');
              { sound(1000); }
              Delay(1000);
             { NoSound; }
         end;
end;   {Of DomeAskMove}


Function DomeCalcAzi(Obj:ObjectRec):double;
 const Rd=3.48;                             {Dome radius}
       absp=0.55/Rd;                           {Dist from centre of tube to dome center}
       eta=0.2/Rd;
 var x0,y0,z0,ha,ObjRA,AziRad,AltRAd,Azi:double;
     a,b,c,Aye,Bee,Cee,Alpha,Beta:double;
     Exx1,Why1,Zee1,Exx2,Why2,Zee2,p:double;
 begin
   if EastofPier then
      p:=-absp
   else
       p:=absp;
   ObjRA:=Obj.RA/54000;                     {in hours}
   AziRad:=DegToRad(Obj.Azi);
   AltRad:=DegToRad(Obj.Alt);
   ha:=DegToRad((Obj.Time.LST-ObjRA)*15);   {in rads}

   y0:=-p*sin(ha)*sin(DegToRad(ObsLat));      {N-S comp. of scope centre disp.}
   x0:=p*cos(ha);                            {E-W comp. of scope centre disp. from dome centre}
   z0:=eta-p*sin(ha)*cos(DegToRad(ObsLat));

   a:=-cos(AltRad)*sin(AziRad);
   b:=-cos(AltRad)*cos(AziRad);
   c:=sin(AltRAd);

   Alpha:=(a*a+c*c)/(b*b);
   Beta:=2*(a*x0+c*z0)/b;

   Aye:=Alpha+1;
   Bee:=Beta-2*Alpha*y0;
   Cee:=+(Alpha*y0*y0 - Beta*y0 + x0*x0 + z0*z0 - 1);

   Why1:=( -Bee + Sqrt(Bee*Bee-4*Aye*Cee) )/(2*Aye);
   Exx1:=((Why1-y0)*a/b+x0);
   Zee1:=(Why1-y0)*c/b+z0;

   Why2:=( -Bee - Sqrt(Bee*Bee-4*Aye*Cee) )/(2*Aye);
   Exx2:=((Why2-y0)*a/b+x0);
   Zee2:=(Why2-y0)*c/b+z0;


   if Zee1>0 then
      Azi:=RadToDeg(ArcTan2(Exx1,Why1))
   else
       Azi:=RadToDeg(ArcTan2(Exx2,Why2));

   Azi:=Azi+180;

   if (Azi > 360) then
     Azi:=Azi-360;

   DomeCalcAzi:=Azi;
 end;


Function WaitPrompt:boolean;
var c:char;
    gots:string[20];
    missed:integer;
begin
   missed:=0;
   gots:=' ';
   repeat
         c:=' ';
         if TimedReadCom(DomePort,c) then
            gots:=gots+c
         else
             missed:=missed+1;
   until missed>1;

   if Pos('?',gots) = 0 then
      begin
           EmptyBuffer(DomePort,true);
           WriteCom(DomePort,chr(13));
           Delay(200);
           WaitPrompt:=false;
      end
   else
       begin
            WaitPrompt:=true;
            delay(300);
       end;
end;


Procedure DomeInitialise;
 var c:char;
     err:integer;
 begin
   SetUpComPort(DomePort,4,8,0,2);
   DomeInUse:=false;
   DomeThere:=true;
   ShutterInUse:=false;
   NewShutter:='';
 end;


Procedure DomeMove(Azi:double);
var Azstr:string40;
begin
     if not AutoDome then
        begin
             eWrite('Dome not in auto mode.');
             system.exit;
        end;
     if DomeInUse or ShutterInUse then
        begin
             wWrite('Dome or shutter active - wait for it to finish...');
             system.exit;
        end;

     NewDomeAzi:=Azi;
     DomeInUse:=true;
     DomeThere:=false;
     DomeMoved:=false;
     if WaitPrompt then
        begin
             DomeMoved:=true;
             Str(Azi:0:0,Azstr);
             WriteCom(DomePort,Azstr);
        end;
end;

Procedure DomeCheckMove;
var azstr:string40;
begin
     if DomeInUse then
        begin
             if DomeMoved then
                DomeThere:=WaitPrompt
             else
                 if WaitPrompt then
                    begin
                         DomeMoved:=true;
{                         writeln('Sending Azi to dome...');     }
                         Str(NewDomeAzi:0:0,Azstr);
                         WriteCom(DomePort,Azstr);
                    end;
             if DomeThere then
                begin
                     DomeInUse:=false;
                     DomeLastTicks:=Ticks;
{                     Writeln('Dome Move Completed- Dome Azi Now:',NewDomeAzi:0:0);
}
                end;
        end;
     if ShutterInUse then
        begin
             if DomeMoved then
                DomeThere:=WaitPrompt
             else
                 if WaitPrompt then
                    begin
                         DomeMoved:=true;
{                         writeln('Sending Command to shutter...');    }
                         WriteCom(DomePort,NewShutter+Chr(13));
                    end;
             if DomeThere then
                begin
                     ShutterInUse:=false;
{                     Writeln('Shutter Move Completed- Now:'+NewShutter);   }
                end;
        end;


end;


Procedure DomeOpen;
begin
     if not AutoDome then
        begin
             eWrite('Dome not in auto mode.');
             system.exit;
        end;
     if DomeInUse or ShutterInUse then
        begin
             wWrite('Dome or shutter active - wait for it to finish...');
             system.exit;
        end;

     NewShutter:='O';
     ShutterOpen:=true;
     ShutterInUse:=true;
     DomeThere:=false;
     DomeMoved:=false;
     if WaitPrompt then
        begin
             DomeMoved:=true;
             WriteCom(DomePort,'O'+chr(13));
        end;
end;


Procedure DomeClose;
var c,oldc:char;
begin
     if not AutoDome then
        begin
             eWrite('Dome not in auto mode.');
             system.exit;
        end;
     if DomeInUse or ShutterInUse then
        begin
             wWrite('Dome or shutter active - wait for it to finish...');
             system.exit;
        end;

     NewShutter:='C';
     ShutterOpen:=false;
     ShutterInUse:=true;
     DomeThere:=false;
     DomeMoved:=false;
     if WaitPrompt then
        begin
             DomeMoved:=true;
             WriteCom(DomePort,'C'+chr(13));
        end;
end;

Procedure DomeOpenWait(var OK:boolean);
begin
     DomeOpen;
     GotoXY(1,4);
     writeln('Waiting for shutter:');
     repeat
           DetermineEvent;
     until not ShutterInUse;
     OK:=true;
     GotoXY(1,4);
     writeln('                                ')
end;

Procedure DomeCloseWait(var OK:boolean);
begin
     DomeClose;
     GotoXY(1,4);
     writeln('Waiting for shutter:');
     repeat
           DetermineEvent;
     until not ShutterInUse;
     OK:=true;
     GotoXY(1,4);
     writeln('                           ');
end;

Procedure DomeMoveWait(Azi:double);
begin
     DomeMove(Azi);
     GotoXY(1,4);
     writeln('Waiting for dome:');
     repeat
           DetermineEvent;
     until not DomeInUse;
     GotoXY(1,4);
     writeln('                           ');
end;


Procedure DomeCleanUp;
 begin
   RemoveInt(DomePort);
 end;

begin
     DomeLastTicks:=0;
     DomeTracking:=i2b(GetProfileInt(Inif,'Toggles','DomeTracking',0));
end.
