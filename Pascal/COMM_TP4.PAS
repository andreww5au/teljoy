UNIT Comm_TP4;                                                                  {-This is the comment column }
                                                                                { which will be used to tell }
{$S-} { Interrupt handlers should not be compiled with stack checking enabled } {-Else the system may crash! }
                                                                                {                            }
{$DEFINE ErrorChecking}                                                         {-Enable/Disable Error Check }
{$DEFINE NoMessageCode}                                                         {-Enable/Disable Error Msgs  }
{.$DEFINE FWriteCOM}                                                             {-WriteCOM is a Func or Proc }
                                                                                {                            }
INTERFACE                                                                       {                            }
                                                                                {                            }
USES DOS, CRT;                                                                  {                            }
                                                                                {                            }
CONST                                                                           {                            }
  MaxPorts = 2;                                                                 {-Max # of COM ports to use  }
  MaxInSize = 255;                                                              {-Maximum input buffer size  }
  MaxOutSize = 511;                                                             {-Maximum output buffer size }
                                                                                {                            }
  THR = 0;    { Transmit Holding Register  }                                    {-These constants are used   }
  RHR = 0;    { Receive Holding Register   }                                    { to make the code readable. }
  DLL = 0;    { Divisor Latch Register LSB }                                    { They are the offsets from  }
  IER = 1;    { Interrupt Enable Register  }                                    { the base address of the    }
  DLM = 1;    { Divisor Latch Register MSB }                                    { 8250 UART. If, for example,}
  IIR = 2;    { Interrupt ID Register      }                                    { you need the value of the  }
  LCR = 3;    { Line Control Register      }                                    { #3 Line Status Register,   }
  MCR = 4;    { Modem Control Register     }                                    { you could get it using:    }
  LSR = 5;    { Line Status Register       }                                    {                            }
  MSR = 6;    { Modem Status Register      }                                    {  PORT [COMPort [3] + LSR]  }
                                                                                {                            }
  { The following declarations are crucial to the operation of this program. }  { Improper setting of the    }
  { I would advise you not to change the information unless you are sure you }  { IRQNmbr array may cause a  }
  { know what you are doing.  See the .DOC file for further information. For }  { system crash!              }
  { standard MaxPorts settings of 1 - 4, move the comment bracket as needed. }  {                            }
                                                                                {                            }
  COMNmbr  : ARRAY [1..MaxPorts] OF BYTE    = (     1,     2); {,     3,     4 );-Define the COM port number }
  COMPort  : ARRAY [1..MaxPorts] OF WORD    = ( $03F8, $02F8); {, $03E8, $02E8 );-Base addresses 8250 Regs   }
  IRQNmbr  : ARRAY [1..MaxPorts] OF BYTE    = (     4,     3); {,     4,     3 );-IRQ numbers of the ports   }
  ChainInt : ARRAY [1..MaxPorts] OF BOOLEAN = ( FALSE, FALSE); {, FALSE, FALSE );-When port interrupt done,  }
                                                                                { jump to OldIntVector [x]?  }
TYPE                                                                            {                            }
  BaudType = (B110,B150,B300,B600,B1200,B2400,B4800,B9600,B19200,B38400);       {-Baud rates supported       }
  ParityType = (None, Odd, Null, Even, MarkOff, Mark, SpaceOff, Space);         {-Parity types supported     }
  ProcNameType = STRING [20];                                                   {-Used by error checking code}
                                                                                {                            }
VAR                                                                             {                            }
  Framing, Overrun, Parity, Break : ARRAY [1..MaxPorts] OF WORD;                {-Port error counters        }
  OutBuffer : ARRAY [1..MaxPorts, 0..MaxOutSize] OF BYTE;                       {-Port output buffers        }
  InBuffer : ARRAY [1..MaxPorts, 0..MaxInSize] OF BYTE;                         {-Port input buffers         }
  CTS, DSR, RI, CD : ARRAY [1..MaxPorts] OF BOOLEAN;                            {-Port input line status     }
  OutHead, OutTail : ARRAY [1..MaxPorts] OF WORD;                               {-Output buffer pointers     }
  InHead, InTail : ARRAY [1..MaxPorts] OF WORD;                                 {-Input buffer pointers      }
  IntInstalled : ARRAY [1..MaxPorts] OF BOOLEAN;                                {-TRUE if interrupt in place }
  DTR_RTS : ARRAY [1..MaxPorts] OF BOOLEAN;                                     {-Allowed to alter DTR/RTS?  }
  ErrorCode, ErrorPort : BYTE;                                                  {-Error type code & the port }
  {$IFNDEF NoMessageCode}                                                       { which had the error.       }
    ErrMsgX, ErrMsgY : BYTE;                                                    {-Error message coordinates  }
    ShowMessages : BOOLEAN;                                                     {-FALSE disables the error   }
  {$ENDIF}                                                                      { messages/TRUE enables them.}
                                                                                {                            }
