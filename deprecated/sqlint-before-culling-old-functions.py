
import datetime

"""Interface library for communicating with the SQL database. 
   Converted to Python, but retaining the (ugly) query generation code from
   the original Pascal.
   
   Should work for postgres or mysql, but only tested under mysql
   
   These functions fall into three groups:
   -Save or load internal Teljoy state (position, etc)
   -Write or read from 'mailbox' tables, used for interprocess communication
      between Teljoy, Prosp (the CCD camera controller) and Vista (the supernova
      search software). These tables normally contain no rows - if a row is written, 
      it represents a task to be completed, and the row is deleted by the recipient
      when the task is finished. 
   
   Many of these functions are legacy code, that probably won't be used again. 
"""

INTERFACE = 'mysqldb'
#INTERFACE = 'pgdb'

if INTERFACE == 'mysqldb':
  import MySQLdb as dblib
elif INTERFACE == 'pgdb':
  import pgdb as dblib


from globals import *
import correct

USER = 'honcho'
PASSWORD = ''
HOST = 'mysql'
DATABASE = ''


def getdb(user=None, password=None, host=None, database=None):
  """Return a database connection object given user, password, host and database
     arguments.
  """
  if INTERFACE == 'mysqldb':
    dbob = dblib.connect(user=user, passwd=password, host=host)
  elif INTERFACE == 'pgdb':
    dbob = dblib.connect(user=user, password=password, host=host, database=database)
  return dbob


class Info:
  """Used to pass miscellaneous state information to and from the database function/s.
     Names reflect the original attribute names in correct.CalcPosition, 
     motors.MotorControl, globals.Prefs, pdome.DomeStatus as well as the detevent.LastError
     variable.

     Used to let clients access Teljoy internal state, required to interface to Prosp, the
     CCD control software for automatic observing.
  """
  def __init__(self):
    self.posviolate = False
    self.moving = False
    self.EastOfPier = False
    self.NonSidOn = False
    self.DomeInUse = False
    self.ShutterInUse = False
    self.ShutterOpen = False
    self.DomeTracking = False
    self.Frozen = False
    self.RA_GuideAcc = 0.0
    self.DEC_GuideAcc = 0.0
    self.LastError = ''
    if CLASSDEBUG:
      self.__setattr__ = self.debug

  def debug(self,name,value):
    """Trap all attribute writes, and raise an error if the attribute
       wasn't defined in the __init__ method. Debugging code to catch all
       the identifier mismatches due to the fact that Pascal isn't case
       sensitive for identifier names.
    """
    if name in self.__dict__.keys():
      self.__dict__[name] = value
    else:
      raise AssertionError, "Setting attribute %s=%s for the first time."

  def __getstate__(self):
    """Can't pickle the __setattr__ function when saving state
    """
    d = self.__dict__.copy()
    del d['__setattr__']
    return d


class TJboxrec:
  """Stores the extra information in the TJbox table, that can't be stored in a 
     correct.CalcPosition object.
     
     Used for handling external commands, required to interface to Prosp, the
     CCD control software for automatic observing.
  """
  def __init__(self):
    self.action = 'none'      #String containing desired action command
    self.OffsetRA = 0.0       #RA offset for small slew, in arcsec
    self.OffsetDec = 0.0      #DEC offset for small slew, in arcsec
    self.DomeAzi = 0.0        #New dome azimuth to move dome
    self.Shutter = False      #New shutter state, to open or close shutter
    self.Freeze = False       #new state for motion.motors.Frozen
    self.LastMod = 0          #time since last modification time for command record in database
    if CLASSDEBUG:
      self.__setattr__ = self.debug

  def debug(self,name,value):
    """Trap all attribute writes, and raise an error if the attribute
       wasn't defined in the __init__ method. Debugging code to catch all
       the identifier mismatches due to the fact that Pascal isn't case
       sensitive for identifier names.
    """
    if name in self.__dict__.keys():
      self.__dict__[name] = value
    else:
      raise AssertionError, "Setting attribute %s=%s for the first time."

  def __getstate__(self):
    """Can't pickle the __setattr__ function when saving state
    """
    d = self.__dict__.copy()
    del d['__setattr__']
    return d

  def __str__(self):
    return "[%s] Offset:%4.2f,%4.2f DomeAz:%3.0f Shutter:%s Freeze:%s LastMod:%d" % (self.action,
                                                                                self.OffsetRA,
                                                                                self.OffsetDec,
                                                                                self.DomeAzi,
                                                                                self.Shutter,
                                                                                self.Freeze,
                                                                                self.LastMod)


class Candidate:
  """A candidate supernova detection to be recorded in the database.
  
     Used to store results from an automated supernova search run on
     one image, passed from Vista. Probably not useful any more.
  """
  def __init__(self, X=0.0, Y=0.0, Q=0.0):
    self.X = X         #X coord on image
    self.Y = Y         #Y coord on image
    self.Q = Q         #Quality factor for the detection
    if CLASSDEBUG:
      self.__setattr__ = self.debug

  def debug(self,name,value):
    """Trap all attribute writes, and raise an error if the attribute
       wasn't defined in the __init__ method. Debugging code to catch all
       the identifier mismatches due to the fact that Pascal isn't case
       sensitive for identifier names.
    """
    if name in self.__dict__.keys():
      self.__dict__[name] = value
    else:
      raise AssertionError, "Setting attribute %s=%s for the first time."

  def __getstate__(self):
    """Can't pickle the __setattr__ function when saving state
    """
    d = self.__dict__.copy()
    del d['__setattr__']
    return d


