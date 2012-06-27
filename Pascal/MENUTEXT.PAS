unit menutext;

interface

procedure MenuMain;
procedure MenuConf;
procedure MenuJump;
procedure MenuTracking;

implementation
uses Crt;

Procedure MenuMain;
  begin
    clrscr;
    writeln;
    writeln;
    writeln('Teljoy - Main Menu');
    writeln('                 ESC -  Exit Program');
    writeln;
    writeln('                   C -  Configure Teljoy...');
    writeln('                   T -  Tracking Menu...');
    writeln;
    writeln('                   S -  Shutdown System');
    writeln('                   M -  Move Dome');
{$IFDEF NZ}
      writeln('                   H -  Halt Dome motion');
{$ELSE}
      writeln('                   O -  Open Dome');
      writeln('                   N -  Close Dome');
{$ENDIF}

    writeln;
    writeln('                   F -  Freeze sidereal motion');
    writeln('                   J -  Jump Menu...');
    writeln('                   A -  Automatic Operation');
    writeln('                   K -  Immediate stop');
  end;

Procedure MenuConf;
begin
     ClrScr;
     writeln;
     writeln;
     writeln('Configure Teljoy Parameters:');
     writeln('        ESC - Go back to Main Menu');
     writeln('          V - Change hand-paddle velocities');
     writeln('          R - Reset to default hand-paddle velocities');
     writeln('          E - Modify Environmental parameters');
     writeln;
     writeln('          P - Print current velocities and Environmental parameters');
     writeln('          S - Save parameters to disk');
     writeln('          L - Load parameters from disk');
     writeln;
     writeln('          D - Set Dome mode (manual or Auto)');
     writeln('          T - Toggle Dome Tracking');
     writeln('          H - Toggle High Horizon Cutoff');

     writeln('          A - Toggle Semi/Fully automatic mode');
     writeln('          N - Toggle Refraction correction');
     writeln('          F - Toggle Flexure correction');
     writeln('          M - Toggle Realtime corrections');
     writeln('          I - Toggle EastOfPier');
end;

Procedure MenuJump;
  begin
    clrscr;
    writeln;
    writeln;
    writeln('   Jump Menu');
    writeln('                ESC -  Go back to Main Menu');
    writeln;
    writeln('                  R -  Reset Current Position');
    writeln;
    writeln('                  G -  Goto Position');
    writeln('                  N -  Goto object in database by name');
    writeln('                  O -  Move small offset distance');
    writeln;
    writeln('                  F -  Freeze sidereal motion');
    writeln('                  S -  Toggle non-sidereal velocity offset');
{$IFDEF NZ}
    writeln('                  L -  Override East/West limit temporarily');
{$ENDIF}
    writeln('                  I -  Toggle East-Of-Pier');
    writeln;
    writeln('                  M -  Move Dome to Azi');
    writeln('                  A -  Align dome to current position');
{$IFDEF NZ}
    writeln('                  H -  Halt Dome motion');
{$ENDIF}
  end; {Goto help}

Procedure MenuTracking;
  begin
    clrscr;
    writeln;
    writeln;
    writeln('   Non-Sidereal Tracking Offset Velocity');
    writeln;
    writeln('                ESC - Exit to Main Menu');
    writeln;
    writeln('                  R -  Reset the non-sidereal Tracking rates to zero');
    writeln('                  A -  Adjust/Modify non-sidereal Tracking rates');
    writeln('                  S -  Show non-sidereal Tracking rates');
    writeln;
  end;

end.
