{$N+$E+}
unit ReadList;

interface

uses Globals,ObjList, Use32;

procedure ParseLine(line:string; linenum:integer; var Obj:ObjectRec;
                     var err:integer);

procedure GetList(listname:string; var ObjList:List; var numread,err:integer);

implementation

uses ReadIn,SysUtils,crt;

type FieldType=(name,ID,RA,Dec,Epoch,Filter,ExpTime,ImageType,XYPos,Comment,error);


function LineType(s:string):FieldType;
begin
     if Pos('NAME',s)<>0 then
        LineType:=name
     else if Pos('ID',s)<>0 then
             LineType:=ID
     else if Pos('RA',s)<>0 then
             LineType:=RA
     else if Pos('DEC',s)<>0 then
             LineType:=Dec
     else if Pos('EPOCH',s)<>0 then
             LineType:=Epoch
     else if Pos('FILT',s)<>0 then
             LineType:=Filter
     else if Pos('EXP',s)<>0 then
             LineType:=ExpTime
     else if Pos('TYPE',s)<>0 then
             LineType:=ImageType
     else if Pos('XYPOS',s)<>0 then
             LineType:=XYPos
     else if Pos('COMMENT',s)<>0 then
             LineType:=Comment
     else
          LineType:=error;
end;

procedure ParseLine(line:string; linenum:integer; var Obj:ObjectRec;
                     var err:integer);
var hdr:string;
    value:string;
    ltype:FieldType;
    colon:integer;
    negdec:boolean;
    v:double;

begin
     err:=0;
     colon:=Pos(':',line);
     if colon=0 then
        begin
            { Writeln('Warning- no colon on line ',linenum,': ',line);  }
             colon:=10;
        end;

     hdr:=System.Copy(line,1,colon-1);
     value:=munchspace(System.Copy(line,colon+1,999));
     hdr:=UpString(hdr);

     ltype:=LineType(hdr);

     case ltype of
          name:Obj.NameDesc:=value;
          ID:Obj.ID:=value;
          RA:begin
                  ConvStr(value,v,dms,err);
                  if err<>0 then
                     begin
                          Writeln('Error in RA value on line ',linenum,': ',line);
                          System.Exit;
                     end;
                  Obj.RA:=v*15;
                  ConvDMS(Obj.RA/15,Obj.RaH,Obj.RaM,Obj.RaS);
             end;
          Dec:begin
                   ConvStr(value,v,dms,err);
                   if err<>0 then
                      begin
                           Writeln('Error in Dec Value on line ',linenum,': ',line);
                           System.Exit;
                      end;
                   Obj.Dec:=v;
                   ConvDMS(Obj.Dec,Obj.DecD,Obj.DecM,Obj.DecS);
              end;
          Epoch:begin
                     ConvStr(value,v,num,err);
                     if err<>0 then
                        begin
                             Writeln('Error in Epoch value on line ',linenum,': ',line);
                             System.Exit;
                        end;
                     Obj.Epoch:=v;
                end;
          Filter:begin
                      value:=munchspace(value);
                      Obj.FiltNum:=GetFiltNum(value);
                      Obj.FiltName:=value;
                      if Obj.FiltNum=8 then
                         writeln('Unknown filter name ''',value,''' on line ',linenum);
                 end;
          ExpTime:begin
                       ConvStr(value,v,num,err);
                       if err<>0 then
                          begin
                               Writeln('Error in Exp. time on line ',linenum,': ',line);
                               System.Exit;
                          end;
                       Obj.ExpTime:=v;
                  end;
          ImageType:Obj.ImageType:=value;
          XYPos:begin
                     value:=munchspace(value);   {strip leading spaces}
                     Val(System.Copy(value,1,pos(' ',value)-1),Obj.Xoff,err);
                     value:=System.Copy(value,pos(' ',value)+1,999);
                     if err=0 then
                        Val(value,Obj.Yoff,err);
                     writeln('XYPos=',Obj.Xoff,' ',Obj.Yoff);
                     if err<>0 then
                        begin
                             writeln('Error in XYPOS value on line ',linenum,': ',line);
                             System.Exit;
                        end;
                end;
          Comment:Obj.Comment:=value;
          error:begin
                     Writeln('Error- unknown field on line ',linenum,': ',line);
                     System.Exit;
                end;
     end;  {of case}
end;  {of ParseLine}

procedure GetList(listname:string; var ObjList:List; var numread,err:integer);
var f:text;
    linenum:integer;
    DirInfo:TSearchRec;
    line:string;
    Obj:ObjectRec;
    tmp:integer;

begin
     err:=1;
     writeln('Opening file: ',listname);
{$I-}
     tmp:=FindFirst(listname,faAnyFile,DirInfo);
     FindClose(DirInfo);
     if IOResult <> 0 then
        System.Exit;
     if tmp<>0 then
        begin
             Writeln('File |'+listname+'| not found...  Error = ',tmp);
             delay(2000);
             System.Exit;
        end;
     Assign(f,listname);
     Reset(f);
{$I+}
     if IOResult <> 0 then
        System.Exit;

     writeln('About to read the list.');

     linenum:=0;
     numread:=0;
     Obj.Comment:='';    {initialise object fields}
     Obj.ImageType:='junk';
     Obj.FiltNum:=8;
     Obj.FiltName:='XXXXX';
     Obj.NameDesc:='Nil Name';
     Obj.ID:='Nil';
     Obj.TraRA:=0;
     Obj.TraDEC:=0;
     Obj.Xoff:=0;
     Obj.Yoff:=0;

     repeat
           repeat
                 ReadLn(f,line);
                 linenum:=linenum+1;
           until (line<>'') or Eof(f);

           if not EoF(f) then
              begin
                   repeat
                         ParseLine(line,linenum,Obj,err);
                         if err<>0 then
                            begin
                                 Writeln('Error in file on line ',linenum,': ',line);
                                 close(f);
                                 System.Exit;
                            end;

                         Readln(f,line);
                         linenum:=linenum+1;
                   until (line='') or EoF(f);

                   Obj.Comp:=true;
                   Obj.TraRa:=0;
                   ObjList:=append(Objlist,Obj);
                   numread:=numread+1;
                   writeln('Got object: ',Obj.ID);
              end;  {of if not eof}
     until Eof(f);
     writeln('List successfull. ',numread,' objects read.');
     close(f);

end;

end.

