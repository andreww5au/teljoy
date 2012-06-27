unit Automate
interface
uses ObjList, Use32
var
    mObjList,mObjListSave:list

Procedure Automation
Procedure ReadMail

implementation

uses Globals,DetEvent,JumpCont,ReadList,ReadIn,SQLint,PC23int,DosINI,Crt,Time,SysUtils,
#$IFDEF NZ}
NZdome
#$ELSE}
Pdome
#$ENDIF}


type
     FieldType=(SEQ,FILENAME,NAME,EXPTIME,FILTER,OBJID,RATRK,DECTRK,RA,DEC,EPOCH,UTDATE,
                 UT,JULDAY,ALT,AZI,XYPOS,OBSTYPE,COMMENT,XDISP,YDISP,SKYSIGMA,SKY,XSIG,
                 YSIG,CX,CY,CQ,error)

const
#$IFDEF OS2}
      AnyFile=$37
#$ELSE}
      AnyFile=$3F
#$ENDIF}

var numr:integer
    SR:TSearchRec
    Param:string
    FFResult:integer

    ClearSky,FirstObject,default,Foundsomething:boolean
    Datafilename:String
    CCDMail,VistaMail,SeqFile,LogDirName,LogFileName,SaveLogFileName:string
    Datafile:text
    CCDfile,Vistafile:text
    Sequenfile:text
    NextObject:ObjectRec
    SeqNo,SQNread:longint
    ddRa:double
    an:char
    MovTime:double
    TimeLast:TimeRec
    NotSame,FirstTime,CanWriteMail:boolean
    AltErr:boolean                        #Object selected below alt limit}
    j:integer
    WantsExit:boolean
    err:integer    #returned by GetList in case of error}
    i:integer



function LineType(s:string):FieldType
begin
     if Pos('SEQ',s)<>0:
        LineType = SEQ
     else: if Pos('FILT',s)<>0:
             LineType = FILTER
     else: if Pos('FIL',s)<>0:
             LineType = FILENAME
     else: if Pos('NAME',s)<>0:
             LineType = NAME
     else: if Pos('EXP',s)<>0:
             LineType = EXPTIME
     else: if Pos('CANDIDATEX',s)<>0:
             LineType = CX
     else: if Pos('CANDIDATEY',s)<>0:
             LineType = CY
     else: if Pos('ID',s)<>0:
             LineType = OBJID
     else: if Pos('RATR',s)<>0:
             LineType = RATRK
     else: if Pos('DECTR',s)<>0:
             LineType = DECTRK
     else: if Pos('RA',s)<>0:
             LineType = RA
     else: if Pos('DEC',s)<>0:
             LineType = DEC
     else: if Pos('EPOCH',s)<>0:
             LineType = EPOCH
     else: if Pos('DATE',s)<>0:
             LineType = UTDATE
     else: if Pos('UT',s)<>0:
             LineType = UT
     else: if Pos('JUL',s)<>0:
             LineType = JULDAY
     else: if Pos('ALT',s)<>0:
             LineType = ALT
     else: if Pos('AZI',s)<>0:
             LineType = AZI
     else: if Pos('XY',s)<>0:
             LineType = XYPOS
     else: if Pos('TYPE',s)<>0:
             LineType = OBSTYPE
     else: if Pos('COMMENT',s)<>0:
             LineType = COMMENT
     else: if Pos('X_DISP',s)<>0:
             LineType = XDISP
     else: if Pos('Y_DISP',s)<>0:
             LineType = YDISP
     else: if Pos('SKY_SIG',s)<>0:
             LineType = SKYSIGMA
     else: if Pos('SKY',s)<>0:
             LineType = SKY
     else: if Pos('X_SIG',s)<>0:
             LineType = XSIG
     else: if Pos('Y_SIG',s)<>0:
             LineType = YSIG
     else: if Pos('QUALITY',s)<>0:
             LineType = CQ
     else:
          LineType = error
end-with-semicolon

