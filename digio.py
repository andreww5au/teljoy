"""
    Functions to read the digital inputs, originally from the 8255 card and now using the
    USB controller. For testing, a few functions are defined for for 'faking' button presses.
    
    ReadCoarse   -           Read the coarse paddle of the telescope.
    ReadFine     -           Read the fine paddle of the telescope.
    ReadLimit    -           Read the limit and power-down status.

    The New Zealand installation also uses digital port IO to control the
    dome. Instead of a serial link to a dedicated controller, as in Perth, 
    the serial link is to an encoder returning a stream of bytes containing
    the dome azimuth, and digital IO is used to emulate the 'dome left' and
    'dome right' paddle buttons, which control the motors. This module contains
    the port IO for that task, while NZDOME.PAS contains the rest of the logic.    

    The constants and types given below are the old (ISA bus) locations of buffers,
    control registers or board address.  The Perth 8255 I/O board is assumed
    to be at 0x1b0 = 432, and the base address of the New Zealand board (a PC-711B)
    is at 0x216 = 534.
"""

from globals import *
import motion            # Current state of input buts are in motion.motors.Driver.inputs

CNorth    = 0x01                        # Mask for north on coarse paddles (red on test cable)
CSouth    = 0x02                        # Mask for south (green on test cable)
CEast     = 0x04                        # Mask for east (blue on test cable
CWest     = 0x08                        # Mask for west (yellow on test cable)

FNorth    = 0x01                        # Mask for north on fine paddle (Fine paddle doesn't exist on NZ telescope)
FSouth    = 0x02                        # Mask for south
FEast     = 0x04                        # Mask for east
FWest     = 0x08                        # Mask for west

# Speed bits for Perth telescope, with a two position toggle switch on each paddle
CSlewMsk  = 0x10                        # This bit is set if the coarse paddle is set to 'Slew' speed
FGuideMsk = 0x10                        # This bit is set if the fine paddle is set to 'Guide' speed


# NZ telescope only uses one paddle, with a three-position speed toggle switch requiring two bits.
CspaMsk   = 0x10                        # Speed bit A on coarse paddle (16)}
CspbMsk   = 0x20                        # Speed bit B on coarse paddle (32)}

# Output bits used in NZ for dome motor control
LeftBit = 8    # Output bit number for driving dome motor 'left' - bit 0 of port 2_C
RightBit = 9   # Output bit number for driving dome motor 'right' - bit 1 of port 2_C

# Paddle switch emulation for testing:
CB = 0           # 'Coarse paddle' value used to emulate button presses for testing
FB = 0           # 'Fine paddle' value used to emulate button presses for testing
LastDirn = ''
LastPaddle = ''


# Wrappers for actual bit IO functions
def set_outputs(n):
  """'n' is a 64 bit integer, and any bit set in 'n' is forced high (assuming it is configured as an output
     bit). Bits in 'n' that are zero are left unchanged.
  """
  d = motion.motors.Driver.set_outputs(n)
  return d


def clear_outputs(n):
  """'n' is a 64 bit integer, and any bit set in 'n' is forced low (assuming it is configured as an output
     bit). Bits in 'n' that are zero are left unchanged.
  """
  d = motion.motors.Driver.clear_outputs(n)
  return d


def ReadCoarse():
  """Return either the 6 bits of data from the coarse paddle bits, or a dummy value if
     we're emulating the paddle in software.
     In NZ, on the old card, this was port $216 = DI-low
  """
  inputs = motion.motors.Driver.inputs
  if 'C' in DUMMYPADDLES:
    return CB
  if SITE == 'PERTH':
    val = (inputs >> 24) & 0x3F
  else:
    val = (inputs >> 0) & 0x3F     # bits 0-5 of port 2_A
  if ((val & 0x03) == 0x03) or ((val & 0x0C) == 0x0C):
    return 0    # more than one button pressed, so ignore inputs
  else:
    return val


