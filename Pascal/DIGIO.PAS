unit DigIO;

{
    ReadCoarse   -           Read the coarse joystick of the telescope.
    ReadFine     -           Read the fine joystick of the telescope.
    ReadLimit    -           Read the limit and power-down status.

    These procedures handle all the I/O operations with the 8255 card.
    The procedures are:

    ReadPort            - Read a given port (1 -A,B,C or 2 -A,B,C).
    WritePort           - Write to a given port (must first write to
                          control register of port to enable it to be
                          writeable).

    The constants and types given below are the locations of buffers,
    control registers or board address.  The 8255 I/O board is assumed
    to be at $h1b0.
}

interface

Const
    Adr82     = 432;                   {Default address of 8255 card}
    A1        = 432;                   {Port 1A read/write buffer}
    B1        = 433;                   {Port 1B read/write buffer}
    C1        = 434;                   {Port 1C read/write buffer}
    Ctrl1     = 435;                   {Port 1 control register}
    A2        = 436;                   {Port 2A read/write buffer}
    B2        = 437;                   {Port 2B read/write buffer}
    C2        = 438;                   {Port 2C read/write buffer}
    Ctrl2     = 439;                   {Port 2 control register}
    ReadAll   = $9b;                   {Set control register, ports read
                                        only}
    WriteAll  = $80;                   {Set control register, ports writeable}

    ST5_Left   = $08;
    ST5_Right  = $04;
    ST5_Up     = $01;
    ST5_Down   = $02;

    CNorth    = $01;                        {Mask for north on coarse paddles (1)}
    CSouth    = $02;                        {Mask for south (2)}
    CEast     = $04;                        {Mask for east (4)}
    CWest     = $08;                        {Mask for west (8)}

    FNorth    = $01;                        {Mask for north on fine paddle (1)}
    FSouth    = $02;                        {Mask for south (2)}
    FEast     = $04;                        {Mask for east (4)}
    FWest     = $08;                        {Mask for west (8)}

    CspaMsk   = $10;                        {Speed bit A on coarse paddle (16)}
    CspbMsk   = $20;                        {Speed bit B on coarse paddle (32)}

    CSlewMsk  = $10;
    FGuideMsk = $10;


Type
    PortN = 1..2;                      {1=Port 1  2=Port 2}
    PortCh = 1..3;                     {1=A 2=B 3=C}

Procedure ReadPort(var B:byte; N:PortN; Ch:PortCh);

Procedure WritePort(var B:byte; N:PortN; Ch:PortCh);

Procedure ReadCoarse(var CB:byte);

Procedure ReadFine(var FB:byte);

Procedure ReadLimit(var LB:byte);


{$IFDEF NZ}
  Function DomeGoingLeft:boolean;
  Procedure DomeLeft;

  Function DomeGoingRight:boolean;
  Procedure DomeRight;

  Procedure DomeStop;
{$ENDIF}



implementation

uses Crt;

const LeftMsk=1;   {Masks for left and right dome output bits}
      RightMsk=2;

var CurrentOut:byte;      {Current state of the output ports}


Procedure ReadPort(Var B:byte; N:PortN; Ch:PortCh);
  begin
    case N of
      1: begin
           port[Ctrl1]:=ReadAll;
           case Ch of
             1: B:=port[A1];
             2: B:=port[B1];
             3: B:=port[C1];
             end;
           end;
      2: begin
           port[Ctrl2]:=ReadAll;
           case Ch of
             1: B:=port[A2];
             2: B:=port[B2];
             3: B:=port[C2];
             end;
           end;
      end;
  end;

Procedure WritePort(Var B:byte; N:PortN; Ch:PortCh);
  begin
    case N of
      1: begin
           port[Ctrl1]:=WriteAll;
           case Ch of
             1: port[A1]:=B;
             2: port[B1]:=B;
             3: port[C1]:=B;
             end;
           end;
      2: begin
           port[Ctrl2]:=WriteAll;
           case Ch of
             1: port[A2]:=B;
             2: port[B2]:=B;
             3: port[C2]:=B;
             end;
           end;
      end;
  end;





{$IFDEF NZ}

Procedure ReadCoarse(var CB:byte);
var b:byte;
begin
     b:=Port[$216];
     b:=b and port[$216];
     b:=not b;
{     CB:=n + 2*s + 4*e + 8*w + 16*spa + 32*spb   }
     CB:=b and 63;

end;

Procedure ReadFine(var FB:byte);
begin
       FB:=0;
end;

Procedure ReadLimit(var LB:byte);
var pw,hl,ms,el,wl:0..1;
    b:byte;
begin
     b:=Port[$217];
     b:=b and port[$217];
     el:=(b and 1);
     wl:=(b and 2) div 2;
     ms:=(b and 4) div 4;
     pw:=(b and 32) div 32;
     hl:=(b and 64) div 64;
     LB:=pw + 2*hl + 4*ms + 8*el + 16*wl;
end;

Function DomeGoingLeft:boolean;
var b:byte;
begin
     b:=port[$216];
     b:=b and port[$216];
     DomeGoingLeft:=((b and 64)=64);
end;

Procedure DomeLeft;
begin
     if DomeGoingRight then
        begin
             DomeStop; {Open the relay so we can read the paddle button}
             delay(500);
        end;
     if not DomeGoingRight then  {Right paddle button isn't pressed}
        begin
             CurrentOut:=(CurrentOut or LeftMsk) and (not RightMsk);
             Port[$21D]:=CurrentOut;
        end;
end;

Function DomeGoingRight:boolean;
var b:byte;
begin
     b:=port[$216];
     b:=b and port[$216];
     DomeGoingRight:=((b and 128)=128);
end;

Procedure DomeRight;
begin
     if DomeGoingLeft then
        begin
             DomeStop; {Open the relay so we can read the paddle button}
             delay(500);
        end;
     if not DomeGoingLeft then  {Left paddle button isn't pressed}
        begin
             CurrentOut:=(CurrentOut or RightMsk) and (not LeftMsk);
             Port[$21D]:=CurrentOut;
        end;
end;

Procedure DomeStop;
begin
     CurrentOut:=CurrentOut and (not (LeftMsk or RightMsk));
     Port[$21D]:=CurrentOut;
end;






{$ELSE}

Procedure ReadCoarse(Var CB:byte);
  begin
    ReadPort(CB,1,1);
  end;

Procedure ReadFine(VAR FB:byte);
  begin
    ReadPort(FB,1,2);
  end;

Procedure ReadLimit(Var LB:byte);
begin
     LB:=0;
end;





{$ENDIF}

begin
  {$IFDEF NZ}
     CurrentOut:=0;      {No outputs high on startup}
     Port[$21D]:=0;
     Port[$21E]:=0;
  {$ENDIF}
end.
