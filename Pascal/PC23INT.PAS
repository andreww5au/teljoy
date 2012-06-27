{$S-}
{$F+}
{$N-}
{$E-}

unit PC23int;


interface

Uses
  Dos, PC23io, Crt, Use32, VPUtils, Os2Def, Os2Base;

const motor_accel=2.0;
      pulse=0.05;
      PowerMsk   = $01;
      HorizMsk   = $02;
      MeshMsk    = $04;
      EastMsk    = $08;
      WestMsk    = $10;

procedure InstallInt;
procedure KickStart;


var
   hexstr:array[0..15] of char;

   RAsid:double;
   RA_track:double;    {RA Non-sidereal tracking velocity - steps/50ms}
   DEC_track:double;   {as for RA}
   RA_jump:double;     {jump velocity in RA - steps/50ms}
   DEC_jump:double;    {as for DEC}
   RA_remain:double;   {remainder in RA - used in telescope jump}
   DEC_remain:double;  {remainder in DEC - used in telescope jump}
   int_RA:integer;   {integer part of send_RA, the distance to move in this 50ms tick}
   int_DEC:integer;  {as for RA}
   frac_RA:double;     {fractional part of send_RA}
   frac_DEC:double;    {as for RA}
   RA_hold:integer;  {Used to delay one 50ms pulse value if direction changes}
   DEC_hold:integer;  {as for RA}
   RA_up:longint;    {number of 50ms ticks to ramp motor to max velocity}
   RA_plateau:longint; {number of 50ms ticks in the plateau of an RA jump}
   RA_down:longint;  {number of 50ms ticks to ramp motor down after RA jump}
   DEC_up:longint;     {as for RA}
   DEC_plateau:longint;  {as for RA}
   DEC_down:longint;     {as for RA}
   max_vel:double;     {maximum motor velocity in steps/50ms}
   RA_max_vel:double;  {plateau velocity in RA in steps/50ms}
   DEC_max_vel:double; {as for RA}
   paddle_start_RA:boolean;  { true if RA paddle button pressed}
   paddle_stop_RA:boolean;   { true if RA paddle button released}
   paddle_start_DEC:boolean;   {as for RA}
   paddle_stop_DEC:boolean;   {as for RA}
   teljump:boolean;     { true if telescope is jumping to new coords}
   finish_RA:boolean;   { true if move in RA axis is finished}
   finish_DEC:boolean;    {as for RA}
   add_to_vel:double;     {delta velocity ramp}
   RA_add_vel:double;     {delta velocity for ramp in RA axis}
   DEC_add_vel:double;      {as for RA}
   sign_RA:boolean;    {flag used to detected change in motor direction}
   sign_DEC:boolean;      {as above}
   old_sign_RA:boolean;   {as above}
   old_sign_DEC:boolean;  {as above}
   DEC_scl:integer;    {Correction to the down ramp on a jump}
   RA_scl:integer;       {as for Dec}
   RA_max:double;    {used for jump scaling}
   DEC_max:double;         {as above}
   i:integer;
   RA_Refraction:double;       {real time refraction correction}
   DEC_Refraction:double;      {as above}
   RA_padlog:double;        {Log of paddle movements}
   DEC_padlog:double;       {as above}
   RA_reflog:double;        {Log of refraction movements}
   DEC_reflog:double;       {as above}
   ticks:longint;  {milliseconds since int. started (inc. by 300 evry 300msec)}
   PosDirty:boolean;   {true if telescope has just finished moving, and the}
                    {position log file is out of date}
   RA_Guide:integer;           {Guide rate movement accumulator, in 'ticks'}
   DEC_Guide:integer;          {as above}
   RA_Guidelog:double;   {log of guide motion, in motor steps, zeroed on in each detevent loop}
   DEC_Guidelog:double;
   Watchdog:integer;    {Incremented by DetermineEvent, zeroed by PC23 queue}
                        {calculation loop if all is well}
   GuideDebug:byte;
   HRticktime:double;   {Period, in milliseconds, of the HR timer tick}
   HRlast, HRnow: QWord; {Quad word, with .hi and .lo integer parts}

