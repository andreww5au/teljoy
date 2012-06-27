{$N+$E+}
unit DetEvent;
interface

Procedure DetermineEvent;

implementation

uses Dosini,Globals,SetPro,Crt,ObjList,PC23int,PC23IO,DigIO,Use32,Time, SQLInt,JumpCont,Database,Automate,
{$IFDEF NZ}
NZdome;
{$ELSE}
Pdome;
{$ENDIF}

const
    Dead_Band = 20;                         {Encoder dead band}

type
    FineModes   = (FGuide,FSet);
    CoarseModes = (CSlew,CSet,CGuide);
    RaDirections= (fineWest,fineEast,coarseWest,coarseEast);
    DecDirections=(fineNorth,fineSouth,coarseNorth,coarseSouth);
    Axes        = (Ra,Dec,Dual);
    Paddles     = (Fine,Coarse);
    Cardinal    = 0..maxint;


var
   poslog:text;                            {current position file}
   LogDirName:string;

   CoarseB,FineB,ControlB:Byte;            {Bytes containing the status
                                                  of the two paddles}

   MaskC,MaskF:Byte;

   FineMode:FineModes;                     {Current mode of fine paddle whether
                                             set for Guide or Set}
   CoarseMode:CoarseModes;                 {Current mode of coarse paddle whether
                                             set for Slew or Set}
   RaDir:RaDirections;                     {Current RA Axis direction}
   DecDir:DecDirections;                   {Current DEC axis direction}
   ChangedDir:boolean;                     {Has an axis changed direction}
   Axis:Axes;                              {What axis}
   ChangedAxis:boolean;                    {Have we changes axis}
   StoppedRa:boolean;
   Paddle:Paddles;
   paddle_max_vel:double;                  {current paddle vel, in rev/sec}
   WaitBeforePosUpdate:integer;            {milliseconds before dome moves}
                                              {to new telescope position}
                                              {when dome-tracking is on}
   MinWaitBetweenDomeMoves:integer;       {min time between dome-tracking}
                                           {moves, in milliseconds}

   DBLastTicks,LimitOffTicks,LimitOnTicks:longint;
   ProspLastTicks:longint;    {tick value the last time we saw a TJbox}

   RA_GuideAcc,DEC_GuideAcc:double;
   TJboxAction:TJaction;

Procedure UpdatePosFile(var Here:ObjectRec);

    procedure FWritelnDMS(var f:text;strn:string40;r:double);
    var d,m,s:double;
    begin
         Write(f,strn);

         ConvDMS(r,d,m,s);

         if d<>0 then    {if d=0 then keep m,s negative}
            begin
                 m:=Abs(m);
                 s:=Abs(s);
            end;

         if (r<0) then
            write(f,'-');
         Writeln(f,Abs(d):0:0,' ',m:0:0,' ',s:0:1);

    end;



var thour,tmin,tsec,thund,dday,dmon,dyear:integer;
begin
      GetSysTime(thour,tmin,tsec,thund);
      GetSysDate(dday,dmon,dyear);
{$I-}
      rewrite(poslog);
{$I+}
      if IOResult <> 0 then
         writeln('(detevent L99) Path not found - probably logged into network incorrectly')
      else
          begin
               writeln(poslog,'ID:      ',Here.ID);
               FWritelnDMS(poslog,'Cor. RA: ',Here.RaC/15);
               FWritelnDMS(poslog,'Cor. Dec:',Here.DecC);
               writeln(poslog,'SysT:    ',thour,' ',tmin,' ',tsec,'.',thund);
               writeln(poslog,'Sys_Date:',dday,' ',dmon,' ',dyear);
               writeln(poslog,'Jul Day: ',Here.Time.JD:0:7);
               FWritelnDMS(poslog,'LST:     ',Here.Time.LST*3600);
               close(poslog);
          end;
end;

