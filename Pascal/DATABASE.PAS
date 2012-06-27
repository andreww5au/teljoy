unit DataBase;
interface
uses Globals, Use32;

function DataLookup(name:string10; var Obj:ObjectRec; ask:boolean):boolean;

implementation

uses Crt, SQLInt, SysUtils;

const DataName='d:\ObjData.txt';
var data:text;


function MergeStrDMS(const dms:string40; var dmsVal:double):boolean;
                           {returns true if no error in conversion}
var d,m,s:string10;
    tmps:string40;
    dv,mv,sv:single;
    sign:integer;
    dcode,mcode,scode,i:integer;
begin
     d:='';    m:='';    s:='';
     dv:=0;    mv:=0;    sv:=0;
     d:=Copy(dms,1,Pos(':',dms)-1);
     if d[1]='-' then
        sign:=-1
     else
         sign:=1;
     tmps:=Copy(dms,Pos(':',dms)+1,255);
     if Pos(':',tmps) <> 0 then
        begin
             m:=Copy(tmps,1,Pos(':',tmps)-1);
             s:=Copy(tmps,Pos(':',tmps)+1,255);
        end
     else
         m:=Copy(tmps,1,255);

     Val(d,dv,dcode);
     Val(m,mv,mcode);
     if s<>'' then
        Val(s,sv,scode)
     else
         scode:=0;

     if (d='') or (m='') or (dcode<>0) or (mcode<>0) or (scode<>0) then
        MergeStrDMS:=false
     else
         MergeStrDMS:=true;

     dmsVal:=dv*3600 + sign*mv*60 + sign*sv;
end;


function OldLookup(name:string10; var Obj:ObjectRec):boolean;
var found:boolean;
    dataline:string;
    RA,Dec,Epoch:double;
    i,j,code:integer;
    tmps1,tmps2,tmps3,tmps4:string40;
begin
     Assign(data,DataName);
     reset(data);
     found:=false;
     Epoch:=0;
     if name='' then
        begin
             Result:=false;
             close(data);
             Exit;
        end;
     for i:=1 to length(name) do
         name[i]:=upcase(name[i]);
     while (not eof(data)) and (not found) do
           begin
                readln(data,dataline);
                i:=1;
                tmps1:='';
                while (dataline[i] <> ' ') and (dataline[i] <> chr(9)) and
                    (i <= length(dataline)) do
                      begin
                           tmps1:=tmps1+upcase(dataline[i]);
                           inc(i);
                      end;

                if name=tmps1 then
                   found:=true;
                if dataline[1]='*' then
                   begin
                        tmps1:=Copy(dataline,2,length(dataline));
                        Val(tmps1,Epoch,code);
                        if code<>0 then
                           Epoch:=0;
                   end;
           end;
     if not found then
        begin
             Result:=false;
             close(data);
             Exit;
        end;
     for j:=1 to length(dataline) do   {Convert tabs to spaces in dataline}
         if ord(dataline[j])=9 then
            dataline[j]:=' ';

     writeln('Object found:');
     writeln(dataline);

     tmps2:='';
     tmps3:='';
     tmps4:='';
     while (dataline[i]=' ') and (i <= length(dataline)) do
           inc(i);
     while (dataline[i] <> ' ') and (i <= length(dataline)) do
           begin
                tmps2:=tmps2+dataline[i];
                inc(i);
           end;
     while (dataline[i]=' ') and (i <= length(dataline)) do
           inc(i);
     while (dataline[i] <> ' ') and (i <= length(dataline)) do
           begin
                tmps3:=tmps3+dataline[i];
                inc(i);
           end;
     while (dataline[i]=' ') and (i <= length(dataline)) do
           inc(i);
     while (dataline[i] <> ' ') and (i <= length(dataline)) do
           begin
                tmps4:=tmps4+dataline[i];
                inc(i);
           end;

     if tmps4 <> '' then
        Val(tmps4,Obj.Epoch,code)
     else
         Obj.Epoch:=Epoch;

     if MergeStrDMS(tmps2,Obj.RA) and MergeStrDMS(tmps3,Obj.Dec) and (code=0) then
        begin
             Result:=true;
             Obj.ID:=tmps1;
             Obj.RA:=Obj.RA*15;
             Obj.Comp:=true;
        end
     else
         Writeln('Error in object coordinates!');

     close(data);
end;



function DataLookup(name:string10; var Obj:ObjectRec; ask:boolean):boolean;
var found:boolean;
    i:integer;
    gal:galaxy;
    s:string;
begin
     found:=GetObject(name, Obj);
     if not found then
        found:=OldLookup(name, Obj);
     if not found then
        begin
             i:=GetRC3byName(name, gal, 1);   {Return first match}
             if i>0 then
                begin
                     if length(gal.name)>7 then
                        Obj.ID:='P'+IntToStr(gal.PGC)
                     else
                         Obj.ID:=gal.name;
                     Obj.ID:=gal.name;
                     Obj.RA:=gal.RA2000*15*3600;
                     Obj.DEC:=gal.DEC2000*3600;
                     Obj.Epoch:=2000;
                     Obj.NameDesc:=gal.name;
                     Obj.Comp:=true;
                     if i>1 then
                        writeln(i,' possible matches to that name, taking the first candidate.');
                     found:=true;
                end;
        end;

     if ask then
        if found then
           begin
                writeln('Object: '+Obj.ID+' ('+Obj.NameDesc+') found:');
                writeln('RA  = ',DMSstrp(Obj.RA/15, ':'));
                writeln('DEC = ',DMSstrp(Obj.Dec, ':'));
                writeln('Epoch=',Obj.Epoch:0:1);
                writeln;
                write('Is this correct? (Y) ');
                readln(s);
                if length(s)>1 then
                   s:=s[1];
                if (s<>'') and (s<>'Y') and (s<>'y') then
                   found:=false;
           end
        else
           eWrite('Object '+name+' not found by DataLookup');

     Result:=found;
end;



end.