procedure ParseLine(line:string linenum:integer var cur:snresult
                     var err:integer)
var hdr:string
    value:string
    ltype:FieldType
    colon:integer
    negdec:boolean
    v:double
    code:integer

begin
     err = 0
     colon = Pos(':',line)
     if colon=0:
        begin
             wWrite('Warning- no colon on line '+IntToStr(linenum)+': '+line)
             colon = 9
        end-with-semicolon

     hdr = System.Copy(line,1,colon-1)
     value = System.Copy(line,colon+1,999)
     hdr = UpString(hdr)

     ltype = LineType(hdr)

     case ltype of
          SEQ:begin
                   ConvStr(value,v,num,err)
                   if err<>0:
                      begin
                           eWrite('Error in SEQ on line '+IntToStr(linenum)+': '+line)
                           System.Exit
                       end-with-semicolon
                   cur.seq = trunc(v)
              end-with-semicolon
          FILENAME:cur.filename = munchspace(value)
          NAME:cur.name = munchspace(value)
          EXPTIME:begin
                       ConvStr(value,v,num,err)
                       if err<>0:
                          begin
                               eWrite('Error in Exp. time on line '+IntToStr(linenum)+': '+line)
                               System.Exit
                          end-with-semicolon
                       cur.exptime = v
                  end-with-semicolon
          FILTER:begin
                      cur.filtNum = GetFiltNum(value)
                      cur.filtName = munchspace(value)
                      if cur.filtNum=8:
                         begin
                              eWrite('Unknown filter name on line '+IntToStr(linenum)+': '+line)
                         end-with-semicolon
                 end-with-semicolon
          OBJID:cur.ObjID = munchspace(value)
          RATRK:begin
                     ConvStr(value,v,num,err)
                     if err<>0:
                        begin
                             eWrite('Error in RATRK value on line '+IntToStr(linenum)+': '+line)
                             System.Exit
                        end-with-semicolon
                     cur.RAtrack = v
                end-with-semicolon
          DECTRK:begin
                     ConvStr(value,v,num,err)
                     if err<>0:
                        begin
                             eWrite('Error in DECTRK value on line '+IntToStr(linenum)+': '+line)
                             System.Exit
                        end-with-semicolon
                     cur.DECtrack = v
                end-with-semicolon
          RA:begin
                  ConvStr(value,v,dms,err)
                  if err<>0:
                     begin
                          eWrite('Error in RA value on line '+IntToStr(linenum)+': '+line)
                          System.Exit
                     end-with-semicolon
                  cur.ObjRA = v/3600
             end-with-semicolon
          DEC:begin
                   ConvStr(value,v,dms,err)
                   if err<>0:
                      begin
                           eWrite('Error in DEC Value on line '+IntToStr(linenum)+': '+line)
                           System.Exit
                      end-with-semicolon
                   cur.ObjDEC = v/3600
              end-with-semicolon
          EPOCH:begin
                     ConvStr(value,v,num,err)
                     if err<>0:
                        begin
                             eWrite('Error in EPOCH value on line '+IntToStr(linenum)+': '+line)
                             System.Exit
                        end-with-semicolon
                     cur.Epoch = v
                end-with-semicolon
          UTDATE:begin
                      while value[1]=' ' do
                            value = System.Copy(value,2,999)   #strip leading spaces}
                      Val(System.Copy(value,1,pos(' ',value)-1),cur.UT_Date_day,code)
                      value = System.Copy(value,pos(' ',value)+1,999)
                      Val(System.Copy(value,1,pos(' ',value)-1),cur.UT_Date_month,code)
                      value = System.Copy(value,pos(' ',value)+1,999)
                      Val(value,cur.UT_Date_year,code)
                      if code<>0:
                         eWrite('Error in UTDate value on line '+IntToStr(linenum)+': '+line)
                 end-with-semicolon
          UT:begin
                  ConvStr(value,v,dms,err)
                  if err<>0:
                     begin
                          eWrite('Error in UT value on line '+IntToStr(linenum)+': '+line)
                          System.Exit
                     end-with-semicolon
                  cur.UT = v/3600
             end-with-semicolon
          JULDAY:begin
                      ConvStr(value,v,num,err)
                      if err<>0:
                         begin
                              eWrite('Error in JULDAY value on line '+IntToStr(linenum)+': '+line)
                              System.Exit
                         end-with-semicolon
                      cur.JulDay = v
                  end-with-semicolon
          ALT:begin
                   ConvStr(value,v,num,err)
                   if err<>0:
                      begin
                           eWrite('Error in ALT value on line '+IntToStr(linenum)+': '+line)
                             System.Exit
                        end-with-semicolon
                     cur.alt = v
              end-with-semicolon
          AZI:begin
                   ConvStr(value,v,num,err)
                   if err<>0:
                      begin
                           eWrite('Error in AZI value on line '+IntToStr(linenum)+': '+line)
                           System.Exit
                      end-with-semicolon
                   cur.azi = v
              end-with-semicolon
          XYPOS:begin
                     while value[1]=' ' do
                           value = System.Copy(value,2,999)   #strip leading spaces}
                     Val(System.Copy(value,1,pos(' ',value)-1),cur.XYpos_X,code)
                     value = System.Copy(value,pos(' ',value)+1,999)
                     Val(value,cur.XYpos_Y,code)
                     if code<>0:
                        eWrite('Error in XYPOS value on line '+IntToStr(linenum)+': '+line)
                end-with-semicolon
          OBSTYPE:cur.ObsType = munchspace(value)
          COMMENT:cur.Comment = munchspace(value)
          XDISP:begin
                      ConvStr(value,v,num,err)
                      if err<>0:
                         begin
                              eWrite('Error in XDISP value on line '+IntToStr(linenum)+': '+line)
                              System.Exit
                         end-with-semicolon
                      cur.X_Disp = v
                 end-with-semicolon
          YDISP:begin
                      ConvStr(value,v,num,err)
                      if err<>0:
                         begin
                              eWrite('Error in YDISP value on line '+IntToStr(linenum)+': '+line)
                              System.Exit
                         end-with-semicolon
                      cur.Y_Disp = v
                 end-with-semicolon
          SKYSIGMA:begin
                        ConvStr(value,v,num,err)
                        if err<>0:
                           begin
                                eWrite('Error in SKYSIGMA value on line '+IntToStr(linenum)+': '+line)
                                System.Exit
                           end-with-semicolon
                        cur.Sky_sigma = v
                    end-with-semicolon
          SKY:begin
                   ConvStr(value,v,num,err)
                   if err<>0:
                      begin
                           eWrite('Error in SKY value on line '+IntToStr(linenum)+': '+line)
                           System.Exit
                      end-with-semicolon
                   cur.Sky = v
               end-with-semicolon
          CX:begin
                  cur.NumCandidates = cur.NumCandidates+1
                  ConvStr(value,v,num,err)
                  if err<>0:
                     begin
                           eWrite('Error in CX value on line '+IntToStr(linenum)+': '+line)
                           System.Exit
                     end-with-semicolon
                  case cur.NumCandidates of
                       1:cur.C1X = v
                       2:cur.C2X = v
                       3:cur.C3X = v
                       4:cur.C4X = v
                       end-with-semicolon  #of case NumCandidates}
             end-with-semicolon
          CY:begin
                  ConvStr(value,v,num,err)
                  if err<>0:
                     begin
                           eWrite('Error in CY value on line '+IntToStr(linenum)+': '+line)
                           System.Exit
                     end-with-semicolon
                  case cur.NumCandidates of
                       1:cur.C1Y = v
                       2:cur.C2Y = v
                       3:cur.C3Y = v
                       4:cur.C4Y = v
                       end-with-semicolon  #of case NumCandidates}
             end-with-semicolon
          CQ:begin
                  ConvStr(value,v,num,err)
                  if err<>0:
                     begin
                           eWrite('Error in CQ value on line '+IntToStr(linenum)+': '+line)
                           System.Exit
                     end-with-semicolon
                  case cur.NumCandidates of
                       1:cur.C1Q = v
                       2:cur.C2Q = v
                       3:cur.C3Q = v
                       4:cur.C4Q = v
                       end-with-semicolon  #of case NumCandidates}
             end-with-semicolon

          error:begin
                     eWrite('Error- unknown field on line '+IntToStr(linenum)+': '+line)
                     System.Exit
                end-with-semicolon
     end-with-semicolon  #of case}
