{$N+$E+}
unit Globals;
interface

uses Use32;

const
      Inif='teljoy.ini';
{$IFDEF NZ}
      dObsLat = -43.9866666667;               {Lat: -43 59.2}
      dObsLong = -170.465;                     {Long: -170 27.9}
      PC23 = 800;         {PC23 Base address = $320 hex}
{$ELSE}
      dObsLat = -32.008083333;               {Lat: -32 00 29.1}
      dObsLong= -116.13501944;               {Long: -116 08 06.07}
      PC23 = 768;         {PC23 Base address = $300 hex}
{$ENDIF}
      dfTemp = 0;                               {default Temp in deg C}
      dfPress = 1015.92;                         {default atm. press. in mb}


type
     string10 = string[10];
     string40 = string[40];
     string80 = string[80];
     TimeRec = record
                 lthr,ltm,lts,lthn:integer; {Local time hours, minutes, seconds,
                                             hundreths}
                 dy,mnth,yr:integer;        {Date day, month, year}
                 Ltdec:double;              {Local time in decimal form}
                 UTdec:double;              {Universal time decimal form}
                 JD:double;                 {Julian date based upon universal
                                             time}
                 LST:double;                {Local sidereal time}
                 end;

      ObjectRec = record
                    RaH,RaM,RaS:double;     {Human readable form of Ra}
                    Ra:double;              {mean Ra in arcesc}
                    DecD,DecM,DecS:double;  {Human readable form of Dec}
                    Dec:double;             {mean Dec in arcsec}
                    RaC:double;             {fully Corrected Ra}
                    DecC:double;            {fully Corrected Dec}
                    RaA,DecA:double;        {App. Pos. (not inc. refrac)}
                    Epoch:double;           {Epoch for apparent Ra & Dec}
                    Alt,Azi:double;         {Apparent Altitude and Azimuth}
                    Priority:integer;       {Scheduler priority}
                    NameDesc:string[80];    {Object description}
                    ExpTime:double;         {Exposure length in seconds}
                    FiltNum:byte;
                    FiltName:string[8];       {Filter name}
                    Output:string;          {Output file name including
                                             full path name}
                    TraRa:double;           {Ra tracking rate}
                    TraDec:double;          {Dec tracking rate}
                    Xoff:integer;           {X offset for offset guider}
                    Yoff:integer;           {Y offset for offset guider}
                    Comp:boolean;           {Use computer date & time}
                    Imagetype:string[10];       {Type of image}
                    Time:TimeRec;           {Time information}
                    ID:string[7];           {Object ID in catalog}
                    Comment:string[128];    {Any other info}
                    end;


      snresult= record
                     seq:integer;
                     name:string;
                     exptime:real;
                     filtNum:byte;
                     filtName:string[8];
                     ObjID:string[8];
                     ObjRA:double;
                     ObjRAs:string[12];
                     ObjDec:double;
                     ObjDecs:string[12];
                     Epoch:real;
                     UT:double;
                     UT_Date_day,UT_Date_month,UT_Date_year:integer;
                     JulDay:double;
                     Alt:real;
                     Azi:real;
                     RAtrack:real;
                     DECtrack:real;
                     XYpos_X,XYpos_Y:integer;
                     ObsType:string[8];
                     Filename:string;
                     Comment:string;
                     X_Disp:real;
                     Y_Disp:real;
                     Sky:real;
                     Sky_sigma:real;
                     X_Sigma:real;
                     Y_sigma:real;
                     NumCandidates:byte;
                     C1X,C1Y,C1Q:real;
                     C2X,C2Y,C2Q:real;
                     C3X,C3Y,C3Q:real;
                     C4X,C4Y,C4Q:real;
               end;

      galaxy=record
                   RA2000s:string[8];
                   RA2000:double;          {Fractional hours}
                   DEC2000s:string[8];
                   DEC2000:double;         {Fractional degrees}

                   RA1950s:string[8];
                   RA1950:double;          {Fractional hours}
                   DEC1950s:string[8];
                   DEC1950:double;         {Fractional degrees}
                   Name:string[80];
                   PGC:integer;
                   Hubble_T:real;
                   R25:real;
                   Bmag:real;
                   V3K:real;
             end;