Procedure UpdatePos;  {Update RA and Dec from paddle and refraction motion}
begin
    {disable the interrupt to stop position log variables from being}
    {changed at interrupt time partway through update}

    {invalidate orig RA and Dec if paddle or non-sidereal move}
      if (RA_padlog<>0) or (Dec_padlog<>0) then
         posviolate:=true;

    {account for paddle and non-sid. motion, and limit encounters}
      IObj.RaA:=IObj.RaA+RA_padlog/20;
      IObj.DecA:=IObj.DecA+Dec_padlog/20;

    {above, plus real-time refraction+flexure+guide in the fully corrected coords}
      IObj.RaC:=IObj.RaC+RA_padlog/20 + RA_reflog/20 + RA_Guidelog/20;
      IObj.DecC:=IObj.DecC+Dec_padlog/20 + Dec_reflog/20 + DEC_Guidelog/20;

      RA_guideAcc:=RA_guideAcc + RA_Guidelog/20;
      DEC_guideAcc:=DEC_guideAcc + DEC_Guidelog/20;

      RA_padlog:=0;
      RA_reflog:=0;
      Dec_padlog:=0;
      Dec_reflog:=0;
      RA_guidelog:=0;
      DEC_guidelog:=0;

      if IObj.RaA > (24*60*60*15) then
         IObj.RaA:=IObj.RaA - (24*60*60*15);
      if IObj.RaA < 0 then
         IObj.RaA:=IObj.RaA + (24*60*60*15);

      if IObj.RaC > (24*60*60*15) then
         IObj.RaC:=IObj.RaC - (24*60*60*15);
      if IObj.RaC < 0 then
         IObj.RaC:=IObj.RaC + (24*60*60*15);

end;



Procedure ShowStatus;
var lb:byte;    {Dump - used for debugging}
    tmpd:double;
begin
     TextBackground(Red);
     TextColor(yellow);
     Window(1,1,80,6);

     GotoXY(1,1);
     Write('Top RA:  ');
     WriteDMS(IObj.RaC/15);
     GotoXY(21,1);
     if EastOfPier then
        write('INV ')
     else
         write('    ');

     GotoXY(1,2);
     Write('Top Dec: ');
     WriteDMS(IObj.DecC);

     GotoXY(1,3);
     Write('Alt: ');
     WriteDMS(Iobj.Alt*3600);

     GotoXY(1,4);
     Write('Airmass: ');
     Write(1/Cos((90-Iobj.Alt)/180*Pi):0:4);

     GotoXY(25,1);
     Write('LST: ');
     WriteDMS(Iobj.Time.LST*3600);

     GotoXY(25,2);
     Write('UT: ');
     WriteDMS(IObj.Time.UTdec*3600);

     GotoXY(25,3);
     Write('HA: ');
     tmpd:= IObj.RaC/54000-IObj.Time.LST;
     if tmpd < -12 then
        tmpd:=tmpd+24;
     if tmpd > 12 then
        tmpd:=tmpd-24;
     Write(tmpd:0:4,' hr   ');

     GotoXY(50,1);
     Write('Obj ID: ',IObj.ID,'           ');

     GotoXY(50,2);
     if (not posviolate) and AutoRunning then
        Write('Obj Num: ',CurNum,' of ',NumRead)
     else
         write('                            ');

     GotoXY(25,4);
     write('NonSidereal: ');
     if NonSidOn then
        write('ON  ')
     else
         write('OFF ');

     GotoXY(25,5);
     write('Frozen:');
     if Frozen then
        write('Yes  ')
     else
         write('No  ');


     GotoXY(1,5);
     write('Moving:');
     if moving then
        write('Yes ')
     else
         write('No ');

     GotoXY(1,6);
     Write('Dome:');
     if (DomeInUse or ShutterInUse) then
        write('Active   ')
     else
         write('Inactive');

     GotoXY(25,6);
     write('Dome Tracking:');
     if DomeTracking then
        write('ON ')
     else
         write('OFF');

     GotoXY(50,3);
     Write('Obj RA: ');
     if (not posviolate) then
        WriteDMS(IObj.Ra/15)
     else
         write('               ');

     GotoXY(50,4);
     Write('Obj Dec: ');
     if (not posviolate) then
        WriteDMS(IObj.Dec)
     else
         write('               ');

     GotoXY(50,5);
     Write('Obj Epoch: ');
     if (not posviolate) then
        Write(IObj.Epoch:0:3)
     else
         write('               ');

     GotoXY(50,6);
{$IFDEF NZ}
     Write('HW status: ');
{     ReadLimit(lb);
     write(lb,' '); }

     if PowerOff then
             write('Power Off.     ')
     else if MeshLim then
             write('Mesh Out.      ')
     else if HorizLim then
             write('Horizon cut.   ')
     else if EastLim then
             write('East Limit.    ')
     else if WestLim then
             write('West Limit.    ')
     else
             write('               ');
     GotoXY(75,6);
     if LimOverride then
        write('OVER!')
     else write('     ');
{$ELSE}
     Write('G ',GuideDebug:0,'  ',RA_GuideAcc:0:2,'", ',DEC_GuideAcc:0:2,'"   ');
{$ENDIF}

     Window(1,7,80,25);
     TextBackground(black);
     TextColor(lightGray);