implementation

Uses
  globals, DigIO;

var IntExitSave:pointer;
    OldInt3Vec:pointer;
    fb,lb:byte;
    CutFrac:0..10;   {fraction of distance to cut for limit decelleration}
                     {1=10%, 5=50%, etc. Normally 0, counts up to 10 after}
                     {limit is hit}

procedure KickStart;
var Cmd:CmdStr;
    answer:AnswerStr;
begin
{$IFNDEF DUMMY}
     {**Enter time streaming mode**}
     {Q2  -  enter the Time streaming mode}
     Cmd:='1Q2';                            {axis 1/clear input buffer}
     PCwritecmd(PC23adr,Cmd);
     Cmd:='2Q2';                            {axis 2/clear input buffer}
     PCwritecmd(PC23adr,Cmd);

     {MSL - define  the clock relationship between axes}
     Cmd:='MSL11X';
     PCwritecmd(PC23adr,Cmd);


     {TD  -  time duration in milliseconds}
     Cmd:='1TD'+'50';
     PCwritecmd(PC23adr,Cmd);
     Cmd:='2TD'+'50';
     PCwritecmd(PC23adr,Cmd);

     { delay(200); }

     {SD  - generate the first interupt(pulse) toggle output 1 on PC23}
{$IFNDEF NZ}
     Cmd:='SD80008000 SD7FC1 SD7FFE SD80008000 SD7FC0 SD7FFE SD80008000';
{$ELSE}
     Cmd:='SD80008000 SD7FC1 SD7FFE SD80008000 SD80008000 SD80008000 SD80008000';
{$ENDIF}
     PCwritecmd(PC23adr,Cmd);

     {Clear the output buffer}
     Cmd:='1W3';
     PCwritecmd(PC23adr,Cmd);
     repeat
      PCReadanswer(PC23adr,Answer);
     until answer <> '';


     {MSS - start the Master clock}
     Cmd:='1MSS';
     PCwritecmd(PC23adr,Cmd);
{$ENDIF}
end;



procedure IntWriteCmd(var Cmd:CmdStr);
{Write a character string to the PC23 board. The base address is in PC23}
  var i:integer;
      alpha:char;
  begin
    alpha:=chr(32);
    PCWriteChar(PC23,alpha);
    for i:=1 to length(Cmd) do
      begin
        alpha:=Cmd[i];                      {Get next character to send}
        PCWriteChar(PC23,alpha);        {Send character}
        end;
    alpha:=chr(13);
    PCWriteChar(PC23,alpha);            {Terminate with CR}
  end;


procedure IntReadAnswer(var Response:AnswerStr);
  var sbyte:byte;
      ascii:byte;
      i:byte;
  begin
    Response:='            ';             {Initialise response string}
    sbyte:=port[PC23+1];                       {Read status for ODB ready}
    ShortDelay;
    i:=0;
    if ((sbyte and $08) <> 0) then
      repeat
        PCReadChar(PC23,ascii);              {Read PC23 response character}
        if (ascii > 0) then
          begin
               i:=i+1;
               Response[i]:=chr(ascii);    {Add response to string}
          end;
      until (ascii = 13) or (i>12);  {Continue reading until CR}
  end;

procedure IntRead(var val:longint);
  var sbyte:byte;
      i:integer;
  begin
    val:=0;
    for i:=1 to 5 do
        begin
            repeat
                  sbyte:=port[PC23+1];            {Read Status until SB bit 3}
                  ShortDelay;
            until ((sbyte and $08) > 0);   {indicates ODB ready}
            val:=val*256+port[PC23];        {Read character byte from PC23}
            ShortDelay;
            port[PC23+1]:=$E0;                {Signal read byte}
            ShortDelay;
            repeat
                  sbyte:=port[PC23+1];            {Read Status until SB bit 3}
                  ShortDelay;
            until ((sbyte and $08) = 0);   {indicates ODB busy}
            port[PC23+1]:=$60;                {Restore CB}
            ShortDelay;
            end;
  end;

