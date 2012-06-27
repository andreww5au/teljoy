{$N+,E+}
unit setpro;

interface

uses Globals;

const
     pulse=0.05;   {seconds between interrupts}
     RA_Sidereal=-20*1.002737912*pulse*15; {(steps/sidsec)*(sidsec/sec)*(sec/pulse)}

var delRA,delDEC:double;

procedure setprof(delRA,delDEC,Rate:double);

procedure start_motor(Which_motor:boolean;paddle_max_vel:double);

procedure stop_motor(which_motor:boolean);

procedure setup;

procedure relref(var Obj:Objectrec);


implementation

uses pc23int,Crt,PC23io,Time,Correct,Flexure;

procedure DisableInts;
begin
end;
procedure EnableInts;
begin
end;

procedure relref(var Obj:ObjectRec);
{Calculates a real time refraction correction for inclusion in INTPAS
 routine. The effect of refraction is calculated by
   (1) The effect of refraction is calculated at time+time_inc.
   (2) Divided by the number of interupts in the time interval and added
       to RA_send & DEC_send every time through the loop.
   (3) The next refract value is calculated and held ready for when
       a log decremented in INTPAS reaches zero.
       Global variables:
            RA_refraction    value passed to INTPAS to correct for refraction.
            DEC_refraction   as for RA.
            int_time         interupt time (50ms).}

Const
          num_ref=600;               { no of interrupts in time_inc time.}
          time_inc=30.0;             { Update time}
          SidCorrect=30.08213727/3600; {number of siderial hours in update time}

var
   oldRAref,oldDECref,newRAref,newDECref,oldRAflex,oldDECflex,newRAflex,
   newDECflex,deltaRA,deltaDEC,HourC,DecCd:double;

begin
      {**Begin refraction correction**}
      GetSidereal(Obj);       {Current sidereal time}
      AltAziConv(obj);

      AltError:=false;
      if obj.alt < AltWarning then
         AltError:=true;


      if RefractionOn then
         refrac(oldRAref,oldDECref,Obj)
      else
          begin
               oldRAref:=0;
               oldDECref:=0;
          end;

      if FlexureOn then
         begin
              Flex(oldRAflex,oldDECflex,Obj);
          end
      else
          begin
               oldRAflex:=0;
               oldDECflex:=0;
          end;



      if RealTimeOn then
         begin
             Obj.time.LST:=Obj.time.LST+SidCorrect; {advance sid time}
             AltAziConv(Obj);               {Calculate the alt/az}

             if RefractionOn then
                refrac(newRAref,newDECref,Obj)  {Calculate refraction for new time}
             else
                 begin
                      newRAref:=0;
                      newDECref:=0;
                 end;

             if FlexureOn then
                begin
                     Flex(newRAflex,newDECflex,Obj);
                 end
             else
                 begin
                      newRAflex:=0;
                      newDECflex:=0;
                 end;

             deltaRA:=(newRAref-oldRAref)+(newRAflex-oldRAflex);
             deltaDEC:=(newDECref-oldDECref)+(newDECflex-oldDECflex);

             {Start the refraction corrections}
             RA_refraction:=20.0*(deltaRA/num_ref);
             DEC_refraction:=20.0*(deltaDEC/num_ref);

             RefError:=false;
             if Abs(RA_refraction)>200 then
                begin
                     RA_refraction:=200*(RA_refraction/Abs(RA_refraction));
                     RefError:=true;
                end;
             if Abs(Dec_refraction)>200 then
                begin
                     Dec_refraction:=200*(Dec_refraction/Abs(Dec_refraction));
                     RefError:=true;
                end;
         end
      else
          begin
             {**Stop the refraction correction**}
             RA_refraction:=0.0;
             DEC_refraction:=0.0;
             RefError:=false;
          end;

      GetSysTime(Obj.Time.lthr,Obj.Time.ltm,Obj.Time.lts,Obj.Time.lthn);
      GetSysDate(Obj.Time.dy,Obj.Time.mnth,Obj.Time.yr);
      TimetoDec(Obj.Time);
      UTConv(Obj.Time);
      UTtoJD(Obj.Time);

      GetSidereal(Obj);       {Current sidereal time}
      AltAziConv(obj);

end; {of procedure RelRef}


procedure setprof (delRA,delDEC,Rate:double);

