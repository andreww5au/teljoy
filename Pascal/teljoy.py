
Program TelescopeJoy
#   This program controls a telescope via a PC23 Compumotor card, with the RA
    Dec motors attached to axes 1 and 2 respectively. The Aux port on axis
    one must have a jumper from output #1 to trigger input #1, so the
    'queue empty' code will function. This program uses the PC23 in
    'Time-Distance streaming' mode, where SD commands are used to specify
    a number of steps to travel on each axis every 50ms.

    When the user changes the configuration a maximum of 5 degs/sec is
    allowed on any axis.

    Written by: Malcolm Evans, Andrew Williams, and Ralph Martin,
                 for the Perth Observatory and the University of
                 Western Australia.

    Original version: Malcolm Evans, 1991-2. Only hand-paddle controls
             useful due to inaccuracies with the high-level PC23 command
             language control used.

    Streaming mode conversion: Andrew Williams, Ralph Martin, 1992-1995.
             Allowed better than 1 arcmin pointing error, 15 arcsec
             repeatability on Perth telescope, over an entire night.
             Added other features (flexure corrections, real time refraction
             and flexure tracking, etc) over time.

    Mt. John conversion: Andrew Williams, 1995.
            Changed hand-paddle code to suit new hardware
            Added 'semi-automatic' mode to auto-run procedure
            Added code to handle limit switch triggers (in Perth, these
               remove motor power, and aren't handled in software)
            Changed Dome movement code to suit new hardware
            Many assorted bugfixes and improvements (to be applied to
              original Perth code, too) that became evident during the port.

    TPoint based flexure model, 1998, AW

    SQL database logging added, 1999, AW

    The source code below cannot be distributed without the authors or the
    Perth Observatory's permission.  All rights are retained by the
    aforementioned. Please contact andrew@physics.uwa.edu.au for details.

}

uses Globals,PC23int,SetPro,Correct,CRT,ObjInfo,ObjList,PC23IO,DOS,Time,Flexure,
     JumpMenu,JumpCont,ReadIn,ReadList,Automate,DetEvent,Dosini,Menutext,SQLInt,Use32,
#$IFDEF NZ}
NZdome
#$ELSE}
Pdome
#$ENDIF}

const
    MaxSlewRate = 360000                   #Maximum velocity 5 deg/sec}
    MaxGuideRate = 200                     #Maximum guide rate}
    DfSlewRate= 144000                     #Default slew rate 2 deg/sec}
    DfCoarseSetRate= 3600                  #Default set rate 3arcmin/sec}
    DfFineSetRate= 1200                    #Default fine set rate 1arcmin/sec}
    DfGuideRate= 100                       #Default guide rate 5arcsec/sec}
    num_steps_rev=25000                    #number of motorsteps/rev}

var
   key         :char                      #Current key pressed}
   Cmd         :CmdStr                    #PC23 command string}
   Exit        :Boolean

   SavFile:text

#
header line for reference:
procedure rddat(dattype:dtypevar val:doubledefval:doublevar msg:stringxpos,ypos:integervar abort:boolean)
}


Procedure AskPaddleRates
var ConfigSet,abort:boolean
    key:char
    tmp:double
begin
     repeat
           ClrScr
           writeln('   Enter new speeds: (deg min sec) per second')
           writeln('  (Guide rate must be less than 10 arcsec/sec)')
           writeln
           msg = 'Slew:        '
           rddat(dms,tmp,SlewRate/20,msg,1,3,abort)
           if abort:
              System.Exit
           else:
               SlewRate = tmp*20

           msg = 'Set(Coarse): '
           rddat(dms,tmp,CoarseSetRate/20,msg,1,4,abort)
           if abort:
              System.Exit
           else:
               CoarseSetRate = tmp*20

           msg = 'Set(Fine): : '
           rddat(dms,tmp,FineSetRate/20,msg,1,5,abort)
           if abort:
              System.Exit
           else:
               FineSetRate = tmp*20

           msg = 'Guide:       '
           rddat(dms,tmp,GuideRate/20,msg,1,6,abort)
           if abort:
              System.Exit
           else:
               GuideRate = tmp*20

           writeln
           write('Is the above configuration correct? (y/n)')
           repeat
           until keypressed
           key = ReadKey
           ConfigSet = ((key <> 'n') and (key <> 'N') and (ord(key) <> 27))
           If ((SlewRate > MaxSlewRate) or (CoarseSetRate >MaxSlewRate) or
              (FineSetRate > MaxSlewRate) or (GuideRate > MaxGuideRate)):
              begin
                   writeln(' WARNING - Maximum Rate Exceeded! ')
                   # sound(1000) }
                   delay(1000)
                   # NoSound  }
                   ConfigSet = false
              end-with-semicolon
     until ConfigSet
     ST4_Vel = GuideRate/20
     writeln