end;


procedure ShowErrors;
var tone:integer;
begin
    tone:=0;
    Watchdog:=Watchdog+1;   {increment watchdog timer}
    GotoXY(1,1);
    if CalError or RefError or AltError or (WatchDog>100) then
       begin
            write('Errors:                                                                  ');
            GotoXY(9,1);
       end;
    if CalError then
       begin
            tone:=tone+250;
            Write('**Teljoy Calibration Error - Reset Position!**  ');
       end;
    if RefError then
       begin
            tone:=tone+1000;
            write('**Refrac velocity**  ');
       end;
    if AltError then
       begin
            tone:=tone+2000;
            write('**Object too LOW**  ');
       end;
    if Watchdog>100 then
       begin
            tone:=tone+2500;
            write('**Interrupt lost** ');
       end;


    if tone>0 then
       { Sound(tone) }
    else
        begin
         {  NoSound; }
          GotoXY(1,1);
          writeln('                                                                             ');
        end;


end;

procedure CheckDirtyPos;

begin
     if PosDirty and (DirtyTicks=0) then
        DirtyTicks:=Ticks;                 {just finished move}

     if (DirtyTicks<>0) and
        (Ticks-DirtyTicks > WaitBeforePosUpdate) and not Moving then
        begin
             UpdatePosFile(IObj);
             DirtyTicks:=0;
             PosDirty:=false;
             RA_GuideAcc:=0;
             DEC_GuideAcc:=0;
        end;
end;



Procedure CheckDirtyDome;

begin
     if (Abs(DomeCalcAzi(IObj)-DomeAzi) > 6) and
        ((Ticks-DomeLastTicks) > MinWaitBetweenDomeMoves) and
        (not DomeInUse) and
        (not ShutterInUse) and
        DomeTracking and
        (not Moving) and
        AutoDome and
        (not PosDirty) then
             DomeMove(DomeCalcAzi(IObj));

end;

procedure CheckDBUpdate;
var Current:CurrentInfo;
begin
     if (Ticks-DBLastTicks)>1000 then
        begin
             Current.posviolate:=posviolate;
             Current.moving:=moving;
             Current.EastOfPier:=EastOfPier;
             Current.NumRead:=NumRead;
             Current.CurNum:=CurNum;
             Current.NonSidOn:=NonSidOn;
             Current.DomeInUse:=DomeInUse;
             Current.ShutterInUse:=ShutterInUse;
             Current.ShutterOpen:=ShutterOpen;
             Current.DomeTracking:=DomeTracking;
             Current.Frozen:=Frozen;
             Current.AutoRunning:=AutoRunning;
             Current.RA_GuideAcc:=RA_GuideAcc;
             Current.Dec_GuideAcc:=Dec_GuideAcc;
             Current.LastError:=LastError;
             UpdateSQLCurrent(Iobj,Current);
             DBLastTicks:=Ticks;
        end;
end;


procedure DoTJbox;
var
   DObj:ObjectRec;
   other:TJboxrec;
   LastMod:integer;
   action:TJaction;
   RAOffset,DecOffset:double;
   AltErr:boolean;