class SNresult(Position):
  """Complete results from an automated supernova search run on
     one image, passed from Vista.
     
     All teljoy does with these results is store them into the sn.snlog
     table. Probably not useful any more.
  """
  def __init__(self, ra=None, dec=None, epoch=2000.0, objid=''):
    self.Seq = 0
    self.Name = ''
    self.Exptime = 0.0
    self.FiltNum = 0
    self.FiltName = ''
    self.ObjRAs = ''
    self.ObjDecs = ''
    self.RAtrack = 0.0
    self.DECtrack = 0.0
    self.XYpos_X, self.XYpos_Y = 0, 0
    self.ObsType = ''
    self.Filename = ''
    self.Comment = ''
    self.X_Disp = 0.0
    self.Y_Disp = 0.0
    self.Sky = 0.0
    self.Sky_Sigma = 0.0
    self.X_Sigma = 0.0
    self.Y_Sigma = 0.0
    self.Candidates = []
    Position.__init__(self, ra=ra, dec=dec, epoch=epoch, objid=objid)


class Galaxy(correct.CalcPosition):
  """Position subclass used to store data read from the RC3 or ESO-Upsalla
     galaxy catalogue tables. Extra attributes for galaxy data.
     
     Useful for looking up targets from the galaxy catalogues in the database
     from the command line, probably not much else.
  """
  def __init__(self, ra=None, dec=None, epoch=2000.0, objid=''):
    self.Name = ''           #Full name of galaxy (arbitrary string)
    self.RA2000s = ''        #J2000 coordinates as sexagesimal string
    self.DEC2000s = ''
    self.RA1950s = ''        #B1950 coordinates as sexagesimal string
    self.DEC1950s = ''
    self.PGC = 0             #Galaxy ID number in RC3 catalogue
    self.Hubble_T = 0.0      #Galaxy Hubble Type code (0 for elliptical, etc)
    self.R25 = 0.0           #Galaxy radius, in arcminutes
    self.Bmag = 0.0          #B magnitude
    self.V3K = 0.0           #Galaxy redshift, corrected to the local microwave background reference frame
    self.numfound = 0        #Number of targets found that match the ID given. If >1, you may have the wrong object
    correct.CalcPosition.__init__(self, ra=ra, dec=dec, epoch=epoch, objid=objid)


def IsTarget(oid, db=None):
  """Returns True if the specified object ID is in sn.targets (it's a valid Supernova Search
     target object). Probably not useful any more.
  """
  if not SQLActive:
    logger.error("sqlint.IsTarget: No SQL connection active, can't read sn.targets.")
    return False
  else:
    if db is None:
      db = gdb
    curs = db.cursor()
  qstr = "select ObjID from sn.targets where ObjID='%s' or altID='%s'" % (oid, oid)
  try:
    curs.execute(qstr)
  except dblib.Error as error:
    logger.error("sqlint.IsTarget: sn.targets query error '%s'" % error)
    return False
  if curs.rowcount:
    return True
  else:
    return False