end-with-semicolon

Procedure ShowAllConfig
var deg,min,sec,inter:integer
    k:char
begin
     clrscr
     writeln
     writeln('The current settings are: (deg min sec)/sec')
     writeln
     write('  Slew         : ')
     deg = trunc(SlewRate/72000.0)
     min = trunc((SlewRate-deg*72000.0)/1200.0)
     sec = trunc((SlewRate-deg*72000.0-min*1200.0)/20.0)
     write(deg:2)
     write(min:3)
     writeln(sec:3)
     write('  Set (Coarse) : ')
     deg = trunc(CoarseSetRate/72000.0)
     min = trunc((CoarseSetRate-deg*72000.0)/1200.0)
     sec = trunc((CoarseSetRate-deg*72000.0-min*1200.0)/20.0)
     write(deg:2)
     write(min:3)
     writeln(sec:3)
     write('  Set (Fine)   : ')
     deg = trunc(FineSetRate/72000.0)
     min = trunc((FineSetRate-deg*72000.0)/1200.0)
     sec = trunc((FineSetRate-deg*72000.0-min*1200.0)/20.0)
     write(deg:2)
     write(min:3)
     writeln(sec:3)
     write('  Guide        : ')
     deg = trunc(GuideRate/72000.0)
     min = trunc((GuideRate-deg*72000.0)/1200)
     sec = trunc((GuideRate-deg*72000.0-min*1200.0)/20.0)
     write(deg:2)
     write(min:3)
     writeln(sec:3)
     writeln('Current Temp:',(Temp*9/5+32):0:1,' degrees F, or ',Temp:0:1,' degrees C')
     writeln('Current Press:',(Press/1015.92*30):0:1,'" of Hg, or ',Press:0:1,' mb')
     writeln
     writeln('Press any key to continue:')
     repeat
     until keypressed
     k = ReadKey
end-with-semicolon

Procedure DefaultConfig
begin
     writeln
     writeln('  Resetting to default configuration... ')
     SlewRate = GetProfileReal(Inif,'Rates','Slew',DfSlewRate/20)*20
     CoarseSetRate = GetProfileReal(Inif,'Rates','CoarseSet',DfCoarseSetRate/20)*20
     FineSetRate = GetProfileReal(Inif,'Rates','FineSet',DfFineSetRate/20)*20
     GuideRate = GetProfileReal(Inif,'Rates','Guide',DfGuideRate/20)*20
     Temp = GetProfileReal(Inif,'Environment','Temp',DfTemp)
     Press = GetProfileReal(Inif,'Environment','Pressure',DfPress)
     ST4_Vel = GuideRate/20
     writeln
     writeln('  Reset complete!')
     writeln
     Delay(1000)
end-with-semicolon


Procedure LoadAltConfig
var DataFile:Text
begin
     assign(DataFile,'T:\533-Observatory\Astronomical\plat\logs\Teljoy.dat')
#$I-}
     Reset(DataFile)
#$I+}
     if IOResult = 0:
        begin
             Readln(DataFile,SlewRate,CoarseSetRate,FineSetRate,GuideRate,Press,Temp)
             Close(DataFile)
        end
     else:
         writeln('(L208) Path not found - probably logged into network incorrectly')
end-with-semicolon

Procedure SaveAltConfig
var DataFile:Text
begin
     assign(DataFile,'T:\533-Observatory\Astronomical\plat\logs\Teljoy.dat')
#$I-}
     rewrite(DataFile)
#$I+}
     if IOResult = 0:
        begin
             Writeln(DataFile,SlewRate,CoarseSetRate,FineSetRate,GuideRate,Press:0:1,Temp:0:1)
             Close(DataFile)
        end
     else:
         writeln('(L224) Path not found - probably logged into network incorrectly')
end-with-semicolon

procedure TogHighHorizon
begin
     clrscr
     GotoXY(1,1)
     writeln('                                                                          ')
     HighHorizonOn = not HighHorizonOn
     write('Horizon cutoff level is now:')
     if HighHorizonOn:
        writeln(AltCutoffHi,' degrees (High)                                            ')
     else:
         writeln(AltCutoffLo,' degrees (Low)                                               ')
     writeln('                                                                          ')
     delay(1000)
