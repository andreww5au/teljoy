"""
    Functions to read the digital inputs from the 8255 card (and in this
    Python version added functions for 'faking' button presses).
    
    To be replaced by USB interface code.
    
    ReadCoarse   -           Read the coarse paddle of the telescope.
    ReadFine     -           Read the fine paddle of the telescope.
    ReadLimit    -           Read the limit and power-down status.

    These procedures handle all the I/O operations with the 8255 card.
    The procedures are:

    ReadPort            - Read a given port (1 -A,B,C or 2 -A,B,C).
    WritePort           - Write to a given port (must first write to
                          control register of port to enable it to be
                          writeable).
                          
    The New Zealand installation also uses 8255 port IO to control the 
    dome. Instead of a serial link to a dedicated controller, as in Perth, 
    the serial link is to an encoder returning a stream of bytes containing
    the dome azimuth, and 8255 IO is used to emulate the 'dome left' and
    'dome right' paddle buttons, which control the motors. This module contains
    the port IO for that task, while NZDOME.PAS contains the rest of the logic.    

    The constants and types given below are the locations of buffers,
    control registers or board address.  The Perth 8255 I/O board is assumed
    to be at 0x1b0 = 432.
"""

Adr82     = 432                   #Default address of 8255 card}
A1        = 432                   #Port 1A read/write buffer}
B1        = 433                   #Port 1B read/write buffer}
C1        = 434                   #Port 1C read/write buffer}
Ctrl1     = 435                   #Port 1 control register}
A2        = 436                   #Port 2A read/write buffer}
B2        = 437                   #Port 2B read/write buffer}
C2        = 438                   #Port 2C read/write buffer}
Ctrl2     = 439                   #Port 2 control register}
ReadAll   = 0x9b                   #Set control register, ports read
                                   # only}
WriteAll  = 0x80                   #Set control register, ports writeable}

ST5_Left   = 0x08
ST5_Right  = 0x04
ST5_Up     = 0x01
ST5_Down   = 0x02

CNorth    = 0x01                        #Mask for north on coarse paddles (1)}
CSouth    = 0x02                        #Mask for south (2)}
CEast     = 0x04                        #Mask for east (4)}
CWest     = 0x08                        #Mask for west (8)}

FNorth    = 0x01                        #Mask for north on fine paddle (1)}
FSouth    = 0x02                        #Mask for south (2)}
FEast     = 0x04                        #Mask for east (4)}
FWest     = 0x08                        #Mask for west (8)}

CspaMsk   = 0x10                        #Speed bit A on coarse paddle (16)}
CspbMsk   = 0x20                        #Speed bit B on coarse paddle (32)}

CSlewMsk  = 0x10
FGuideMsk = 0x10


port = {432:0,433:0,434:0,435:0,436:0,437:0,438:0,439:0, 534:0, 535:0, 541:0}   #Dummy port IO

#IFDEF NZ
#LeftMsk =  1   #Masks for left and right dome output bits
#RightMsk = 2

def ReadPort(N, Ch):
  """Will not do anything, no port IO from Python
  """
  if N == 1:
    port[Ctrl1] = ReadAll
    if Ch == 1:
      B = port[A1]
    elif Ch == 2:
      B = port[B1]
    elif Ch == 3:
      B = port[C1]
  elif N == 2:
    port[Ctrl2] = ReadAll
    if Ch == 1:
      B = port[A2]
    elif Ch == 2:
      B = port[B2]
    elif Ch == 3:
      B = port[C2]
  return B

def WritePort(B, N, Ch):
  """Will not do anything, no port IO from Python
  """
  if N == 1:
    port[Ctrl1] = WriteAll
    if Ch == 1:
      port[A1] = B
    elif Ch == 2:
      port[B1] = B
    elif Ch == 3:
      port[C1] = B
  elif N == 2:
    port[Ctrl2] = WriteAll
    if Ch == 1:
      port[A2] = B
    elif Ch == 2:
      port[B2] = B
    elif Ch == 3:
      port[C2] = B


#$IFDEF NZ}
#Procedure ReadCoarse(var CB:byte)
#var b:byte
#begin
#     b = Port[$216]
#     b = b and port[$216]
#     b = not b
#     CB = b and 63
#end-with-semicolon

#Procedure ReadFine(var FB:byte)
#begin
#       FB = 0
#end-with-semicolon

#Procedure ReadLimit(var LB:byte)
#var pw,hl,ms,el,wl:0..1
#    b:byte
#begin
#     b = Port[$217]
#     b = b and port[$217]
#     el = (b and 1)
#     wl = (b and 2) div 2
#     ms = (b and 4) div 4
#     pw = (b and 32) div 32
#     hl = (b and 64) div 64
#     LB = pw + 2*hl + 4*ms + 8*el + 16*wl
#end-with-semicolon

#Function DomeGoingLeft:boolean
#var b:byte
#begin
#     b = port[$216]
#     b = b and port[$216]
#     DomeGoingLeft = ((b and 64)=64)
#end-with-semicolon