begin
     DObj:=FObj;
     action:=ReadTJBox(DObj,other,LastMod);
     ProspLastTicks:=Ticks;
     if (LastMod<0) or (LastMod>5) or moving then
        begin
             action:=none;
{            eWrite('Remote control command ignored.');  }
        end;
     case action of
          error,none:
                 begin
                      ClearTJbox;
                      TJboxAction:=none;
                 end;
          jumpID:
                 begin
                      if DataLookup(DObj.ID,DObj,false) and (not HWlimit) then
                         begin
                              Jump(IObj,DObj,SlewRate,AltErr);  {Goto new position}
                              if AutoDome and (not AltErr) then
                                 DomeMove(DomeCalcAzi(DObj));
                              if AltErr then
                                 eWrite('Object in TJbox below Alt Limit')
                              else
                                  begin
                                       FObj:=IObj;
                                       IObj:=DObj;
                                  end;
                         end;
                      TJboxAction:=action;
                 end;

          jumpRD:
                 begin
                      Jump(IObj, DObj, SlewRate, AltErr);
                      if AutoDome and (not AltErr) then
                         DomeMove(DomeCalcAzi(DObj));
                      if AltErr then
                         eWrite('Object in TJbox below Alt Limit')
                      else
                          begin
                               FObj:=IObj;
                               IObj:=DObj;
                          end;
                      TJboxAction:=action;
                 end;

          jumpAA:
                 begin
                      ClearTJbox;
                      eWrite('Remote control command not supported.');
                 end;

          nonsid:
                 begin
                      ClearTJbox;
                      eWrite('Remote control command not supported.');
                 end;

          offset:
                 begin
                      RAOffset:=other.OffsetRA;
                      DecOffset:=other.OffsetDec;
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
                      TJboxAction:=action;
                 end;
          dome:
               begin
                    if other.DomeAzi<0 then
                       DomeMove(DomeCalcAzi(IObj))
                    else
                        DomeMove(other.DomeAzi);
                    TJboxAction:=action;
               end;
          shutter:
               begin
                    if other.shutter then
                       DomeOpen           {True for open}
                    else
                        DomeClose;
                    TJboxAction:=action;
               end;
          freez:
               begin
                    if other.freeze then
                       Frozen:=true
                    else
                        Frozen:=false;
                    TJboxAction:=none;    {Action complete}
                    ClearTJbox;
               end;
     end;  {of case}
end;  {Of DoTJbox}


Procedure CheckTJBox;
begin
     case TJBoxAction of
          none:
               if ExistsTJbox then
                  DoTJbox;
          jumpID,jumpRD,jumpAA,offset:
               if (not moving) and (not DomeInUse) then
                  begin
                       TJboxAction:=none;
                       ClearTJbox;
                  end;
          dome:
               if not DomeInUse then
                  begin
                       TJboxAction:=none;
                       ClearTJbox;
                  end;
          shutter:
               if not ShutterInUse then
                  begin
                       TJboxAction:=none;
                       ClearTJbox;
                  end;
     end;  {of case}
end;  {of CheckTJbox}


Procedure CheckTimeout;
begin
     if ((Ticks-ProspLastTicks) > 600000) and ShutterOpen and (not ShutterInUse) then
        begin
             eWrite('No communication with Prosp for over 10 minutes!');
             eWrite('Closing Shutter, Freezing Telescope.');
             DomeClose;
             Frozen:=true;
        end;
end;

Procedure CheckLimits;
begin
     if Frozen then
        posviolate:=true;

     if (not OldLim) and (HWlimit) then
        begin
             Frozen:=true;

             DomeHalt;
             LimitOnTicks:=Ticks;
             LimitOffTicks:=MaxLongInt;

             OldLim:=true;
        end;

     if (not PowerOff) and (not HorizLim) and (not MeshLim) and
       (not moving) and (not EastLim) and (not WestLim) and HWlimit then
        begin
             Frozen:=false;

             OldLim:=false;
             HWLimit:=false;
             LimOverride:=false;
        end;
end;

function CanEast:boolean;
begin
     CanEast:=(not HWlimit) or (LimOverride and WestLim);
end;

function CanWest:boolean;
begin
     CanWest:=(not HWlimit) or (LimOverride and EastLim);
end;


Procedure DetermineEvent;
{The new version of determine event
      (1) Calculate real-time refraction corr.
      (2) Read the encoders
      (3) Update status box
      (4) Test and indicate Error conditions
      (5) Check if position log needs updating
      (6) Check if dome needs to track telescope
      (7) Check progress of any dome activity
      (8) Read Hand Paddles.        }

