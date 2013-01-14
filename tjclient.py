"""Pyro4 RPC client library for Teljoy
"""

import Pyro4

class Status(object):
  pass     #A record to store arbitrary fields

class TelClient(object):
  """Client object, using a Pyro4 proxy of the remote telescope
     object to get status and send commands.
  """
  def __init__(self):
    """Set up the client object on creation
    """
    self.connected = False
    self.proxy = None
    self.dome = Status()
    self.current = Status()
    self.motors = Status()
    self.prefs = Status()

  def update(self):
    self.motors.__dict__.update(self.proxy.GetMotors())
    self.current.__dict__.update(self.proxy.GetCurrent())
    self.dome.__dict__.update(self.proxy.GetDome())


def InitClient():
  """Connect to the Teljoy server process and create a proxy object to the
     real telescope object.
  """
  global plat
  plat = TelClient()
  plat.connected = False
  try:
    plat.proxy = Pyro4.Proxy('PYRONAME:Teljoy')
    plat.connected = True
  except Pyro4.errors.PyroError:
    print "Can't connect to Teljoy server - run teljoy.py to start the server"
  try:
    plat.update()
  except Pyro4.errors.PyroError:
    plat.connected = False
  return plat.connected   #True if we have a valid, working proxy
