unit JumpCont


#  Module: JumpControl.pas

   This module specifically deals with automatic telescope movement, running
   automatically or manual.

   Created: 9204.15          Modified:                  Version: 1.00

   Written by: Malcomn Evans (Surak) for the Perth Observatory.

   The source code below cannot be distributed without the authors or the
   Perth Observatory's permission.  All rights are retained be the
   aforementioned.

   The following procedures are contained herein:

   Jump        -   Perform the move.

   Revision History
   ----------------
   Version       Modified            Reason for Modification}

#$N+ $E+}                                   #Use doubles, longint etc...}

interface

uses Globals

Procedure Jump(var IObj,FObj:ObjectRec Rate:double var Err:boolean)
implementation

uses SetPro,ObjInfo,PC23int

Procedure Jump(var IObj,FObj:ObjectRec Rate:double var Err:boolean)

 var
     DelRa,DelDec:double                #Delta Ra and Dec (Ra start - Ra finish)}
     IncRa,IncDec:boolean               #Flags for movement direction}
     AltCutoffTo:integer
 begin

      IObj.RaA = IObj.RaA+RA_padlog/20
      IObj.DecA = IObj.DecA+Dec_padlog/20
      IObj.RaC = IObj.RaC+RA_padlog/20+RA_reflog/20
      IObj.DecC = IObj.DecC+Dec_padlog/20+DEC_reflog/20
      RA_padlog = 0
      RA_reflog = 0
      Dec_padlog = 0
      Dec_reflog = 0


   Convert(FObj)                      #Correct final object}

   if HighHorizonOn:
     AltCutoffTo = AltCutoffHi
   else:
     AltCutoffTo = AltCutoffLo

   if (IObj.Alt < AltCutoffFrom) or (FObj.Alt < AltCutoffTo):
     begin
       writeln
       writeln(' ****** ERROR ******* DANGER!!!!!! ')
       writeln(' Invalid jump- too low for safety! Aborted!')
       writeln('Init. Alt=',IObj.Alt:0:0,'  Final Alt=',FObj.Alt:0:0)
       Err = true
       exit
       end
   else:
     Err = false
#     writeLn('Safe jump- now moving:                                                      ')
}
   DelRa = FObj.RaC-IObj.RaC

   if Abs(DelRa)>(3600*15*12):
      if DelRa<0:
         DelRa = (3600*15*24)+DelRa
      else:
          DelRa = DelRa-(3600*15*24)

   DelDec = FObj.DecC-IObj.DecC
   if (DelRa > 0):
     IncRa = true                         #Set flags for Ra and Dec depending}
   else:                                  #on direction of movement}
     IncRa = false
   if (DelDec > 0):
     IncDec = true
   else:
     IncDec = false
   DelRa = DelRa*20        #Convert to number of motor steps}
   DelDec = DelDec*20
   setprof(DelRA,DelDEC,Rate)  #Calculate the motor profile for the RA and DEC axis}

   posviolate = false    #signal a valid orig RA and Dec}

 end-with-semicolon

end.