var
     cb,fb:byte;                  {coarse paddle byte,fine paddle byte & spare byte}

begin

    UpdatePos;      {add all motion to current IObj coordinates}
    RelRef(IObj);   {calculate refrac velocity correction, check for}
                    {altitude too low and set 'AltError' if true}
    ShowStatus;     {Update status window at top of screen}
    ShowErrors;     {Beep and indicate if an error condition is active}
    CheckDirtyPos;  {Check to see if dynamic position file needs updating}
    CheckDirtyDome; {Check to see if domw needs moving if DomeTracking is on}
    DomeCheckMove;  {Check to see if dome has reached destination azimuth}
    CheckLimits;    {Test to see if any hardware limits are active}
    CheckDBUpdate;  {Update database at intervals}
    CheckTJbox;     {Look for a TJbox entry for automatic control events}
    CheckTimeout;   {Check to see if Prosp is still alive and monitoring weather}
    ReadMail;       {Look for a mailbox from VISTA and log it if found}


    {Read the Hand-paddle inputs}
    ReadCoarse(cb);
    ReadFine(fb);


    {* Check the fine paddle by comparing fb to a set of masks}
    if (FineMode<>FGuide) then   {Ignore fine guide motion, its handled by the
                                  54ms clock tick interrupt for lower latency}
       begin

            if ((fb and FNorth)=FNorth) then        {Compare with the north mask}
               begin
                    if not ButtonPressedDec then          {The button has just been pressed}
                       begin
                            ButtonPressedDec:=true;
                            Decdir:=fineNorth;
                            Paddle_max_vel:=(FineSetRate)/25000;
                            start_motor(false,paddle_max_vel);
                       end;
               end
            else if ButtonPressedDEC and (Decdir=fineNorth) then
              {Mask does not match but the motor is running}
                 begin
                      ButtonPressedDEC:=false;
                      Stop_motor(False);
                 end;

            if ((fb and FSouth)=FSouth)then            {Check with South Mask}
               begin
                    if not ButtonPressedDec then
                       begin
                            ButtonPressedDec:=true;
                            DecDir:=fineSouth;
                            Paddle_max_vel:=-(FineSetRate)/25000;
                            Start_motor(False,paddle_max_vel);
                       end;
               end
            else if ButtonPressedDEC and (DecDir=fineSouth) then
                    {Mask does not match but the motor is running}
                 begin
                      ButtonPressedDEC:=false;
                      Stop_motor(False);
                 end;

            if ((fb and FEast)=FEast) then              {Check the Eastmask}
               begin
                    if (not ButtonPressedRA) and CanEast then
                       begin
                            ButtonPressedRA:=true;
                            RAdir:=fineEast;
                            Paddle_max_vel:=(FineSetRate)/25000;
                            Start_motor(True,paddle_max_vel);
                       end;
               end
            else if ButtonPressedRA and (RADir=fineEast) then
                    {Mask does not match but the motor is running}
                 begin
                      ButtonPressedRA:=false;
                      Stop_motor(true);
                 end;


            if ((fb and FWest)=FWest) then               {Check the West mask}
               begin
                    if (not ButtonPressedRA) and CanWest then
                       begin
                            ButtonPressedRA:=true;
                            RaDir:=fineWest;
                            Paddle_max_vel:=-(FineSetRate)/25000;
                            Start_motor(true,paddle_max_vel);
                       end;
               end
            else if ButtonPressedRA and (RaDir=fineWEST) then
                    {Mask does not match but the motor is running}
                 begin
                      ButtonPressedRA:=false;
                      Stop_motor(true);
                 end;
       end;    {Of masking out the guide rate motions}

    if ((fb and FGuideMsk)=FGuideMsk) then           {check the rate switches}
        FineMode:=FGuide
    else
        FineMode:=FSet;

 {**Check the Coarse paddle by comparing cb to a set of masks}
    if ((cb and CNorth)=CNorth) then
      begin
           if not ButtonPressedDec then
             begin
                  ButtonPressedDec:=true;
                  DecDir:=CoarseNorth;
                  if (CoarseMode = CSlew) then
                     Paddle_max_vel:=(SlewRate)/25000
                  else
                      if (CoarseMode = CSet) then
                         Paddle_max_vel:=(CoarseSetRate)/25000
                      else
                          Paddle_max_vel:=(GuideRate)/25000;

                  Start_motor(false,paddle_max_vel);
             end;
      end
         else
             if ButtonPressedDec and (DecDir=CoarseNorth) then
        {Mask does not match but the motor is running}
                begin
                     ButtonPressedDEC:=false;
                     Stop_motor(false);
                end;

    if ((cb and CSouth)=CSouth) then
       begin
            if not ButtonPressedDec then
               begin
                    ButtonPressedDec:=true;
                    Decdir:=CoarseSouth;
                    if (CoarseMode = CSlew) then
                       Paddle_max_vel:=-(SlewRate)/25000
                    else
                        if (CoarseMode = CSet) then
                           Paddle_max_vel:=-(CoarseSetRate)/25000
                        else
                            Paddle_max_vel:=-(GuideRate)/25000;

                    Start_motor(false,paddle_max_vel);
               end;
       end
    else
        if ButtonPressedDEC and (DecDir=CoarseSouth) then
            {Mask does not match but the motor is running}
           begin
                ButtonPressedDEC:=false;
                Stop_motor(False);
           end;

    if ((cb and CEast)=CEast) then
       begin
            if (not ButtonPressedRA) and CanEast then
               begin
                    ButtonPressedRA:=true;
                    RaDir:=CoarseEast;
                    if (CoarseMode = CSlew) then
                       Paddle_max_vel:=(SlewRate)/25000
                    else
                        if (CoarseMode = CSet) then
                           Paddle_max_vel:=(CoarseSetRate)/25000
                        else
                            Paddle_max_vel:=(Guiderate)/25000;

                    Start_motor(true,paddle_max_vel);
               end;
       end
    else
        if ButtonPressedRA and (RaDir=CoarseEast) then
        {Mask does not match but the motor is running}
           begin
                ButtonPressedRA:=false;
                Stop_motor(True);
           end;


    if ((cb and CWest)=CWest) then
       begin
            if (not ButtonPressedRA) and CanWest then
               begin
                    ButtonPressedRA:=true;
                    RaDir:=CoarseWest;
                    if (CoarseMode = CSlew) then
                       Paddle_max_vel:=-(SlewRate)/25000
                    else
                        if (Coarsemode = CSet) then
                           Paddle_max_vel:=-(CoarseSetRate)/25000
                        else
                            Paddle_max_vel:=-(GuideRate)/25000;

                    Start_motor(true,paddle_max_vel);
               end;
       end
    else
        if ButtonPressedRA and (RaDir=CoarseWest) then
           {Mask does not match but the motor is running}
           begin
                ButtonpressedRA:=false;
                Stop_motor(true);
           end;

{$IFDEF NZ}
    if ((cb and CspaMsk)=CspaMsk) and ((cb and CspbMsk)=CspbMsk) then
      CoarseMode:=CSet
    else
      if ((cb and CspbMsk)=CspbMsk) then
         CoarseMode:=CGuide
      else
          CoarseMode:=CSlew;
{$ELSE}
    if ((cb and CSlewMsk)=CSlewMsk) then
      CoarseMode:=CSlew
    else
      CoarseMode:=CSet;
{$ENDIF}

delay(50);

 end;

begin  {Unit initialisation}
     writeln('Detevent unit init started');
     WaitBeforePosUpdate:=GetProfileInt(Inif,'Dome','WaitTime',100);
     MinWaitBetweenDomeMoves:=GetProfileInt(Inif,'Dome','MinBetween',5000);
     LogDirName:=GetProfileStr(Inif,'Paths','LogDirName','C:\logs');
     assign(poslog,LogDirName+'\teljoy.pos');
     ProspLastTicks:=Ticks;
     DBLastTicks:=0;
     RA_GuideAcc:=0;
     DEC_GuideAcc:=0;
     TJboxAction:=none;
     writeln('Detevent unit init finished');
end.
