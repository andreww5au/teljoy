""" Pyro4 RPC server, allowing teljoy to be controller over the network. Runs a Pyro4 proxy server in a background thread.

    This server is used by the included client programs (the tjclient.py library, and utilities like tjjump.py, that use it)
    as well as the web status page CGI script, to load the current telescope state whenever the page refreshed.

    Note that communications are encrypted using a key (password) found in a file called 'teljoy.pyrokey' in the
    telescope user home directory (file name and path in the constant KEYFILE defined below.)

    Make sure that the same key is present in a corresponding file on any remote machines running the tjclient.py
    library or the programs that use it (tjjump.py, tjpos.py, etc), and that the tjclient.py file has been edited
    so that the path ane file name of this key file are correct.
"""

import Pyro4

import os
import threading
import time
import traceback
import socket

from globals import *
import detevent
import motion

if SITE == 'NZ':
  import nzdome as dome
  TESTHOST = 'www.canterbury.ac.nz'   # Host to use to try and determine the externally-visible IP address for Pyro4 to bind to
  KEYFILE = '~mjuo/teljoy.pyrokey'
else:
  import pdome as dome
  TESTHOST = 'mysql'   # Host to use to try and determine the externally-visible IP address for Pyro4 to bind to
  KEYFILE = '~/teljoy.pyrokey'
import utils

try:
  hmac = file(os.path.expanduser(KEYFILE), 'r').read().strip()
except IOError:
  logger.error('Pyro4 key file not found: %s' % KEYFILE)
  hmac = ''

Pyro4.config.HMAC_KEY = hmac   # or Pyro4.config.HMAC_KEY

PYROPORT = 9696