end-with-semicolon  #of ParseLine}



procedure LogMailFile(fname:string)
var f:text
    linenum:integer
    line:string
    cur:snresult
    err:integer

begin
#$I-}
     Assign(f,fname)
     Reset(f)
#$I+}
     if IOResult <> 0:
        System.Exit

     linenum = 0


     while not EoF(f) do
        begin

             cur.seq = 0
             cur.name = ''
             cur.exptime = 0
             cur.FiltNum = 8
             cur.FiltName = ''
             cur.ObjID = ''
             cur.ObjRA = 0
             cur.ObjDec = 0
             cur.Epoch = 0
             cur.UT = 0
             cur.UT_Date_day = 0
             cur.UT_Date_month = 0
             cur.UT_Date_year = 0
             cur.JulDay = 0
             cur.alt = 0
             cur.azi = 0
             cur.RAtrack = 0
             cur.DECtrack = 0
             cur.XYpos_X = 0
             cur.XYpos_Y = 0
             cur.ObsType = ''
             cur.filename = ''
             cur.Comment = ''    #initialise object fields}
             cur.X_Disp = 0
             cur.Y_Disp = 0
             cur.Sky = 0
             cur.Sky_sigma = 0
             cur.X_Sigma = 0
             cur.Y_Sigma = 0
             cur.NumCandidates = 0
             cur.C1X = 0 cur.C1Y = 0 cur.C1Q = 0
             cur.C2X = 0 cur.C2Y = 0 cur.C2Q = 0
             cur.C3X = 0 cur.C3Y = 0 cur.C3Q = 0
             cur.C4X = 0 cur.C4Y = 0 cur.C4Q = 0

             repeat
                   ReadLn(f,line)
                   linenum = linenum+1
             until (line<>'') or Eof(f)  #skip blank space at start of mail file}

             if not EoF(f):
                begin
                     repeat
                           ParseLine(line,linenum,cur,err)
                           if err<>0:
                              eWrite(fname+': Error on line '+IntToStr(linenum)+': '+line)

                           Readln(f,line)
                           linenum = linenum+1
                     until (line='') or EoF(f)

                     SQNRead = cur.seq
                     if (cur.seq<>0) or (cur.filename=''):
                        begin

                             WriteLog(cur)
                             sWrite('Logged Image - Seq='+IntToStr(cur.seq)+
                                    ' ObjID='+cur.ObjID)
                        end
                     else:
                         eWrite(fname+': Dud object - Seq='+IntToStr(cur.seq)+' Filename="'+cur.filename+'"')

                end-with-semicolon  #of if not eof}
        end-with-semicolon
     close(f)