{This procedure calculates the profile parameters for a telescope jump.
 A jump occurs when a the telescope is positioned on another object or
 a correction to the postion of the telescope (provided by the encoders).
 Starting with the (1) the number of motor steps in a jump (delRA & delDEC)
                   (2) maximum velocity for the jump (JumpRate)
                   (3) the acceleration of the motor (max_accel)
                   (4) the duration of one pulse ( one interupt)
 calculate the number of pulses for the jump.

 A jump has three components they are the ramp up, the plateau and the ramp
 down. The size of the jump, the acceleration  and the maximum velocity
 determine the values for the three jump component. Components are described in terms
 of the number of pulses(interupts) and the number of motor steps per pulses.


 All parameters output from this procedure are in motor steps/time pulse.

 This information is used by the interrupt software - see PC23int.pas.}


{input:
motor_max_vel           maximum motor velocity - rev/sec
motor_accel             acceleration of the motor - rev/sec/sec
delRA  *                number of motor steps in RA
delDEC *                number of motor steps in DEC
pulse                   duration of a pulse in seconds
num_steps_rev
output:
RA_up                   number of time pulses in a up ramp
RA_down                 number of time pulses in a down ramp
RA_plateau              number of time pulses in the plateau
DEC_up                  as for RA
DEC_down                as for RA
DEC_plateau             as for RA
add_to_vel              change in the ramp velocity - motor steps/pulse
max_vel                 maximum motor velocity - motorsteps/pulse
teljump                 Logical - set true if we are executing a jump
finish_RA               Logical - set true if the RA move is finished
finish_DEC              as for RA
               *         LOCAL VARIABLE}

var
   motor_max_vel,num_ramp_steps,steps_plateau,RA_sign,DEC_sign,
   pulses_plateau,num_steps_hold,steps_used,ramp_time,RA_test,DEC_test:double;
   num_pulses,sum_of_pulses,ramp_pulses_part:longint;
   loop:boolean;

begin
{Determine motor speeds and displacements.}
      {If teljump or paddle flags are true, loop until they go false.}
      while teljump or Paddle_start_RA or Paddle_stop_RA
            or Paddle_start_DEC or Paddle_stop_DEC do
               begin
                    GotoXY(1,1);
                    Writeln;
                    writeln('Waiting for telescope to stop moving:                                 ');
                    writeln;
               end;

      {calculate max_vel.}
      motor_max_vel:=Rate/25000;            {revs/sec}
      max_vel:=Rate*pulse;                  {unsigned value steps/pulse}

      {number of time pulses in the ramp up.}
      ramp_time:=motor_max_vel/motor_accel;
      num_pulses:=Trunc(ramp_time/pulse);

      {speed incrument per time pulse in motor steps/pulse.}
      if num_pulses>0 then
         add_to_vel:=max_vel/num_pulses
      else
         add_to_vel:=0;

      {The number of motor steps in a ramp is?}
      num_ramp_steps:=add_to_vel*(num_pulses*num_pulses/2.0+num_pulses/2.0);


      if add_to_vel=0 then
          add_to_vel:=max_vel;



{Account for the direction of the jump.}
       if delRA<0 then
         begin
           RA_add_vel:=-add_to_vel;
           RA_max_vel:=-max_vel;
           RA_sign:=-1.0;
           end
       else
         begin
           RA_add_vel:=add_to_vel;
           RA_max_vel:=max_vel;
           RA_sign:=1.0;
           end;

       if delDEC<0 then
         begin
           DEC_add_vel:=-add_to_vel;
           DEC_max_vel:=-max_vel;
           DEC_sign:=-1.0;
           end
       else
         begin
           DEC_add_vel:=add_to_vel;
           DEC_max_vel:=max_vel;
           DEC_sign:=1.0;
           end;


