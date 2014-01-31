
import MySQLdb
from MySQLdb.cursors import DictCursor

import os
import time

from teljoy import globals

PWFILE = '~mjuo/teljoy.dbpass'


USER = 'honcho'
if globals.SITE == 'NZ':
  HOST = 'localhost'
  try:
    PASSWORD = file(os.path.expanduser(PWFILE), 'r').read().strip()
  except IOError:
    print "Can't load MySQL database pasword file: %s" % PWFILE
    PASSWORD = ''
elif globals.SITE == 'PERTH':
  HOST = 'mysql'
  PASSWORD = ''
DATABASE = ''


class Object:

  def empty(self):
    self.ObjID = ''
    self.name = ''
    self.origid = ''
    self.ObjRA = ''
    self.ObjDec = ''
    self.ObjEpoch = 0
    self.filtnames = ''
    self.exptimes = 1
    self.filtname = ''
    self.exptime = 1
    self.subframes = 1
    self.sublist = [('', 0.0)]
    self.XYpos = (0,0)
    self.type = 'IMAGE'
    self.period = 0.0
    self.comment = ''
    self.LastObs = 0.0
    self.errors = ''

  def __init__(self, str='', curs=None):
    if not curs:
      curs = db.cursor()
    if str == '':
      self.empty()
    else:
      curs.execute("""select * from teljoy.objects where UPPER(ObjID)='""" + str.upper() + "'")
      
      if not curs.rowcount:
        self.empty()
        self.ObjID = str
        return
      else:
        c = curs.fetchallDict()[0]
      self.ObjID = c['ObjID'].strip()
      self.name = c['name']
#     self.name = c['name'].strip()
      self.origid = self.ObjID
      self.ObjRA = c['ObjRA'].strip()
      self.ObjDec = c['ObjDec'].strip()
      self.ObjEpoch = float(c['ObjEpoch'])
#     self.ObjEpoch = float(c['ObjEpoch'].strip())
      filtnames = c['filtnames'].strip()
      exptimes = c['exptimes'].strip()
      self.subframes, self.sublist = psl(filtnames, exptimes)
      self.XYpos = (int(c['XYpos_X']), int(c['XYpos_Y']))
      self.type = c['type'].strip()
      try:
        self.period = float(c['period'])
#       self.period = float(c['period'].strip())
      except TypeError:
        self.period = 0.0
      self.comment = c['comment'.strip()]
      try:
        self.LastObs = time.mktime(c['LastObs'.strip()].timetuple())
      except (TypeError, AttributeError):
        self.LastObs = 0
      if not self.ObjRA:
        self.ObjRA = ''
      if not self.ObjDec:
        self.ObjDec = ''
      if not self.type:
        self.type = ''
      if not self.comment:
        self.comment = ''
      self.errors = ''
      self.subframe(0)

  def subframe(self, n=0):
    """Change the exposure time and filter to the n'th pair in the subframes list
    """
    if (n > self.subframes) or (n > len(self.sublist) - 1):
      print "Invalid subframe number ", n, " in object ", self.ObjID
    else:
      self.filtname, self.exptime = self.sublist[n]

  def updatetime(self, curs=None):
    if not curs:
      curs = db.cursor()
    curs.execute("""update teljoy.objects set lastobs=NOW() where UPPER(ObjID)='""" + self.ObjID.upper() + "'")

  def display(self):
    print '%9s:%11s %11s (%6.1f)%8s%6.5g (%5d,%5d)%8s * %d' % (self.ObjID,
                                                               self.ObjRA,
                                                               self.ObjDec,
                                                               self.ObjEpoch,
                                                               self.filtname,
                                                               self.exptime,
                                                               self.XYpos[0], self.XYpos[1],
                                                               self.type,
                                                               self.subframes)

  def __repr__(self):
    return "Object[" + self.ObjID + "]"

  def __str__(self):
    return 'O[%9s:%11s %11s (%6.1f)%8s%6.5g (%5d,%5d)%8s * %d]' % (self.ObjID,
                                                                   self.ObjRA,
                                                                   self.ObjDec,
                                                                   self.ObjEpoch,
                                                                   self.filtname,
                                                                   self.exptime,
                                                                   self.XYpos[0], self.XYpos[1],
                                                                   self.type,
                                                                   self.subframes)
 

  def save(self, ask=1, force=0, curs=None):
    if not curs:
      curs = db.cursor()
    if self.ObjID == '':
      print "Empty ObjID, can't save object."
      return 0
    filtnames, exptimes = pls(self.sublist)
    if not curs.execute("""select * from teljoy.objects where UPPER(ObjID)='""" + self.ObjID.upper() + "'"):
      curs.execute("""insert into teljoy.objects (ObjID,name,ObjRA,ObjDec,ObjEpoch,filtnames,""" +
                   "exptimes," +
                   "XYpos_X,XYpos_Y,type,period,comment) values (" +
                   "'" + self.ObjID.strip() + "', " +
                   "'" + self.name.strip() + "', " +
                   "'" + self.ObjRA.strip() + "', " +
                   "'" + self.ObjDec.strip() + "', " +
                   `self.ObjEpoch` + ", " +
                   "'" + filtnames.strip() + "', " +
                   "'" + exptimes.strip() + "', " +
                   `self.XYpos[0]` + ", " +
                   `self.XYpos[1]` + ", " +
                   "'" + self.type.strip() + "', " +
                   `self.period` + ", " +
                   "'" + self.comment.strip() + "') ")
      if self.origid.upper() != self.ObjID.upper():
        if self.origid != '':
          curs.execute("""delete from teljoy.objects where UPPER(ObjID)='""" + self.origid.upper() + "'")
    else:
      if ask:
        print "Entry " + self.ObjID + " already exists, do you want to replace it?"
        ans = raw_input("y/n (default n): ").strip().lower()[:1]
        if ans != 'y':
          print "Object " + self.ObjID + " not overwritten."
          return 0
      else:
        if not force:
          print "Object " + self.ObjID + " not overwritten."
          return 0
      curs.execute("""update teljoy.objects set """ +
                   "ObjID='" + self.ObjID + "', " +
                   "name='" + self.name + "', " +
                   "ObjRA='" + self.ObjRA + "', " +
                   "ObjDec='" + self.ObjDec + "', " +
                   "ObjEpoch=" + `self.ObjEpoch` + ", " +
                   "filtnames='" + filtnames + "', " +
                   "exptimes='" + exptimes + "', " +
                   "XYpos_X=" + `self.XYpos[0]`+", " +
                   "XYpos_Y=" + `self.XYpos[1]`+", " +
                   "type='" + self.type + "', " +
                   "period=" + `self.period` + ", " +
                   "comment='" + self.comment + "' " +
                   "where UPPER(ObjID)='" + self.ObjID.upper() + "'")

    db.commit()
    print "Object " + self.ObjID + " saved."
    return 1

  def delete(self, ask=1, curs=None):
    if not curs:
      curs = db.cursor()
    if self.ObjID == '':
      print "Empty ObjID, can't delete object."
      return 0
    curs.execute("""select * from teljoy.objects where UPPER(ObjID)='""" + self.ObjID.upper() + "'")
    if not curs.rowcount:
      print "Object not found in database."
      return 0
    if ask:
      print "Entry " + self.ObjID + " already exists, do you want to replace it?"
      ans = raw_input("y/n (default n): ").strip().lower()[:1]
      if ans != 'y':
        print "Object " + self.ObjID + " not deleted."
        return 0
    curs.execute("""delete from teljoy.objects where UPPER(ObjID)='""" + self.ObjID.upper() + "'")
    db.commit()
    print "Object " + self.ObjID + " deleted from database."
    return 1