function Sgn(a:integer):integer;
begin
     if a<0 then
          Sgn:=-1
     else if a>0 then
         Sgn:=1
     else
         Sgn:=0;
end;

{$IFDEF NZ}
procedure PCIntAck;
    i:integer;
    Cmd:CmdStr;
begin
{$IFNDEF DUMMY}
      Cmd:='1IO000000';
      IntWriteCmd(Cmd);
      for i:=1 to 10 do
          ShortDelay;
{$ENDIF}
end;

{$ELSE}
procedure PCIntAck;
var
    sbyte : byte;
begin
{$IFNDEF DUMMY}
    sbyte:=port[PC23+1];
    repeat
          port[PC23+1] := $60;
          port[PC23+1] := $20;
          delay(2);
          port[PC23+1] := $60;
          port[PC23+1] := $68;
          delay(2);
          sbyte:=port[PC23+1];
     until ((sbyte and $40)=0);
     port[PC23+1]:=$60;
{$ENDIF}
end;
{$ENDIF}

Function Timeint(P:Pointer):longint;

{When an interupt is detected this procedure is executed.
 This procedure sends six SD commands to the PC23 board.
 Interupts are set by toggling output 1 (on the PC23 card).
 This pulse is fed back into trigger 1 which is read to see if
 the queue needs data.
}


var
  MSB_RA,LSB_RA,MSB_DEC,LSB_DEC:string[2];
  word_RA,word_DEC:word;
  sbyte,msbra,lsbra,msbdec,lsbdec:byte;
  send_RA,send_DEC,RA_big:double;
  num_SD:integer;
  cmd:CmdStr;
  Resp:AnswerStr;
  ch:array[1..9] of char;
  i:integer;
  guidesteps:integer;


begin

Writeln(DosSetPriority(PRTYS_THREAD,PRTYC_TIMECRITICAL,PRTYD_MAXIMUM,0));

DosTmrQueryTime(HRlast);

repeat

DosSleep(20);

DosTmrQueryTime(HRnow);
guidesteps:=round((HRnow.lo - HRlast.lo)*HRticktime*GuideRate/1000);
HRlast:=HRnow;

ReadFine(fb);
if ((fb and 15)<>0) and ((fb and FGuideMsk) = FGuideMsk) then
   begin
         if ((fb and FWest)=FWest) then
            if RA_Guide<0 then
               RA_Guide:=RA_Guide-guidesteps
            else
                RA_Guide:=-guidesteps;
         if ((fb and FEast)=FEast) then
            if RA_Guide>0 then
               RA_Guide:=RA_Guide+guidesteps
            else
                RA_Guide:=guidesteps;

         if ((fb and FNorth)=FNorth) then
            if DEC_Guide<0 then
               DEC_Guide:=DEC_Guide-guidesteps
            else
                DEC_Guide:=-guidesteps;
         if ((fb and FSouth)=FSouth) then
            if DEC_Guide>0 then
               DEC_Guide:=DEC_Guide+guidesteps
            else
                DEC_Guide:=guidesteps;
   end;

ReadPort(fb,2,1);  {Port A on 8255 chip 2}
GuideDebug:=(fb and 15);

if (fb and 15)<>0 then
   begin
         if ((fb and FWest)=FWest) then
            if RA_Guide<0 then
               RA_Guide:=RA_Guide-guidesteps
            else
                RA_Guide:=-guidesteps;
         if ((fb and FEast)=FEast) then
            if RA_Guide>0 then
               RA_Guide:=RA_Guide+guidesteps
            else
                RA_Guide:=guidesteps;

         if ((fb and FNorth)=FNorth) then
            if DEC_Guide>0 then
               DEC_Guide:=DEC_Guide+guidesteps
            else
                DEC_Guide:=guidesteps;
         if ((fb and FSouth)=FSouth) then
            if DEC_Guide<0 then
               DEC_Guide:=DEC_Guide-guidesteps
            else
                DEC_Guide:=-guidesteps;
   end;