def GetGalaxy(gid, ObjDec=None, db=None):
  """Given an ID string and an optional rough declination to narrow down the right galaxy, 
     return a Galaxy object.
     
     This function is deprecated, and should only be used for old object ID's from the
     original ESO-Uppsala catalog, which were based on the RA (B1950) coordinate string.
     An optional approximate Dec can be provided as an extra argument, which allows the
     correct galaxy to be returned from the (larger, more accurate) RC3 catalogue, where
     many galaxies can have the same RA coordinate string.
     
     For general cases (not supernova search target lookups) use GetRC3ByName.
     
     Probably not useful any more.
  """
  logger.debug("sqlint.GetGalaxy: Getting galaxy '%s':" % gid)
  if not SQLActive:
    logger.error("sqlint.GetGalaxy: No SQL connection active")
    return None
  else:  
    if db is None:
      db = gdb
    curs = db.cursor()
  gid = gid.upper().strip()
  ids = gid[2:]
  gal = Galaxy()
  if gid.startswith('N'):
    ids = ''
    for c in gid:
      if c.isdigit():
        ids += c
    qstr2 = 'Name regexp "NGC +'+ids+'$"'
  elif gid.startswith('P'):
    ids = ''
    for c in gid:
      if c.isdigit():
        ids += c
    qstr2 = 'PGC="'+ids+'"'
  elif gid.startswith('I'):
    ids = ''
    for c in gid:
      if c.isdigit():
        ids += c
    qstr2 = 'Name like "IC %'+ids+'"'
  elif gid.startswith('R') and (len(gid)==7):
    qstr2 = "RA1950 between lpad('" + ids + "'-1.0,8,'0') and lpad('" + ids + "'+1.0,8,'0')"
    if ObjDec:
      qstr2 = qstr2 + ( " and ( DEC1950 between concat('-',lpad('" +
                        sexstring(abs(ObjDec),'',fixed=True) +
                        "'-60,6,'0')) and concat('-',lpad('" +
                        sexstring(abs(ObjDec),'',fixed=True) +
                        "'+60,6,'0')) )" )
  elif gid.startswith('J') and (len(gid)==7):
    qstr2 = "RA2000 between lpad('" + ids + "'-1.0,8,'0') and lpad('" + ids + "'+1.0,8,'0')"
    if ObjDec:
      qstr2 = qstr2 + ( " and ( DEC2000 between concat('-',lpad('" +
                        sexstring(abs(ObjDec),'',fixed=True) +
                        "'-60,6,'0')) and concat('-',lpad('" +
                        sexstring(abs(ObjDec),'',fixed=True) +
                        "'+60,6,'0')) )" )
  elif gid.startswith('E') and (len(gid)==7):
    qstr2 = "( RA1950 between lpad('" + ids + "'-2.5,8,'0') and lpad('" + ids + "'+2.5,8,'0') )"
    if ObjDec:
      qstr2 = qstr2 + ( " and ( DEC1950 between concat('-',lpad('" +
                        sexstring(abs(ObjDec),'',fixed=True) +
                        "'-60,6,'0')) and concat('-',lpad('" +
                        sexstring(abs(ObjDec),'',fixed=True) + 
                        "'+60,6,'0')) )" )
  elif gid.startswith('T') and (len(gid)==7):
    qstr2 = "( RA1950 between lpad('" + ids + "'-2.5,8,'0') and lpad('" + ids + "'+2.5,8,'0') )"
    if ObjDec:
      qstr2 = qstr2 + ( " and ( DEC1950 between concat('-',lpad('" +
                        sexstring(abs(ObjDec),'',fixed=True) +
                        "'-10000,6,'0')) and concat('-',lpad('" +
                        sexstring(abs(ObjDec),'',fixed=True) +
                        "'+10000,6,'0')) )" )
  else:
    qstr2 = "Name='" + gid + "' or PGC='" + gid + "'"

  qstr = 'select RA2000,DEC2000,RA1950,DEC1950,Name,PGC,Hubble_T,R25,BT,Bmag,V3K from sn.rc3 where '
  logger.debug("sqlint.GetGalaxy: Query='%s'" % (qstr+qstr2))

  try:
    curs.execute(qstr+qstr2)
  except dblib.Error as error:
    logger.error("sqlint.GetGalaxy: sn.rc3 query error: '%s'" % error)
    return None

  rows = curs.fetchall()
  gal.numfound = curs.rowcount
  if rows:
    row = rows[0]
    gal.RA2000s = row[0]
    RA2000 = stringsex(gal.RA2000s, compressed=True)
    gal.DEC2000s = row[1]
    DEC2000 = stringsex(gal.DEC2000s, compressed=True)
    gal.RA1950s = row[2]
    RA1950 = stringsex(gal.RA1950s, compressed=True)
    gal.DEC1950s = row[3]
    DEC1950 = stringsex(gal.DEC1950s, compressed=True)
    if (RA2000 is not None) and (DEC2000 is not None):
      gal.Ra = RA2000*15.0*3600.0
      gal.Dec = DEC2000*3600.0
      gal.Epoch = 2000.0
    elif (RA1950 is not None) and (DEC1950 is not None):
      gal.Ra = RA1950*15.0*3600.0
      gal.Dec = DEC1950*3600.0
      gal.Epoch = 1950.0
    else:
      gal.Ra = 0.0
      gal.Dec = 0.0

    gal.Name = row[4]
    gal.PGC = int(row[5])
    gal.Hubble_T = float(row[6])
    gal.R25 = float(row[7])
    BT = float(row[8])
    Bmag = float(row[9])
    if BT>0:
      gal.Bmag = BT
    else:
      gal.Bmag = Bmag
    gal.V3K = float(row[10])
    gal.update()
    return gal
  else:
    ids = fixup(gid)
    if ids <> '':   #it was in fixups, and 'ids' is the PGC}
      return GetGalaxy(ids, ObjDec, db=db)
    else:   #It wasn't in the fixup list, check in esogals}
      qstr = ( "select RA1950,DEC1950d,Name,PGC," +
               "Hubble_T,BMag,RadVel from sn.esogals where " +
               "RA1950='" + gid[1:7] + "'" )
    try:
      curs.execute(qstr)
    except dblib.Error as error:
      logger.error("sqlint.GetGalaxy: sn.esogals query error: '%s'" % error)
      return None

    rows  =  curs.fetchall()
    gal.numfound = curs.rowcount
    if rows:
      row = rows[0]
      gal.RA1950s = row[0]
      RA1950 = stringsex(gal.RA1950s, compressed=True)
      DEC1950 = float(row[1])
      gal.DEC1950s = sexstring(DEC1950)
      gal.Ra = RA1950*15.0*3600.0
      gal.Dec = DEC1950*3600.0
      gal.Epoch = 1950.0
      gal.Name = row[2]
      gal.PGC = int(row[3])
      gal.Hubble_T = float(row[4])
      gal.Bmag = float(row[5])
      gal.V3K = float(row[6])
      gal.R25 = 0
      if gal.numfound == 1:
        logger.debug('sqlint.GetGalaxy: PGC=%d' % gal.PGC)
      elif gal.numfound > 1:
        logger.warn('sqlint.GetGalaxy: Warning - Duplicate match for %s' % ids)
      gal.update()
      return gal
    else:
      return None


