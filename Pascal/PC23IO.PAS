unit PC23IO;

{   Module:  PC23I/O
    The procedures in this module carry out all I/O operations with the
    PC23 control board.  These procedures are :

    Initialise          - Initialisies/resets PC23 control board.
    PCWriteChar         - Write a single character to the PC23.
    PCWriteCmd          - Write a command string to the PC23.
    PCReadChar          - Read a response character from the PC23.
    PCReadStr           - Read a response string from the PC23.
    PCintchk            - acknowledge inerupt flag.

    These procedures are based upon the information supplied in the PC23
    Compumotor Manual and the sample programs contained therein.

    Constants and types are those used to control/mask the PC23 board.  It
    is assumed that the board is at $300, this can be changed by modifying
    PC23Adr.
}

interface

uses Globals;

Const
    FailMsk  = $20;                         {Board fail mask used to read SB bit 5}
    StartMsk = $7f;                         {Recovery mask used to test for PC23
                                             recovery}
    IntrClr  = $20;                         {Clear interrupt output mask CB}
    ReStart  = $17;                         {Used to verify recovery}
    StopMsk  = $64;                         {Stop mask used to stop timer, set CB bit 2}
    Start    = $40;                         {Used to restart, clear CB bit 5}
    IDBMsk   = $10;                         {Mask used to read SB bit 4}
    IDB      = $70;                         {Used to set CB bit 4}
    ODBMsk   = $08;                         {Used to read CB bit 3}
    Ack      = $e0;                         {Used to set SB bit 7}
    NormCB   = $60;                         {Normal control byte, bits 5 & 6 set}
    PC23Adr  = PC23;                         {PC23 address}

type
    AnswerStr = string[12];                 {Responce string from PC23}
    CmdStr    = string[64];                 {Command string for PC23}

function Initialise(boardadr:integer):boolean;

Procedure PCWriteChar(boardadr:integer;alpha:char);

Procedure PCWriteCmd(boardadr:integer; var Cmd:CmdStr);

Procedure PCReadChar(boardadr:integer; var ascii:byte);

Procedure PCReadAnswer(boardadr:integer; var Response:AnswerStr);

procedure ShortDelay;

implementation

uses CRT;

procedure ShortDelay;
var i,j:longint;
begin
{$IFDEF NZ}
     for i:=1 to 20 do        {75=Wait for 0.1 millisec on a 66MHz 486DX2}
         j:=j+i-5;
{$ELSE}
     for i:=1 to 2 do
         j:=j+i-5;
{$ENDIF}
end;

procedure DisableInts;
begin
end;
procedure EnableInts;
begin
end;


function Initialise(boardadr:integer):boolean;
  var Status,Control,count:integer;
      sbyte:byte;
  begin
{$IFNDEF DUMMY}
    DisableInts;
    Control:=boardadr+1;                    {Set control address}
    Status:=boardadr+1;                     {Set status address}
    port[Control]:=StopMsk;                 {Set CB bit 2, stop the timer}
    repeat
      sbyte:=port[Status];                  {Read status until SB bit 5}
      delay(1);
    until ((sbyte and FailMsk) > 0);        {indicates board fail}
    port[Control]:=Start;                   {Restart timer}
    port[Control]:=NormCB;
    repeat
      sbyte:=port[Status];                  {Read Status until SB bit 5}
      count:=count+1;
      delay(1);                            {indicates board recovery or}
    until ((sbyte and StartMsk) = ReStart) or (count = 5000);
    if (count = 5000) then                {board failure}
      begin
        Initialise:=false;                  {Board failure or board address
        Halt;                                     is wrong}
        end;
    port[Control]:=IntrClr;                 {Shuttin off interrupt output}
     Delay(5);
    port[Control]:=NormCB;                  {Restoring normal CB}
    Initialise:=true;                    {Able to initialise board and reset}
    EnableInts;
{$ENDIF}
  end;

procedure PCWriteChar(boardadr:integer;alpha:char);
  var sbyte,ascii:byte;
      Status,Control,Command,i:integer;
  begin
{$IFNDEF DUMMY}
    Command:=boardadr;                      {Set PC23 command address}
    Control:=boardadr+1;                    {Set interface control address}
    Status:=boardadr+1;
    i:=0;
    repeat
      sbyte:=port[Status];                  {Read status until SB bit 4 is set}
      i:=i+1;
      ShortDelay;
    until ((sbyte and IDBMsk) > 0) or (i>5000);         {Indicated IDB ready}
    ascii:=ord(alpha);                      {Convert character to ASCII value}
    port[Command]:=ascii;                   {Write character to PC23}
    ShortDelay;
    port[Control]:=IDB;                     {Signal a valid character}
    ShortDelay;
    repeat
      i:=i+1;
      sbyte:=port[Status];                  {Read Status until SB bit 4 set}
      ShortDelay;
    until ((sbyte and IDBMsk) = 0) or (i>5000);
    port[Control]:=NormCB;                  {Indicated IDB is ready again}
    ShortDelay;
{$ENDIF}
  end;

procedure PCWriteCmd(boardadr:integer; var Cmd:CmdStr);
  var i:integer;
      alpha:char;
  begin
{$IFNDEF DUMMY}
    DisableInts;
    alpha:=chr(32);
    PCWriteChar(boardadr,alpha);
    for i:=1 to length(Cmd) do
      begin
        alpha:=Cmd[i];                      {Get next character to send}
        PCWriteChar(boardadr,alpha);        {Send character}
        end;
    alpha:=chr(13);
    PCWriteChar(boardadr,alpha);            {Terminate with CR}
    EnableInts;
{$ENDIF}
  end;

procedure PCReadChar(boardadr:integer; var ascii:byte);
  var sbyte:byte;
      i:integer;
  begin
{$IFNDEF DUMMY}
    sbyte:=port[PC23+1];                    {Read status for ODB ready}
    Shortdelay;
    ascii:=0;

    if ((sbyte and $08) <> 0) then
      begin
        i:=0;
        repeat
          sbyte:=port[PC23+1];              {Read Status until SB bit 3}
          i:=i+1;
          ShortDelay;
        until ((sbyte and $08) > 0) or (i>5000);     {indicates ODN ready}
        ascii:=port[PC23];                  {Read character byte from PC23}
        ShortDelay;
        port[PC23+1]:=Ack;                 {Signal read byte}
        ShortDelay;
        repeat
          sbyte:=port[PC23+1];              {Read Status until SB bit 3}
          i:=i+1;
          ShortDelay;
        until ((sbyte and $08) = 0) or (i>5000);     {indicates ODB busy}
        port[PC23+1]:=NormCB;              {Restore CB}
        ShortDelay;
      end;
{$ENDIF}
  end;

procedure PCReadAnswer(boardadr:integer; var Response:AnswerStr);
  var sbyte:byte;
      ascii:byte;
  begin
{$IFNDEF DUMMY}
    DisableInts;
    Response:='';                           {Initialise response string}
    sbyte:=port[PC23+1];                       {Read status for ODB ready}
    if ((sbyte and $08) <> 0) then
      repeat
        PCReadChar(PC23+1,ascii);              {Read PC23 response character}
        if (ascii > 0) then
          Response:=Response+chr(ascii);    {Add response to string}
      until (ascii = 13);  {Continue reading until CR}
    EnableInts;
{$ENDIF}
  end;


end.