{Calculate the ramp and plateau values for both axes.}
       if delRA=0.0 then
         {no jump in RA axis}
         begin
               RA_up:=0;
               RA_down:=0;
               RA_plateau:=0;
               RA_remain:=0;
               finish_RA:=true;
               end

       else if abs(delRA)<abs(2.0*RA_add_vel) then
          {Small jump - add delRA to frac_RA}
          begin
               RA_UP:=0;
               RA_down:=0;
               RA_plateau:=0;
               RA_remain:=0;
               finish_RA:=true;
               frac_RA:=frac_RA+delRA;
               end

       else if abs(delRA)>2.0*num_ramp_steps then
         {Jump is large enough to reach max velocity - has a Plateau}
         begin
               RA_up:=num_pulses;
               RA_down:=num_pulses;
               steps_plateau:=delRA-2.0*(num_ramp_steps)*(RA_sign);
               pulses_plateau:=steps_plateau/(RA_max_vel);
               RA_plateau:=Trunc(pulses_plateau);      {number of pulses in the plateau}
               sum_of_pulses:=RA_up*2+RA_plateau;
               RA_remain:=(steps_plateau-RA_plateau*RA_max_vel)/sum_of_pulses;
               finish_RA:=false;
               end
       else
         {Jump is to short to reach max velocity - no plateau}
         begin
               ramp_pulses_part:=0;
               num_steps_hold:=abs(delRA);
               loop:=true;
               while loop Do
                     begin
                        steps_used:=2.0*add_to_vel*(ramp_pulses_part+1);
                        num_steps_hold:=num_steps_hold-steps_used;
                        if num_steps_hold<0.0 then
                         begin
                           num_steps_hold:=num_steps_hold+steps_used;
                           loop:=false;
                           end
                        else
                            ramp_pulses_part:=ramp_pulses_part+1;
                        end;

               RA_up:=ramp_pulses_part;
               RA_down:=ramp_pulses_part;
               RA_plateau:=0;
               sum_of_pulses:=RA_up*2;

               RA_remain:=(num_steps_hold*RA_sign)/sum_of_pulses;
               finish_RA:=false;
               end;

       {Check the number of pulses = delRA}
{       RA_Test:=RA_max_vel*RA_plateau+(RA_up+RA_down+RA_plateau)*RA_remain+
       2*(RA_add_vel*((RA_up*RA_up)/2+RA_up/2));
       if RA_Test<>delRA then
         begin
           writeln('Difference between number of steps in RA profile and delRA');
           writeln(RA_Test-delRA, ' ',delRA)
        end;
       writeln('RA_up:=',RA_up);
       writeln('RA_up:=',RA_up);
       writeln('RA_plateau:=',Ra_plateau);
       writeln('RA_add_vel=',RA_add_vel);
       writeln('RA_max_vel=',Ra_max_vel);
       writeln('RA_remain=',Ra_remain);
}



       if delDEC=0 then
          {no jump in DEC axis}
          begin
               DEC_up:=0;
               DEC_down:=0;
               DEC_plateau:=0;
               DEC_remain:=0;
               finish_DEC:=true;
               end

       else if abs(delDEC)<abs(2.0*DEC_add_vel) then
          {Small jump - add delDEC to frac_DEC}
          begin
               DEC_UP:=0;
               DEC_down:=0;
               DEC_plateau:=0;
               DEC_remain:=0;
               finish_DEC:=true;
               frac_DEC:=frac_DEC+delDEC;
               end

       else if abs(delDEC)>2.0*num_ramp_steps then
          {Jump large enough to reach max velocity - has a Plateau.}
          begin
               DEC_up:=num_pulses;
               DEC_down:=num_pulses;
               steps_plateau:=delDEC-2.0*(num_ramp_steps*DEC_sign);
               pulses_plateau:=steps_plateau/(DEC_max_vel);
               DEC_plateau:=Trunc(pulses_plateau);
               sum_of_pulses:=DEC_up*2+DEC_plateau;
               DEC_remain:=(steps_plateau-DEC_plateau*DEC_max_vel)/sum_of_pulses;
               finish_DEC:=false;
               end

       else
            {Jump is to small to reach max velocity- no Plateau.}
            begin
                 ramp_pulses_part:=0;
                 num_steps_hold:=abs(delDEC);
                 loop:=true;
                 while loop Do
                       begin
                            steps_used:=2.0*add_to_vel*(ramp_pulses_part+1);
                            num_steps_hold:=num_steps_hold-steps_used;
                            if num_steps_hold<0.0 then
                             begin
                               num_steps_hold:=num_steps_hold+steps_used;
                               loop:=false;
                               end
                            else
                               ramp_pulses_part:=ramp_pulses_part+1;
                       end;
                 DEC_up:=ramp_pulses_part;
                 DEC_down:=ramp_pulses_part;
                 DEC_plateau:=0;
                 sum_of_pulses:=DEC_up*2;
                 DEC_remain:=(num_steps_hold*DEC_sign)/sum_of_pulses;
                 finish_DEC:=false;
                 end;

       {Check the number of pulses = deldec}
{       DEC_Test:=DEC_max_vel*DEC_plateau+(DEC_up+DEC_down+DEC_plateau)*DEC_remain+
       2*(DEC_add_vel*((DEC_up*DEC_up)/2+DEC_up/2));
       if DEC_Test<>delDEC then
         begin
           writeln('Difference between number of steps in DEC profile and delDEC');
           writeln(DEC_Test-delDEC,' ',delDEC)
        end;

       writeln('DEC_up:=',DEC_up);
       writeln('DEC_up:=',DEC_up);
       writeln('DEC_plateau:=',DEC_plateau);
       writeln('DEC_add_vel=',DEC_add_vel);
       writeln('DEC_max_vel=',DEC_max_vel);
       writeln('DEC_remain=',DEC_remain);
}