{$IFDEF NZ}
ReadLimit(lb);
PowerOff:=((lb and PowerMsk)=PowerMsk);
if not PowerOff then
   begin
        HorizLim:=((lb and HorizMsk)=HorizMsk);
        MeshLim:=((lb and MeshMsk)=MeshMsk);
        EastLim:=((lb and EastMsk)=EastMsk);
        WestLim:=((lb and WestMsk)=Westmsk);
   end;
if PowerOff or HorizLim or MeshLim or EastLim or WestLim then
   begin
        HWlimit:=true;
        Frozen:=true;
   end;
if PowerOff or HorizLim or MeshLim then
   LimOverride:=false;   {Only allow east and west limits overriden}
if HWlimit and (not LimOverride) and (CutFrac<10) then
   CutFrac:=CutFrac+1;
if (not HWlimit) or LimOverride then
   CutFrac:=0;
if CutFrac<>0 then
   PosViolate:=true;
{$ENDIF}

{$IFNDEF DUMMY}
{$IFDEF NZ}
Cmd:='1TS';
IntWriteCmd(Cmd);
repeat
      IntReadAnswer(Resp);
until Resp<>'            ';
if Resp[3]='1' then
{$ELSE}
sbyte:=port[PC23+1];
if (sbyte and $40)>0 then
{$ENDIF}
{$ENDIF}

begin

{$IFDEF NZ}
  {Reset the PC23 output}
  PCIntAck;
{$ENDIF}


  Watchdog:=0;   {Reset watchdog each time we get a signal from pc23 queue}

{This is the beginning of the SD loop. This loop sends 6 SD commands every
 time an interupt is detected.}
  for num_SD:=1 to 6 do
   begin
    ticks:=ticks+50;

    {**HAND PADDLE**}
    if paddle_start_RA then
    if RA_up>0 then
      begin
      RA_jump:=RA_jump+RA_add_vel;
      RA_up:=RA_up-1;
      RA_down:=RA_down+1;
      RA_big:=RA_jump;
      end
    else
      RA_jump:=RA_max_vel;     {continue till paddle button released}

    if paddle_start_DEC then
      if DEC_up>0 then
         begin
         DEC_jump:=DEC_jump+DEC_add_vel;
         DEC_up:=DEC_up-1;
         DEC_down:=DEC_down+1;
         end
      else
         DEC_jump:=DEC_max_vel;   {continue till paddle button released}

    if paddle_stop_RA then
      if RA_down>0.0 then
         begin
         RA_jump:=RA_jump-RA_add_vel;
         RA_down:=RA_down-1;
         end
      else
         begin
           RA_jump:=0.0;
           paddle_stop_RA:=false;   {finished}
           paddle_start_RA:=false;
           end;
    if paddle_stop_DEC then
      if DEC_down>0.0 then
         begin
           DEC_jump:=DEC_jump-DEC_add_vel;
           DEC_down:=DEC_down-1;
           end
      else
         begin
           DEC_jump:=0.0;
           paddle_stop_DEC:=false;   {finished}
           paddle_start_DEC:=false;
           end;


    {**TELESCOPE JUMP**}
    if teljump then
       begin
            if RA_up>0 then
               begin
                    RA_jump:=RA_jump+RA_add_vel;
                    RA_max:=RA_jump;
                    RA_up:=RA_up-1;
               end
            else
                if RA_plateau>0 then
                   begin
                        RA_jump:=RA_max_vel;
                        RA_plateau:=RA_plateau-1;
                   end
                else
                    if RA_down>0 then
                       begin
                            RA_jump:=RA_max-RA_scl*RA_add_vel;
                            RA_down:=RA_down-1;
                            RA_scl:=RA_scl+1;
                       end
                    else
                        begin
                             RA_jump:=0.0;                {finished jump}
                             RA_remain:=0;
                             RA_scl:=0;
                             finish_RA:=true;
                        end;

            if DEC_up>0 then
               begin
                    DEC_jump:=DEC_jump+DEC_add_vel;
                    DEC_max:=DEC_jump;
                    DEC_up:=DEC_up-1;
               end
            else
                if DEC_plateau>0 then
                   begin
                        DEC_jump:=DEC_max_vel;
                        DEC_plateau:=DEC_plateau-1;
                   end
                else
                    if DEC_down>0 then
                       begin
                            DEC_jump:=DEC_max-DEC_scl*DEC_add_vel;
                            DEC_down:=DEC_down-1;
                            DEC_scl:=DEC_scl+1;
                       end
                    else
                        begin
                             DEC_jump:=0.0;              {finished jump}
                             finish_DEC:=true;
                             DEC_remain:=0.0;
                             DEC_scl:=0;
                        end;

            if finish_DEC and finish_RA then
               begin
                    teljump:=false;   {finished the telescope jump}
                    PosDirty:=true;   {Flag invalid position log file}
                    moving:=false;    {telescope no longer in motion}
                    RA_reflog:=0;
                    Dec_reflog:=0;
               end;
       end;  {of if teljump}

