Unit comm_vp;

{$Cdecl-,Optimize+,Frame+,G3+,R-,SmartLink+,V+,X+}

interface

TYPE                                                                            {                            }
  BaudType = (B110,B150,B300,B600,B1200,B2400,B4800,B9600,B19200,B38400);
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

implementation

Uses
  Use32, Crt, Dos, VPUtils, Os2Def, Os2Base;

Const
  BaudTable: array[0..9] of integer = (110,150,300,600,1200,2400,4800,9600,19200,38400);


Var
  idcbInfo : DcbInfo;
  hCom1,hCom2,hCom3,hCom4 : hFile;                    { COM handles   }



PROCEDURE SetupCOMPort (Com, Baud, DataBits, Parity, StopBits : BYTE);

Const
{  ulAction     : ApiRet = 0; }
{  rc           : ApiRet = 0; }
{  ulParmLen    : ULong  = 0; }
  ComThreadId  : Tid    = 0;

Var
  ulAction   : ApiRet;
  rc         : ApiRet;
  ulParmLen  : ULong;
  hCom       : hFILE;
  port       : PChar;
  ulBaudRate : ULong;
  LineCtrl : Record
    dataBits : Byte;
    parity   : Byte;
    stopBits : Byte;
  end;  { ( databits:8; Parity:0; StopBits: 0 ) ==  ( 8,N,1 ) }

begin

  { Open and initialize COM1                                     }
  ulAction:=0;
  case com of
       1:port:='COM1';
       2:port:='COM2';
       3:port:='COM3';
       4:port:='COM4';
       else
           port:='';
  end;

  ulBaudRate:=BaudTable[Baud];
  LineCtrl.databits:=8; {force 8 databits}
  LineCtrl.parity:=0;   {force no parity}
  LineCtrl.stopbits:=0; {force 1 stop bit}

  if DosOpen( port,
              hCom,
              ulAction,
              0,
              0,
              1,
              $12,
              nil ) <> 0 then
    begin
      Writeln(port,' not available or COM$.SYS not loaded');
      Halt(1);
    end;

  { Set data rate and line format to N81              }

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
      usWriteTimeout := 60;

      {************************************************************}
      {* 0.6 second write timeout                                  *}
      {************************************************************}

      usReadTimeout := 6;

      {************************************************************}
      {* 0.06 second readtimeout                                    *}
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

  case com of
       1:hCom1:=hCom;
       2:hCom2:=hCom;
       3:hCom3:=hCom;
       4:hCom4:=hCom;
  end;


end;   {of SetupCOMport}

procedure InstallInt(com:byte);
begin
end;

procedure RemoveInt(com:byte);
var hCom:hFILE;
begin
  case com of
       1:hCom:=hCom1;
       2:hCom:=hCom2;
       3:hCom:=hCom3;
       4:hCom:=hCom4;
  end;

  DosClose(hCom);

  case com of
       1:hCom1:=0;
       2:hCom2:=0;
       3:hCom3:=0;
       4:hCom4:=0;
  end;

end;

PROCEDURE EmptyBuffer (Buffer : BYTE; TrueInFalseOut : BOOLEAN);                {                            }
var inbuffer:array[0..63] of byte;
    cbread:ULONG;
    hCom:hFILE;
begin
     if TrueInFalseOut then
        begin
             case Buffer of
                  1:hCom:=hCom1;
                  2:hCom:=hCom2;
                  3:hCom:=hCom3;
                  4:hCom:=hCom4;
             end;
             repeat
                   DosRead(hCom,inbuffer,sizeof(buffer),cbread);
             until cbread=0;
        end;
end;

PROCEDURE WriteCOM (Com : BYTE; Data : STRING);
var
   hCom:hFILE;
   outbuffer:array[1..512] of byte;
   cbWritten:ULONG;
   i:integer;
begin
     case com of
          1:hCom:=hCom1;
          2:hCom:=hCom2;
          3:hCom:=hCom3;
          4:hCom:=hCom4;
     end;
     if length(data) <=512 then
        for i:=1 to length(data) do
            outbuffer[i]:=ord(data[i])
     else
         begin
              writeln('Buffer too small to send string');
              data:='';
         end;
     DosWrite(hCom,outbuffer,length(data),cbWritten);
end;



FUNCTION  ReadCOM (Com : BYTE) : CHAR;
var
   hCom:hFILE;
   inbuffer:array[0..63] of byte;
   cbRead:ULONG;
begin
     case com of
          1:hCom:=hCom1;
          2:hCom:=hCom2;
          3:hCom:=hCom3;
          4:hCom:=hCom4;
     end;
     repeat
           DosRead(hCom,inbuffer,1,cbRead);
     until cbRead=1;

     ReadCOM:=chr(inbuffer[0]);
end;



FUNCTION  TimedReadCOM (Com : BYTE; VAR Data : CHAR) : BOOLEAN;
var
   hCom:hFILE;
   inbuffer:array[0..63] of byte;
   cbRead:ULONG;
begin
     case com of
          1:hCom:=hCom1;
          2:hCom:=hCom2;
          3:hCom:=hCom3;
          4:hCom:=hCom4;
     end;

     DosRead(hCom,inbuffer,1,cbRead);

     data:=chr(inbuffer[0]);
     TimedReadCOM:=(cbRead=1);
end;

begin   {unit init}
     hCom1:=0;
     hCom2:=0;
     hCom3:=0;
     hCom4:=0;
end.