{inform the interupt that we have a telescope jump to execute}
       {Check the paddles arent in use}
       while teljump or Paddle_start_RA or Paddle_stop_RA
             or Paddle_start_DEC or Paddle_stop_DEC do
                write(',');

       if (not finish_RA or not finish_DEC) then
          begin
               teljump:=true;
               Moving:=true;
          end
       else
            teljump:=false;

end;
{**The end**}


procedure start_motor(Which_motor:boolean;paddle_max_vel:double);

{This procedure is used to start one of the compumotors

paddle_max_vel           the max speed of the paddles in revs/sec (does this describe direction????)
motor_accel              the acceleration of the motors in revs/sec
pulse                    the duration of a time pulse (interupt)
num_steps_rev            the number of motor steps in 1 rev
Which_motor              logical - true then this call refers to the RA motor else DEC motor
RA_up                    the number of pulses in the up ramp
DEC_up                   as for RA
Paddle_start_RA          logical - if true then start the Ra motor
Paddle_start_DEC         as for RA}

var ramp_time:double;
    num_pulses:longint;

begin
     Moving:=true;   {signal telescope in motion}
{Test that to see if the telescope is in jump mode}
     While teljump do
           Writeln('Waiting for the telescope jump to end.');

     if Which_motor then {Is the RA axis stationary?}
        while (Paddle_start_RA or Paddle_stop_RA) do

     else     {Is the DEC axis stationary?}
        while (Paddle_start_DEC or Paddle_stop_DEC) do;

     {The following calculations are assumed to be the same for
      RA and DEC axis}
     {number of pulses in ramp_up}
     ramp_time:=abs(paddle_max_vel)/motor_accel;
     num_pulses:=Trunc(ramp_time/pulse);

     {maximum velocity in motor steps per pulse}
     max_vel:=paddle_max_vel*25000*pulse;

     {Incrument velocity ramp by add_to_vel -  also error trap for num_pulses=0}
     if num_pulses>0 then
        add_to_vel:=max_vel/num_pulses
     else
        add_to_vel:=0;

     {Set global values for the motor}
     if which_motor then    {RA axis}
        begin
             RA_up:=num_pulses;
             RA_down:=0;
             Paddle_start_RA:=true;
             Paddle_stop_RA:=false;
             RA_max_vel:=max_vel;
             RA_add_vel:=add_to_vel;
             end
     else                   {DEC axis}
        begin
             DEC_up:=num_pulses;
             DEC_down:=0;
             Paddle_start_DEC:=true;
             Paddle_stop_DEC:=false;
             DEC_max_vel:=max_vel;
             DEC_add_vel:=add_to_vel;
             end;

end;
{**The End**}

procedure stop_motor(which_motor:boolean);

{Ramp one of the compumotors down
 which_motor             logical - if true then stop RA motor else stop DEC motor
 paddle_start_RA         logical - if true then continue moving the RA motor
 paddle_start_DEC        as for RA
 paddle_stop_RA          logical - if true then ramp the RA motor down
 paddle_stop_DEC         as for RA}

begin
     PosDirty:=true;    {flag pos log file as out of date}
     Moving:=false;     {no longer in motion}
     if which_motor then
        begin
                   paddle_start_RA:=false;
                   paddle_stop_RA:=true;
        end
     else
               begin
              paddle_start_DEC:=false;
                    paddle_stop_DEC:=true;
         end;

end;
{**The End**}


procedure resetPC23;