{Next the velocities for sidereal rate, tracking rate & jump are mixed
together. The result is passed to the PC23 compumotor board.}


    {**MIX VELOCITIES for next pulse**}
    if teljump then
       begin
            send_RA:=RAsid+RA_jump+RA_remain;
            if NonSidOn then
               send_RA:=send_RA+RA_track;

            send_DEC:=DEC_jump+DEC_remain;
            if NonSidOn then
               send_DEC:=send_DEC+DEC_track;

            RA_Guide:=0;
            DEC_Guide:=-0;
       end
    else
        begin
             send_RA:=RA_jump;
             send_DEC:=DEC_jump;
             RA_padlog:=RA_padlog + RA_jump;
             DEC_padlog:=DEC_padlog + DEC_jump;

             if not Frozen then
                begin
                     if abs(RA_Guide) > GuideRate/20 then
                        begin
                             send_RA:=send_RA + Sgn(RA_Guide)*GuideRate/20;
                             RA_Guidelog:=RA_Guidelog + Sgn(RA_Guide)*GuideRate/20;
                             RA_Guide:=RA_Guide - Round(Sgn(RA_Guide)*GuideRate/20);
                        end
                     else        {Use up remaining short guide motion}
                         begin
                              send_RA:=Send_RA + RA_Guide;
                              RA_GuideLog:=RA_GuideLog + RA_Guide;
                              RA_Guide:=0;
                         end;


                     if abs(DEC_Guide) > GuideRate/20 then
                        begin
                             send_DEC:=send_DEC + Sgn(DEC_Guide)*GuideRate/20;
                             DEC_Guidelog:=DEC_Guidelog + Sgn(DEC_Guide)*GuideRate/20;
                             DEC_Guide:=DEC_Guide - Round(Sgn(DEC_Guide)*GuideRate/20);
                        end
                     else        {Use up remaining short guide motion}
                         begin
                              send_DEC:=send_DEC + DEC_Guide;
                              DEC_Guidelog:=DEC_Guidelog + DEC_Guide;
                              DEC_Guide:=0;
                         end;

                     send_RA:=send_RA + RAsid + RA_refraction;
                     send_DEC:=send_DEC + DEC_refraction;
                     RA_reflog:=RA_reflog+RA_refraction;     {real-time bits}
                     Dec_reflog:=Dec_reflog+Dec_refraction;

                     if NonSidOn then
                        begin
                             send_RA:=send_RA + RA_track;
                             send_DEC:=send_DEC + DEC_track;
                             RA_padlog:=RA_padlog + RA_track;
                             DEC_padlog:=DEC_padlog + DEC_track;
                        end;

                end    {of if not frozen}
             else
                 RA_padlog:=RA_padlog - RAsid;

        end;   {of if teljump - else clause}


    if RA_hold<>0 then
       begin
            send_RA:=send_RA + RA_hold;
            RA_hold:=0;
       end;
    if DEC_hold<>0 then
       begin
            send_DEC:=send_DEC + DEC_hold;
            DEC_hold:=0;
       end;

    RA_padlog:=RA_padlog - send_RA*(CutFrac/10);
    DEC_padlog:=DEC_padlog - send_DEC*(CutFrac/10);
        {Subtract the cut portion of motion from the paddle log}
        {If no limits, cutfrac=0, if limit decel. finished cutfrac=10}
    send_RA:=send_RA*(1-CutFrac/10);
    send_DEC:=send_DEC*(1-CutFrac/10);
        {Multiply send values by 1 if no limit, or 0.9, 0.8, .07 ... 0.0}
        {successively if we hit a limit}


    if EastOfPier then
       send_DEC:=-send_DEC;      {Invert dec direction if tel. east of pier}


    {Break into integer & fraction}
    int_RA:=Trunc(send_RA);
    frac_RA:=frac_RA+frac(send_RA);
    {if the absolute value of frac_RA is greater than 1 update int_RA}
    if Abs(frac_RA)>1.0 then
       begin
         int_RA:=int_RA+Trunc(frac_RA);
         frac_RA:=frac_RA-int(frac_RA);
       end;

    {Break into integer & fraction}
    int_DEC:=Trunc(send_DEC);
    frac_DEC:=frac_DEC+frac(send_DEC);      {accumulate residuals}
    {if the frac_DEC is greater than 1 update int_DEC}
    if Abs(frac_DEC)>1.0 then
       begin
         int_DEC:=int_DEC+Trunc(frac_Dec);
         frac_DEC:=frac_DEC-int(frac_Dec);
         end;



    {**CHECKS**}
    {if the sign of either send_RA or send_DEC has changed since the last
     pulse add int_** to frac_** and reset int_** to 0.0 }
    sign_RA:=(int_RA>=0);
    if sign_RA<>old_sign_RA then     {Set an initial value for old_sign_RA}
        begin
          old_sign_RA:=sign_RA;
          RA_hold:=int_RA; {include this velocity in the next pulse}
          int_RA:=0;
          end;

    sign_DEC:=(int_DEC>=0);
    if sign_DEC<>old_sign_DEC then   {as for old_sign_RA}
        begin
          old_sign_DEC:=sign_DEC;
          DEC_hold:=int_DEC;
          int_DEC:=0;
          end;


    {**COMPUMOTOR SECTION**}

    {send the number of steps for this pulse}
    if int_RA<0 then
        word_RA:=32768+abs(int_RA)
    else
        word_RA:=int_RA;
    if int_DEC<0 then
        word_DEC:=32768+abs(int_DEC)
    else
        word_DEC:=int_DEC;

    msbra:=word_RA div 256;
    lsbra:=word_RA mod 256;
    msbdec:=word_DEC div 256;
    lsbdec:=word_DEC mod 256;

    ch[1]:=hexstr[msbra div 16];
    ch[2]:=hexstr[msbra mod 16];
    ch[3]:=hexstr[lsbra div 16];
    ch[4]:=hexstr[lsbra mod 16];
    ch[5]:=hexstr[msbdec div 16];
    ch[6]:=hexstr[msbdec mod 16];
    ch[7]:=hexstr[lsbdec div 16];
    ch[8]:=hexstr[lsbdec mod 16];
    ch[9]:=chr(13);