def GetRC3ByName(gid, num=0, db=None):
  """Given an object ID string and an optional object index, search the RC3 catalog
     for names that match. If there's more than one match, return match number 'num'
     (defaults to the first match).
     
     Probably useful if you want to jump to galaxies by name (from the command line or
     external command via teljoy.tjbox), but not very often.
  """
  if not SQLActive:
    logger.error("sqlint.GetGalaxy: No SQL connection active")
    return None
  else:
    if db is None:
      db = gdb
    curs = db.cursor()
  logger.debug("sqlint.GetRC3ByName: Searching for galaxy '" + gid + "' in RC3 catalog.")
  gids = gid.upper().strip()
  gal = Galaxy()
  i = 0
  num1 = ''
  num2 = ''
  num3 = ''
  while (i < len(gids)) and not gids[i].isdigit():
    i += 1
  while (i < len(gids)) and gids[i].isdigit():
    num1 += gids[i]
    i += 1
  while (i < len(gids)) and not gids[i].isdigit():
    i += 1
  while (i < len(gids)) and gids[i].isdigit():
    num2 += gids[i]
    i += 1
  while (i < len(gids)) and not gids[i].isdigit():
    i += 1
  while (i < len(gids)) and gids[i].isdigit():
    num3 += gids[i]
    i += 1

  if gids.startswith('N'):
    qstr2 = 'Name regexp "NGC +0*' + num1.lstrip('0') + '$" '
  elif gids.startswith('P'):
    qstr2 = 'PGC="' + num1 + '"'
  elif gids.startswith('IR'):
    qstr2 = 'desig regexp "IRAS' + num1 + '-' + num2 + '$" '
  elif gids.startswith('I'):
    qstr2 = 'Name regexp "IC +0*' + num1.lstrip('0') + '$" '
  elif gids.startswith('A'):
    qstr2 = 'Name regexp "A *' + gids[1:] + '" '
  elif gids.startswith('U'):
    qstr2 = 'altname regexp "UGC +0*' + num1.lstrip('0') + '$" '
  elif gids.startswith('E'):
    qstr2 = 'altname regexp "ESO +0*' + num1.lstrip('0') + '- *0*' + num2.lstrip('0') + '$" '
  elif gids.startswith('M'):
    qstr2 = 'altname regexp "MCG +-?0*' + num1.lstrip('0') + '- *0*' + num2.lstrip('0') + '- *0*' + num3.lstrip('0') + '$" '
    #The above line can find duplicates becasue it doesn't distinguish
    #  between entries with a leading minus sign and no leading minus sign
  else:
    qstr2 = 'Name regexp "' + gids + '$" or desig regexp "' + gids + '$" '

  qstr = ( 'select RA2000,DEC2000,RA1950,DEC1950,Name,PGC,Hubble_T,R25,BT,'+
             'Bmag,V3K from sn.rc3 where ' + qstr2 )
  try:
    curs.execute(qstr)
  except dblib.Error as error:
    logger.error("sqlint.GetRC3byName: sn.rc3 query error: '%s'" % error)
    return None

  rows = curs.fetchall()
  gal.numfound = curs.rowcount
  if rows:
    if num < len(rows):
      row = rows[num]
    else:
      row = rows[0]
    gal.RA2000s = row[0]
    RA2000 = stringsex(gal.RA2000s, compressed=True)
    gal.DEC2000s = row[1]
    DEC2000 = stringsex(gal.DEC2000s, compressed=True)
    gal.RA1950s = row[2]
    RA1950 = stringsex(gal.RA1950s, compressed=True)
    gal.DEC1950s = row[3]
    DEC1950 = stringsex(gal.DEC1950s, compressed=True)
    if (RA2000 is not None) and (DEC2000 is not None):
      gal.Ra = RA2000*15.0*3600.0
      gal.Dec = DEC2000*3600.0
      gal.Epoch = 2000.0
    elif (RA1950 is not None) and (DEC1950 is not None):
      gal.Ra = RA1950*15.0*3600.0
      gal.Dec = DEC1950*3600.0
      gal.Epoch = 1950.0
    else:
      gal.Ra = 0.0
      gal.Dec = 0.0

    gal.Name = row[4]
    gal.PGC = int(row[5])
    gal.Hubble_T = float(row[6])
    gal.R25 = float(row[7])
    BT = float(row[8])
    Bmag = float(row[9])
    if BT>0:
      gal.Bmag = BT
    else:
      gal.Bmag = Bmag
    gal.V3K = float(row[10])
    gal.update()
    return gal
  else:
    return None