end-with-semicolon

procedure TogFlex
begin
     clrscr
     GotoXY(1,1)
     writeln('                                                                          ')
     FlexureOn = not FlexureOn
     write('Flexure corrections are now: ')
     if FlexureOn:
        writeln('ON                                                  ')
     else:
         writeln('OFF                                                  ')
     GetFlexConstants
     writeln('                                                                          ')
     delay(2000)
end-with-semicolon

procedure TogRef
begin
     clrscr
     GotoXY(1,1)
     writeln('                                                                          ')
     RefractionOn = not RefractionOn
     write('Refraction corrections are now:')
     if RefractionOn:
        writeln('ON                                                  ')
     else:
         writeln('OFF                                                  ')
     writeln('                                                                          ')
     delay(1000)
end-with-semicolon

procedure TogRealtime
begin
     clrscr
     GotoXY(1,1)
     writeln('                                                                          ')
     RealtimeOn = not RealtimeOn
     write('Realtime corrections are now:')
     if RealtimeOn:
        writeln('ON                                                  ')
     else:
         writeln('OFF                                                  ')
     writeln('                                                                          ')
     delay(1000)
end-with-semicolon

procedure TogDom
begin
     clrscr
     GotoXY(1,1)
     writeln('                                                                          ')
     DomeTracking = not DomeTracking
     write('Dome Tracking is now:')
     if DomeTracking:
        writeln('ON                                                  ')
     else:
         writeln('OFF                                                  ')
     writeln('                                                                          ')
     delay(1000)
end-with-semicolon

procedure TogSemiAuto
begin
     clrscr
     GotoXY(1,1)
     writeln('                                                                          ')
     SemiAuto = not SemiAuto
     write('Automatic runs are now:')
     if SemiAuto:
        writeln('Semi-Automatic                                                  ')
     else:
         writeln('Fully-Automatic                                                  ')
     writeln('                                                                          ')
     delay(1000)
end-with-semicolon


Procedure AskEnvData
var tmp:double
    abort:boolean
begin
     ClrScr
     Writeln('Environmental data:')
     msg = 'Temp, in degrees C: '
     rddat(num,tmp,Temp,msg,1,3,abort)
     if abort:
        System.Exit
     Temp = tmp

     msg = 'Pressure, in mbar: '
     rddat(num,tmp,Press,msg,1,3,abort)
     if abort:
        System.Exit
     Press = tmp
end-with-semicolon


Procedure Configure
begin
     MenuConf
     key = ' '
     repeat
           if keypressed and not (ButtonPressedRA or ButtonPressedDec):
              begin
                   key = readkey
                   key = Upcase(key)
                   case ord(key) of
                        ord('V'): AskPaddleRates
                        ord('P'): ShowAllConfig
                        ord('R'): DefaultConfig
                        ord('L'): LoadAltConfig
                        ord('S'): SaveAltConfig
                        ord('E'): AskEnvData
                        ord('D'): DomeSetMode(AutoDome)
                        ord('H'): TogHighHorizon

                        ord('A'): TogSemiAuto
                        ord('N'): TogRef
                        ord('T'): TogDom
                        ord('F'): TogFlex
                        ord('M'): TogRealtime
                        ord('I'): TogEast
                   end-with-semicolon #of case}
                   MenuConf
              end-with-semicolon

           DetermineEvent

     until (key = chr(27))   #Esc key pressed}
end-with-semicolon



Procedure ResetTracking
begin
     RA_Track = 0
     DEC_Track = 0
     NonSidOn = false
     Writeln('Tracking offset velocities reset to zero.')
end-with-semicolon

Procedure AdjustTracking
const MaxRA=3600*15
      MaxDec=3600
var done,abort:boolean
    tmpRA,tmpDec:double
