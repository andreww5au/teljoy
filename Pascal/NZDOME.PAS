unit NZDome;

interface

uses Globals;

const DomePort=2;     {Serial port for dome encoder}
      MaxDomeMove=300000;   {Milliseconds of dome travel time before}
                            {A a dome-failure timeout occurs}

var DomeInUse,ShutterInUse:boolean;
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

uses DigIO,Maths,DetEvent,CRT,Comm_vp,ReadIn,PC23int,DosINI;

Procedure DomeSetMode(var DomeMode:boolean); {Ask if dome on manual or auto mode}
var an:char;
begin
     clrscr;
     writeln;
     writeln('                     Dome Mode Inquiry');
     writeln;
     writeln(' Move Dome automatically?');
     writeln;
     repeat
     until keypressed;
     an:=ReadKey;
     if (an='y') or (an='y') then
        DomeMode:=true;
end;  {Of DomeSetMode}

Function GrayToBin(t:byte):byte;   {Converts 8 bit Gray code value from}
var b:byte;                        {dome to flat binary}
begin
     b:=0;
     while t<>0 do
           begin
                b:=b xor t;
                t:=t shr 1;
           end;
     GrayToBin:=b;
end;

Function DomeAzi:double;   {Return current Dome azimuth from encoder}
var Data:char;
begin
     EmptyBuffer(DomePort,true);      {Empty dome input buffer to get}
                                      {most recent position}
     if TimedReadCom(DomePort,Data) then
        DomeAzi:=GrayToBin(ord(Data))/256*360      {Convert to degrees}
     else
         DomeAzi:=-1;
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
     if AutoDome and (not ShutterInUse) then
        DomeMove(Azi)
     else
         begin
              writeln('Unable to Move Dome');
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
end;  {Of DomeCalcAzi}


Procedure DomeInitialise;
var c:char;
    err:integer;
begin
     SetUpComPort(DomePort,7,8,0,1);
     DomeInUse:=false;
     ShutterInUse:=false;
     NewShutter:='';
end;

Procedure DomeMove(Azi:double);
begin
     NewDomeAzi:=Azi;
     DomeInUse:=true;
     DomeStartTicks:=Ticks;
end;

Procedure DomeHalt;
begin
     DomeStop;     {Stop the dome motion}
     DomeInUse:=false;    {Indicate move finished so it doesn't restart}
     DomeLastTicks:=Ticks;
end;

Procedure DomeCheckMove;
var CurAz:double;
begin
     CurAz:=DomeAzi;     {Azi of -1 if no response from encoder}
     if DomeInUse then
        if (Abs(CurAz-NewDomeAzi) < 2.5) or (CurAz < 0) or
         (Ticks-DomeStartTicks > MaxDomeMove) then
           begin
                DomeStop;
                DomeInUse:=false;
                DomeLastTicks:=Ticks;
           end
        else
            if (NewDomeAzi > CurAz) then
               if (NewDomeAzi-CurAz < 180) then
                  DomeRight
               else
                   DomeLeft
            else
                if (CurAz-NewDomeAzi < 180) then
                   DomeLeft
                else
                    DomeRight;
end;


Procedure DomeOpen;
begin
end;


Procedure DomeClose;
begin
end;

Procedure DomeOpenWait(var OK:boolean);
begin
end;

Procedure DomeCloseWait(var OK:boolean);
begin
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