def fixup(gid, db=None):
  """Fixes cases where recorded object ID's are broken, for ugly 
     historical reasons. Takes an object ID and returns the PGC number
     (unique ID in the RC3 catalogue) if the object is in the sn.fixup
     table.
     
     Probably not useful any more.
  """
  if not SQLActive:
    logger.error("sqlint.fixup: No SQL connection active")
    return ''
  else:
    if db is None:
      db = gdb
    curs = db.cursor()
  qstr = "select PGC from sn.fixup where ObjID='" + gid + "'"
  curs.execute(qstr)
  try:
    curs.execute(qstr)
  except dblib.Error as error:
    logger.error("sqlint.fixup: sn.fixup query error: '%s'" % error)
    return ''
  rows = curs.fetchall()
  if rows:
    fixup = rows[0][0]
    return fixup
  else:
    return ''
   

def process(field, s):
  """Given a field name and a string, convert and return the string as a 
     float. If there's an error, use the logger object to display it,
     using the given field name.
  """
  try:
    val = float(s)
  except ValueError:
    logger.error('sqlint.process: Error processing %s=%s' % (field,s))
    val = 0.0
  return val
  

def sprocess(s):
  """Silently process the given string into a float. Return the 
     value and an validity boolean (True if the value is valid)
     as a tuple. If there was an error, the value returned is 0.0.
  """
  try:
    val = float(s)
  except (ValueError,TypeError):
    return 0.0, False
  return val, True
  

def ReadSQLCurrent(Here, db=None):
  """Read the current position data and other state information
     into an correct.CalcPosition object and an sqlint.Info object. 
     Return (CurrentInfo, HA, LastMod), and modify 'Here' in place.
     
     Used by Teljoy to read the last saved telescope position on
     startup (RA, DEC, LST) and use that as a starting position.
  """
  if not SQLActive:
    logger.error("sqlint.ReadSQLCurrent: No SQL connection active")
    return None, 0, 0
  else:
    if db is None:
      db = gdb
    curs = db.cursor()
  try:
    curs.execute('select name,ObjRA,ObjDec,ObjEpoch,RawRA,RawDec,'+
                 'RawHourAngle,Alt,Azi,LST,UTDec,posviolate,moving,'+
                 'EastOfPier,NonSidOn,DomeInUse,ShutterInUse,'+
                 'ShutterOpen,DomeTracking,Frozen,'+
                 'RA_GuideAcc,DEC_GuideAcc,LastError,'+
                 'unix_timestamp(now())-unix_timestamp(LastMod) '+
                 'from teljoy.ncurrent')
  except dblib.Error as error:
    logger.error("sqlint.ReadSQLCurrent: teljoy.ncurrent query error: '%s'" % error)
    return None, 0, 0

  rows = curs.fetchall()
  if not rows:
    logger.error('sqlint.ReadSQLCurrent: No rows returned from teljoy.ncurrent')
    return None, 0, 0
  else:
    row = rows[0]

  CurrentInfo = Info()
  Here.ObjID = row[0]    #The row is an array of strings, one per value
  Here.Ra, valid = sprocess(row[1])
  if valid:
    Here.Ra = Here.Ra*15*3600  #convert from hours to arcsec}
  Here.Dec, valid = sprocess(row[2])
  if valid:
    Here.Dec = Here.Dec*3600  #convert from hours to arcsec}
  Here.Epoch, valid = sprocess(row[3])
  Here.RaC = process('RawRA',row[4])
  Here.RaC = Here.RaC*15*3600
  Here.DecC = process('RawDec',row[5])
  Here.DecC = Here.DecC*3600
  HA = process('RawHourAngle',row[6])
  Here.Alt = process('Alt',row[7])
  Here.Azi = process('Azi',row[8])
  Here.Time.update()   #Clear time record and make it 'now' in UTC
  Here.Time.LST = process('LST',row[9])
  UTdec = process('UTdec',row[10])
  h = int(UTdec)
  m = int(60*(UTdec-h))
  s = int(60*(60*(UTdec-h)-m))
  us = int(1e6*3600*(UTdec - h - m/60.0 - s/3600.0))
  Here.Time.UT = Here.Time.UT.replace(hour=h,minute=m,second=s,microsecond=us)

  CurrentInfo.posviolate = bool(process('posviolate',row[11]))
  CurrentInfo.moving = bool(process('moving',row[12]))
  CurrentInfo.EastOfPier = bool(process('EastOfPier',row[13]))
  CurrentInfo.NonSidOn = bool(process('NonSidOn',row[14]))
  CurrentInfo.DomeInUse = bool(process('DomeInUse',row[15]))
  CurrentInfo.ShutterInUse = bool(process('ShutterInUse',row[16]))
  CurrentInfo.ShutterOpen = bool(process('ShutterOpen',row[17]))
  CurrentInfo.DomeTracking = bool(process('DomeTracking',row[18]))
  CurrentInfo.Frozen = bool(process('Frozen',row[19]))
  CurrentInfo.RA_GuideAcc = process('RA_GuideAcc',row[20])
  CurrentInfo.DEC_GuideAcc = process('DEC_GuideAcc',row[21])
  CurrentInfo.LastError = row[22]
  LastMod = process('LastMod',row[23])
  return CurrentInfo, HA, LastMod