#Procedure DomeLeft
#begin
#     if DomeGoingRight:
#        begin
#             DomeStop #Open the relay so we can read the paddle button}
#             delay(500)
#        end-with-semicolon
#     if not DomeGoingRight:  #Right paddle button isn't pressed}
#        begin
#             CurrentOut = (CurrentOut or LeftMsk) and (not RightMsk)
#             Port[$21D] = CurrentOut
#        end-with-semicolon
#end-with-semicolon

#Function DomeGoingRight:boolean
#var b:byte
#begin
#     b = port[$216]
#     b = b and port[$216]
#     DomeGoingRight = ((b and 128)=128)
#end-with-semicolon

#Procedure DomeRight
#begin
#     if DomeGoingLeft:
#        begin
#             DomeStop #Open the relay so we can read the paddle button}
#             delay(500)
#        end-with-semicolon
#     if not DomeGoingLeft:  #Left paddle button isn't pressed}
#        begin
#             CurrentOut = (CurrentOut or RightMsk) and (not LeftMsk)
#             Port[$21D] = CurrentOut
#        end-with-semicolon
#end-with-semicolon

#Procedure DomeStop
#begin
#     CurrentOut = CurrentOut and (not (LeftMsk or RightMsk))
#     Port[$21D] = CurrentOut
#end-with-semicolon

#$ELSE}

CB = 0           #Defauly to Coarse-set speed
FB = 0           #Default to Fine-set speed (ignore fine-guide)
LastDirn = ''
LastPaddle = ''

def ReadCoarse():
#  return ReadPort(1,1)
  return CB

def ReadFine():
#  return ReadPort(1,2)
  return FB

def ReadLimit():
 return 0     #No limit switches readable on Perth telescope
 

#################
# Dummy button-push routines, used for testing



def press(dirn, paddle='F'):
  """Flag a button as 'pressed'. Args are 'dirn' which must equal 'N','S','E', or 'W',
     and 'paddle' which must be 'C' or 'F' (default 'F')
     
     Code to emulate button presses until actual hardware IO is working.
  """
  global CB,FB,LastDirn,LastPaddle
  dirn = dirn.upper().strip()
  paddle = paddle.upper().strip()
  if paddle == 'C':
    if dirn == 'N':
      CB |= CNorth
    elif dirn == 'S':
      CB |= CSouth
    elif dirn == 'E':
      CB |= CEast
    elif dirn == 'W':
      CB |= CWest
    else:
      print "Invalid direction: %s" % dirn
      return
  elif paddle == 'F':
    if dirn == 'N':
      FB |= FNorth
    elif dirn == 'S':
      FB |= FSouth
    elif dirn == 'E':
      FB |= FEast
    elif dirn == 'W':
      FB |= FWest
    else:
      print "Invalid direction: %s" % dirn
      return
  else:
    print "Invalid paddle: %s" % paddle
    return
  LastDirn = dirn
  LastPaddle = paddle


def release(dirn=None, paddle=None):
  """Flag a button as 'pressed'. Args are 'dirn' which must equal 'N','S','E', or 'W',
     and 'paddle' which must be 'C' or 'F'. If neither 'dirn' nor 'paddle' are given,
     then 'release' the last button 'press'ed.
     
     Code to emulate button presses until actual hardware IO is working.
  """
  global CB,FB,LastDirn,LastPaddle
  if dirn is None and paddle is None:
    dirn = LastDirn
    paddle = LastPaddle
  if paddle is None:
    paddle = 'F'
  dirn = dirn.upper().strip()
  paddle = paddle.upper().strip()
  if paddle == 'C':
    if dirn == 'N':
      CB &= ~ CNorth
    elif dirn == 'S':
      CB &= ~ CSouth
    elif dirn == 'E':
      CB &= ~ CEast
    elif dirn == 'W':
      CB &= ~ CWest
    else:
      print "Invalid direction: %s" % dirn
      return
  elif paddle == 'F':
    if dirn == 'N':
      FB &= ~ FNorth
    elif dirn == 'S':
      FB &= ~ FSouth
    elif dirn == 'E':
      FB &= ~ FEast
    elif dirn == 'W':
      FB &= ~ FWest
    else:
      print "Invalid direction: %s" % dirn
      return
  else:
    print "Invalid paddle: %s" % paddle
    return
  LastDirn = None
  LastPaddle = None


def cset():
  """Set the Coarse paddle to 'set' speed.
     
     Code to emulate button presses until actual hardware IO is working.
  """
  global CB
  CB &= ~ CSlewMsk
  
def cslew():
  """Set the Coarse paddle to 'slew' speed.
     
     Code to emulate button presses until actual hardware IO is working.
  """
  global CB
  CB |= CSlewMsk

#$ENDIF}

#$IFDEF NZ}
#CurrentOut = 0      #No outputs high on startup, so the dome won't start moving.
#     Port[$21D] = 0
#     Port[$21E] = 0
#$ENDIF}