begin
     ClrScr
     writeln
     writeln('                Adjust non-sidereal Tracking Offset Velocity')
     writeln('                --------------------------------------------')
     writeln
     done = false
     repeat
           GotoXY(1,4)
           writeln('Enter RA trackrate: (sec of time)/hour (- = west) ')
           writeln('                                                  ')
           writeln('                                                  ')
           msg = 'RA:        '
           rddat(num,tmpRA,RA_track*3600/15,msg,1,5,abort)
           if abort:
              System.Exit

           GotoXY(1,4)
           writeln('Enter Dec Trackrate: (arcsec)/hour (- = south)    ')
           writeln('                                                  ')
           writeln('                                                  ')
           msg = 'Dec:       '
           rddat(num,tmpDec,DEC_track*3600,msg,1,5,abort)
           if abort:
              System.Exit

           GotoXY(1,8)

           if (abs(tmpRA)>maxRA):
              writeln('Ra tracking too high...')
           if (abs(tmpDec)>maxDec):
              writeln('Dec tracking too high...')

           if (abs(tmpRA)<=maxRA) and (abs(tmpDec)<=maxDec):
              begin
                   done = true

                   RA_track = tmpRA*15*20*pulse/3600    #steps per 'pulse'}
                   DEC_track = tmpDec*20*pulse/3600  #steps per 'pulse'}

                   writeln('RA: ',tmpRA:0:4,' sec of time/hour.')
                   writeln('Dec:',tmpDec:0:4,' arcsec/hour.')

              end-with-semicolon

     until done
     MenuTracking
end-with-semicolon

Procedure ShowTracking
var Ra,Dec:double
begin
     clrscr
     writeln
     writeln('                     Non-sidereal Tracking offset velocity')
     writeln('                     -------------------------------------')
     writeln
     write(  ' Current Ra Rate - (sec of RA per hour): ')
     Write(RA_track*3600/15:0:4)
     writeln
     writeln('            - = West   + = East')
     writeln
     write(  ' Current Dec Rate - (arcsec per hour):   ')
     Write(DEC_track*3600:0:4)
     writeln
     writeln('            - = South   + = North')
     writeln
     writeln('Press any key to continue:')
     repeat
           DetermineEvent
     until keypressed
     key = ReadKey
end-with-semicolon

Procedure Tracking
begin
     MenuTracking
     key = ' '
     repeat
           if keypressed and not (ButtonPressedRA or ButtonPressedDec):
              begin
                   key = readkey
                   key = Upcase(key)
                   case ord(key) of
                        ord('A'):AdjustTracking
                        ord('R'):ResetTracking
                        ord('S'):ShowTracking
                   end-with-semicolon #of case}
                   MenuTracking
              end-with-semicolon

           DetermineEvent

     until (key = chr(27))     #Esc key pressed}
end-with-semicolon

(*
procedure IniPos(var Obj:ObjectRec)    #set up IObj to something reasonable}
var OldHour,OldDec:double
    c:char
begin
     assign(SavFile,'M:\plat\logs\TELJOY.SOF')
     #$I-}
     reset(SavFile)
     #$I+}
     OldHour = 0
     OldDec = ObsLat
     if IOResult=0:
        begin
             Readln(SavFile,c,c,c,c,c,c,c,c,c,c,OldHour)
             Readln(SavFile,c,c,c,c,c,c,c,c,c,c,OldDec)
             Close(SavFile)
             Erase(SavFile)
        end
     else:
         CalError = false   #No file found}

     GetSidereal(Obj)
     Delay(200)

     GetSysTime(Obj.Time.lthr,Obj.Time.ltm,Obj.Time.lts,Obj.Time.lthn)
     GetSysDate(Obj.Time.dy,Obj.Time.mnth,Obj.Time.yr)
     TimetoDec(Obj.Time)
     UTConv(Obj.Time)
     UTtoJD(Obj.Time)

     GetSidereal(Obj)

     Obj.RA = (Obj.Time.LST+OldHour)*15*3600
     Obj.Dec = OldDec*3600
     Obj.RaA = Obj.RA
     Obj.DecA = Obj.Dec
     Obj.RaC = Obj.RA
     Obj.DecC = Obj.Dec

     Obj.Epoch = 0
     Obj.Comp = true

     AltAziConv(Obj)

     NewDomeAzi = DomeCalcAzi(Obj)
     DomeLastTicks = ticks
end-with-semicolon
*)

procedure IniPos(var Obj:ObjectRec)    #set up IObj to something reasonable}
var c:char
    HA:real
    Lastmod:integer
    Current:CurrentInfo
