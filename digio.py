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


CNorth    = 0x40                        #Mask for north on coarse paddles (Green on test cable)
CSouth    = 0x80                        #Mask for south (red on test cable)
CEast     = 0x20                        #Mask for east (blue on test cable
CWest     = 0x10                        #Mask for west (yellow on test cable)

FNorth    = 0x40                        #Mask for north on fine paddle (1)}
FSouth    = 0x80                        #Mask for south (2)}
FEast     = 0x20                        #Mask for east (4)}
FWest     = 0x10                        #Mask for west (8)}

#Only used on NZ telescope which only uses one paddle, with a three-position speed toggle switch
#IFDEF NZ
#LeftMsk =  1   #Masks for left and right dome output bits
#RightMsk = 2
#CspaMsk   = 0x10                        #Speed bit A on coarse paddle (16)}
#CspbMsk   = 0x20                        #Speed bit B on coarse paddle (32)}

CSlewMsk  = 0x08
FGuideMsk = 0x08


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

def ReadCoarse(inputs):
  if inputs <> 0L:
    print hex((inputs >> 16) & 0xFF)
  return (inputs >> 16) & 0xFF
#  return CB

def ReadFine(inputs):
#  return (inputs >> 24) & 0xFF
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