PROCEDURE Set_DTR_RTS (Com : BYTE; Status : BOOLEAN);                           {                            }
PROCEDURE SetupCOMPort (Com, Baud, DataBits, Parity, StopBits : BYTE);          {                            }
PROCEDURE InstallInt (Com : BYTE);                                              {                            }
PROCEDURE RemoveInt (Com : BYTE);                                               {                            }
PROCEDURE EmptyBuffer (Buffer : BYTE; TrueInFalseOut : BOOLEAN);                {                            }
                                                                                {                            }
{$IFDEF FWriteCOM}                                                              {                            }
FUNCTION WriteCOM (Com : BYTE; Data : STRING) : BOOLEAN;                        {                            }
{$ELSE}                                                                         {                            }
PROCEDURE WriteCOM (Com : BYTE; Data : STRING);                                 {                            }
{$ENDIF}                                                                        {                            }
                                                                                {                            }
PROCEDURE IWriteCOM (Com : BYTE; Data : STRING);                                {                            }
FUNCTION  ReadCOM (Com : BYTE) : CHAR;                                          {                            }
FUNCTION  TimedReadCOM (Com : BYTE; VAR Data : CHAR) : BOOLEAN;                 {                            }
                                                                                {                            }
IMPLEMENTATION                                                                  {                            }
                                                                                {                            }
VAR                                                                             {                            }
  OldIntVector : ARRAY [1..MaxPorts] OF POINTER;                                {-Original COMx int. vectors }
  IRQMask, Loop : BYTE;                                                         {                            }
  ExitSave : POINTER;                                                           {-Saves original ExitProc    }
                                                                                {                            }
{ This procedure sets the global error identification variables ErrorCode and ErrorPort.  It also prints an  }
{ appropriate error message if the $DEFINE NoMessageCode directive was not present at compile time and if    }
{ ShowMessages is TRUE at run-time.  The error messages are displayed at the current cursor position when    }
{ ErrMsgX and/or ErrMsgY = 0 (Default).  If the calling program needs the messages at a specific location,   }
{ it must set ErrMsgX and ErrMsgY to the desired screen coordinates.  Error messages consist of a beep, the  }
{ procedure or function in which the error took place, the port number, and a description of the problem     }
{ encountered.  At all times, ErrorCode and ErrorPort can also be used to find error conditions.  ErrorCode  }
{ is 0 for no errors, or a value from 1-5 describing the error.  ErrorPort is the handler number which had   }
{ the problem.  These values are valid for the last serial operation requested.                              }
                                                                                {                            }