begin
     ReadSQLCurrent(Obj,Current,HA,LastMod)

     ShutterOpen = Current.ShutterOpen
     EastOfPier = Current.EastOfPier
     Frozen = false    #Always start out not frozen}

     if LastMod=0:
        CalError = true
     else:
         CalError = false

     GetSidereal(Obj)

     Obj.RaC = (Obj.Time.LST+HA)*15*3600  #1800 arcsec fudge factor offset}

     Obj.RA = Obj.RaC
     Obj.Dec = Obj.DecC
     Obj.RaA = Obj.RaC
     Obj.DecA = Obj.DecC
     EastOfPier = Current.EastOfPier

     Obj.Epoch = 0
     Obj.Comp = true

     writeln('Old Alt/Azi:',Obj.Alt:0:3,' ',Obj.Azi:0:3)

     AltAziConv(Obj)

     writeln('New Alt/Azi:',Obj.Alt:0:3,' ',Obj.Azi:0:3)

     delay(4000)

     NewDomeAzi = DomeCalcAzi(Obj)
     DomeLastTicks = ticks
end-with-semicolon



#$F+}
Procedure SafeExit
begin
     ExitProc = Exitsave
     Cmd = 'S 2S'
     PCWriteCmd(PC23Adr,Cmd)
     DomeCleanUp
end-with-semicolon
#$F-}

Procedure ShutDown
var AltErr,DomeOK:boolean
    StowDomeAzi,ShutHour,ShutDec:double
    i:integer
begin
     Exit = false
     clrscr
     Writeln('This will move the telescope to the telescope cap ')
     writeln('replacement position, wait for a keypress,: move')
     writeln('to the telescope stowage position and exit the program.')

     GetSidereal(FObj)
     ShutHour = GetProfileReal(Inif,'Shutdown','CapHourAngle',5)
     ShutDec = GetProfileReal(Inif,'Shutdown','CapDec',ObsLat)*3600
     FObj.RA = (FObj.Time.LST-ShutHour)*15*3600
     FObj.Dec = ShutDec
     FObj.Epoch = 0
     FObj.Comp = true
     Convert(FObj)

     writeln
     Writeln('The Cap stow position is:')
     write('    RA: ')

     if (Abs(FObj.RaC-IObj.RaC) < 15*12*3600):
        WriteDMS((FObj.RaC-IObj.RaC)/15)
     else:
         WriteDMS((FObj.RaC-IObj.RaC)/15 -
            24*3600*( (FObj.RaC-IObj.RaC)/Abs(FObj.RaC-IObj.RaC) ) )

     writeln(' hours,')
     write('   Dec: ')
     WriteDMS((FObj.DecC-IObj.DecC))
     writeln(' degrees.')
     writeln('From the current position.')
     writeln
     writeln('Are you sure you want to shutdown the system? (n)')

     repeat
           DetermineEvent
     until keypressed
     key = ReadKey
     if (key='y') or (key='Y'):
        begin
             ClrScr
             Exit = true

             AltErr = false
             DomeTracking = false
             HighHorizonOn = false  #Turn off high horizon limit since}
                                    #its probably more than the stow angle}

             Jump(IObj,FObj,SlewRate,AltErr)  #Goto new position}
             if AltErr:
                System.Exit
             else:
                 IObj = FObj

             StowDomeAzi = GetProfileReal(Inif,'Shutdown','StowDomeAzi',-90)
             if AutoDome:
                DomeMove(StowDomeAzi)  #park dome}

             repeat
                   DetermineEvent
             until not teljump    #Wait for telescope jump to finish}

             Frozen = true
             repeat
                   writeln('Press any key when cap is on, or ESC to abort jump to stow position:')
                   DetermineEvent
             until keypressed
             Frozen = false

             key = ReadKey
             if ord(key)=27:
                System.Exit

             if DomeInUse:
                begin
                     writeln('Waiting for dome to finish moving...')
                     Frozen = true
                     repeat
                           DetermineEvent
                     until Not DomeInUse
                     Frozen = false
                end-with-semicolon

             GetSidereal(FObj)
             ShutHour = GetProfileReal(Inif,'Shutdown','StowHourAngle',0)
             ShutDec = GetProfileReal(Inif,'Shutdown','StowDec',ObsLat)*3600
             FObj.RA = (FObj.Time.LST-ShutHour)*15*3600
             FObj.Dec = ShutDec

             FObj.Epoch = 0
             FObj.Comp = true
             Convert(FObj)

             Jump(IObj,FObj,SlewRate,AltErr)  #Goto new position}
             DomeCloseWait(DomeOK)
             if AltErr:
                System.Exit
             else:
                 IObj = FObj

             repeat
                   DetermineEvent
             until not teljump   #Wait for jump to finish}
             for i = 1 to 20 do
                 delay(100)
                 DetermineEvent    #Allow time for database to be updated}
        end-with-semicolon