{This Procedure resets the PC23 card. The card is is assumed to be
 running in Time Data(TD) mode.

For normal operation the control byte is set up as
 bit number   state    definition
 0             0       binary input (active high pulse)
 1             0       unused
 2             0       stop watchdog timer (active high pulse)
 3             0       acknowledge interupt (active high pulse)
 4             0       input data buffer command ready (active high handshake)
 5             1       reset watchdog timer (active low pulse)
 6             1       reset interupt output (active low pulse)
 7             0       output date bus character accepted (active high handshake)
}

const
     Fail_mask = $20;       {board fail mask}
     Start_mask= $7F;       {recovery mask used to test for PC23 recovery}
     IntClr    = $20;       {Clear the interupt output latch}
     Restart   = $17;       {variable use to verify presence/recovery}
     Stop      = $64;       {Control byte used to stop timer}
     Start     = $40;       {Control Byte used to restart, clear CB5}
     CB        = $60;       {Normal Control Byte, bits 5 & 6 set}
     ReadyMask  = '00001000';
var
     Status,Control,count,Maxint,int_pulse : Integer;
     sbyte : byte;
     Cmd:CmdStr;
     Answer:Answerstr;
     str_pulse:string[32];
     loop:boolean;
     around:integer;

begin
    writeln('Starting resetPC23');
(*    DisableInts;    {just to make sure}  *)

    Control := PC23+1;                 {address of control byte}
    Status  := PC23+1;                 {address of the status byte}
    Maxint:=100;
    port[Control]:=Stop;
    delay(1);
    count:=0;
    writeln('A');
    repeat
         sbyte := port[Status];           {read status until SB5 }
         count:=count+1;
         delay(1);
    until ((sbyte and Fail_mask)>0) or (count>1000);{indicates Board has Failed}
    if count>1000 then
       begin
            Writeln('Board init. failure.');
            Delay(1000);
            Halt;
       end;
    writeln(count);

    port[Control]:=Start;
    delay(1);
    port[Control]:=CB;
    delay(1);
    count:=0;
    writeln('B');
    repeat
          sbyte:=port[Status];
          count:=count+1;
          delay(1);
    until (((sbyte and Start_mask)=Restart) or (count>1000));
    if count>1000 then
      begin
        Writeln('The PC23 board address is invalid. Response (',sbyte,')');
        Delay(1000);
        Halt;
      end;
    writeln('C');
    {clear the interupt output latch}
    port[Control]:=IntClr;
    Delay(1);

    {restore normal CB}
    port[Control]:=CB;
    delay(1);
    Writeln('Finished initialization of the board');


    {**Set all buffered commands before entering Time streaming mode**}
    {Set the motor resolution}
    Cmd:='1MR10 2MR10';
    PCWriteCmd(PC23adr,Cmd);

    {Make sure power motors are powered up}
    Cmd:='1ST0 2ST0';
    PCWriteCmd(PC23adr,Cmd);

{$IFNDEF NZ}
    {QS - set the interupt condition (Trigger 1)}
    Cmd:='QSA1';
    PCwritecmd(PC23adr,Cmd);
    Cmd:='1ER100000 2ER100000';
    PCWriteCmd(PC23adr,Cmd);
    Cmd:='1FSA1 1FSB1 2FSA1 2FSB1';
    PCwritecmd(PC23adr,Cmd);
    Cmd:='1OSE1 2OSE1';
    PCwritecmd(PC23adr,Cmd);
    Cmd:='1FSD1 2FSD1';
    PCwritecmd(PC23adr,Cmd);
    Cmd:='1PZ 2PZ';
    PCWriteCmd(PC23adr,Cmd);
{$ELSE}
    Cmd:='1ER100000 2ER100000';
    PCWriteCmd(PC23adr,Cmd);
    Cmd:='1FSA1 2FSA1';
    PCwritecmd(PC23adr,Cmd);
    Cmd:='1PZ 2PZ 1A4 2A4';
    PCWriteCmd(PC23adr,Cmd);
{$ENDIF}

    Delay(2000);                    {Wait for the end of buffer commands}

    writeln('About to Kickstart!');
    KickStart;           {Set up axes in streaming mode, send first data}

    EnableInts;    {Let 'er rip!}
    writeln('wheeee!!!!');

end;
{**The End**}



procedure setup;
begin
{$IFNDEF DUMMY}
     resetPC23;        {Call the procedure to initialize the PC23 card}
{$ENDIF}
end;


end.