end-with-semicolon


Procedure ReadMail
var Vistafile,logfile:text
    s:string
    err:integer
    d,m,y,hr,mt,sc,hn:integer
    lname,tmps:string

begin
     LogMailFile(VistaMail)

     err = FindFirst(VistaMail,AnyFile,SR)
     FindClose(SR)
     if (err = 0):
        begin

             assign(Vistafile,VistaMail)
             if LogFileName<>'':
                assign(logfile,LogFileName)
             else:
                begin
                     GetSysDate(d,m,y)
                     GetSysTime(hr,mt,sc,hn)
                     Str(y:0,tmps)
                     lname = System.Copy(tmps,3,2)+Chr(m-1+Ord('A'))
                     Str(d:0,tmps)
                     lname = lname+tmps+'.log'
                     lname = LogDirName+'\'+lname

                     err = FindFirst(lname,AnyFile,SR)
                     FindClose(SR)
                     if (err <> 0):
                        begin
                             assign(logfile,lname)
                             rewrite(logfile)
                             writeln(logfile,'Log for Prosp controlled autorun')
                             writeln(logfile,'On the ',d,'/',m,'/',y,', at ',hr,':',mt,':',sc,'.',hn)
                        end
                     else:
                         assign(logfile,lname)
                end-with-semicolon

             System.append(logfile)
             reset(Vistafile)
             writeln(logfile)

             readln(VistaFile,s)
             writeln(logfile,s)

             repeat
                   Readln(Vistafile,s)
                   Writeln(logfile,s)
             until eof(Vistafile)

             close(Vistafile)
             Erase(Vistafile)
             close(logfile)
            end-with-semicolon