def UpdateSQLCurrent(Here, CurrentInfo, db=None):
  """The reverse of the above function - take a correct.CalcPosition
     object and sqlint.Info object containing position and state information,
     and write them to the database.
     
     Used to let external clients (Prosp, etc) access internal teljoy state
     until I replace this with an RPC call. 
     
     Also used by Teljoy to recover the actual telescope position on startup,
     from the last saved RA, DEC, and LST.
  """
  if not SQLActive:
    logger.error("sqlint.UpdateSQLCurrent: No SQL connection active")
    return
  else:
    if db is None:
      db = gdb
    curs = db.cursor()
  if not CurrentInfo.posviolate:  #if telescope position is valid}
    qstr1 = "update teljoy.ncurrent set name='%s', ObjRA='%g', ObjDec='%g', ObjEpoch='%g', " % (
                    Here.ObjID,
                    Here.Ra/(15.0*3600),
                    Here.Dec/3600.0,
                    Here.Epoch )
  else:
    qstr1 = "update teljoy.ncurrent set name='%s', ObjRA=NULL, ObjDec=NULL, ObjEpoch=NULL, " % Here.ObjID

  tmpd = Here.RaC/54000.0 - Here.Time.LST
  if tmpd < -12:
    tmpd += 24
  if tmpd > 12:
    tmpd -= 24

  qstr2 = "RawRA='%g', RawDec='%g', RawHourAngle='%g', Alt='%g', Azi='%g', " % (
             Here.RaC/(15.0*3600),
             Here.DecC/3600.0,
             tmpd,
             Here.Alt,
             Here.Azi)
  qstr2 += "LST='%g', UTDec='%g', posviolate='%d', moving='%d', EastOfPier='%d', NonSidOn='%d', " % (
             Here.Time.LST,
             Here.Time.UT.hour + Here.Time.UT.minute/60.0 + Here.Time.UT.second/3600.0 + Here.Time.UT.microsecond/3.6e9,
             int(CurrentInfo.posviolate),
             int(CurrentInfo.moving),
             int(CurrentInfo.EastOfPier),
             int(CurrentInfo.NonSidOn) )
  qstr3 = "DomeInUse='%d', ShutterInUse='%d', ShutterOpen='%d', DomeTracking='%d', Frozen='%d', " % (
             int(CurrentInfo.DomeInUse),
             int(CurrentInfo.ShutterInUse),
             int(CurrentInfo.ShutterOpen),
             int(CurrentInfo.DomeTracking),
             int(CurrentInfo.Frozen) )
  qstr4 = "RA_GuideAcc='%g', DEC_GuideAcc='%g', LastError=%s " % (
             CurrentInfo.RA_GuideAcc,
             CurrentInfo.DEC_GuideAcc,
             db.escape(CurrentInfo.LastError) )
  querystr = qstr1 + qstr2 + qstr3 + qstr4
  try:
    curs.execute(querystr)
  except dblib.Error as error:
    logger.error("sqlint.UpdateSQLCurrent: teljoy.ncurrent query error: '%s'" % error)
    return None


def WriteLog(cur, db=None):
  """Take the results of a supernova search run on an image (passed from Vista), and
     write it to the sn.snlog table. The argument 'cur' is an sqlint.SNresult object.
     
     Legacy code, unlikely to be used.
  """
  if not SQLActive:
    logger.error("sqlint.WriteLog: No SQL connection active")
    return
  else:
    if db is None:
      db = gdb
    curs = db.cursor()
  qstr1 = ( "insert into sn.snlog ( seq,name,exptime,filtnum,filtname,ObjID,ObjRA,ObjDec," +
            "Epoch,UT,JulDay,Alt,Azi,RAtrack,DECtrack,XYPos_X,XYPos_Y," +
            "ObsType,Filename,Comment,X_Disp,Y_Disp,Sky,Sky_Sigma," +
            "X_Sigma,Y_Sigma,NumCandidates,Candidates )  " )
  qstr2 = " VALUES('%d', %s, '%6g', '%d', '%s', '%s', '%15g', '%15g', '%6g', " % (
              cur.seq,
              db.escape(cur.name),
              cur.Exptime,
              cur.FiltNum,
              cur.FiltName,
              cur.ObjID,
              cur.Ra/3600.0/15.0,
              cur.Dec/3600.0,
              cur.Epoch )
  qstr3 = "'%d-%d-%d %d:%d:%d', '%15g', '%6g', '%6g', '%10g', '%10g', " % (
              cur.Time.UT.year,
              cur.Time.UT.month,
              cur.Time.UT.day,
              cur.Time.UT.hour, cur.Time.UT.minute, cur.Time.UT.second,
              cur.Time.JD,
              cur.Alt,
              cur.Azi,
              cur.RAtrack,
              cur.DECtrack )
  qstr4 = "'%d', '%d', '%s', '%s', " % (
              cur.XYpos_X,
              cur.XYpos_Y,
              cur.ObsType,
              cur.Filename )
  qstr5 = "%s, " % db.escape(cur.comment)
  qstr6 = "'%7g', '%7g', '%8g', '%7g', '%5g', '%5g', '%d', " % (
              cur.X_Disp,
              cur.Y_Disp,
              cur.Sky,
              cur.Sky_Sigma,
              cur.X_Sigma,
              cur.Y_Sigma,
              len(cur.Candidates) )
  if cur.Candidates:
    qstr7 = "'"
    for c in cur.Candidates:
      qstr7 += "%7g %7g %7g " % (c.X, c.Y, c.Q)
    qstr7 += "' ) "
  else:
    qstr7 = "NULL ) "

  querystr = qstr1 + qstr2 + qstr3 + qstr4 + qstr5 + qstr6 + qstr7
  try:
    curs.execute(querystr)
  except dblib.Error as error:
    logger.error("sqlint.WriteLog: sn.snlog query error: '%s'" % error)
    return None


