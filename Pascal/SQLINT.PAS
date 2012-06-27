unit sqlint;

interface

uses Use32,Globals,libMySQL;

type
    CurrentInfo = record
                        posviolate:boolean;
                        moving:boolean;
                        EastOfPier:boolean;
                        NonSidOn:boolean;
                        DomeInUse:boolean;
                        ShutterInUse:boolean;
                        ShutterOpen:boolean;
                        DomeTracking:boolean;
                        Frozen:boolean;
                        AutoRunning:boolean;
                        NumRead:integer;
                        CurNum:integer;
                        RA_GuideAcc:double;
                        LastError:string[80];
                        Dec_GuideAcc:double;
                  end;

    TJboxrec = record
                     OffsetRA:double;
                     OffsetDec:double;
                     DomeAzi:double;
                     Shutter:boolean;   {True for open}
                     Freeze:boolean;    {True for frozen}
                     LastMod:string;
               end;
    TJaction = (none,error,jumpID,jumpRD,jumpAA,nonsid,offset,dome,shutter,freez);

var MySQLActive:boolean;  {true if DB connection is up}
    quer                  : PChar;
    mysql                 : libMySQL.MYSQL;
    res                   : PMYSQL_RES;
    row                   : PMYSQL_ROW;
    SQLExitSave           : pointer;


function ReadTJbox(var Pos:ObjectRec; var other:TJboxrec; LastMod:integer):TJaction;
      {Read the Teljoy box data into an object record}

function ExistsTJbox:boolean;

procedure ClearTJBox;

procedure ReadSQLCurrent(var Here:ObjectRec; var Current:CurrentInfo; var HA:real; var LastMod:integer);
      {Read the current position data into an object record}

procedure UpdateSQLCurrent(var Here:ObjectRec; var Current:CurrentInfo);

procedure WriteLog(cur:snresult);

function IsTarget(id:string):boolean;

procedure GetGalaxy(id:string; var gal:galaxy; var numr:integer; ObjDec:double);

function GetRC3ByName(id:string; var gal:galaxy; num:integer):integer;

procedure WriteSQLBox(cur:snresult);

procedure ClearSQLBox;

function ExistsSQLBox:boolean;

function fixup(id:string):string;

function fVal(s:string):double;

function GetObject(n:string; var Pos:ObjectRec):boolean;


implementation

uses crt,SysUtils,VPUtils,ReadIn;

function fVal(s:string):double;
var dummy:integer;
begin
     Val(s,Result,dummy);
end;

function RASplit(ra:string):double;
var h,m,s:real;
begin
     ra:=munchspace(ra);
     h:=fVal(Copy(ra,1,2));
     m:=fVal(Copy(ra,3,2));
     s:=fVal(Copy(ra,5,99));
     Result:=h+m/60+s/3600;
end;

function DECSplit(dec:string):double;
var d,m,s:real;
    sign:real;
begin
     dec:=munchspace(dec);
     sign:=-1;
     if dec[1]<>'-' then
        begin
             sign:=1;
             if dec[1]<>'+' then
                dec:='+'+dec;
        end;

     d:=fVal(Copy(dec,2,2));
     m:=fVal(Copy(dec,4,2));
     s:=fVal(Copy(dec,6,99));
     Result:=sign*(d+m/60+s/3600);
end;


function lzstrip(n:string):string;
var i:integer;
begin
     i:=1;
     while n[i]='0' do
           i:=i+1;
     Result:=Copy(n,i,999);
end;


function IsTarget(id:string):boolean;
var qstr:string;
begin
     Result:=false;
     if not MySQLActive then
        begin
             eWrite('No SQL connection active, can''t read sn.targets.');
             System.Exit;
        end;

     qstr:='select ObjID from targets where ObjID='''+ID+''' or altID='''+ID+''''#0;
     mysql_select_db(@mysql,'sn');
     mysql_query(@mysql,@qstr[1]);
     {return the table elements in that order}

     res:=mysql_use_result(@mysql);  {returns a handle to a result}
     if res=nil then
        begin
             eWrite(Format('sn.targets failed; error: ''%s'''#7#13#10,[mysql_error(@mysql)]));
        end
     else
         begin
              row := mysql_fetch_row(res);  {given a result handle, return the next row}

              if row<>nil then
                 Result:=true;

              repeat
                    row:=mysql_fetch_row(res);
              until row=nil;

              mysql_free_result(res);  {Free result buffer on server}
         end; {of valid result processing}
end;  {Of function IsTarget}


procedure GetGalaxy(id:string; var gal:galaxy; var numr:integer; ObjDec:double);
var
   ids:string[8];
   i:integer;
   qstr,qstr2:string;
   BT,BMag:single;
   dummy:array[0..1024] of char;
   querystr:PChar;