def ZapPeriods(period=0, type='', curs=None):
  """Take an object type and set the desired observing interval for all objects of that
     type to the specified period, in days.
  """
  if not curs:
    curs = db.cursor()
  if type:
    curs.execute("""update teljoy.objects set period=""" + `period` + " where type='" + type + "' and ObjID not like 'P%'")
  db.commit()
   

def psl(filtnames='I', exptimes='1.0'):
  """Given filtnames and exptimes, return subframes and sublist.
  """
  filtlist = filtnames.replace(',', ' ').split()
  exptlist = exptimes.replace(',', ' ').split()
  if not filtlist:
    filtlist = ['I']
  if not exptlist:
    exptlist = [10.0]
  sublist = []
  if len(exptlist) == 1:
    subframes = len(filtlist)
    for fn in filtlist:
      sublist.append( (fn, float(exptlist[0])) )
  else:
    if len(filtlist) == 1:
      subframes = len(exptlist)
      for et in exptlist:
        sublist.append( (filtlist[0], float(et)) )
    else:
      if len(filtlist) == len(exptlist):
        subframes = len(exptlist)
        for i in range(len(filtlist)):
          sublist.append( (filtlist[i], float(exptlist[i])) )
      else:
        print "No match between number of filts and number of exptimes in object"
        subframes = 1
        sublist.append( (filtlist[0], float(exptlist[0])) )
  return subframes, sublist


def pls(sublist):
  """Given a subframe list of (filter,exptime) pairs, return
     filtnames and exptimes strings for putting in the database.
  """
  filtnames = ''
  exptimes = ''
  for p in sublist:
    filtnames += p[0] + ' '
    exptimes += `p[1]` + ' '
  return filtnames.strip(), exptimes.strip()


def allobjects(curs=None):
  """Return a list of all objects in the Object database.
  """
  if not curs:
    curs = db.cursor()
  curs.execute("""select ObjID from teljoy.objects""")
  c = curs.fetchallDict()
  olist = []
  for row in c:
    olist.append(Object(row['ObjID']))
  return olist