def ReadFine():
  """Return the byte of data from the fine hand paddle port, or a dummy value if
     we're emulating the paddle in software.
     Return zero if called by the code in NZ.
  """
  if SITE == 'NZ':
    return 0   # No fine paddle on NZ telescope, so always return 0
  inputs = motion.motors.Driver.inputs
  if 'F' in DUMMYPADDLES:
    return FB
  val = (inputs >> 40) & 0xFF         # bits 40-44, not inverted for real fine paddle
  if ((val & 0x03) == 0x03) or ((val & 0x0C) == 0x0C):
    return 0    # N+S pressed at the same time, or E+W
  else:
    return val


def ReadLimit(inputs=None):
  """Read the state of the limit switch input bits, and return a list of
     active limit states (each a string). An empty list means no limits are
     active. On old card, this was port $217 = DI-high.

     Note that if the power switch is off (0x20 is set), then all the other
     limit inputs will go high as well, as the relays all open.
  """
  if SITE == 'PERTH':
    return []     # Hardware limits can't be read in Perth
  if inputs is None:
    inputs = motion.motors.Driver.inputs
  val = (inputs >> 16) & 0x7F                 # bits 0,1,2,5,6 of port 2_B
  limits = []
  if (val & 0x01) == 0x01:
    limits.append('EAST')
  if (val & 0x02) == 0x02:
    limits.append('WEST')
  if (val & 0x04) == 0x04:
    limits.append('MESH')
  if (val & 0x20) == 0x20:
    limits.append('POWER')
  if (val & 0x40) == 0x40:
    limits.append('HORIZON')
  return limits


def DomeGoingLeft():
  """Returns true if the dome motor is moving left. This happens if the user presses the 'Dome Left' button on the paddle.
  """
  if SITE == 'PERTH':
    return False     # No digital IO for dome in Perth
  inputs = motion.motors.Driver.inputs
  val = (inputs >> 0) & 0xFF                 # bit 6 of port 2_A
  return (val & 0x40) == 0x40


def DomeGoingRight():
  """Returns true if the dome motor is moving right. This happens if the user presses the 'Dome Right' button on the paddle.
  """
  if SITE == 'PERTH':
    return False     # No digital IO for dome in Perth
  inputs = motion.motors.Driver.inputs
  val = (inputs >> 0) & 0xFF                 # bit 7 of port 2_A
  return (val & 0x80) == 0x80


def DomeStop():
  """Turn off both dome motors.
  """
  if SITE == 'PERTH':
    return      # No digital IO for dome in Perth
  clear_outputs((1 << RightBit) + (1 << LeftBit))


def DomeLeft():
  """Move the dome left.
  """
  if SITE == 'PERTH':
    return      # No digital IO for dome in Perth
  if DomeGoingRight():
    DomeStop()
    time.sleep(0.5)
  if not DomeGoingRight():
    clear_outputs(1 << RightBit)
    set_outputs(1 << LeftBit)


def DomeRight():
  """Move the dome right.
  """
  if SITE == 'PERTH':
    return      # No digital IO for dome in Perth
  if DomeGoingLeft():
    DomeStop()
    time.sleep(0.5)
  if not DomeGoingLeft():
    clear_outputs(1 << LeftBit)
    set_outputs(1 << RightBit)


############################################################
# Dummy button-push routines, used for testing

def press(dirn, paddle='F'):
  """Flag a button as 'pressed'. Args are 'dirn' which must equal 'N','S','E', or 'W',
     and 'paddle' which must be 'C' or 'F' (default 'F')
     
     Code to emulate button presses for testing.
  """
  global CB, FB, LastDirn, LastPaddle
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
     
     Code to emulate button presses for testing.
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
     
     Code to emulate button presses for testing.
  """
  global CB
  CB &= ~ CSlewMsk


def cslew():
  """Set the Coarse paddle to 'slew' speed.
     
     Code to emulate button presses for testing.
  """
  global CB
  CB |= CSlewMsk