begin
     sWrite('Getting galaxy '+id+': ');
     if not MySQLActive then
        begin
             eWrite('No SQL connection active, can''t GetGalaxy.');
             System.Exit;
        end;

     id:=upstring(id);
     ids:=Copy(id,2,6);

     if (id[1]='N') then
        begin
             ids:='';
             for i:=1 to length(id) do
                 if (id[i]>='0') and (id[i]<='9') then
                    ids:=ids+id[i];
             qstr2:='Name regexp "NGC +'+ids+'$"'#0;
        end
     else if (id[1]='P') then
             begin
                  ids:='';
                  for i:=1 to length(id) do
                      if (id[i]>='0') and (id[i]<='9') then
                         ids:=ids+id[i];
                  qstr2:='PGC="'+ids+'"'#0;
             end
     else if (id[1]='I') then
             begin
                  ids:='';
                  for i:=1 to length(id) do
                      if (id[i]>='0') and (id[i]<='9') then
                         ids:=ids+id[i];
                  qstr2:='Name like "IC %'+ids+'"'#0;
             end
     else if (id[1]='R') and (length(id)=7) then
        begin
             qstr2:='RA1950 between lpad('''+ids+
                    '''-1.0,8,''0'') and lpad('''+ids+'''+1.0,8,''0'')';
             if ObjDec<>0 then
                qstr2:=qstr2+' and ( DEC1950 between concat(''-'',lpad('''+
                        DMSStrp(Abs(ObjDec),'')+
                        '''-60,6,''0'')) and concat(''-'',lpad('''+
                        DMSStrp(Abs(ObjDec),'')+'''+60,6,''0'')) )'#0
             else
                 qstr2:=qstr2+#0;
        end
     else if (id[1]='J') and (length(id)=7) then
        begin
             qstr2:='RA2000 between lpad('''+ids+
                    '''-1.0,8,''0'') and lpad('''+ids+'''+1.0,8,''0'')';
             if ObjDec<>0 then
                qstr2:=qstr2+' and ( DEC2000 between concat(''-'',lpad('''+
                        DMSStrp(Abs(ObjDec),'')+
                        '''-60,6,''0'')) and concat(''-'',lpad('''+
                        DMSStrp(Abs(ObjDec),'')+'''+60,6,''0'')) )'#0
             else
                 qstr2:=qstr2+#0;
        end
     else if (id[1]='E') and (length(id)=7) then
        begin
             qstr2:='( RA1950 between lpad('''+ids+
                    '''-2.5,8,''0'') and lpad('''+ids+'''+2.5,8,''0'') )';
             if ObjDec<>0 then
                qstr2:=qstr2+' and ( DEC1950 between concat(''-'',lpad('''+
                        DMSStrp(Abs(ObjDec),'')+
                        '''-60,6,''0'')) and concat(''-'',lpad('''+
                        DMSStrp(Abs(ObjDec),'')+'''+60,6,''0'')) )'#0
             else
                 qstr2:=qstr2+#0;
        end
     else if (id[1]='T') and (length(id)=7) then
        begin
             qstr2:='( RA1950 between lpad('''+ids+
                    '''-2.5,8,''0'') and lpad('''+ids+'''+2.5,8,''0'') )';
             if ObjDec<>0 then
                qstr2:=qstr2+' and ( DEC1950 between concat(''-'',lpad('''+
                        DMSStrp(Abs(ObjDec),'')+
                        '''-10000,6,''0'')) and concat(''-'',lpad('''+
                        DMSStrp(Abs(ObjDec),'')+'''+10000,6,''0'')) )'#0
             else
                 qstr2:=qstr2+#0;
        end
     else
         qstr2:='Name='''+id+''' or PGC='''+id+''''#0;


     qstr:='select RA2000,DEC2000,RA1950,DEC1950,Name,PGC,Hubble_T,R25,BT,Bmag,V3K from rc3 where '#0;
     querystr:=dummy;
     querystr:=StrCopy(querystr,@qstr[1]);
     querystr:=StrCat(querystr,@qstr2[1]);

{     writeln(querystr);
}
     mysql_select_db(@mysql,'sn');
     mysql_query(@mysql,@querystr[0]);

     res:=mysql_use_result(@mysql);  {returns a handle to a result}
     if res=nil then
        begin
             eWrite(Format('sn.rc3 failed; error: ''%s'''#7#13#10,[mysql_error(@mysql)]));
        end
     else
         begin
              row := mysql_fetch_row(res);  {given a result handle, return the next row}

              numr:=0;
              if row<>nil then
                 begin
                      gal.RA2000s:=Strpas(row^[0]);
                      gal.RA2000:=RAsplit(gal.RA2000s);
                      gal.DEC2000s:=StrPas(row^[1]);
                      gal.DEC2000:=DECSplit(gal.DEC2000s);

                      gal.RA1950s:=Strpas(row^[2]);
                      gal.RA1950:=RAsplit(gal.RA1950s);
                      gal.DEC1950s:=StrPas(row^[3]);
                      gal.DEC1950:=DECSplit(gal.DEC1950s);

                      gal.Name:=StrPas(row^[4]);
                      gal.PGC:=StrToInt(row^[5]);
                      gal.Hubble_T:=fVal(StrPas(row^[6]));
                      gal.R25:=fVal(StrPas(row^[7]));
                      BT:=fVal(StrPas(row^[8]));
                      Bmag:=fVal(StrPas(row^[9]));
                      if BT>0 then
                         gal.Bmag:=BT
                      else
                          gal.Bmag:=Bmag;
                      gal.V3K:=fVal(StrPas(row^[10]));
                      numr:=1;
                 end;  {of row<>nil}

              repeat
                    row:=mysql_fetch_row(res);
                    if row<>nil then
                       numr:=numr+1;
              until row=nil;

              mysql_free_result(res);  {Free result buffer on server}
         end; {of valid result processing}