def ExistsTJbox(db=None):
  """Returns true if a record is waiting in the teljoy.tjbox table containing
     an external command to execute.
     
     Used to handle external commands from Prosp, required for automatic observing
     until I replace this with an RPC call.
  """
  if not SQLActive:
    logger.error("sqlint.ExistsTJbox: No SQL connection active")
    return
  else:
    if db is None:
      db = gdb
    curs = db.cursor()
  querystr = "select ObjID from teljoy.tjbox"
  try:
    curs.execute(querystr)
  except dblib.Error as error:
    logger.error("sqlint.ExistsTJbox: teljoy.tjbox query error: '%s'" % error)
    return None
  if curs.rowcount:
    return True
  else:
    return False


def ClearTJbox(db=None):
  """Delete the contents of the teljoy.tjbox table, indicating to the 
     external process that the command has been executed.

     Used to handle external commands from Prosp, required for automatic observing
     until I replace this with an RPC call.
  """
  if not SQLActive:
    logger.error("sqlint.ClearTJbox: No SQL connection active")
    return
  else:
    if db is None:
      db = gdb
    curs = db.cursor()
  querystr = "delete from teljoy.tjbox"
  try:
    curs.execute(querystr)
  except dblib.Error as error:
    logger.error("sqlint.ClearTJbox: teljoy.tjbox query error: '%s'" % error)
    return None


class _ValidClass:
  """Store validity booleans for each table column, so we can
     check that each of the possible commands is accompanied by
     the arguments needed for that command.

     Used to handle external commands from Prosp, required for automatic observing
     until I replace this with an RPC call.
  """
  def __init__(self):
    self.ObjID = False
    self.ObjRA = False
    self.ObjDEC = False
    self.ObjEpoch = False
    self.RAtrack = False
    self.DECtrack = False
    self.Alt = False
    self.Azi = False
    self.OffsetRA = False
    self.OffsetDEC = False
    self.DomeAzi = False
    self.shutter = False
    self.freeze = False
    if CLASSDEBUG:
      self.__setattr__ = self.debug

  def debug(self,name,value):
    """Trap all attribute writes, and raise an error if the attribute
       wasn't defined in the __init__ method. Debugging code to catch all
       the identifier mismatches due to the fact that Pascal isn't case
       sensitive for identifier names.
    """
    if name in self.__dict__.keys():
      self.__dict__[name] = value
    else:
      raise AssertionError, "Setting attribute %s=%s for the first time."