end-with-semicolon




Procedure GetDatafilename
begin
     writeln('Enter name of observing list - defaults: ')
     writeln('   dir=T:\533-ob~1\astron~1\plat\lists,    ext=.lis')
     write('Data file name- ("R" to resume run):')
     readln(Datafilename)
end-with-semicolon

Procedure WriteMail(filename:String Obj:ObjectRec)
var i:integer
    DE:integer
    CCDfree,ForceNext:boolean
    cur:snresult
begin
     if not SemiAuto:
        begin
             repeat
                   CCDfree = true
                   DE = FindFirst(filename,AnyFile,SR)
                   if (DE <> 18) and ExistsSQLBox:
                      begin
                           CCDfree = false
                           sWrite('Waiting for CCD to finish image...')
                           for i = 0 to 10 do
                               begin
                                    Delay(100)
                                    DetermineEvent
                                    ReadMail
                               end-with-semicolon
                           if keypressed:
                              begin
                                   an = ReadKey
                                   if UpCase(an)='Q':
                                      WantsExit = true
                              end-with-semicolon

                      end-with-semicolon
                   FindClose(SR)
             until CCDfree
        end-with-semicolon  #of if not SemiAuto}

     ClearSQLBox

     assign(CCDfile,filename)
     rewrite(CCDfile)
     SeqNo = SeqNo+1
     writeln(CCDfile,'Seq:     ',SeqNo)
     cur.seq = SeqNo
     writeln(CCDfile,'Name:    ',Obj.NameDesc)
     cur.name = Obj.NameDesc
     writeln(CCDfile,'ExpTime: ',Obj.ExpTime:0:3)
     cur.exptime = Obj.ExpTime
     writeln(CCDfile,'Filter:  ',Obj.FiltName)
     cur.FiltNum = Obj.FiltNum
     cur.FiltName = Obj.FiltName
     writeln(CCDfile,'Obj ID:  ',Obj.ID)
     cur.ObjID = Obj.ID
     writeln(CCDfile,'App. RA: ',Obj.RaH:0:0,' ',Obj.RaM:0:0,' ',Obj.RaS:0:3)
     cur.ObjRAs = Format('%2.0f %2.0f %2.2f', [Obj.RaH, Obj.RaM, Obj.RaS])
     writeln(CCDfile,'App. Dec:',Obj.DecD:0:0,' ',Obj.DecM:0:0,' ',Obj.DecS:0:3)
     cur.ObjDecs = Format('%2.0f %2.0f %2.2f', [Obj.DecD, Obj.DecM, Obj.DecS])
     writeln(CCDfile,'Epoch:   ',Obj.Epoch:0:7)
     cur.Epoch = Obj.Epoch
     write(CCDfile,  'UT:      ',int(Obj.Time.UTdec):2:0,' ')
     write(CCDfile,int(frac(Obj.Time.UTdec)*60):2:0,' ')
     writeln(CCDfile,frac(Obj.Time.UTdec)*3600-int(frac(Obj.Time.UTdec)*60)*60:2:3)
     cur.UT = Obj.Time.UTdec

