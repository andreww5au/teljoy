{$N+}
{$E+}

unit readin;

interface

uses Use32;

const MaxReadStr=41;
      MaxMsgStr=80;

type dtype=(dms,num);
     readstr=string[MaxReadStr];
     msgstr=string[MaxMsgStr];

var msg:msgstr;

procedure rddat(dattype:dtype;var val:double;defval:double;var msg:msgstr;xpos,ypos:integer;var abort:boolean);

procedure ConvStr(st:readstr;var v:double;dt:dtype;var erp:integer);

implementation

uses Crt;

procedure getstr(var st,dst:readstr; xp,yp:integer;var abort:boolean);
var x,y:integer;
    ch:char;
    k:char;
    done:boolean;
begin
     st:=' ';
     y:=yp;
     x:=xp+1;
     done:=false;
     abort:=false;
     repeat
           GotoXY(xp,yp);
           write(st,'           ');
           GotoXY(x,y);

           repeat
                 delay(50);
           until keypressed;
           k:=ReadKey;
           case ord(k) of
                0:begin
                       k:=ReadKey;
                       case ord(k) of
                            75:if x>xp then    {left arrow}
                                  x:=x-1;
                            77:if x<(xp+length(st)-1) then   {right arrow}
                                  x:=x+1;
                            83:if x<(xp+length(st)-1) then
                                  begin                    {Delete}
                                     st:=Copy(st,1,x-xp)+Copy(st,x-xp+2,255);
                                     x:=x-0;
                                  end;
                            72:begin                    {Up arrow}
                                    st:=dst;
                                    x:=xp+length(st);
                               end;
                            71:begin
                                    st:=' ';
                                    x:=xp+1;
                               end;

                            end;  {of ext key case}
                  end; {of ext begin}
                27:begin       {Escape}
                        done:=true;
                        abort:=true;
                   end;
                13:done:=true;   {Enter}
                8:if x>xp then
                     begin                    {Backspace}
                           st:=Copy(st,1,x-xp-1)+Copy(st,x-xp+1,255);
                           x:=x-1;
                     end;
           else
                if ( length(st) < MaxReadStr-1 ) then
                   begin
                        st:=Copy(st,1,x-xp)+k+Copy(st,x-xp+1,255);
                        x:=x+1;
                   end;
           end;
     until done;
end;


procedure ConvStr(st:readstr;var v:double;dt:dtype;var erp:integer);
var p:integer;
    ds,ms,ss:string[10];
    dv,mv,sv:double;
    fin:boolean;
    erpd,erpm,erps:integer;

    function IsNum(ch:char):boolean;
    begin
         IsNum:=((ch='.') or (ch='-') or ((ch>='0') and (ch<='9')));
    end;

    function GrabDigits(var fin:boolean):readstr;
    var gd:string[30];
    begin
         fin:=true;
         gd:='';
         GrabDigits:='';
         while not IsNum(st[p]) do
               begin
                    p:=p+1;
                    if p>length(st) then
                       Exit;
               end;
         repeat
               gd:=gd+st[p];
               p:=p+1;
         until (p>length(st)) or (not IsNum(st[p]));
         if p<length(st) then
            fin:=false;
         GrabDigits:=gd;
    end;


begin
     erp:=0;
     case dt of
          num:begin
                   p:=1;
                   Val(GrabDigits(fin),v,erp);
              end;
          dms:begin
                   p:=1;
                   ds:='';
                   ms:='';
                   ss:='';
                   ds:=GrabDigits(fin);
                   if not fin then
                      ms:=GrabDigits(fin);
                   if not fin then
                      ss:=GrabDigits(fin);

                   dv:=0;  erpd:=999;
                   mv:=0;  erpm:=999;
                   sv:=0;  erps:=0;
                   Val(ds,dv,erpd);
                   if ms<>'' then
                      Val(ms,mv,erpm);
                   if ss<>'' then
                      Val(ss,sv,erps);
                   if (ds[1]='-') or (ms[1]='-') or (ss[1]='-') then
                      v:=dv*3600-abs(mv)*60-abs(sv)
                   else
                       v:=dv*3600+mv*60+sv;
                   erp:=erpd+erpm+erps;
              end;
     end;  {of case on dattype}
end;


procedure rddat(dattype:dtype;var val:double;defval:double;var msg:msgstr;xpos,ypos:integer;var abort:boolean);
var s,defst,ds,ms,ss:readstr;
    ab:boolean;
    err:integer;
    d,m,sec:double;
begin
     GotoXY(1,16);
     Write('[Esc]=Abort [Up]=load default [Home]=clear field [Left],[Right]=move cursor');
     GotoXY(xpos,ypos);
     case dattype of
          num: Str(defval:0:1,defst);
          dms:begin
                   d:=Trunc(defval/3600);
                   Str(d:0:0,ds);
                   if (defval<0) and (d=0) then
                      ds:='-'+ds;
                   m:=Trunc((defval-d*3600)/60);
                   Str(Abs(m):0:0,ms);
                   sec:=defval-d*3600-m*60;
                   Str(Abs(sec):0:1,ss);
                   defst:=ds+' '+ms+' '+ss;
              end;
          end;  {of case on dattype}

     msg:=msg+'('+defst+'):';
     write(msg);

     repeat
           getstr(s,defst,xpos+length(msg),ypos,ab);
           abort:=ab;
           if s<>' ' then
              ConvStr(s,val,dattype,err)
           else
               ConvStr(defst,val,dattype,err);
     until (err=0) or abort;
     GotoXY(1,16);
     Write('                                                                           ');

end;

end.  {of unit}
