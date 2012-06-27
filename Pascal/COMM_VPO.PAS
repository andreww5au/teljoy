{ÛßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßÛ}
{Û                                                       Û}
{Û      Virtual Pascal Examples. Version 1.0.            Û}
{Û        Communication via device driver                Û}
{Û        The Art Of OS/2, Chapter 8,                    Û}
{Û      ÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÛ}
{Û      Copyright (c) 1992-1996 by Arthur Panov          Û}
{Û      VP/2 Version Copyright (C) 1996 fPrint UK Ltd    Û}
{Û                                                       Û}
{ßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßßß}

{ Virtual Pascal for OS/2 notes:                          }

Unit comm_vp;

{$Cdecl-,Optimize+,Frame+,G3+,R-,SmartLink+,V+,X+}

interface;

TYPE                                                                            {                            }
  BaudType = (B110,B150,B300,B600,B1200,B2400,B4800,B9600,B19200,B38400);       {-Baud rates supported       }
  ParityType = (None, Odd, Null, Even, MarkOff, Mark, SpaceOff, Space);         {-Parity types supported     }
                                                                                {                            }
                                                                                {                            }
PROCEDURE SetupCOMPort (Com, Baud, DataBits, Parity, StopBits : BYTE);          {                            }
PROCEDURE InstallInt (Com : BYTE);                                              {                            }
PROCEDURE RemoveInt (Com : BYTE);                                               {                            }
PROCEDURE EmptyBuffer (Buffer : BYTE; TrueInFalseOut : BOOLEAN);                {                            }
                                                                                {                            }
PROCEDURE WriteCOM (Com : BYTE; Data : STRING);                                 {                            }
                                                                                {                            }
FUNCTION  ReadCOM (Com : BYTE) : CHAR;                                          {                            }
FUNCTION  TimedReadCOM (Com : BYTE; VAR Data : CHAR) : BOOLEAN;                 {                            }

implementation;

Uses
  Use32, Crt, Dos, VPUtils, Os2Def, Os2Base;

Const
  STACK_SIZE   = 8192;
  BPS          = 9600;
  KBD_HANDLE   = 0;
  VIO_HANDLE   = 0;

Const
  LineCtrl : Record
    dataBits : Byte;
    parity   : Byte;
    stopBits : Byte;
  end = ( databits:8; Parity:0; StopBits: 0 );  { 8,N,1 }

Var
  idcbInfo : DcbInfo;
  hCom     : hFile;                    { COM handle   }
  inBuffer : Array[0..255] of Byte;    { input buffer }

{***************************************************************}
{*  Thread to read characters from COM1 and write to screen    *}
{***************************************************************}

Function ComThread( P : Pointer ) : Longint;
Var
  i           : ULong;
  ulBytesRead : ULong;
  rc          : ApiRet;

begin
  ulBytesRead := 0;
  rc := 0;
  while rc = 0 do
    begin
      rc := DosRead( hCom,
                     inBuffer,
                     1,
                     ulBytesRead );

      if ulBytesRead <> 0 then
        begin
          for i := 0 to ulBytesRead-1 do
            inBuffer[i] := inBuffer[i] and $7f;
          VioWrtTTY( @inBuffer,
                     ulBytesRead,
                     VIO_HANDLE);
        end;
     end;

   Writeln;
   Write  (' Could not read from COM1');
   Writeln('killing the LISTEN thread.');
   Writeln;
end;

{***************************************************************}
{*  main                                                       *}
{***************************************************************}

Const
  ulAction     : ApiRet = 0;
  rc           : ApiRet = 0;
  ulBaudRate   : ULong  = BPS;
  ulParmLen    : ULong  = 0;
  ComThreadId  : Tid    = 0;
  ulKbdChar    : ULong  = 0;

Var
  ulBytesWritten : ULong;

begin
  Writeln;
  Writeln(' Each keystroke is echoed to COM1, 9600,8,N,1');
  Writeln(' Ctrl-C or Ctrl-Brk to exit...');
  Writeln;

  { Open and initialize COM1                                     }

  if DosOpen( 'COM1',
              hCom,
              ulAction,
              0,
              0,
              1,
              $12,
              nil ) <> 0 then
    begin
      Writeln('COM1 not available or COM$.SYS not loaded');
      Halt(1);
    end;

  { Set data rate to 9600bps and line format to N81              }

  ulParmLen := sizeof( ulBaudRate );

  rc := DosDevIOCtl( hCom,
                     IOCTL_ASYNC,
                     ASYNC_SETBAUDRATE,
                     @ulBaudRate,
                     ulParmLen,
                     @ulParmLen,
                     nil,
                     0,
                     nil );

  ulParmLen := sizeof( lineCtrl );

  rc := DosDevIOCtl( hCom,
                     IOCTL_ASYNC,
                     ASYNC_SETLINECTRL,
                     @lineCtrl,
                     ulParmLen,
                     @ulParmLen,
                     nil,
                     0,
                     nil );

  { Set device control block parameters                          }

  ulParmLen := sizeof( DCBINFO );

  rc := DosDevIOCtl( hCom,
                     IOCTL_ASYNC,
                     ASYNC_GETDCBINFO,
                     nil,
                     0,
                     nil,
                     @idcbInfo,
                     ulParmLen,
                     @ulParmLen );

  With idcbInfo do
    begin
      usWriteTimeout := 6000;

      {************************************************************}
      {* 60 second write timeout                                  *}
      {************************************************************}

      usReadTimeout := 6000;

      {************************************************************}
      {* 60 second readtimeout                                    *}
      {************************************************************}

      fbCtlHndShake := MODE_DTR_CONTROL;

      {************************************************************}
      {* enable DTR                                               *}
      {************************************************************}

      fbFlowReplace := MODE_RTS_CONTROL;

      {************************************************************}
      {* enable RTS                                               *}
      {************************************************************}

      fbTimeout := MODE_WAIT_READ_TIMEOUT;
    end;

  {************************************************************}
  {* wait-for-something reads                                 *}
  {************************************************************}

  ulParmLen := sizeof( DCBINFO );

  rc := DosDevIOCtl( hCom,
                     IOCTL_ASYNC,
                     ASYNC_SETDCBINFO,
                     @idcbInfo,
                     ulParmLen,
                     @ulParmLen,
                     nil,
                     0,
                     nil );

  { Create a thread to monitor the serial port                   }

  ComThreadId := VPBeginThread( ComThread,
                                Stack_Size,
                                nil );

  { Monitor the keyboard and output typed characters
    Hit Ctrl-C to exit (primitive termination)                   }

  while rc = 0 do
    begin
      ulKbdChar := ord(Readkey);
      rc := DosWrite( hCom,
                      ulKbdChar,
                      1,
                      ulBytesWritten );
   end;

  Writeln;
  Writeln( ' Could not write to COM1, killing the MAIN thread.');
  Writeln;
  Halt( rc );
end.