#Yes, I know the following won't work where TimeZone>0 and the system clock }
#isn't set to UT. It also writes a '0' for day of the month occasionally.   }
#The solution is to leave the computer running on UT, not local time...     }

     if (Obj.Time.UTdec > (24+TimeZone)) and (not UTSystemClock):
        begin
             writeln(CCDfile, 'UT_Date: ',Obj.Time.dy-1,' ',Obj.Time.mnth,' ',Obj.Time.yr)
             cur.UT_Date_day = Obj.Time.dy-1
        end
     else:
         begin
              writeln(CCDfile,'UT_Date: ',Obj.Time.dy,' ',Obj.Time.mnth,' ',Obj.Time.yr)
              cur.UT_Date_day = Obj.Time.dy
         end-with-semicolon
     cur.UT_Date_month = Obj.Time.mnth
     cur.UT_DATE_year = Obj.Time.yr

     writeln(CCDfile,'Jul Day: ',Obj.Time.JD:0:7)
     cur.JulDay = Obj.Time.JD
     writeln(CCDfile,'Alt:     ',Obj.Alt:0:7)
     cur.Alt = Obj.Alt
     writeln(CCDfile,'Azi:     ',Obj.Azi:0:7)
     cur.Azi = Obj.Azi
     writeln(CCDfile,'RATrck:  ',Obj.TraRa:0:7)
     cur.RAtrack = Obj.TraRA
     writeln(CCDfile,'DecTrck: ',Obj.TraDec:0:7)
     cur.DECtrack = Obj.TraDec
     writeln(CCDfile,'XYPos:   ',Obj.Xoff,' ',Obj.Yoff)
     cur.XYpos_X = Obj.Xoff
     cur.XYpos_Y = Obj.Yoff
     writeln(CCDfile,'Imgetype:',Obj.Imagetype)
     cur.ObsType = Obj.Imagetype
     writeln(CCDfile,'Comment: ',Obj.Comment)
     cur.Comment = Obj.Comment
     close(CCDfile)

     WriteSQLBox(cur)

     if SemiAuto:  #Wait for keypress after writing mail}
        begin
             wWrite('Press any key for next object:')
             # Sound(1000) }
             Delay(300)
             # NoSound }
             repeat
                   ForceNext = false
                   if keypressed:
                      begin
                           an = ReadKey
                           if UpCase(an)='Q':
                              WantsExit = true
                           Forcenext = true
                      end-with-semicolon
                   DetermineEvent
                   Delay(100)
             until ForceNext=true
        end-with-semicolon  #of if SemiAuto}

end-with-semicolon



Procedure ClearLogFile
var logfile:text
    d,m,y,hr,mt,sc,hn:integer
    lname,tmps:string[40]
begin
     GetSysDate(d,m,y)
     GetSysTime(hr,mt,sc,hn)
     Str(y:0,tmps)
     lname = System.Copy(tmps,3,2)+Chr(m-1+Ord('A'))
     Str(d:0,tmps)
     lname = lname+tmps+Chr(hr-1+Ord('A'))
     Str(mt:0,tmps)
     lname = lname+tmps+'.log'
     LogFileName = LogDirName+'\'+lname
     SaveLogFileName = LogFileName
     sWrite('Log file name = |'+LogFileName+'|')
     assign(logfile,LogFileName)
     rewrite(logfile)
     writeln(logfile,'Log for list:   ',DataFileName)
     writeln(logfile,'On the ',d,'/',m,'/',y,', at ',hr,':',mt,':',sc,'.',hn)
     close(logfile)
end-with-semicolon

Procedure ReadSeqNo
var DE:integer
begin
     DE = FindFirst(Seqfile,AnyFile,SR)
     if (DE = 0):                #Sequence no file exists, read}
        begin                               #last sequence no.}
             assign(Sequenfile,Seqfile)
             Reset(Sequenfile)
             readln(Sequenfile,SeqNo)
             Close(Sequenfile)
        end
     else:
         SeqNo = 0                    #Sequence No file does not exist}
     FindClose(SR)