{     write(numr,' hits in RC3. ');  }

     if numr=0 then
        begin   {We havent found the galaxy in the RC3 list...}
             ids:=fixup(id);
{             write('fixup=|'+ids+'| ');
}
             if ids<>'' then   {it was in fixups, and 'ids' is the PGC}
                begin
                     GetGalaxy(ids,gal,numr,ObjDec);
                     numr:=1;
                end
             else {It wasn't in the fixup list, check in esogals}
                 begin
                      qstr:='select RA1950,DEC1950d,Name,PGC,'+
                            'Hubble_T,BMag,RadVel from esogals where '+
                            'RA1950='''+Copy(id,2,6)+''''#0;

                      mysql_select_db(@mysql,'sn');
                      mysql_query(@mysql,@qstr[1]);

                      res:=mysql_use_result(@mysql);  {returns a handle to a result}
                      if res=nil then
                         begin
                              eWrite(Format('sn.esogals failed; error: ''%s'''#7#13#10,[mysql_error(@mysql)]));
                         end
                      else
                          begin
                               row := mysql_fetch_row(res);  {given a result handle, return the next row}

                               numr:=0;
                               if row<>nil then
                                  begin
                                       gal.RA1950s:=Strpas(row^[0]);
                                       gal.RA1950:=RAsplit(gal.RA1950s);
                                       gal.DEC1950:=fVal(StrPas(row^[1]));

                                       gal.Name:=StrPas(row^[2]);
                                       gal.PGC:=StrToInt(row^[3]);
                                       gal.Hubble_T:=fVal(StrPas(row^[4]));
                                       gal.Bmag:=fVal(StrPas(row^[5]));
                                       gal.V3K:=fVal(StrPas(row^[6]));
                                       gal.R25:=0;
                                       gal.DEC1950s:='';
                                       gal.RA2000:=gal.RA1950;
                                       gal.RA2000s:=gal.RA1950s;
                                       gal.DEC2000:=gal.DEC1950;
                                       gal.DEC2000s:=gal.DEC1950s;
                                       numr:=1;
                                  end;  {of row<>nil}

                               repeat
                                     row:=mysql_fetch_row(res);
                                     if row<>nil then
                                        numr:=numr+1;
                               until row=nil;

                               mysql_free_result(res);  {Free result buffer on server}
                          end; {of esogal result processing}
                 end;  {of testing 'esogals' table}
        end;  {of 'if numr=0'}

        if numr=1 then
           writeln('PGC=',gal.PGC)
        else if numr>1 then
           writeln('Warning - Duplicate match for '+ids);
end;  {of procedure GetGalaxy}


function GetRC3ByName(id:string; var gal:galaxy; num:integer):integer;
var
   ids,num1,num2,num3:string;
   i:integer;
   qstr,qstr2:string;
   BT,BMag:single;
   dummy:array[0..1024] of char;
   numr:integer;

begin
     Writeln('Searching for galaxy '+id+' in RC3 catalog.');
     if not MySQLActive then
        begin
             eWrite('No SQL connection active, can''t GetRC3ByName.');
             System.Exit;
        end;

     ids:=upstring(id);

     i:=1;
     num1:='';
     num2:='';
     num3:='';
     while ( (id[i]<'0') or (id[i]>'9') ) and (i<=length(id)) do
           i:=i+1;
     while (id[i]>='0') and (id[i]<='9') and (i<=length(id)) do
           begin
                num1:=num1+id[i];
                i:=i+1;
           end;

     while ( (id[i]<'0') or (id[i]>'9') ) and (i<=length(id)) do
           i:=i+1;
     while (id[i]>='0') and (id[i]<='9') and (i<=length(id)) do
           begin
                num2:=num2+id[i];
                i:=i+1;
           end;

     while ( (id[i]<'0') or (id[i]>'9') ) and (i<=length(id)) do
           i:=i+1;
     while (id[i]>='0') and (id[i]<='9') and (i<=length(id)) do
           begin
                num3:=num3+id[i];
                i:=i+1;
           end;


     if (ids[1]='N') then
        qstr2:='Name regexp "NGC +0*'+lzstrip(num1)+'$" '#0
     else if (ids[1]='P') then
             qstr2:='PGC="'+num1+'"'
     else if (ids[1]='I') and (ids[2]='R') then
             qstr2:='desig regexp "IRAS'+num1+'-'+num2+'$" '
     else if (ids[1]='I') then
             qstr2:='Name regexp "IC +0*'+lzstrip(num1)+'$" '
     else if (ids[1]='A') then
             qstr2:='Name regexp "A *'+Copy(ids,2,999)+'" '
     else if (ids[1]='U') then
             qstr2:='altname regexp "UGC +0*'+lzstrip(num1)+'$" '
     else if (ids[1]='E') then
             qstr2:='altname regexp "ESO +0*'+lzstrip(num1)+'- *0*'+lzstrip(num2)+'$" '
     else if (ids[1]='M') then
             qstr2:='altname regexp "MCG +-?0*'+lzstrip(num1)+'- *0*'+lzstrip(num2)+'- *0*'+lzstrip(num3)+'$" '
             {The above line can find duplicates becasue it doens't distinguish
              between entries with a leading minus sign and no leading minus sign}
     else
         qstr2:='Name regexp "'+ids+'$" or desig regexp "'+ids+'$" ';


     qstr:='select RA2000,DEC2000,RA1950,DEC1950,Name,PGC,Hubble_T,R25,BT,'+
           'Bmag,V3K from rc3 where '+qstr2+#0;

{     writeln(qstr);}

     mysql_select_db(@mysql,'sn');
     mysql_query(@mysql,@qstr[1]);

     res:=mysql_use_result(@mysql);  {returns a handle to a result}
     if res=nil then
        begin
             eWrite(Format('sn.rc3 failed; error: ''%s'''#7#13#10,[mysql_error(@mysql)]));
        end
     else
         begin
              row := mysql_fetch_row(res);  {given a result handle, return the next row}

              numr:=0;
              while row<>nil do
                 begin
                      numr:=numr+1;

                      if numr=num then
                         begin
                              gal.RA2000s:=Strpas(row^[0]);
                              gal.RA2000:=RAsplit(gal.RA2000s);
                              gal.DEC2000s:=StrPas(row^[1]);
                              gal.DEC2000:=DECSplit(gal.DEC2000s);

                              gal.RA1950s:=Strpas(row^[2]);
                              gal.RA1950:=RAsplit(gal.RA1950s);
                              gal.DEC1950s:=StrPas(row^[3]);
                              gal.DEC1950:=DECSplit(gal.DEC1950s);

                              gal.Name:=StrPas(row^[4]);
                              gal.PGC:=StrToInt(row^[5]);
                              gal.Hubble_T:=fVal(StrPas(row^[6]));
                              gal.R25:=fVal(StrPas(row^[7]));
                              BT:=fVal(StrPas(row^[8]));
                              Bmag:=fVal(StrPas(row^[9]));
                              if BT>0 then
                                 gal.Bmag:=BT
                              else
                                  gal.Bmag:=Bmag;
                              gal.V3K:=fVal(StrPas(row^[10]));
                         end;

                      row:=mysql_fetch_row(res);
                 end;  {of row<>nil}

              mysql_free_result(res);  {Free result buffer on server}
         end; {of valid result processing}

     Result:=numr;
end;  {of procedure GetRC3ByName}




function fixup(id:string):string;
var qstr:string;
begin
     if not MySQLActive then
        begin
             eWrite('No SQL connection active, can''t GetGalaxy.');
             System.Exit;
        end;
     qstr:='select PGC from fixup where ObjID='''+id+''''#0;
     mysql_select_db(@mysql,'sn');
     mysql_query(@mysql,@qstr[1]);

     res:=mysql_use_result(@mysql);  {returns a handle to a result}
     if res=nil then
        begin
             eWrite(Format('sn.fixup failed; error: ''%s'''#7#13#10,[mysql_error(@mysql)]));
        end
     else
         begin
              row := mysql_fetch_row(res);  {given a result handle, return the next row}

              fixup:='';
              if row<>nil then
                 begin
                      fixup:=Strpas(row^[0]);
                 end;  {of row<>nil}

              repeat
                    row:=mysql_fetch_row(res);
              until row=nil;

              mysql_free_result(res);  {Free result buffer on server}
         end; {of valid result processing}

end;  {of procedure fixup}


procedure ReadSQLCurrent(var Here:ObjectRec; var Current:CurrentInfo; var HA:real; var LastMod:integer);
     {Read the current position data into an object record}
var
   row          : PMYSQL_ROW;
   code         : integer;
   tmpb:integer;
begin

     if not MySQLActive then
        begin
             eWrite('No SQL connection active, can''t read teljoy.current.');
             HA:=0;
             LastMod:=0;
             System.Exit;
        end;

     mysql_select_db(@mysql,'teljoy');
     mysql_query(@mysql,'select name,ObjRA,ObjDec,ObjEpoch,RawRA,RawDec,'+
                        'RawHourAngle,Alt,Azi,LST,UTDec,posviolate,moving,'+
                        'EastOfPier,NonSidOn,DomeInUse,ShutterInUse,'+
                        'ShutterOpen,DomeTracking,Frozen,AutoRunning,'+
                        'NumRead,CurNum,RA_GuideAcc,DEC_GuideAcc,LastError,'+
                        'unix_timestamp(now())-unix_timestamp(LastMod) '+
                        'from current'#0);
     {return the table elements in that order}

     res:=mysql_use_result(@mysql);  {returns a handle to a result}
     if res=nil then
        begin
             eWrite(Format('teljoy.current failed; error: ''%s'''#7#13#10,[mysql_error(@mysql)]));
             HA:=0;
             LastMod:=0;
        end
     else
         begin
              row := mysql_fetch_row(res);  {given a result handle, return the next row}

              if row=nil then
                 begin
                      eWrite('Nil row returned');
                      HA:=0;
                      LastMod:=0;
                      System.Exit;
                 end;

              Here.ID:=StrPas(row^[0]);  {The row is an array of strings, one per value}
                                         {StrPas converts from null-terminated to a Pascal string}

              Val(row^[1],Here.RA,code);
              Here.RA:=Here.RA*15*3600;  {convert from hours to arcsec}
              if code<>0 then          {in case of a null string, assign a default value}
                 Here.RA:=0;

              Val(row^[2],Here.Dec,code);
              Here.Dec:=Here.Dec*3600;    {convert from degrees to arcsec}
              if code<>0 then
                 Here.Dec:=0;

              Val(row^[3],Here.Epoch,code);  {in years}
              if code<>0 then
                 Here.Epoch:=0;

              Val(row^[4],Here.RaC,code);
              Here.RaC:=Here.RaC*15*3600;
              if code<>0 then
                 eWrite('Error in RawRA:'+StrPas(row^[4]));

              Val(row^[5],Here.DecC,code);
              Here.DecC:=Here.DecC*3600;
              if code<>0 then
                 eWrite('Error in RawDec:'+StrPas(row^[5]));

              Val(row^[6],HA,code);    {in hours}
              if code<>0 then
                 eWrite('Error in RawHourAngle:'+StrPas(row^[6]));

              Val(row^[7],Here.Alt,code);    {in degrees}
              if code<>0 then
                 eWrite('Error in Alt:'+StrPas(row^[7]));

              Val(row^[8],Here.Azi,code);
              if code<>0 then
                 eWrite('Error in Azi:'+StrPas(row^[8]));

              Val(row^[9],Here.Time.LST,code);
              if code<>0 then
                 eWrite('Error in LST:'+StrPas(row^[9]));

              Val(row^[10],Here.Time.UTDec,code);
              if code<>0 then
                 eWrite('Error in UTDec:'+StrPas(row^[10]));

              Val(row^[11],tmpb,code);
              if (code<>0) or (tmpb>1) or (tmpb<0) then
                 eWrite('Error in posviolate:'+StrPas(row^[11]))
              else
                  Current.posviolate:=boolean(tmpb);

              Val(row^[12],tmpb,code);
              if (code<>0) or (tmpb>1) or (tmpb<0) then
                 eWrite('Error in moving:'+StrPas(row^[12]))
              else
                  Current.moving:=boolean(tmpb);

              Val(row^[13],tmpb,code);
              if (code<>0) or (tmpb>1) or (tmpb<0) then
                 eWrite('Error in EastOfPier:'+StrPas(row^[13]))
              else
                  Current.EastOfPier:=boolean(tmpb);

              Val(row^[14],tmpb,code);
              if (code<>0) or (tmpb>1) or (tmpb<0) then
                 eWrite('Error in NonSidOn:'+StrPas(row^[14]))
              else
                  Current.NonSidOn:=boolean(tmpb);

              Val(row^[15],tmpb,code);
              if (code<>0) or (tmpb>1) or (tmpb<0) then
                 eWrite('Error in DomeInUse:'+StrPas(row^[15]))
              else
                  Current.DomeInUse:=boolean(tmpb);

              Val(row^[16],tmpb,code);
              if (code<>0) or (tmpb>1) or (tmpb<0) then
                 eWrite('Error in ShutterInUse:'+StrPas(row^[16]))
              else
                  Current.ShutterInUse:=boolean(tmpb);

              Val(row^[17],tmpb,code);
              if (code<>0) or (tmpb>1) or (tmpb<0) then
                 eWrite('Error in ShutterOpen:'+StrPas(row^[17]))
              else
                  Current.ShutterOpen:=boolean(tmpb);

              Val(row^[18],tmpb,code);
              if (code<>0) or (tmpb>1) or (tmpb<0) then
                 eWrite('Error in DomeTracking:'+StrPas(row^[18]))
              else
                  Current.DomeTracking:=boolean(tmpb);

              Val(row^[19],tmpb,code);
              if (code<>0) or (tmpb>1) or (tmpb<0) then
                 eWrite('Error in Frozen:'+StrPas(row^[19]))
              else
                  Current.Frozen:=boolean(tmpb);

              Val(row^[20],tmpb,code);
              if (code<>0) or (tmpb>1) or (tmpb<0) then
                 eWrite('Error in AutoRunning:'+StrPas(row^[20]))
              else
                  Current.AutoRunning:=boolean(tmpb);

              Val(row^[21],Current.NumRead,code);
              if code<>0 then
                 eWrite('Error in NumRead:'+StrPas(row^[21]));

              Val(row^[22],Current.CurNum,code);
              if code<>0 then
                 eWrite('Error in CurNum:'+StrPas(row^[22]));

              Val(row^[23],Current.RA_GuideAcc,code);
              if code<>0 then
                 eWrite('Error in RA_GuideAcc:'+StrPas(row^[23]));

              Val(row^[24],Current.DEC_GuideAcc,code);
              if code<>0 then
                 eWrite('Error in DEC_GuideAcc:'+StrPas(row^[24]));

              Current.LastError:=StrPas(row^[25]);

              Val(row^[26],LastMod,code);
              if code<>0 then
                 eWrite('Error in LastMod:'+StrPas(row^[26]));

              repeat
                    row:=mysql_fetch_row(res);
              until row=nil;

              mysql_free_result(res);  {Free result buffer on server}
         end; {of valid result processing}
end;  {Of procedure ReadSQLCurrent}



procedure UpdateSQLCurrent(var Here:ObjectRec; var Current:CurrentInfo);
var qstr1,qstr2,qstr3,qstr4:string;
    tmpd:real;
    dummy:array[0..1024] of char;
    querystr:PChar;
    err:string;

begin
     if not MySQLActive then
        begin
             System.Exit;
        end;

     mysql_select_db(@mysql,'teljoy');

     if not Current.posviolate then  {if telescope position is valid}
        qstr1:=Format('update current set name=''%s'', ObjRA=''%g'', ObjDec=''%g'', ObjEpoch=''%g'', '#0,
                    [ Here.ID,
                      Here.RA/(15*3600),
                      Here.Dec/3600,
                      Here.Epoch] )
     else
         qstr1:=Format('update current set name=''%s'', ObjRA=NULL, ObjDec=NULL, ObjEpoch=NULL, '#0,
                     [ Here.ID] );

     tmpd:= Here.RaC/54000-Here.Time.LST;
     if tmpd < -12 then
        tmpd:=tmpd+24;
     if tmpd > 12 then
        tmpd:=tmpd-24;

     qstr2:=Format('RawRA=''%g'', RawDec=''%g'', RawHourAngle=''%g'', Alt=''%g'', Azi=''%g'', ',
         [ Here.RaC/(15*3600),
           Here.DecC/3600,
           tmpd,
           Here.Alt,
           Here.Azi]);

     qstr2:=qstr2+Format('LST=''%g'', UTDec=''%g'', posviolate=''%d'', moving=''%d'', EastOfPier=''%d'', NonSidOn=''%d'', '#0,
         [ Here.Time.LST,
           Here.Time.UTdec,
           Ord(Current.posviolate),
           Ord(Current.moving),
           Ord(Current.EastOfPier),
           Ord(Current.NonSidOn) ]);

     qstr3:=Format('DomeInUse=''%d'', ShutterInUse=''%d'', ShutterOpen=''%d'', DomeTracking=''%d'', Frozen=''%d'', ',
         [ Ord(Current.DomeInUse),
           Ord(Current.ShutterInUse),
           Ord(Current.ShutterOpen),
           Ord(Current.DomeTracking),
           Ord(Current.Frozen) ]);

     qstr3:=qstr3+Format('AutoRunning=''%d'', NumRead=''%d'', CurNum=''%d'', '#0,
         [ Ord(Current.AutoRunning),
           Current.NumRead,
           Current.CurNum ]);

     qstr4:=Format('RA_GuideAcc=''%g'', DEC_GuideAcc=''%g'', LastError=%s '#0,
         [ Current.RA_GuideAcc,
           Current.DEC_GuideAcc,
           QuotedStr(Current.LastError) ]);

     querystr:=dummy;
     querystr:=StrCopy(querystr,@qstr1[1]);
     querystr:=StrCat(querystr,@qstr2[1]);
     querystr:=StrCat(querystr,@qstr3[1]);
     querystr:=StrCat(querystr,@qstr4[1]);

     mysql_query(@mysql,@querystr[0]);
     err:=StrPas(mysql_error(@mysql));
     if err<>'' then
        begin
             eWrite(err);
             writeln(querystr);
        end;

end;


procedure WriteLog(cur:snresult);
var qstr1,qstr2,qstr3,qstr4,qstr5,qstr6,qstr7:string;
    uth,utm,uts:integer;
    tmp:double;
    dummy:array[0..1024] of char;
    querystr:PChar;
    err:string;

begin
     if not MySQLActive then
        begin
             eWrite('No SQL connection active, can''t update snlog.');
             System.Exit;
        end;
     mysql_select_db(@mysql,'sn');

     qstr1:='insert into snlog ( seq,name,exptime,filtnum,filtname,ObjID,ObjRA,ObjDec,'+
            'Epoch,UT,JulDay,Alt,Azi,RAtrack,DECtrack,XYPos_X,XYPos_Y,'+
            'ObsType,Filename,Comment,X_Disp,Y_Disp,Sky,Sky_Sigma,'+
            'X_Sigma,Y_Sigma,NumCandidates,Candidates )  '#10#0;

     qstr2:=Format(' VALUES(''%d'', %s, ''%6g'', ''%d'', ''%s'', ''%s'', '+
                   '''%15g'', ''%15g'', ''%6g'', '#10#0,
                    [ cur.seq,
                      QuotedStr(cur.name),
                      cur.exptime,
                      cur.filtnum,
                      cur.filtname,
                      cur.ObjID,
                      cur.ObjRA,
                      cur.ObjDec,
                      Cur.Epoch] );

     uth:=trunc(cur.UT);
     tmp:=(cur.UT-uth)*60;
     utm:=trunc(tmp);
     uts:=trunc((tmp-utm)*60);

     qstr3:=Format('''%d-%d-%d %d:%d:%d'', ''%15g'', ''%6g'', ''%6g'', '+
                   '''%10g'', ''%10g'', '#10#0,
                   [ cur.UT_Date_year,
                     cur.UT_Date_month,
                     cur.UT_Date_day,
                     uth,utm,uts,
                     cur.JulDay,
                     cur.Alt,
                     cur.Azi,
                     cur.RAtrack,
                     cur.DECtrack] );

     qstr4:=Format('''%d'', ''%d'', ''%s'', ''%s'', '#10#0,
                   [ cur.XYpos_X,
                     cur.XYpos_Y,
                     cur.ObsType,
                     cur.Filename] );

     qstr5:=QuotedStr(cur.comment)+', '#10#0;

     qstr6:=Format('''%7g'', ''%7g'', ''%8g'', ''%7g'', ''%5g'', ''%5g'', '+
                   '''%d'', '#10#0,
                   [ cur.X_Disp,
                     cur.Y_Disp,
                     cur.Sky,
                     cur.Sky_Sigma,
                     cur.X_Sigma,
                     cur.Y_Sigma,
                     cur.NumCandidates] );

     if cur.NumCandidates > 0 then
        begin
             qstr7:=Format('''%7g %7g %7g ',
                           [ cur.C1X, cur.C1Y, cur.C1Q]);
             qstr7:=qstr7+Format('%7g %7g %7g ',
                           [ cur.C2X, cur.C2Y, cur.C2Q]);
             qstr7:=qstr7+Format('%7g %7g %7g ',
                           [ cur.C3X, cur.C3Y, cur.C3Q]);
             qstr7:=qstr7+Format('%7g %7g %7g '' ) '#10#0,
                           [ cur.C4X, cur.C4Y, cur.C4Q]);
        end
     else
         qstr7:='NULL ) '#10#0;

     querystr:=dummy;
     querystr:=StrCopy(querystr,@qstr1[1]);
     querystr:=StrCat(querystr,@qstr2[1]);
     querystr:=StrCat(querystr,@qstr3[1]);
     querystr:=StrCat(querystr,@qstr4[1]);
     querystr:=StrCat(querystr,@qstr5[1]);
     querystr:=StrCat(querystr,@qstr6[1]);
     querystr:=StrCat(querystr,@qstr7[1]);

{     writeln(querystr);
}
     mysql_query(@mysql,@querystr[0]);
     err:=StrPas(mysql_error(@mysql));
     if err<>'' then
        eWrite(err);


end;

function ExistsSQLBox:boolean;
var qstr:string;
begin
     Result:=false;
     if not MySQLActive then
        begin
             eWrite('No SQL connection active, can''t test teljoy.ccdbox.');
             System.Exit;
        end;

     qstr:='select ObjID from ccdbox'#0;
     mysql_select_db(@mysql,'teljoy');
     mysql_query(@mysql,@qstr[1]);

     res:=mysql_use_result(@mysql);  {returns a handle to a result}
     if res=nil then
        begin
             eWrite(Format('teljoy.ccdbox failed; error: ''%s'''#7#13#10,[mysql_error(@mysql)]));
        end
     else
         begin
              row := mysql_fetch_row(res);  {given a result handle, return the next row}

              if row<>nil then
                 begin
                      Result:=true;

                      repeat
                            row:=mysql_fetch_row(res);
                      until row=nil;
                 end;

              mysql_free_result(res);  {Free result buffer on server}
         end; {of valid result processing}
end;  {Of function ExistsSQLBox}


procedure ClearSQLBox;
var qstr1,err:string;
begin
     if not MySQLActive then
        begin
             eWrite('No SQL connection active, can''t delete from teljoy.ccdbox.');
             System.Exit;
        end;
     mysql_select_db(@mysql,'teljoy');

     qstr1:='delete from ccdbox '#10#0;
     mysql_query(@mysql,@qstr1[1]);
     err:=StrPas(mysql_error(@mysql));
     if err<>'' then
        eWrite(err);

end;


procedure WriteSQLBox(cur:snresult);
var qstr1,qstr2,qstr3,qstr4,qstr5:string;
    uth,utm,uts:integer;
    tmp:double;
    dummy:array[0..1024] of char;
    querystr:PChar;
    err:string;

begin
     if not MySQLActive then
        begin
             eWrite('No SQL connection active, can''t write teljoy.ccdbox.');
             System.Exit;
        end;
     mysql_select_db(@mysql,'teljoy');

     qstr1:='insert into ccdbox ( seq,name,exptime,filtnum,filtname,ObjID,ObjRA,ObjDec,'+
            'Epoch,UT,JulDay,Alt,Azi,RAtrack,DECtrack,XYPos_X,XYPos_Y,'+
            'ObsType,Comment )  '#10#0;

     qstr2:=Format(' VALUES(''%d'', %s, ''%6g'', ''%d'', ''%s'', ''%s'', '+
                   '''%s'', ''%s'', ''%6g'', '#10#0,
                    [ cur.seq,
                      QuotedStr(cur.name),
                      cur.exptime,
                      cur.filtnum,
                      cur.filtname,
                      cur.ObjID,
                      cur.ObjRAs,
                      cur.ObjDecs,
                      Cur.Epoch] );

     uth:=trunc(cur.UT);
     tmp:=(cur.UT-uth)*60;
     utm:=trunc(tmp);
     uts:=trunc((tmp-utm)*60);

     qstr3:=Format('''%d-%d-%d %d:%d:%d'', ''%15g'', ''%6g'', ''%6g'', '+
                   '''%10g'', ''%10g'', '#10#0,
                   [ cur.UT_Date_year,
                     cur.UT_Date_month,
                     cur.UT_Date_day,
                     uth,utm,uts,
                     cur.JulDay,
                     cur.Alt,
                     cur.Azi,
                     cur.RAtrack,
                     cur.DECtrack] );

     qstr4:=Format('''%d'', ''%d'', ''%s'', '#10#0,
                   [ cur.XYpos_X,
                     cur.XYpos_Y,
                     cur.ObsType] );

     qstr5:=QuotedStr(cur.comment)+' ) '#10#0;

     querystr:=dummy;
     querystr:=StrCopy(querystr,@qstr1[1]);
     querystr:=StrCat(querystr,@qstr2[1]);
     querystr:=StrCat(querystr,@qstr3[1]);
     querystr:=StrCat(querystr,@qstr4[1]);
     querystr:=StrCat(querystr,@qstr5[1]);

{     writeln(querystr);
}
     mysql_query(@mysql,@querystr[0]);
     err:=StrPas(mysql_error(@mysql));
     if err<>'' then
        begin
             ewrite(StrPas(querystr));
             eWrite(err);
        end;


end;


function ExistsTJBox:boolean;
var qstr:string;
begin
     Result:=false;
     if not MySQLActive then
        begin
             eWrite('No SQL connection active, can''t test teljoy.tjbox.');
             System.Exit;
        end;

     qstr:='select ObjID from tjbox'#0;
     mysql_select_db(@mysql,'teljoy');
     mysql_query(@mysql,@qstr[1]);

     res:=mysql_use_result(@mysql);  {returns a handle to a result}
     if res=nil then
        begin
             eWrite(Format('teljoy.tjbox failed; error: ''%s'''#7#13#10,[mysql_error(@mysql)]));
        end
     else
         begin
              row := mysql_fetch_row(res);  {given a result handle, return the next row}

              if row<>nil then
                 begin
                      Result:=true;

                      repeat
                            row:=mysql_fetch_row(res);
                      until row=nil;
                 end;

              mysql_free_result(res);  {Free result buffer on server}
         end; {of valid result processing}
end;  {Of function ExistsSQLBox}


procedure ClearTJBox;
var qstr1,err:string;
begin
     if not MySQLActive then
        begin
             eWrite('No SQL connection active, can''t delete from teljoy.tjbox.');
             System.Exit;
        end;
     mysql_select_db(@mysql,'teljoy');

     qstr1:='delete from tjbox '#10#0;
     mysql_query(@mysql,@qstr1[1]);
     err:=StrPas(mysql_error(@mysql));
     if err<>'' then
        eWrite(err);

end;


(*
function ReadTJbox(var Pos:ObjectRec; var other:TJboxrec; LastMod:integer):TJaction;  {Read the Teljoy box data into an object record}
type validt = record
                    ObjID,ObjRA,ObjDec,ObjEpoch:boolean;
                    RAtrack,DECtrack:boolean;
                    Alt,Azi:boolean;
                    OffsetRA,OffsetDec:boolean;
                    DomeAzi:boolean;
              end;

var
   row          : PMYSQL_ROW;
   code         : integer;
   tmpb:integer;
   valid:validt;
   action:TJaction;
   strn:string;
begin
     valid.ObjID:=false;
     valid.ObjRA:=false;
     valid.ObjDec:=false;
     valid.ObjEpoch:=false;
     valid.RAtrack:=false;
     valid.DECtrack:=false;
     valid.Alt:=false;
     valid.Azi:=false;
     valid.OffsetRA:=false;
     valid.OffsetDec:=false;
     valid.DomeAzi:=false;
     action:=none;

     if not MySQLActive then
        begin
             eWrite('No SQL connection active, can''t read teljoy.tjbox.');
             LastMod:=-1;
             System.Exit;
        end;

     mysql_select_db(@mysql,'teljoy');
     mysql_query(@mysql,'select ObjID,ObjRA,ObjDec,ObjEpoch,RAtrack,DECtrack,'+
                        'Alt,Azi,OffsetRA,OffsetDec,DomeAzi, '+
                        'unix_timestamp(now())-unix_timestamp(lastmod) '+
                        'from tjbox'#0);
     {return the table elements in that order}

     res:=mysql_use_result(@mysql);  {returns a handle to a result}
     if res=nil then
        begin
             eWrite(Format('teljoy.tjbox failed; error: ''%s'''#7#13#10,[mysql_error(@mysql)]));
             LastMod:=-1;
        end
     else
         begin
              row := mysql_fetch_row(res);  {given a result handle, return the next row}

              if row=nil then
                 begin
                      eWrite('Nil row returned');
                      LastMod:=-1;
                      System.Exit;
                 end;

              Pos.ID:=StrPas(row^[0]);  {The row is an array of strings, one per value}
              if Pos.ID<>'' then         {StrPas converts from null-terminated to a Pascal string}
                 valid.ObjID:=true;


              strn:=StrPas(row^[1]);
              ConvStr(strn,Pos.RA,dms,code);  {Convert string to RA in sec of time}
              Pos.RA:=Pos.RA*15;  {convert from sec of time to arcsec}
              if code=0 then          {in case of a null string, assign a default value}
                 valid.ObjRA:=true
              else
                  Pos.RA:=0;

              strn:=StrPas(row^[2]);
              ConvStr(strn,Pos.Dec,dms,code); {Convert string to Dec in arcsec}
              if code=0 then
                 valid.ObjDec:=true
              else
                  Pos.Dec:=0;

              Val(row^[3],Pos.Epoch,code);  {in years}
              if code=0 then
                 valid.ObjEpoch:=true
              else
                  Pos.Epoch:=0;

              Val(row^[4],Pos.TraRA,code);
              Pos.TraRA:=Pos.TraRA*3600/15;  {Convert from sec of time per hour to arcsec per second}
              if (code=0) and (abs(Pos.TraRA)<=1) then
                 valid.RAtrack:=true
              else
                  Pos.TraRA:=0;

              Val(row^[5],Pos.TraDec,code);
              Pos.TraDec:=Pos.TraDec*3600;  {Convert from arcsec per hour to arcsec per second}
              if (code=0) and (abs(Pos.TraDec)<=1) then
                 valid.DECtrack:=true
              else
                  Pos.TraDec:=0;

              if row^[6]<>nil then
                 begin
                      Val(row^[6],Pos.Alt,code);    {in degrees}
                      if code=0 then
                         valid.Alt:=true
                      else
                          eWrite('Error in Alt:'+StrPas(row^[6]));
                 end;

              if row^[7]<>nil then
                 begin
                      Val(row^[7],Pos.Azi,code);
                      if code=0 then
                         valid.Azi:=true
                      else
                          eWrite('Error in Azi:'+StrPas(row^[7]));
                 end;

              if row^[8]<>nil then
                 begin
                      Val(row^[8],other.OffsetRA,code);
                      if code=0 then
                         valid.OffsetRA:=true
                      else
                          eWrite('Error in OffsetRA:'+StrPas(row^[8]));
                 end;

              if row^[9]<>nil then
                 begin
                      Val(row^[9],other.OffsetDec,code);
                      if code=0 then
                         valid.OffsetDec:=true
                      else
                          eWrite('Error in OffsetDec:'+StrPas(row^[9]));
                 end;

              if row^[10]<>nil then
                 begin
                      Val(row^[10],other.DomeAzi,code);
                      if code=0 then
                         valid.DomeAzi:=true
                      else
                          eWrite('Error in DomeAzi:'+StrPas(row^[10]));
                 end;


              Val(row^[11],LastMod,code);
              if code<>0 then
                 LastMod:=-1;

              repeat
                    row:=mysql_fetch_row(res);
              until row=nil;

              mysql_free_result(res);  {Free result buffer on server}


              with valid do
                   begin
                        if DomeAzi then
                           if not (ObjID or ObjRA or ObjDec or
                                  ObjEpoch or RAtrack or DECtrack or Alt or
                                  Azi or OffsetRA or OffsetDec) then
                               action:=dome
                           else
                               action:=error;
                        if (action=none) and (ObjRA or ObjDec or ObjEpoch) then
                           if (ObjRA and ObjDec and ObjEpoch) and
                              not (Alt or Azi or OffsetRA or OffsetDec) then
                              action:=jumpRD
                           else
                               action:=error;
                        if (action=none) and (Alt or Azi) then
                           if (Alt and Azi) and
                              not (ObjID or OffsetRA or OffsetDec or
                                   RAtrack or DECtrack) then
                              action:=jumpAA
                           else
                               action:=error;
                        if (action=none) and (OffsetRA or OffsetDec) then
                           if (OffsetRA and OffsetDec) and
                              not (ObjID or RAtrack or DECtrack) then
                              action:=offset
                           else
                               action:=error;
                        if (action=none) and ObjID then
                           action:=jumpID;
                        if (action=none) and (RAtrack or DECtrack) then
                           if (RAtrack and DECtrack) then
                              action:=nonsid
                           else
                               action:=error;
                   end;  {Of with valid}
         end; {of valid result processing}
     Result:=action;
end;  {Of function ReadTJbox}
*)

function ReadTJbox(var Pos:ObjectRec; var other:TJboxrec; LastMod:integer):TJaction;  {Read the Teljoy box data into an object record}
type validt = record
                    ObjID,ObjRA,ObjDec,ObjEpoch:boolean;
                    RAtrack,DECtrack:boolean;
                    Alt,Azi:boolean;
                    OffsetRA,OffsetDec:boolean;
                    DomeAzi,shutter,freeze:boolean;
              end;

var
   row          : PMYSQL_ROW;
   code         : integer;
   tmpb:integer;
   valid:validt;
   action:TJaction;
   astr,strn:string;
   verr:boolean;
begin
     valid.ObjID:=false;
     valid.ObjRA:=false;
     valid.ObjDec:=false;
     valid.ObjEpoch:=false;
     valid.RAtrack:=false;
     valid.DECtrack:=false;
     valid.Alt:=false;
     valid.Azi:=false;
     valid.OffsetRA:=false;
     valid.OffsetDec:=false;
     valid.DomeAzi:=false;
     valid.shutter:=false;
     valid.freeze:=false;
     action:=none;

     if not MySQLActive then
        begin
             eWrite('No SQL connection active, can''t read teljoy.tjbox.');
             LastMod:=-1;
             System.Exit;
        end;

     mysql_select_db(@mysql,'teljoy');
     mysql_query(@mysql,'select action,ObjID,ObjRA,ObjDec,ObjEpoch,RAtrack,DECtrack,'+
                        'Alt,Azi,OffsetRA,OffsetDec,DomeAzi,shutter,freeze, '+
                        'unix_timestamp(now())-unix_timestamp(lastmod) '+
                        'from tjbox'#0);
     {return the table elements in that order}

     res:=mysql_use_result(@mysql);  {returns a handle to a result}
     if res=nil then
        begin
             eWrite(Format('teljoy.tjbox failed; error: ''%s'''#7#13#10,[mysql_error(@mysql)]));
             LastMod:=-1;
        end
     else
         begin
              row := mysql_fetch_row(res);  {given a result handle, return the next row}

              if row=nil then
                 begin
                      eWrite('Nil row returned');
                      LastMod:=-1;
                      System.Exit;
                 end;

              astr:=Strpas(row^[0]);

              Pos.ID:=StrPas(row^[1]);  {The row is an array of strings, one per value}
              if Pos.ID<>'' then         {StrPas converts from null-terminated to a Pascal string}
                 valid.ObjID:=true;


              strn:=StrPas(row^[2]);
              ConvStr(strn,Pos.RA,dms,code);  {Convert string to RA in sec of time}
              Pos.RA:=Pos.RA*15;  {convert from sec of time to arcsec}
              if code=0 then          {in case of a null string, assign a default value}
                 valid.ObjRA:=true
              else
                  Pos.RA:=0;

              strn:=StrPas(row^[3]);
              ConvStr(strn,Pos.Dec,dms,code); {Convert string to Dec in arcsec}
              if code=0 then
                 valid.ObjDec:=true
              else
                  Pos.Dec:=0;

              Val(row^[4],Pos.Epoch,code);  {in years}
              if code=0 then
                 valid.ObjEpoch:=true
              else
                  Pos.Epoch:=0;

              Val(row^[5],Pos.TraRA,code);
              Pos.TraRA:=Pos.TraRA*3600/15;  {Convert from sec of time per hour to arcsec per second}
              if (code=0) and (abs(Pos.TraRA)<=1) then
                 valid.RAtrack:=true
              else
                  Pos.TraRA:=0;

              Val(row^[6],Pos.TraDec,code);
              Pos.TraDec:=Pos.TraDec*3600;  {Convert from arcsec per hour to arcsec per second}
              if (code=0) and (abs(Pos.TraDec)<=1) then
                 valid.DECtrack:=true
              else
                  Pos.TraDec:=0;

              if row^[7]<>nil then
                 begin
                      Val(row^[7],Pos.Alt,code);    {in degrees}
                      if code=0 then
                         valid.Alt:=true
                      else
                          eWrite('Error in Alt:'+StrPas(row^[7]));
                 end;

              if row^[8]<>nil then
                 begin
                      Val(row^[8],Pos.Azi,code);
                      if code=0 then
                         valid.Azi:=true
                      else
                          eWrite('Error in Azi:'+StrPas(row^[8]));
                 end;

              if row^[9]<>nil then
                 begin
                      Val(row^[9],other.OffsetRA,code);
                      if code=0 then
                         valid.OffsetRA:=true
                      else
                          eWrite('Error in OffsetRA:'+StrPas(row^[9]));
                 end;

              if row^[10]<>nil then
                 begin
                      Val(row^[10],other.OffsetDec,code);
                      if code=0 then
                         valid.OffsetDec:=true
                      else
                          eWrite('Error in OffsetDec:'+StrPas(row^[10]));
                 end;

              if row^[11]<>nil then
                 begin
                      Val(row^[11],other.DomeAzi,code);
                      if code=0 then
                         valid.DomeAzi:=true
                      else
                          eWrite('Error in DomeAzi:'+StrPas(row^[11]));
                 end;

              if row^[12]<>nil then
                 begin
                      Val(row^[12],tmpb,code);
                      if code=0 then
                         valid.shutter:=true
                      else
                          eWrite('Error in shutter:'+StrPas(row^[12]));
                 end;
              if tmpb=0 then
                 other.shutter:=false
              else
                  other.shutter:=true;

              if row^[13]<>nil then
                 begin
                      Val(row^[13],tmpb,code);
                      if code=0 then
                         valid.freeze:=true
                      else
                          eWrite('Error in freeze:'+StrPas(row^[13]));
                 end;
              if tmpb=0 then
                 other.freeze:=false
              else
                  other.freeze:=true;

              Val(row^[14],LastMod,code);
              if code<>0 then
                 LastMod:=-1;

              repeat
                    row:=mysql_fetch_row(res);
              until row=nil;

              mysql_free_result(res);  {Free result buffer on server}

              if astr='none' then
                 action:=none
              else if astr='error' then
                 action:=error
              else if astr='jumpID' then
                 action:=jumpID
              else if astr='jumpRD' then
                 action:=jumpRD
              else if astr='jumpAA' then
                 action:=jumpAA
              else if astr='nonsid' then
                 action:=nonsid
              else if astr='offset' then
                 action:=offset
              else if astr='dome' then
                 action:=dome
              else if astr='shutter' then
                 action:=shutter
              else if (astr='freeze') or (astr='freez') then
                 action:=freez
              else
                  begin
                       action:=error;
                       eWrite('Invalid remote action: '+astr);
                  end;

              verr:=false;
              case action of
                   jumpID:
                          if not valid.ObjID then
                             verr:=true;
                   jumpRD:
                          if not (valid.ObjRA and valid.ObjDec and valid.ObjEpoch) then
                             verr:=true;
                   jumpAA:
                          if not (valid.Alt and valid.Azi) then
                             verr:=true;
                   nonsid:
                          if not (valid.RAtrack and valid.DECtrack) then
                             verr:=true;
                   offset:
                          if not (valid.OffsetRA and valid.OffsetDec) then
                             verr:=true;
                   dome:
                          if not valid.DomeAzi then
                             verr:=true;
                   shutter:
                          if not valid.shutter then
                             verr:=true;
                   freez:
                          if not valid.freeze then
                             verr:=true;
              end;  {of case}
              if verr then
                 action:=error;

         end; {of valid result processing}
     Result:=action;
end;  {Of function ReadTJbox}



function GetObject(n:string; var Pos:ObjectRec):boolean;
var
   row          : PMYSQL_ROW;
   code         : integer;
   tmpb:integer;
   qstr:string;
   strn:string;
begin
     if not MySQLActive then
        begin
             eWrite('No SQL connection active, can''t get teljoy.objects.');
             Result:=false;
             System.Exit;
        end;

     mysql_select_db(@mysql,'teljoy');
     qstr:='select ObjID,ObjRA,ObjDec,ObjEpoch,filtname,exptime,'+
           'XYpos_X,XYpos_Y,type,comment from objects where '+
           'ObjID="'+n+'" '#0;
     mysql_query(@mysql,@qstr[1]);
     {return the table elements in that order}

     res:=mysql_use_result(@mysql);  {returns a handle to a result}
     if res=nil then
        begin
             eWrite(Format('teljoy.objects failed; error: ''%s'''#7#13#10,[mysql_error(@mysql)]));
             Result:=false;
             System.Exit;
        end;

      row := mysql_fetch_row(res);  {given a result handle, return the next row}
      if row=nil then
         begin
              eWrite('Nil row returned');
              Result:=false;
              System.Exit;
         end;

      Pos.ID:=StrPas(row^[0]);  {The row is an array of strings, one per value}

      strn:=StrPas(row^[1]);
      ConvStr(strn,Pos.RA,dms,code);  {Convert string to RA in sec of time}
      Pos.RA:=Pos.RA*15;  {convert from sec of time to arcsec}

      strn:=StrPas(row^[2]);
      ConvStr(strn,Pos.Dec,dms,code); {Convert string to Dec in arcsec}

      Val(row^[3],Pos.Epoch,code);  {in years}

      Pos.filtname:=StrPas(row^[4]);
      Pos.filtnum:=GetFiltNum(Pos.filtname);

      Val(row^[5],Pos.exptime,code);

      Val(row^[6],Pos.Xoff,code);

      Val(row^[7],Pos.Yoff,code);

      Pos.ImageType:=StrPas(row^[8]);

      Pos.Comment:=StrPas(row^[9]);

      Result:=true;

      repeat
            row:=mysql_fetch_row(res);
      until row=nil;

      mysql_free_result(res);  {Free result buffer on server}
end;


procedure InitSQL;
begin
     MySQLActive := false;

     if mysql_connect(@mysql,'192.168.25.72','honcho','') = nil then
        begin
             eWrite(Format('connect to server failed'#7#13#10'error: ''%s''',[mysql_error(@mysql)]));
             if mysql_errno(@mysql) = CR_CONNECTION_ERROR then
                begin
                     eWrite(Format('Check that mysqld is running and that the socket: ''%s'' exists!'#13#10,[mysql_unix_port]));
                end
             else
                 if (mysql_errno(@mysql) = CR_CONN_HOST_ERROR) or
                    (mysql_errno(@mysql) = CR_UNKNOWN_HOST) then
                    begin
                         eWrite(Format('Check that mysqld is running on lear and that the port is %d.'#13#10'You can check this by doing ''telnet lear %d'''#13#10,
                            [mysql_port, mysql_port]));
                    end;
             delay(1000);
        end
     else
         begin
              MySQLActive:=true;
              sWrite('Connected to SQL Server.');
              delay(250);
         end;
end;  {of procedure InitSQL}


procedure SQLCleanup;
begin
     ExitProc:=SQLExitSave;
     if MySQLActive then
        mysql_close(@mysql);
end;


begin {unit init}

      sWrite('SQL init begins.');
      SQLExitSave:=ExitProc;
      ExitProc:=@SQLCleanup;
      InitSQL;
      sWrite('SQL init finished.');
end.