{$IFNDEF DUMMY}

    PCWriteChar(PC23,' ');
    PCWriteChar(PC23,'S');
    PCWriteChar(PC23,'D');
    for i:=1 to 9 do
       PCWriteChar(PC23,ch[i]);

    if num_SD=2 then   {begin interupt}
       {Set output 1 high}
       begin
         cmd:='SD7FC1 SD7FFE';
         IntWriteCmd(cmd);
       end
    else if num_SD=3 then   {end interupt}
       {Set output 1 low}
       begin
         cmd:='SD7FC0 SD7FFE';
         IntWriteCmd(cmd);
       end;

{$ENDIF}

  {end of the SD loop}
  end;

{$IFNDEF NZ}
    PCIntAck;
{$ENDIF}

end;  {of action if queue detected}

until false;


{**The End**}
end;





procedure InstallInt;
var b1,b2:byte;
begin
     ReadCoarse(b1);
     ReadFine(b2);
     if ((b1 and (CNorth or CSouth or CEast or CWest)) <> 0) or
        ((b2 and (FNorth or FSouth or FEast or FWest)) <> 0) then
        begin
             eWrite('ERROR! Hand Paddle button depressed on program startup!'+
                    '   Aborting...');
             delay(3000);
             system.Halt;
        end;

      VPbeginthread(TimeInt,16384,nil);
      writeln('Now installed int28 driver');

   {   SetIntVec(28,@TimeInt); }
   {   SetIntVec($72,@TimeInt); }
   {   port[$A1]:=(port[$A1] and $Fb); }   {write only...}
   {   port[$A1]:=0; }  {unmask all}