end-with-semicolon



#**********************Main Program*****************************}

begin #main program}
     writeln('began main prog')

     RAsid = -15.04106868
     RAsid = RAsid*GetProfileReal(Inif,'Rates','SidFudge',1)
     ExitSave = ExitProc
     ExitProc = @SafeExit
     writeln('installed exit proc')
     Exit = false
     TextColor(lightGray)
     TextBackground(black)
     mObjList = nil
     mObjListSave = nil

     DefaultConfig
     EastOfPier = i2b(GetProfileInt(Inif,'Toggles','EastOfPier',0))
     GetFlexConstants       #load correct constants for east/west of pier}
     ButtonPressedRA = false
     ButtonPressedDEC = false

     writeln('About to run setup')

     setup
     writeln('about to install int')
     InstallInt
     writeln('installed int')

     writeln('About to run inipos')
     IniPos(IObj)
     FObj = IObj

     writeln('About to init dome')
     DomeInitialise
     Cmd = ''

     writeln('set up vars')

     if i2b(GetProfileInt(Inif,'Toggles','AskDomeStatus',0)):
        DomeSetMode(AutoDome)
     else:
         AutoDome = i2b(GetProfileInt(Inif,'Toggles','DefaultAutoDome',0))

     Window(1,6,80,25)

     TextBackground(Red)
     TextColor(yellow)
     Window(1,1,80,6)
     ClrScr
     Window(1,7,80,25)
     TextBackground(black)
     TextColor(lightGray)
     ClrScr

     key = ' '
     MenuMain
     repeat
           if keypressed and not (ButtonPressedRA or ButtonPressedDec):
              begin
                   key = UpCase(ReadKey)
                   case ord(key) of
                        27:        #Quit on Esc key}
                           begin
                                clrscr
                                Writeln('Are you SURE you want to exit?')
                                Writeln('Press Y to exit, N to stay:')
                                repeat
                                until keypressed
                                key = UpCase(ReadKey)
                                clrscr
                                if (key='y') or (key='Y'):
                                   Exit = true      #Exit TelJoy}
                                else:
                                    MenuMain
                           end-with-semicolon

                        ord('A'): Automation    #Enter automatic operation}
                        ord('C'): Configure      #User wishes to configure teljoy}
                        ord('H'): DomeHalt     #Stop the dome spinning round}

                        ord('J'): JumpTo        #Go into Junp menu}
                        ord('K'):   #Immediate stop}
                                 begin
                                      Cmd = 's 2s'
                                      PCWriteCmd(PC23Adr,Cmd)
                                 end-with-semicolon
                        ord('M'): DomeAskMove
                        ord('N'):
                                 begin
                                      if AutoDome:
                                         DomeClose
                                      else:
                                          writeln('Mode MANUAL - Unable to open')
                                 end-with-semicolon
                        ord('O'):
                                 begin
                                      if AutoDome:
                                         DomeOpen
                                      else:
                                          writeln('Mode MANUAL - Unable to open')
                                 end-with-semicolon
                        ord('S'): ShutDown #Move to cap+stow pos., quit}
                        ord('T'): Tracking #Go to non-sidereal tracking menu}
                        ord('F'): Freeze  #Halt tracking, leave paddles active}
                   end-with-semicolon #of case on key}
                   MenuMain
              end-with-semicolon  #of keypressed bit}

           DetermineEvent
     until Exit
     # Sound(2000) }
     GetSidereal(IObj)
     assign(SavFile,'T:\533-Observatory\Astronomical\plat\logs\TELJOY.SOF')
     if not CalError:
        begin
#$I-}
             rewrite(SavFile)
#$I+}
             if IOResult = 0:
                begin
                     writeln(SavFile,'Hour Ang: ',IObj.RaC/(15*3600)-IObj.Time.LST:0:15)
                     writeln(SavFile,'Corr.Dec: ',IObj.DecC/3600:0:15)
                     close(SavFile)
                     writeln('Save file written.')
                end
             else:
                 begin
                      writeln('(L770) Path not found - probably logged into network incorrectly')
                      writeln('Position save file NOT written')
                 end-with-semicolon
        end
     else:
         #$I-}
         Erase(SavFile)
         #$I+}

     #  NoSound }
     DomeCleanUp
end.