PROCEDURE MakeError (Code, Port : BYTE; ProcName : ProcNameType);               {                            }
BEGIN                                                                           {                            }
  ErrorCode := Code;                                                            {-Set the global error type  }
  ErrorPort := Port;                                                            { and port variables.        }
  {$IFNDEF NoMessageCode}                                                       {                            }
    IF ShowMessages                                                             {                            }
      THEN BEGIN                                                                {                            }
             IF (ErrMsgX > 0) THEN GOTOXY (ErrMsgX, WHEREY);                    {-Print error messages. A 0  }
             IF (ErrMsgY > 0) THEN GOTOXY (WHEREX, ErrMsgY);                    { coordinate uses current    }
             WRITE (ProcName, ' ERROR: ', #7);                                  { cursor position.           }
             CASE Code OF                                                       {                            }
               1 : WRITELN ('Invalid port # ', Port);                           { 1 <= Good Port <= MaxPorts }
               2 : WRITELN ('Port # ', Port, 'already installed');              {-Use InstallInt once/port   }
               3 : WRITELN ('Port # ', Port, 'not installed yet');              {-RemoveInt w/o InstallInt   }
               4 : WRITELN ('Timeout writing port # ', Port);                   {-WriteCOM error             }
               5 : WRITELN ('Timeout reading port # ', Port);                   {-TimedReadCOM error         }
             END;                                                               {                            }
           END;                                                                 {                            }
  {$ENDIF}                                                                      {                            }
END;                                                                            {                            }
                                                                                {                            }
{ This function is used to make sure that the requested ports are valid and if the interrupt handlers are    }
{ properly installed or uninstalled.  It calls MakeError to set the global error variables ErrorCode and     }
{ ErrorPort, and to print error messages.  Status should be set to 0 if the port handler should not be       }
{ installed yet, and 1 if it is supposed to be installed already.  Use a status of -1 if the installation    }
{ status is not critical.  ProcName is used to pass the procedure or function name to MakeError so it can be }
{ used in an error message. A TRUE is returned if everything checks out okay, otherwise a FALSE is returned. }
                                                                                {                            }
FUNCTION ValidPort (Port:BYTE; Status:INTEGER; ProcName:ProcNameType):BOOLEAN;  {                            }
BEGIN                                                                           {                            }
  ErrorCode := 0;                                                               {-Default of no errors found }
  IF (Port < 1) OR (Port > MaxPorts)                                            {-Check requested port # for }
    THEN MakeError (1, Port, ProcName)                                          { validity.                  }
    ELSE IF (Status >= 0) AND (ORD (IntInstalled [Port]) <> Status)             {-Check port installation    }
           THEN MakeError (2+Status, Port, ProcName);                           { state with needed status.  }
  ValidPort := (ErrorCode = 0);                                                 {-Returns TRUE if no errors  }
END;                                                                            {                            }
                                                                                {                            }
{ This procedure changes the setting of DTR & RTS if the global variable DTR_RTS is set to TRUE.  The port   }
{ and the desired state are passed as parameters.  TRUE for on, FALSE for off.  Since hardware handshaking   }
{ requirements vary according to the hardware being used, you may have to rewrite Set_DTR_RTS to accommodate }
{ the hardware.  Bit 0 controls DTR and bit 1 controls RTS.  Writing a 0 to the bit will turn the line on.   }
                                                                                {                            }
PROCEDURE Set_DTR_RTS (Com : BYTE; Status : BOOLEAN);                           {                            }
BEGIN                                                                           {                            }
  {$IFDEF ErrorChecking}                                                        {                            }
    IF NOT ValidPort (Com, -1, 'Set_DTR_RTS') THEN EXIT;                        {-Optional error trapping    }
  {$ENDIF}                                                                      {                            }
  IF DTR_RTS [Com]                                                              {-Provided to allow modem    }
    THEN IF Status                                                              { programs to prevent the    }
           THEN PORT [COMPort [Com]+MCR] := PORT [COMPort [Com]+MCR] AND $FC    { modem from being hung up   }
           ELSE PORT [COMPort [Com]+MCR] := PORT [COMPort [Com]+MCR] OR $03;    { during port setups due to  }
END;                                                                            { dropping DTR and/or RTS.   }
                                                                                {                            }
{ This procedure sets up a selected serial port to use specified parameters. Com specifies the port to set   }
{ up.  The Baud parameter must be in the range 0 to 9, and is not range checked, but its maximum valid value }
{ is determined by the number of entries in BaudTable.  BaudType documents the baud rates supported by       }
{ BaudTable.  ParityType is provided to document the parity settings allowed.  Use ORD() to get the correct  }
{ value to pass: ORD(B110) returns the BYTE that selects 110 baud and ORD(None) gives the value that selects }
{ no parity.  1.5 stop bits are used when StopBits = 2 AND DataBits = 5, otherwise StopBits will set the     }
{ indicated number of stop bits in the range 1 to 2.  DataBits may be set with 5 to 8 for the number of data }
{ bits to use.  Mark parity means that the parity bit is always set to 0. Space parity means that the parity }
{ bit is always set to 1.  MarkOff, SpaceOff, NONE, & NULL all disable parity but are here for completeness. }
                                                                                {                            }
PROCEDURE SetupCOMPort (Com, Baud, DataBits, Parity, StopBits : BYTE);          {                            }
CONST BaudTable : ARRAY [0..9] OF WORD = ($0417, $0300, $0180, $00C0, $0060,    { Set baud rate of 8250 when }
                                          $0030, $0018, $000C, $0006, $0003);   { written to DLL & DLM.      }
VAR                                                                             {                            }
  Temporary : BYTE;                                                             {                            }
BEGIN                                                                           {                            }
  {$IFDEF ErrorChecking}                                                        {                            }
    IF NOT ValidPort (Com, -1, 'SetupCOMPort') THEN EXIT;                       {-Optional error trapping    }
  {$ENDIF}                                                                      {                            }
  Set_DTR_RTS (Com, FALSE);                                                     {                            }
  PORT [COMPort [Com] + LCR] := PORT [COMPort [Com] + LCR] OR $80;              {-Set DLL & DLM active       }
  PORT [COMPort [Com] + DLL] := LO (BaudTable [Baud]);                          {-Set the baud rate with the }
  PORT [COMPort [Com] + DLM] := HI (BaudTable [Baud]);                          { predefined divisor values. }
  Temporary := (DataBits - 5) AND $03 OR (((StopBits - 1) SHL 2) AND $04);      {-Set data bits, stop bits,  }
  PORT [COMPort [Com] + LCR] := Temporary OR ((Parity SHL 3) AND $38);          { and parity protocol.       }
  Set_DTR_RTS (Com, TRUE);                                                      {                            }
END;                                                                            {                            }
                                                                                {                            }
{ This procedure handles all interrupts from the 8250 communications chip.  All interrupt types are at least }
{ minimally supported.  Enough code is present to help you know how to modify the code for your specific     }
{ requirements.  Incoming data is ignored if the buffer is full, otherwise it is placed into the InBuffer    }
{ circular queue. Data to be transmitted by interrupt is taken from the OutBuffer queue.  The transmitter is }
{ the only interrupt which has to be manually invoked.  Do so by placing the first character of each trans-  }
{ mission into the THR.  It automatically shuts off when all the data in the buffer has been sent. The other }
{ interrupt types will take care of themselves once enabled. Modem/Port input lines may be monitored by this }
{ handler.  BOOLEAN arrays CTS, DSR, RI, and CD always show current status of these lines IF the interrupt   }
{ handler is active and the Modem Status Change interrupt has been enabled.  A TRUE indicates the signal is  }
{ active.  CD and RI are very helpful for modem related programs.  Line Status errors are counted.  It is up }
{ to you add any corrective action.  All ports with interrupts pending on the IRQ level which invoked this   }
{ handler are processed regardless of which port generated the actual interrupt. This is simple to implement,}
{ yet it preserves the interrupt priority handling between ports.                                            }
                                                                                {                            }
{$F+}                                                                           {-Interrupt handlers MUST be }

PROCEDURE IntHandler;                                                 { FAR calls.                 }
VAR                                                                             {                            }
  Com,                                                                          {-Port being serviced        }
  IRQ,                                                                          {-IRQ # of this interrupt    }
  IMR,                                                                          {-Interrupt Mask Register    }
  Temp : BYTE;                                                                  {-Temporary for misc. uses   }
BEGIN                                                                           {                            }
  IRQ := 0;                                                                     {                            }
  IMR := PORT [$21];                                                            {-Backup IMR for later use   }
  PORT [$20] := $0B;                                                            {-Request 8259 ISR read next }
  Temp := PORT [$20];                                                           {-Get the 8259 ISR value     }
  WHILE (Temp AND 1 = 0) DO                                                     {-Upon loop completion, IRQ  }
    BEGIN                                                                       { will contain the IRQ # of  }
      Temp := Temp SHR 1;                                                       { the interrupt in progress. }
      INC (IRQ);                                                                {                            }
    END;                                                                        {                            }
  PORT [$21] := IMR OR IRQMask;                                                 {-Disable Comm_TP4 interrupts}
  FOR Com := 1 TO MaxPorts DO                                                   {-Process all ports with the }
   IF (IRQNmbr [Com] = IRQ) AND (IntInstalled [Com])                            { same IRQ level which made  }
    THEN                                                                        { this interrupt happen.     }
     BEGIN                                                                      {                            }
      PORT [COMPort [Com] + LCR] := PORT [COMPort [Com] + LCR] AND $7F;         {-Set THR, RHR & IER active  }
      CASE PORT [COMPort [Com] + IIR] AND $07 OF                                {-Identify interrupt type    }
       0 : BEGIN                                                                {                            }
            Temp := PORT [COMPort [Com] + MSR];                                 {    MODEM STATUS CHANGES    }
            CD  [Com] := $80 AND Temp <> 0;                                     {       Carrier Detect       }
            CTS [Com] := $10 AND Temp <> 0;                                     {       Clear To Send        }
            DSR [Com] := $20 AND Temp <> 0;                                     {       Data Set Ready       }
            RI  [Com] := $40 AND Temp <> 0;                                     {       Ring Indicator       }
           END;                                                                 {                            }
       2 : BEGIN                                                                {                            }
            IF (OutHead [Com] = OutTail [Com])                                  {  TRANSMIT REGISTER EMPTY   }
             THEN                                                               {                            }
              PORT [COMPort [Com] + IER] := PORT [COMPort [Com] + IER] AND $FD  {  If no more data to send,  }
             ELSE                                                               {  shut off the transmitter. }
              BEGIN                                                             {  Otherwise, send the next  }
               PORT [COMPort [Com] + THR] := OutBuffer [Com, OutHead [Com]];    {  byte, and remove it from  }
               OutHead [Com] := (OutHead [Com] + 1) MOD (MaxOutSize + 1);       {  the buffer.               }
              END;                                                              {                            }
           END;                                                                 {                            }
       4 : BEGIN                                                                {                            }
            IF (InTail [Com] + 1) MOD (MaxInSize + 1) <> InHead [Com]           {   RECEIVE REGISTER FULL    }
             THEN                                                               {                            }
              BEGIN                                                             { If the buffer is not full, }
               InBuffer [Com, InTail [Com]] := PORT [COMPort [Com] + RHR];      { add the character and set  }
               InTail [Com] := (InTail [Com] + 1) MOD (MaxInSize + 1);          { the queue buffer pointer.  }
              END                                                               { Otherwise, the character   }
             ELSE                                                               { is read but not stored.    }
              BEGIN                                                             {                            }
               IF (PORT [COMPort [Com] + RHR] = $00) THEN { DO Nothing };       {                            }
              END;                                                              {                            }
           END;                                                                 {                            }
       6 : BEGIN                                                                { LINE STATUS CHANGE & ERROR }
             Temp := PORT [COMPort [Com] + LSR] AND $1E;                        {   Just count the errors    }
             IF (Temp AND $02 <> 0) THEN INC (Overrun [Com]);                   {       Overrun Error        }
             IF (Temp AND $04 <> 0) THEN INC (Parity [Com]);                    {       Parity Error         }
             IF (Temp AND $08 <> 0) THEN INC (Framing [Com]);                   {       Framing Error        }
             IF (Temp AND $10 <> 0) THEN INC (Break [Com]);                     {       Break Interrupt      }
           END;                                                                 {                            }
      END;                                                                      {                            }
     END;                                                                       {                            }
  PORT [$21] := IMR;                                                            {-Enable Comm_TP4 interrupts }
  PORT [$20] := $20;                                                            {-Notify 8259 that interrupt }
END;                                                                            { has been completed.        }
{$F-}                                                                           {                            }
                                                                                {                            }
{ This procedure installs and enables the specified serial port interrupt.  All port input line monitoring   }
{ variables are set to match the actual line states.  The old serial port interrupt vector is saved so it    }
{ can be reinstalled when we remove our serial port interrupt.  DTR and RTS are forced to the ready state.   }
{ The 8250 interrupts are enabled by ORing the MCR with $08.  To enable all four 8250 interrupt types, write }
{ $0F to the IER.  (Receive Buffer Full, Line Status, & Modem Status interrupts are enabled by writing $0D   }
{ to the IER).  ORing $EF with PORT [$21] enables IRQ4 (COM1 or COM3), while $F7 enables IRQ3 (COM2 or COM4).}
{ Hardware interrupts should be disabled during the installation process since the 8259 ports are being set. }
{ Error checking is always in place since a crash could occur if it is used when a the handler for the same  }
{ port has already been installed.                                                                           }
                                                                                {                            }
PROCEDURE InstallInt (Com : BYTE);                                              {                            }
VAR                                                                             {                            }
  Temporary : BYTE;                                                             {                            }
BEGIN                                                                           {                            }
  IF ValidPort (Com, 0, 'InstallInt')                                           {-Error checking important!  }
    THEN                                                                        {                            }
      BEGIN                                                                     {                            }
        Temporary := PORT [COMPort [Com]+MSR];                                  {                            }
        CD  [Com] := ($80 AND Temporary <> 0);                                  {-Carrier Detect status      }
        CTS [Com] := ($10 AND Temporary <> 0);                                  {-Clear to Send status       }
        DSR [Com] := ($20 AND Temporary <> 0);                                  {-Data Set Ready status      }
        RI  [Com] := ($40 AND Temporary <> 0);                                  {-Ring Indicator status      }
        Temporary := PORT [COMPort [Com] + LSR];                                {-Reset interrupts that were }
        Temporary := PORT [COMPort [Com] + RHR];                                { waiting to be processed.   }
        Temporary := 1 SHL IRQNmbr [Com];                                       {-If other port using same   }
        IF (IRQMask AND Temporary) = 0                                          { IRQ then nothing must be   }
          THEN BEGIN                                                            { done to 8259 or vectors.   }
                 IRQMask := IRQMask OR Temporary;                               {-Update interrupt record    }
                 PORT [$21] := PORT [$21] AND NOT Temporary;                    {-Enable 8259 IRQ handling   }
               END;                                                             {                            }
        PORT [COMPort [Com] + MCR] := PORT [COMPort [Com] + MCR] OR $08;        {-Enable 8250 interrupt line }
        PORT [COMPort [Com] + LCR] := PORT [COMPort [Com] + LCR] AND $7F;       {-Set THR/RHR/IER active     }
        PORT [COMPort [Com] + IER] := $01;                                      {-Enable 8250 interrupts     }
        IntInstalled [Com] := TRUE;                                             {-The interrupt is installed }
        Set_DTR_RTS (Com, TRUE);                                                {-DTR/RTS on so the other    }
      END;                                                                      { to receive data.           }
END;                                                                            {                            }
                                                                                {                            }
{ This procedure removes the specified serial port interrupt and reinstalls the original interrupt vectors.  }
{ DTR & RTS are set OFF and 8250 interrupt line is disabled by ANDing the MCR with $F7.  All 8250 interrupt  }
{ types are disabled by writing $00 to the IER.  ORing $10 with PORT [$21] disables IRQ4 (COM1 or COM3),     }
{ while $08 disables IRQ3 (COM2 or COM4).  Hardware interrupts must be disabled since the 8259 ports are     }
{ being set.  Some error checking is always in place since attempting RemoveInt on a handler which has not   }
{ been installed can cause the computer to eventually crash.                                                 }
                                                                                {                            }
PROCEDURE RemoveInt (Com : BYTE);                                               {                            }
VAR                                                                             {                            }
  Temporary : BYTE;                                                             {                            }
BEGIN                                                                           {                            }
  IF ValidPort (Com, 1, 'RemoveInt')                                            {-Error checking important!  }
    THEN                                                                        {                            }
      BEGIN                                                                     {                            }
        Set_DTR_RTS (Com, FALSE);                                               {-DTR/RTS off                }
        IntInstalled [Com] := FALSE;                                            {-Uninstalling interrupt     }
        PORT [COMPort [Com] + MCR] := PORT [COMPort [Com] + MCR] AND $F7;       {-Disable 8250 interrupt line}
        PORT [COMPort [Com] + LCR] := PORT [COMPort [Com] + LCR] AND $7F;       {-Set THR, THE & IER active  }
        PORT [COMPort [Com] + IER] := $00;                                      {-Disable 8250 interrupts    }
        Temporary := 1 SHL IRQNmbr [Com];                                       {-Get bit for IRQ mask       }
        IF (IRQMask AND Temporary) <> 0                                         {-If no other Comm_TP4       }
          THEN BEGIN                                                            { interrupt is on this IRQ:  }
                 PORT [$21] := PORT [$21] OR Temporary;                         { Disable 8259 IRQ handling, }
                 IRQMask := IRQMask AND NOT Temporary;                          { and update IRQ mask.       }
               END;                                                             {                            }
      END;                                                                      {                            }
END;                                                                            {                            }
                                                                                {                            }
{ This procedure is provided for situations where you want to be sure that any of the serial port buffers    }
{ are empty.  This could be used for aborting an interrupt driven transmission or for clearing unwanted data }
{ from the input buffers.  The first parameter is the buffer number and the second parameter is TRUE for the }
{ input buffer or FALSE for the output buffer.  A buffer number of 0 causes all buffers to be emptied.       }
                                                                                {                            }
PROCEDURE EmptyBuffer (Buffer : BYTE; TrueInFalseOut : BOOLEAN);                {                            }
VAR                                                                             {                            }
  LoopVar : BYTE;                                                               {                            }
BEGIN                                                                           {                            }
  FOR LoopVar := 1 to MaxPorts DO                                               {-A buffer number of 0 will  }
    IF (Buffer = 0) OR (LoopVar = Buffer)                                       { empty all buffers. Invalid }
      THEN BEGIN                                                                { buffer numbers do nothing. }
             IF TrueInFalseOut                                                  { before changing pointers.  }
               THEN InHead [LoopVar] := InTail [LoopVar]                        {-Clear an input buffer      }
               ELSE OutHead [LoopVar] := OutTail [LoopVar];                     {-Clear an output buffer     }
           END;                                                                 {                            }
END;                                                                            {                            }
                                                                                {                            }
{ This function/procedure writes character or string data to the serial port.  It does this by reading and   }
{ writing to the 8250 communications chip.  This is an example that may be modified to suit your purposes.   }
{ As is, it pauses the program while it sends the data.  If it cannot send a character after 65535 tries, it }
{ aborts the sending process.  Use the conditional compilation directive $DEFINE FWriteCOM in order to make  }
{ WriteCOM a function which returns a BOOLEAN TRUE if the transmission did not timeout. The statement: (PORT }
{ [COMPort [Com]+LSR] AND $20) <> $20 indicates when the THR is ready for a new character to send.  CTS and  }
{ DSR are not checked, but if you want to check for them (PORT [COMPort [Com]+MSR] AND $30) must equal $30.  }
                                                                                {                            }
{$IFDEF FWriteCOM}                                                              {-A $DEFINE/$UNDEF FWriteCOM }
  FUNCTION WriteCOM (Com : BYTE; Data : STRING) : BOOLEAN;                      { directive determines if    }
{$ELSE}                                                                         { WriteCOM is a function or  }
  PROCEDURE WriteCOM (Com : BYTE; Data : STRING);                               { a procedure.               }
{$ENDIF}                                                                        {                            }
                                                                                {                            }
VAR                                                                             {                            }
 LoopVar,                                                                       {-Pointer to output char     }
 TimeLoop : WORD;                                                               {-Timeout counter variable   }
 TimeOut, Ready : BOOLEAN;                                                      {-TRUE if port timed out     }
BEGIN                                                                           {                            }
  {$IFDEF ErrorChecking}                                                        {                            }
    IF NOT ValidPort (Com, 1, 'WriteCOM') THEN EXIT;                            {-Optional error trapping    }
  {$ENDIF}                                                                      {                            }
  LoopVar := 0;                                                                 {                            }
  TimeOut := FALSE;                                                             {                            }
  WHILE (LoopVar < LENGTH (Data)) AND NOT TimeOut DO                            {-Send the data one char at  }
    BEGIN                                                                       { a time unless the port was }
      INC (LoopVar);                                                            { timed out.                 }
      TimeLoop := 0;                                                            {                            }
      REPEAT                                                                    {                            }
        Ready := (PORT [COMPort [Com]+LSR] AND $20) <> 0;                       {                            }
        INC (TimeLoop);                                                         {                            }
      UNTIL Ready OR (TimeLoop = 65535);                                        {                            }
      IF Ready                                                                  {                            }
        THEN BEGIN                                                              {                            }
               PORT [COMPort [Com]+LCR] := PORT [COMPort [Com]+LCR] AND $7F;    {-Allow THR,RHR & IER access }
               PORT [COMPort [Com]+THR] := ORD (Data [LoopVar]);                {-Put the data to send in    }
             END                                                                { the THR.                   }
        ELSE BEGIN                                                              {                            }
               TimeOut := TRUE;                                                 {-WriteCOM aborts if the THR }
               {$IFDEF ErrorChecking}                                           { takes too long to become   }
                 MakeError (4, Com, 'WriteCOM');                                { empty & optionally creates }
               {$ENDIF}                                                         { an error condition.        }
             END;                                                               {                            }
    END;                                                                        {                            }
  {$IFDEF FWriteCOM}                                                            {-With a compiler directive  }
    WriteCOM := NOT TimeOut;                                                    { of $DEFINE FWriteCOM, then }
  {$ENDIF}                                                                      { WriteCOM is a function and }
END;                                                                            { returns TRUE if no timeout }
                                                                                {                            }
{ This procedure is an example of how to write an interrupt driven send routine.  The main idea is that you  }
{ add data to the output buffer, then you get things going by manually placing one byte into the transmitter }
{ holding register.  After doing this, the rest of the buffer will be sent automatically.  Strenuous testing }
{ of this procedure under very high data rates has not been done, and it might be possible to rewrite it to  }
{ provide better throughput.  Data is the information to send to the port in either CHAR or STRING form.  It }
{ is impractical to use this procedure for sending single characters since it calls WriteCOM at least once.  }
{ It is best suited for high volume data transfers.  Interrupts should be off during buffer operations.      }
                                                                                {                            }
PROCEDURE IWriteCOM (Com : BYTE; Data : STRING);                                {                            }
VAR                                                                             {                            }
  BuffFull : BOOLEAN;                                                           {-TRUE if output buffer full }
  StartChr : CHAR;                                                              {-Temporary Buffer           }
  Loop : WORD;                                                                  {-Points to current Data item}
BEGIN                                                                           {                            }
  {$IFDEF ErrorChecking}                                                        {                            }
    IF NOT ValidPort (Com, 1, 'IWriteCOM') THEN EXIT;                           {-Optional error trapping    }
  {$ENDIF}                                                                      {                            }
  Loop := 1;                                                                    {                            }
  PORT [COMPort [Com]+LCR] := PORT [COMPort [Com]+LCR] AND $7F;                 {-Enable access to 8250 IER  }
  WHILE (Loop <= LENGTH (Data)) DO                                              {-Load the output buffer one }
    BEGIN                                                                       { byte at a time.            }
      BuffFull := (OutTail [Com] + 1) MOD (MaxOutSize+1) = OutHead[Com];        {-Is the buffer full?        }
      IF NOT BuffFull                                                           {-If not, add a character to }
        THEN BEGIN                                                              { buffer and update pointers }
               OutBuffer [Com, OutTail [Com]] := ORD (Data [Loop]);             {                            }
               OutTail [Com] := (OutTail [Com] + 1) MOD (MaxOutSize + 1);       { NOTE: Interrupts should be }
               INC (Loop);                                                      { enabled within the Loop so }
             END;                                                               { the interrupt can empty    }
      IF BuffFull OR (Loop > LENGTH (Data))                                     {-Check the interrupt status }
        THEN                                                                    { if the buffer gets full or }
          BEGIN                                                                 { after data is all loaded.  }
            IF (PORT [COMPort [Com] + IER] AND $02 <> 2)                        {-If the transmit interrupt  }
              THEN                                                              { is not on, start it up.    }
                BEGIN                                                           {                            }
                  StartChr := CHR (OutBuffer [Com, OutHead [Com]]);             {-Get the first character &  }
                  OutHead [Com] := (OutHead [Com] + 1) MOD (MaxOutSize + 1);    { take it out of the buffer. }
                  PORT [COMPort [Com]+IER] := PORT [COMPort [Com]+IER] OR $02;  {-Turn transmit interrupt on }
                  {$IFDEF FWriteCOM}                                            {-Kickstart the transmitter  }
                    IF WriteCOM (Com, StartChr) THEN {};                        { interrupt by sending one   }
                  {$ELSE}                                                       { character.  WriteCOM is    }
                    WriteCOM (Com, StartChr);                                   { used for simplicity.       }
                  {$ENDIF}                                                      {                            }
                END;                                                            {                            }
          END;                                                                  {                            }
    END;                                                                        {                            }
END;                                                                            {                            }
                                                                                {                            }
{ This function is an example of how to get a character from the serial port. As is, if the buffer is empty, }
{ it waits until a character arrives, so this will not work for the TTY emulation. The interrupts are always }
{ disabled when the buffer pointers are checked or modified.  Beware!  Do not completely disable interrupts  }
{ in the wait loop or else you never will get a character if there is not one there already.                 }
                                                                                {                            }
FUNCTION ReadCOM (Com : BYTE) : CHAR;                                           {                            }
VAR                                                                             {                            }
  CharReady : BOOLEAN;                                                          {-TRUE if there is data in   }
BEGIN                                                                           { the input buffer           }
  {$IFDEF ErrorChecking}                                                        {                            }
    IF NOT ValidPort (Com, 1, 'ReadCOM') THEN EXIT;                             {-Optional error trapping    }
  {$ENDIF}                                                                      {                            }
  CharReady := FALSE;                                                           {                            }
  REPEAT                                                                        {-Wait for data to arrive    }
    CharReady := InTail [Com] <> InHead [Com];                                  {-Check to see if buffer is  }
  UNTIL CharReady;                                                              {                            }
  ReadCOM := CHR(InBuffer [Com, InHead [Com]]);                                 {-Read a character of data   }
  InHead [Com] := (InHead [Com] + 1) MOD (MaxInSize + 1);                       {-Update the buffer pointer  }
END;                                                                            {                            }
                                                                                {                            }
{ This function is an example of how to get a character from the serial port.  Unlike ReadCOM, this routine  }
{ returns if no data appears in the buffer for a short period of time. This makes it useful for applications }
{ which process data only if it is available.  The interrupts are always disabled when the buffer pointers   }
{ are checked or modified.  Beware!  Do not completely disable interrupts in the wait loop or else you never }
{ will get a character if there is not one there already.  Returns TRUE if valid data has been returned. You }
{ may optimize the time out period to a shorter one for your applications.  65535 is the maximum wait time.  }
                                                                                {                            }
FUNCTION TimedReadCOM (Com : BYTE; VAR Data : CHAR) : BOOLEAN;                  {                            }
VAR                                                                             {                            }
  CharReady : BOOLEAN;                                                          {-TRUE if there is data in   }
  TimeOut : WORD;                                                               { the input buffer           }
BEGIN                                                                           {                            }
  {$IFDEF ErrorChecking}                                                        {                            }
    IF NOT ValidPort (Com, 1, 'TimedReadCOM') THEN EXIT;                        {-Optional error trapping    }
  {$ENDIF}                                                                      {                            }
  TimeOut := 0;                                                                 {                            }
  REPEAT                                                                        {-Wait for data to arrive    }
    CharReady := InTail [Com] <> InHead [Com];                                  {-Is the buffer empty or not }
    delay(1);
    INC (TimeOut);                                                              {-Increment the timer        }
  UNTIL CharReady OR (TimeOut = 50);                                            {-Set the maximum time to    }
  IF CharReady                                                                  { wait for data here.  Lower }
    THEN BEGIN                                                                  { number for shorter timeout.}
           Data := CHR (InBuffer [Com, InHead [Com]]);                          {-If data became available,  }
           InHead [Com] := (InHead [Com] + 1) MOD (MaxInSize + 1);              { read a character, and set  }
         END                                                                    {                            }
    ELSE MakeError (5, Com, 'TimedReadCOM');                                    {-Record the timeout error   }
  TimedReadCOM := CharReady;                                                    {                            }
END;                                                                            {                            }
                                                                                {                            }
{$F+}                                                                           {-VERY IMPORTANT!  When the  }
PROCEDURE RemoveIntOnExit;                                                      { program quits normally or  }
BEGIN                                                                           { abnormally, the interrupt  }
  FOR Loop := 1 TO MaxPorts DO                                                  { handler is automatically   }
    IF IntInstalled [Loop]                                                      { uninstalled when Turbo     }
      THEN RemoveInt (Loop);                                                    { invokes this procedure.    }
  ExitProc := ExitSave;                                                         {-Return control to the      }
END;                                                                            { original exit procedure    }
{$F-}                                                                           {                            }
                                                                                {                            }
{ The following code is executed when any program which uses this unit first  } { Changeable defaults are    }
{ starts up.  It performs all necessary initializations.                      } { marked with a '*'          }
                                                                                {                            }
BEGIN                                                                           {                            }
  writeln('beginning comm_tp4 inits');
  ExitSave := ExitProc;                                                         {-VERY IMPORTANT!  This lets }
  ExitProc := @RemoveIntOnExit;                                                 { the program halt safely.   }
  FOR Loop := 1 TO MaxPorts DO                                                  {                            }
    BEGIN                                                                       {                            }
      InHead [Loop] := 0;                                                       {-Default all buffers set to }
      InTail [Loop] := 0;                                                       { empty on startup.          }
      OutHead [Loop] := 0;                                                      {                            }
      OutTail [Loop] := 0;                                                      {                            }
      DTR_RTS [Loop] := FALSE;                                                  {*Default DTR/RTS setting on }
      IntInstalled [Loop] := FALSE;                                             {-Default interrupts not on  }
      CD  [Loop] := ($80 AND PORT [COMPort [Loop]+MSR] <> 0);                   {-Carrier Detect status set  }
      CTS [Loop] := ($10 AND PORT [COMPort [Loop]+MSR] <> 0);                   {-Clear To Send status set   }
      DSR [Loop] := ($20 AND PORT [COMPort [Loop]+MSR] <> 0);                   {-Data Set Ready status set  }
      RI  [Loop] := ($40 AND PORT [COMPort [Loop]+MSR] <> 0);                   {-Ring Indicator status set  }
      Framing [Loop] := 0;                                                      {-Reset framing error count  }
      Overrun [Loop] := 0;                                                      {-Reset overrun error count  }
      Parity [Loop] := 0;                                                       {-Reset parity error count   }
      Break [Loop] := 0;                                                        {-Reset break interrupt count}
    END;                                                                        {                            }
  ErrorCode := 0;                                                               {-Default of no port errors  }
  ErrorPort := 0;                                                               {                            }
  IRQMask := 0;                                                                 {-No interrupts installed    }
  {$IFNDEF NoMessageCode}                                                       {                            }
    ShowMessages := TRUE;                                                       {*Default error messages on  }
    ErrMsgX := 0;                                                               {*Default of error messages  }
    ErrMsgY := 0;                                                               {*placed at cursor position. }
  {$ENDIF}                                                                      {                            }

  writeln('finished comm_tp4 inits');

END.                                                                            {                            }