const  FilterIDs:array[0..8] of string[8]=(
                                      'C',
                                      'R',
                                      'PB',
                                      'V',
                                      'PG',
                                      'I',
                                      'PR',
                                      'B',
                                      'XX');
       FilterNames:array[0..8] of string[8]=(
                                        'Clear',
                                        'Red',
                                        'PhotBlue',
                                        'Visual',
                                        'PhotGrn',
                                        'Infrared',
                                        'PhotRed',
                                        'Blue',
                                        'XXXXX');


var Press:double;   {Pressure in mmHg}
    Temp:double;    {Temp in F}
    RefError:boolean;
    AltError:boolean;
    CalError:boolean;
    Frozen:boolean;
    HighHorizonOn:boolean;
    RefractionOn:boolean;
    FlexureOn:boolean;
    RealTimeOn:boolean;
    SemiAuto:boolean;
    AltWarning,AltCutoffHi,AltCutoffLo,AltCutoffFrom:integer;
    NonSidOn:boolean;       {true if non-sidereal trackrate enabled}
    Moving:boolean;        {true if telescope is moving!}
    AutoRunning:boolean;   {true if teljoy in 'auto run' mode}
    posviolate:boolean;     {true if non-sid rate or paddle has been used since last auto jump or reset}
    DirtyTicks:longint;   {ticks value just after move finishes. 0 if pos}
                         {has been updated since move finished}

    SlewRate    :double;                    {Current slew rate}
    CoarseSetRate:double;                   {Coarse set rate}
    FineSetRate :double;                    {Fine set rate}
    GuideRate   :double;                    {Guide set rate}
    ST4_Vel     :double;                      {ST4 guide rate in arcsec/50ms}

    IObj,FObj:ObjectRec;                    {Initial and Final objects}
    Exitsave:pointer;
    ManualMode:boolean;

    ButtonPressedRA:Boolean;                {Is/was the RA button pressed   }
    ButtonPressedDEC:Boolean;               {Is/was the Dec button pressed  }
    EastOfPier:boolean;  {true if telescope is east of pier. If true, it inverts}
                     {the dec directions, and modifies dome and flexure calcs}
    NumRead,CurNum:integer;               {num of objects in list, current object}
    ObsLat,ObsLong:double;
    Eastlim,WestLim,MeshLim,HorizLim,PowerOff,HWlimit,LimOverride:boolean;
    OldLim:boolean;
    LastError:string[80];

function GetFiltNum(nam:string):byte;

procedure ConvDMS(const r:double; var d,m,s:double);
procedure WriteDMS(r:double);
function DMSstr(r:double; c:string):string;
function DMSstrp(r:double; c:string):string;

function UpString(ins:string):string;
function munchspace(str:string):string;

function b2i(b:boolean):integer;
function i2b(i:integer):boolean;

procedure sWrite(s:string);  {Status Write - in LightGreen}
procedure eWrite(s:string);  {Error Write - in lightred}
procedure wWrite(s:string);  {Warning Write - in lightblue}


implementation

uses Dosini,SysUtils,Crt;



function GetFiltNum(nam:string):byte;
var i,out:byte;
    dummy:integer;
begin
     out:=8;
     nam:=UpString(Munchspace(nam));
     for i:=0 to 7 do
         begin
              if nam=FilterIDs[i] then
                 out:=i;
              if nam=UpString(FilterNames[i]) then
                 out:=i;
         end;
     if (out=8) and (nam[1]<>'P') then
        for i:=1 to 7 do
            if nam[1]=FilterIDs[i][1] then
               out:=i;
     if (out=8) and (nam>='0') and (nam<='7') and (System.length(nam)=1) then
        Val(nam,out,dummy);
     GetFiltNum:=out;
end;

procedure ConvDMS(const r:double; var d,m,s:double);
begin   {Note - if r is negative, d,m, and s will _all_ be negative or zero}
     d:=Trunc(r/3600);
     m:=Trunc((r-d*3600)/60);
     s:=r-d*3600-m*60;
end;

procedure WriteDMS(r:double);
var d,m,s:double;
begin
     ConvDMS(r,d,m,s);
     if (r<0) then
        write('-');
     Write(Abs(d):0:0,':',Abs(m):0:0,':',Abs(s):0:1,'    ');
end;