def ReadTJbox(db=None):
  """Read the new row from the teljoy.tjbox table into an object record
     returns (Pos, other) where Pos is a correct.CalcPosition object and 'other'
     is an sqlint.TJboxrec object.

     Used to handle external commands from Prosp, required for automatic observing
     until I replace this with an RPC call.
  """
  valid = _ValidClass()
  Pos = correct.CalcPosition()
  other = TJboxrec()
  if not SQLActive:
    logger.error("sqlint.ReadTJbox: No SQL connection active")
    return None, None
  else:
    if db is None:
      db = gdb
    curs = db.cursor()

  querystr = ( "select action,ObjID,ObjRA,ObjDec,ObjEpoch,RAtrack,DECtrack," +
               "Alt,Azi,OffsetRA,OffsetDec,DomeAzi,shutter,freeze, " +
               "unix_timestamp(now())-unix_timestamp(lastmod) " +
               "from teljoy.tjbox" )
  try:
    curs.execute(querystr)
  except dblib.Error as error:
    logger.error("sqlint.ReadTJbox: teljoy.tjbox query error: '%s'" % error)
    return None, None

  rows = curs.fetchall()
  if not rows:
    logger.info("sqlint.ReadTJbox: No rows returned from teljoy.tjbox")
    return None, None
  else:
    row = rows[0]

  other.action = row[0].strip().lower()
  Pos.ObjID = row[1] 
  if Pos.ObjID:         #StrPas converts from null-terminated to a Pascal string}
    valid.ObjID = True
  Pos.Ra = stringsex(row[2])
  if Pos.Ra is not None:
    Pos.Ra = Pos.Ra*15*3600
    valid.ObjRa = True
  else:
    Pos.Ra = 0.0
  Pos.Dec = stringsex(row[3])
  if Pos.Dec is not None:
    Pos.Dec = Pos.Dec*3600
    valid.ObjDEC = True
  else:
    Pos.Dec = 0.0
  Pos.Epoch, valid.ObjEpoch = sprocess(row[4])
  Pos.TraRA, valid.RAtrack = sprocess(row[5])
  Pos.TraRA = Pos.TraRA*3600.0/15       #Convert from sec of time per hour to arcsec per second
  if abs(Pos.TraRA) > 1.0:
    valid.RAtrack = False    #Fail if trackrate > 1 arcsec/second
  Pos.TraDEC, valid.DECtrack = sprocess(row[6])
  Pos.TraDEC = Pos.TraDEC*3600.0       #Convert from sec of time per hour to arcsec per second
  if abs(Pos.TraDEC) > 1.0:
    valid.DECtrack = False    #Fail if trackrate > 1 arcsec/second
  Pos.Alt, valid.Alt = sprocess(row[7])
  Pos.Azi, valid.Azi = sprocess(row[8])

  other.OffsetRA, valid.OffsetRA = sprocess(row[9])
  other.OffsetDEC, valid.OffsetDEC = sprocess(row[10])
  other.DomeAzi, valid.DomeAzi = sprocess(row[11])
  tmpv, valid.shutter = sprocess(row[12])
  other.Shutter = bool(tmpv)
  tmpv, valid.freeze = sprocess(row[13])
  other.Freeze = bool(tmpv)
  other.LastMod, tmpb = sprocess(row[14])
  if not tmpb:
    other.LastMod = -1

  verr = False
  if other.action == 'jumpid':
    if not valid.ObjID:
      verr = True
  elif other.action == 'jumprd':
    if not (valid.ObjRA and valid.ObjDEC and valid.ObjEpoch):
      verr = True
  elif other.action == 'jumpaa':
    if not (valid.Alt and valid.Azi):
      verr = True
  elif other.action == 'nonsid':
    if not (valid.RAtrack and valid.DECtrack):
      verr = True
  elif other.action == 'offset':
    if not (valid.OffsetRA and valid.OffsetDEC):
      verr = True
  elif other.action == 'dome':
    if not valid.DomeAzi:
      verr = True
  elif other.action == 'shutter':
    if not valid.shutter:
      verr = True
  elif (other.action == 'freeze') or (other.action == 'freez'):
    if not valid.freeze:
      verr = True
  elif other.action == 'none':
    pass
  else:
    verr = True

  if verr:
    other.action = 'error'
  if other.action <> 'none':
    logger.debug("sqlint.ReadTJbox: Found box - %s, %s" % (other,Pos) )
  Pos.update()
  return Pos, other



def GetObject(name, db=None):
  """Given 'name', looks it up in teljoy.objects.
     returns a correct.CalcPosition object if found, None if not.
     
     If the given object ID is in teljoy.objects, return the object
     data in a CalcPosition object to use for a Jump. Used to handle
     external 'jump to object by name' commands, also useful on the
     command line.
  """
  if not SQLActive:
    logger.error("sqlint.GetObject: No SQL connection active")
    return None
  else:
    if db is None:
      db = gdb
    curs = db.cursor()
  querystr = ( "select ObjID,ObjRA,ObjDec,ObjEpoch,filtname,exptime," +
               "XYpos_X,XYpos_Y,type,comment from teljoy.objects where " +
               "ObjID='%s'" % name )
  try:
    curs.execute(querystr)
  except dblib.Error as error:
    logger.error("sqlint.GetObject: teljoy.objects query error: '%s'" % error)
    return None

  Pos = correct.CalcPosition()
  rows = curs.fetchall()
  if not rows:
    logger.error("sqlint.GetObject: no objects found in teljoy.objects")
    return None
  else:
    row = rows[0]

  Pos.ObjID = row[0]
  Pos.Ra = stringsex(row[1])
  if Pos.Ra is not None:
    Pos.Ra = Pos.Ra*15.0*3600.0
  else:
    Pos.Ra = 0.0
  Pos.Dec = stringsex(row[2])
  if Pos.Dec is not None:
    Pos.Dec = Pos.Dec*3600.0
  else:
    Pos.Dec = 0.0
  Pos.Epoch = process('Epoch',row[3])  #in years

  Pos.update()
  return Pos
  

def InitSQL():
  """Return a database connection object using the defined username, password, host, and database.
  """
  try:
    db = getdb(user=USER, password=PASSWORD, host=HOST)
  except dblib.Error as error:
    logger.error("sqlint.InitSQL: connect to SQL server failed: '%s'" % error)
    return None
  logger.debug("sqlint.InitSQL: Connected to SQL Server.")
  return db


#Create a default module-wide database connection object on startup, to be used if 
#the calling code doesn't pass its own database object
gdb = InitSQL()
SQLActive = (gdb is not None)