end-with-semicolon                                    #will be created.}


Procedure WriteSeqNo
begin
     assign(Sequenfile,Seqfile)
     Rewrite(Sequenfile)
     writeln(Sequenfile,SeqNo)            #Write out current sequence no.}
     Close(Sequenfile)
end-with-semicolon


Procedure CheckWeather(var ClearSky:boolean)
var i:integer
begin
     ClearSky = true #This will change if weather sensors are ever used...}
     for i = 0 to 10 do
         begin
              Delay(100)
              DetermineEvent
              ReadMail
         end-with-semicolon
end-with-semicolon


Procedure Automation
var DE:integer
begin
     CCDMail = GetProfileStr(Inif,'Paths','CCDMail','c:\mail\ccd.box')
     VistaMail = GetProfileStr(Inif,'Paths','VistaMail','c:\mail\sch.box')
     Seqfile = GetProfileStr(Inif,'Paths','SeqFile','c:\Logs\Sequen.dat')
     LogDirName = GetProfileStr(Inif,'Paths','LogDirName','C:\logs')

     Window(1,7,80,25)
     TextBackground(White)
     TextColor(Blue)
     clrscr
     SeqNo = 0

     GetDataFilename
     if ((DataFileName='R') or (DataFileName='r')) and (mObjList<>nil):
        begin
             sWrite('Resuming old list:')
             LogFileName = SaveLogFileName
        end
     else:
         begin
              CurNum = 1

              if Pos(' ',DataFileName)<>0:
                 begin
                      Val(System.Copy(DataFileName, Pos(' ',DataFileName) ,255),CurNum,err)
                      DataFileName = System.Copy(DataFilename,1,Pos(' ',DataFileName)-1)
                 end-with-semicolon
              CurNum = CurNum-1
              if CurNum<0:
                 CurNum = 0

              mObjList = NIL
              CleanUp(mObjListSave)
              if pos('\',DataFileName)=0:
                 DataFileName = 'T:\533-ob~1\astron~1\plat\lists\'+DataFileName
              if pos('.',DataFileName)=0:
                 DataFileName = DataFileName+'.lis'
              GetList(DataFileName,mObjList,numread,err)
              if (err<>0):
                 eWrite('*****     Warning - error in file!  *****')
              if (numread=0) or (CurNum+1 > NumRead):
                 begin
                      eWrite('*****     No objects to jump to. Aborting.    *****')
                      delay(4000)
                      CleanUp(mObjList)
                      System.Exit
                 end-with-semicolon
              mObjListSave = mObjList

              for i = 2 to CurNum+1 do
                  mObjList = tail(mObjList)

         end-with-semicolon

     ClearLogFile

     ReadSeqNo
     CanWriteMail = false

     sWrite('*****     Beginning Automatic operation...   *****')

     if true:                 #Insert apropriate test here - eg, ask}
                                  #if dome is open}
        begin
             CheckWeather(ClearSky)
             if ClearSky:             #Check weather, dummy code for now}
                begin
                     FirstObject = true
                     FirstTime = true
                     NotSame = true
                     Foundsomething = false
                     WantsExit = false
                     TimeLast.Ltdec = 0
                     AutoRunning = true

                     while (not WantsExit) and ClearSky and (not null(mObjList))
                         and (not HWlimit) do
                           begin
                                CheckWeather(ClearSky)

                                if keypressed:
                                   begin
                                        an = ReadKey
                                        if (UpCase(an)='Q') or (ord(an)=27):
                                           WantsExit = true
                                   end-with-semicolon

                                if NotSame:
                                   begin
                                        if FirstTime:
                                           begin
                                                DE = FindFirst(CCDMail,AnyFile,SR)
                                                if (DE = 18) or (not ExistsSQLBox) or SemiAuto:
                                                   begin
                                                        CurNum = CurNum+1
                                                        head(NextObject,mObjList)

                                                        repeat
                                                              if not HWlimit:
                                                                 Jump(IObj,NextObject,SlewRate,AltErr)
                                                              if AltErr:
                                                                 begin
                                                                      eWrite('*****    Object '+IObj.ID+
                                                                         ' Below Alt Limit:   *******')
                                                                      mObjList = tail(mObjList)
                                                                      CurNum = CurNum+1
                                                                      if (not null(mObjList)) and
                                                                        (not HWlimit):
                                                                         head(NextObject,mObjList)
                                                                      else:
                                                                          NextObject = IObj
                                                                 end-with-semicolon
                                                        until (not AltErr) or (null(mObjList)) or HWlimit

                                                        if AutoDome:
                                                           DomeMoveWait(DomeCalcAzi(NextObject))

                                                        FirstTime = false
                                                        CanWriteMail = true
                                                        IObj = NextObject

                                                        repeat
                                                              DetermineEvent
                                                              ReadMail
                                                              delay(1000)
                                                        until not moving

                                                   end-with-semicolon #of if doserror=18}
                                                FindClose(SR)
                                           end-with-semicolon      #of if FirstTime}
                                   end-with-semicolon         #of if NotSame}

                                if not teljump:
                                   begin
                                        if CanWriteMail:
                                           begin

                                                sWrite('Writing mail file for SeqNo '+
                                                    IntToStr(SeqNo)+' = '+IObj.ID+
                                                   ', object number '+IntToStr(CurNum)+' of '+
                                                   IntToStr(NumRead)+'.')
                                                WriteMail(CCDMail,NextObject) #Write mail file}
                                                WriteSeqNo           #Update seq. no. file}

                                                if keypressed:
                                                   begin
                                                        an = ReadKey
                                                        if (UpCase(an)='Q') or (ord(an)=27):
                                                           WantsExit = true
                                                   end-with-semicolon

                                                NotSame = false
                                                CanWriteMail = false
                                           end-with-semicolon    #of if CanWriteMail}
                                   end-with-semicolon    #of if not teljump}


                                if Not(NotSame):
                                   begin
                                        ReadMail

                                        if not null(mObjList):
                                           mObjList = tail(mObjList)
                                        FirstObject = false
                                        FirstTime = true
                                        NotSame = true
                                   end-with-semicolon  #of if not(NotSame) }
                           end-with-semicolon  #of while not(WantsExit ... }
                end    #of if ClearSky }
             else: #not ClearSky}
                 eWrite('CheckWeather returned false, Sky/Weather Unsuitable')

        end   #of final check }
     else:    #final check failed}
         eWrite('Dome Failure')

         sWrite('Ending automation')

     LogFileName = ''
     AutoRunning = false

     if not WantsExit:
        begin
              CleanUp(mObjListSave)
              mObjList = nil
              mObjListSave = nil
              if not SemiAuto:
                 begin
                      sWrite('Waiting for last sch.box file.')
                      repeat
                            ReadMail
                            DetermineEvent
                            if keypressed:
                               begin
                                    an = ReadKey
                                    if (UpCase(an)='Q') or (ord(an)=27):
                                       WantsExit = true
                               end-with-semicolon
                      until WantsExit or (SeqNo=SQNread)
                 end-with-semicolon

        end-with-semicolon
     ClearSQLBox    #Tidy up mailbox}
     assign(CCDFile,CCDMail)
     Erase(CCDFile)
end-with-semicolon      #of procedure Automation}


begin #unit init}
      CCDMail = GetProfileStr(Inif,'Paths','CCDMail','c:\mail\ccd.box')
      VistaMail = GetProfileStr(Inif,'Paths','VistaMail','c:\mail\sch.box')
      Seqfile = GetProfileStr(Inif,'Paths','SeqFile','c:\Logs\Sequen.dat')
      LogDirName = GetProfileStr(Inif,'Paths','LogDirName','C:\logs')

      LogFileName = ''
      SaveLogFileName = ''
      mObjList = nil
      mObjListSave = nil
end.
