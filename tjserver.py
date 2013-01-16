"""Handle RPC comms with other components of the observing system, using Pyro4
"""

import Pyro4
import threading
import time
import traceback
import socket

from globals import *
import detevent
import motion
import pdome
import utils

#hmac = "ShiverMeTimbers"
#Pyro4.config.HMAC_KEY = hmac or Pyro4.config.HMAC_KEY

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
        logger.error("Can't locate Pyro nameserver - waiting 10 sec to retry")
        time.sleep(10)
        break

      try:
        existing = ns.lookup("Teljoy")
        logger.info("Teljoy still exists in Pyro nameserver with id: %s" % existing.object)
        logger.info("Previous Pyro daemon socket port: %d" % existing.port)
        # start the daemon on the previous port
        pyro_daemon = Pyro4.Daemon(host=Pyro4.socketutil.getInterfaceAddress('chef'), port=existing.port)
        # register the object in the daemon with the old objectId
        pyro_daemon.register(self, objectId=existing.object)
      except (Pyro4.errors.PyroError, socket.error):
        try:
          # just start a new daemon on a random port
          pyro_daemon = Pyro4.Daemon(host=Pyro4.socketutil.getInterfaceAddress('chef'))
          # register the object in the daemon and let it get a new objectId
          # also need to register in name server because it's not there yet.
          uri =  pyro_daemon.register(self)
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

  def GetCurrent(self):
    return detevent.current.__getstate__()

  def GetDome(self):
    return pdome.dome.__getstate__()

  def GetPrefs(self):
    return prefs.__dict__

  def GetInfo(self):
    return detevent.current.__repr__()

  def jump(self, *args, **kws):
    ob = utils.Pos(*args, **kws)
    if ob is None:
      return "ERROR: Can't parse those arguments to get a valid position"
    mesg = "Jumping to: %s\n" % ob
    detevent.current.Jump(ob)
    if pdome.dome.AutoDome:
      mesg += "Moving dome."
      pdome.dome.move(az=pdome.dome.CalcAzi(ob))
    return mesg

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

  def freeze(self):
    """Freeze the telescope
    """
    motion.motors.Frozen = True
    return "Telescope frozen"

  def unfreeze(self):
    """Un-Freeze the telescope
    """
    motion.motors.Frozen = False
    return "Telescope un-frozen"

  def dome(self, arg):
    """move, open, or close the dome.
    """
    if not pdome.dome.AutoDome:
      return "ERROR: Dome not in automatic mode."
    if type(arg)==int or type(arg)==float:
      pdome.dome.move(arg)
      return "Dome moving to %s" % arg
    elif type(arg)==str:
      if arg.upper() in ['O','OPEN']:
        pdome.dome.open()
        return "Dome opening"
      elif arg.upper() in ['C','CLOSE']:
        pdome.dome.close()
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