function DMSstr(r:double; c:string):string;
var d,m,s:double;
begin
     ConvDMS(r,d,m,s);
     if (r<0) then
        Result:=('-')
     else
         Result:='';
     Result:=Result+Format('%0.0f%s%0.0f%s%0.1f',[Abs(d),c,Abs(m),c,Abs(s)]);
end;

function DMSstrp(r:double; c:string):string;
var d,m,s:double;
    i:integer;
begin
     ConvDMS(r,d,m,s);
     if (r<0) then
        Result:=('-')
     else
         Result:='';
     Result:=Result+Format('%2d%s%2d%s%2d',[Trunc(Abs(d)),c,Trunc(Abs(m)),c,Trunc(Abs(s))]);
     if c<>' ' then
        for i:=1 to Length(Result) do
            if Result[i]=' ' then
               Result[i]:='0';
end;



function b2i(b:boolean):integer;
begin
     if b then
        b2i:=1
     else
         b2i:=0;
end;

function i2b(i:integer):boolean;
begin
     if i<>0 then
        i2b:=true
     else
         i2b:=false;
end;

function UpString(ins:string):string;
var i:integer;
    tmp:string;
begin
     tmp:='';
     for i:=1 to System.Length(ins) do
         tmp:=tmp+UpCase(ins[i]);
     UpString:=tmp;
end;


function munchspace(str:string):string;
begin
     while (str[1]=' ') and (length(str)>1) do
           str:=Copy(str,2,255);
     while (str[length(str)]=' ') and (length(str)>1) do
           str:=Copy(str,1,length(str)-1);
     munchspace:=str;
end;


procedure sWrite(s:string);  {Status Write - in LightGreen}
begin
     Window(1,7,80,25);
     GotoXY(1,19);
     TextColor(lightgreen);
     TextBackground(Black);
     writeln(s);
     TextColor(lightgray);
end;

procedure eWrite(s:string); {Error Write - in lightred}
begin
     Window(1,7,80,25);
     GotoXY(1,19);
     TextColor(lightred);
     TextBackground(Black);
     writeln(s);
     TextColor(lightgray);
     LastError:=Copy(s,1,80);
end;

procedure wWrite(s:string); {Warning Write - in lightblue}
begin
     Window(1,7,80,25);
     GotoXY(1,19);
     TextColor(lightblue);
     TextBackground(Black);
     writeln(s);
     TextColor(lightgray);
end;


begin
     RefError:=false;
     AltError:=false;
     CalError:=i2b(GetProfileInt(Inif,'Alarms','OrigPosWarn',1));
                 {flag invalid orig pos on startup?}
     FlexureOn:=i2b(GetProfileInt(Inif,'Toggles','FlexureOn',1));
                     {flexure corrections on?}
     HighHorizonOn:=i2b(GetProfileInt(Inif,'Toggles','HighHorizonOn',0));
                     {whether to use AltCutoffHi or AltCutoffLo}
     RefractionOn:=i2b(GetProfileInt(Inif,'Toggles','RefractionOn',1));
                     {refraction corr. on?}
     RealTimeOn:=i2b(getProfileInt(Inif,'Toggles','RealTimeOn',1));
                   {real-time refraction and/or flexure corrections if on}
     SemiAuto:=i2b(GetProfileInt(Inif,'Toggles','SemiAutomatic',1));
                  {Do we wit for key or CCD mailbox deletion in auto run?}

     AltWarning:=GetProfileInt(Inif,'Alarms','AltWarning',10);
     AltCutoffFrom:=GetProfileInt(Inif,'Alarms','AltCutoffFrom',6);
     AltCutoffHi:=GetProfileInt(Inif,'Alarms','AltCutoffHi',30);
     AltCutoffLo:=GetProfileInt(Inif,'Alarms','AltCutoffLo',15);
     ObsLat:=GetProfileReal(Inif,'Environment','ObsLat',dObsLat);
     ObsLong:=GetProfileReal(Inif,'Environment','ObsLong',dObsLong);
     Moving:=false;
     NonSidOn:=false;
     posviolate:=true;
     AutoRunning:=false;
     Frozen:=false;
     EastLim:=false;
     WestLim:=false;
     MeshLim:=false;
     HorizLim:=false;
     PowerOff:=false;
     HWlimit:=false;
     OldLim:=false;
     LimOverride:=false;
     DirtyTicks:=0;
     ST4_Vel:=0;
     writeln('Globals init finished');
end.