end;




Procedure Deinstall;
begin
     writeln('Deinstalled int28');
     ExitProc:=IntExitSave;
   {  SetIntVec(28,OldInt3Vec);  }
   {  SetIntVec($72,OldInt3Vec); }
   {  port[$A1]:=(port[$A1] or 4); }    {write only...}
   {  port[$A1]:=4; }  {mask irq10}
end;


begin  {Main init routine for unit}
      {Set initial values}

    {  GetIntVec(28,OldInt3Vec);  }
    {  GetIntVec($72,OldInt3Vec); }

      Writeln ('Initializing Global variables');
      Delay(500);
      RA_up:=0;
      RA_down:=0;
      DEC_up:=0;
      DEC_down:=0;
      RA_plateau:=0;
      DEC_plateau:=0;
      RA_track:=0.0;
      DEC_track:=0.0;
      RA_jump:=0.0;
      DEC_jump:=0.0;
      RA_remain:=0.0;
      DEC_remain:=0.0;
      finish_RA:=true;
      finish_DEC:=true;
      int_RA:=0;
      int_DEC:=0;
      frac_RA:=0;
      frac_dec:=0;
      Paddle_start_RA:=false;
      Paddle_stop_RA:=false;
      Paddle_start_DEC:=false;
      Paddle_stop_DEC:=false;
      Teljump:=false;
      RA_hold:=0;
      DEC_hold:=0;
      RA_scl:=0;
      DEC_scl:=0;
      RA_refraction:=0.0;
      DEC_refraction:=0.0;
      RA_padlog:=0.0;
      DEC_padlog:=0.0;
      RA_reflog:=0;
      Dec_reflog:=0;
      RA_Guide:=0;
      DEC_Guide:=0;
      RA_Guidelog:=0;
      DEC_Guidelog:=0;
      Watchdog:=-10;

      DosTmrQueryFreq(i);     {Find frequency of H timer}
      HRticktime:=1/(i/1000);  {Convert to period in ms, trying to avoid}
                              {roundoff error by dividing by 1000 first}

      CutFrac:=0;

      writeln('finished global vars');

      IntExitSave:=ExitProc;
      ExitProc:=@Deinstall;

      writeln('Installed pc23int exit proc');

      hexstr[0]:='0';
      hexstr[1]:='1';
      hexstr[2]:='2';
      hexstr[3]:='3';
      hexstr[4]:='4';
      hexstr[5]:='5';
      hexstr[6]:='6';
      hexstr[7]:='7';
      hexstr[8]:='8';
      hexstr[9]:='9';
      hexstr[10]:='A';
      hexstr[11]:='B';
      hexstr[12]:='C';
      hexstr[13]:='D';
      hexstr[14]:='E';
      hexstr[15]:='F';
      ticks:=0;


end.  {of unit inits}
