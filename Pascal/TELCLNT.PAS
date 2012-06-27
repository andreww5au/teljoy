program telclient;
uses Globals, SQLInt, Crt;

var IObj:ObjectRec;
    HA:real;
    Current:CurrentInfo;
    LastMod:string;


Procedure ShowStatus;
var lb:byte;    {Dump - used for debugging}
    tmpd:double;
begin
   with Current do
    begin
     TextBackground(Red);
     TextColor(yellow);
     Window(1,1,80,6);

     GotoXY(1,1);
     Write('Top RA:  ');
     WriteDMS(IObj.RaC/15);
     GotoXY(21,1);
     if EastOfPier then
        write('INV ')
     else
         write('    ');

     GotoXY(1,2);
     Write('Top Dec: ');
     WriteDMS(IObj.DecC);

     GotoXY(1,3);
     Write('Alt: ');
     WriteDMS(Iobj.Alt*3600);

     GotoXY(1,4);
     Write('Airmass: ');
     Write(1/Cos((90-Iobj.Alt)/180*Pi):0:4);

     GotoXY(25,1);
     Write('LST: ');
     WriteDMS(Iobj.Time.LST*3600);

     GotoXY(25,2);
     Write('UT: ');
     WriteDMS(IObj.Time.UTdec*3600);

     GotoXY(25,3);
     Write('HA: ');
     tmpd:= IObj.RaC/54000-IObj.Time.LST;
     if tmpd < -12 then
        tmpd:=tmpd+24;
     if tmpd > 12 then
        tmpd:=tmpd-24;
     Write(tmpd:0:4,' hr   ');

     GotoXY(50,1);
     Write('Obj ID: ',IObj.ID,'           ');

     GotoXY(50,2);
     if (not posviolate) and AutoRunning then
        Write('Obj Num: ',CurNum,' of ',NumRead)
     else
         write('                            ');

     GotoXY(25,4);
     write('NonSidereal: ');
     if NonSidOn then
        write('ON  ')
     else
         write('OFF ');

     GotoXY(25,5);
     write('Frozen:');
     if Frozen then
        write('Yes  ')
     else
         write('No  ');


     GotoXY(1,5);
     write('Moving:');
     if moving then
        write('Yes ')
     else
         write('No ');

     GotoXY(1,6);
     Write('Dome:');
     if (DomeInUse or ShutterInUse) then
        write('Active   ')
     else
         write('Inactive');

     GotoXY(25,6);
     write('Dome Tracking:');
     if DomeTracking then
        write('ON ')
     else
         write('OFF');

     GotoXY(50,3);
     Write('Obj RA: ');
     if (not posviolate) then
        WriteDMS(IObj.Ra/15)
     else
         write('               ');

     GotoXY(50,4);
     Write('Obj Dec: ');
     if (not posviolate) then
        WriteDMS(IObj.Dec)
     else
         write('               ');

     GotoXY(50,5);
     Write('Obj Epoch: ');
     if (not posviolate) then
        Write(IObj.Epoch:0:3)
     else
         write('               ');

     GotoXY(50,6);
     Write('G  ',RA_GuideAcc/20:0:2,'", ',DEC_GuideAcc/20:0:2,'"   ');

     Window(1,7,80,25);
     TextBackground(black);
     TextColor(lightGray);
    end;
end;


begin
     TextBackground(Red);
     TextColor(yellow);
     Window(1,1,80,6);
     ClrScr;
     Window(1,7,80,25);
     TextBackground(black);
     TextColor(lightGray);
     ClrScr;

     repeat
           ReadSQLCurrent(IObj,Current,HA,LastMod);
           ShowStatus;
           delay(500);
     until keypressed;
     writeln('finishing');
end.