def filtobjects(curs=None,
                id=None,                          # ObjID wildcard
                sortby=None,                      # Field to sort list by
                ramin=None, ramax=None,           # RA limits (hours)
                decmin=None, decmax=None,         # Dec limits (degrees)
                lodmin=None, lodmax=None,         # last observed limits (days ago)
                type=None,                        # type (no wildcard, ALL for all types)
                page=1, pagesize=9999,            # page number, and number of objects/page
                count=0):                         # if count, return total number, not list
  "Return a list of objects filtered by parameter"
  if not curs:
    curs = db.cursor()

  #Update table with floating point RA and Dec values for everything in teljoy.objects
  curs.execute("""select teljoy.objects.ObjID as ObjID, ObjRA, ObjDec from teljoy.objects left join teljoy.objtemp """ +
               "on (teljoy.objects.ObjID = teljoy.objtemp.ObjID) " +
               "where (teljoy.objtemp.ObjID is NULL) or (teljoy.objects.LastMod > teljoy.objtemp.LastMod) ")
  if curs.rowcount:
    ulist = curs.fetchallDict()
    for c in ulist:        
      fObjRA = globals.stringsex(c['ObjRA'])
      fObjDec = globals.stringsex(c['ObjDec'])
      curs.execute('''replace into teljoy.objtemp set ObjID=""''' + c['ObjID'] + '", '
                   'fObjRA=' + `fObjRA` + ', fObjDec=' + `fObjDec` + ' ')

  db.commit()

  if ramin:
    sramin = str(ramin)
  else:
    sramin = "0.0"

  if ramax:
    sramax = str(ramax)
  else:
    sramax = "24.0"

  if decmin:
    sdecmin = str(decmin)
  else:
    sdecmin = "-90.0"

  if decmax:
    sdecmax = str(decmax)
  else:
    sdecmax = "90.0"

  if lodmin:
    slodmin = str(lodmin)
  else:
    slodmin = "0.0"

  if lodmax:
    slodmax = str(lodmax)
  else:
    slodmax = "99999999.0"

  if (not id) or (id == "NONE"):
    sid = "%"
  else:
    sid = id.replace(r'%', r'\%')
    sid = sid.replace(r'_', r'\_')
    sid = sid.replace(r'*', r'%')
    sid = sid.replace(r'?', r'_')

  if (not type) or (type == "NONE"):
    stype = "%"
  else:
    stype = type.strip().upper()
    if stype == 'ALL':
      stype = "%"

  if (not sortby) or (sortby == "NONE"):
    sortby = "ObjID"
  else:
    sortby = sortby.strip().upper()
    if sortby == 'OBJRA':
      sortby = 'fObjRA'
    elif sortby == 'OBJDEC':
      sortby = 'fObjDec'

  if count:
    squery = """
      select count(*) as num
      from teljoy.objects left join teljoy.objtemp on teljoy.objects.ObjID = teljoy.objtemp.ObjID
      where 
        (UPPER(teljoy.objects.ObjID) like "%s") and
        ( (fObjRA >= %s) and (fObjRA <= %s) ) and
        ( (fObjDec >= %s) and (fObjDec <= %s) ) and
        ( ( (to_days(now())-IFNULL(to_days(LastObs),0)) >= %s) and 
          ( (to_days(now())-IFNULL(to_days(LastObs),0)) <= %s) ) and
        (type like "%s")
    """
    squery = squery % (sid.upper(), sramin, sramax, sdecmin, sdecmax, slodmin, slodmax, stype)
    curs.execute(squery)
    if curs.rowcount:
      try:
        return int(curs.fetchallDict()[0]['num'])
      except:
        return 0
    else:
      return 0

  squery = """
    select teljoy.objects.ObjID
    from teljoy.objects left join teljoy.objtemp on teljoy.objects.ObjID = teljoy.objtemp.ObjID
    where 
      (UPPER(teljoy.objects.ObjID) like "%s") and
      ( (fObjRA >= %s) and (fObjRA <= %s) ) and
      ( (fObjDec >= %s) and (fObjDec <= %s) ) and
      ( ( (to_days(now())-IFNULL(to_days(LastObs),0)) >= %s) and 
        ( (to_days(now())-IFNULL(to_days(LastObs),0)) <= %s) ) and
      (type like "%s")
    order by %s 
    limit %d, %d
  """
  squery = squery % (sid.upper(), sramin, sramax, sdecmin, sdecmax, slodmin, slodmax, stype,
                     sortby, (page - 1) * pagesize, pagesize)
#  print squery + "\n<br>"
  curs.execute(squery)

  olist = []
  if curs.rowcount:
    ulist = curs.fetchallDict()
    for c in ulist:        
      olist.append(Object(c['ObjID']))
  return olist


def sortid(o, p):
  return cmp(o.ObjID, p.ObjID)


def sortra(o, p):
  return cmp(o.ObjRA, p.ObjRA)


def sortdec(o, p):
  return cmp(o.ObjDec, p.ObjDec)


def sorttype(o, p):
  return cmp(o.type, p.type)


# Create a database connection:
#print 'connecting to database for objects database access'
db = MySQLdb.Connection(host=HOST, user=USER, passwd=PASSWORD,
                        db=DATABASE, cursorclass=DictCursor)
#print 'connected'