class Telescope(object):
  """Class representing RPC access to the internals of an active telescope control object.
  """
  def __init__(self):
    self.lock = threading.RLock()
  def _servePyroRequests(self):
    """When called, start serving Pyro requests.
    """
    while True:
      logger.info("Starting teljoy.rpc Pyro4 server")
      try:
        ns = Pyro4.locateNS()
      except:
        logger.debug("Can't locate Pyro nameserver - continuing on port %d" % PYROPORT)
        ns = None

      try:
        assert ns is not None      # Skip this bit if there's no nameserver found
        existing = ns.lookup("Teljoy")
        logger.info("Teljoy still exists in Pyro nameserver with id: %s" % existing.object)
        logger.info("Previous Pyro daemon socket port: %d" % existing.port)
        # start the daemon on the previous port, and try to detect the IP address of an external interface.
        try:
          pyro_daemon = Pyro4.Daemon(host=Pyro4.socketutil.getInterfaceAddress(TESTHOST), port=existing.port)
        except:   # Fails if the above DNS name isn't found, eg no internet connection
          pyro_daemon = Pyro4.Daemon(port=existing.port)   # Bind to the loopback address if we can't find an external interface
        # register the object in the daemon with the old objectId
        print "Pyro4 registered: ", pyro_daemon.register(self, objectId=existing.object)
      except (AssertionError, Pyro4.errors.PyroError, socket.error):
        try:
          # just start a new daemon on a random port, and try to detect the IP address of an external interface.
          try:
            pyro_daemon = Pyro4.Daemon(host=Pyro4.socketutil.getInterfaceAddress(TESTHOST), port=PYROPORT)
          except:     # Fails if the above DNS name isn't found, eg no internet connection
            pyro_daemon = Pyro4.Daemon(port=PYROPORT)     # Bind to the loopback address if we can't find an external interface
          # register the object in the daemon and let it get a new objectId
          # also need to register in name server because it's not there yet.
          uri =  pyro_daemon.register(self, objectId='Teljoy')
          print "Pyro4 uri is: ", uri
          if ns is not None:
            ns.register("Teljoy", uri)
        except:
          logger.error("Exception in Teljoy Pyro4 startup. Retrying in 10 sec: %s" % (traceback.format_exc(),))
          time.sleep(10)
      try:
        pyro_daemon.requestLoop()
      except:
        logger.error("Exception in Teljoy Pyro4 server. Restarting in 10 sec: %s" % (traceback.format_exc(),))
        time.sleep(10)

  def Ping(self):
    detevent.ProspLastTime = time.time()
    return

  def Lock(self):
    self.lock.acquire()

  def Unlock(self):
    self.lock.release()

  def GetMotors(self):
    return motion.motors.__getstate__()

  def GetLimits(self):
    return motion.motors.limits.__getstate__()

  def GetCurrent(self):
    return detevent.current.__getstate__()

  def GetDome(self):
    return dome.dome.__getstate__()

  def GetPrefs(self):
    return prefs.__dict__

  def GetInfo(self):
    return detevent.current.__repr__()

  def Active(self):
    return safety.Active.is_set()

  def jump(self, *args, **kws):
    ob = utils.Pos(*args, **kws)
    if ob is None:
      return "ERROR: Can't parse those arguments to get a valid position"
    if safety.Active.is_set():
      mesg = "Jumping to: %s\n" % ob
      detevent.current.Jump(ob)
      if dome.dome.AutoDome:
        mesg += "Moving dome."
        dome.dome.move(az=dome.dome.CalcAzi(ob))
      return mesg
    else:
      return "ERROR: safety interlock set, can't jump telescope"

  def reset(self, *args, **kws):
    """Set the current RA and DEC to the values given.
       'ra' and 'dec' can be sexagesimal strings (in hours:minutes:seconds for RA and degrees:minutes:seconds
       for DEC), or numeric values (fractional hours for RA, fractional degrees for DEC). Epoch is in decimal
       years, and objid is an optional short string with an ID.
    """
    ob = utils.Pos(*args, **kws)
    if ob is None:
      return "ERROR: Can't parse those arguments to get a valid position"
    detevent.current.Reset(obj=ob)
    return "Resetting current position to: %s" % ob

  def offset(self, ora, odec):
    """Make a tiny slew from the current position, by ora,odec arcseconds.
    """
    detevent.current.Offset(ora=ora, odec=odec)
    return "Moved small offset distance: %4.1f,%4.1f" % (ora,odec)

  def autoguide(self, on):
    """Turn the autoguider mode on or off.
    """
    if on:
      motion.motors.Autoguide(True)
      return "Autoguiding turned ON"
    else:
      motion.motors.Autoguide(False)
      return "Autoguiding turned OFF"

  def freeze(self):
    """Freeze the telescope
    """
    motion.motors.Frozen = True
    return "Telescope frozen"

  def unfreeze(self):
    """Un-Freeze the telescope
    """
    if safety.Active.is_set():
      motion.motors.Frozen = False
      return "Telescope un-frozen"
    else:
      return "ERROR: Safety interlock, can't unfreeze telescope!"

  def dome(self, arg):
    """move, open, or close the dome.
    """
    if not dome.dome.AutoDome:
      return "ERROR: Dome not in automatic mode."
    if not safety.Active.is_set():
      return "ERROR: safety interlock, can't open, shut, or move dome"
    if type(arg)==int or type(arg)==float:
      dome.dome.move(arg)
      return "Dome moving to %s" % arg
    elif type(arg)==str:
      if arg.upper() in ['O','OPEN']:
        dome.dome.open()
        return "Dome opening"
      elif arg.upper() in ['C','CLOSE']:
        dome.dome.close()
        return "Dome closing"
      else:
        return "ERROR: Unknown argument: specify an azimuth in degrees, or 'open', or 'close'"
    else:
      return "ERROR: Unknown argument: specify an azimuth in degrees, or 'open', or 'close'"



def InitServer():
  global plat, pyro_thread
  plat = Telescope()

  #Start the Pyro4 daemon thread listening for status requests and receiver 'putState's:
  pyro_thread = threading.Thread(target=plat._servePyroRequests, name='PyroDaemon')
  pyro_thread.daemon = True
  pyro_thread.start()
  logger.info("Started Pyro4 communication process to serve Teljoy connections")
  #The daemon threads will continue to spin for eternity....

  return True


