
INTERFACE = 'mysqldb'
#INTERFACE = 'pgdb'

if INTERFACE == 'mysqldb':
  import MySQLdb as dblib
elif INTERFACE == 'pgdb':
  import pgdb as dblib



#Use as:
# class Observation(dbObject):
#   _table='mwa_observation'
#   _attribs = [('id','id',0),('name','observation_name',''),('user','username','')]
#   _readonly = ['id','modtime']
#   _key = ('name',)
#   _reprf = 'MWA_Observation[%(name)s]'
#   _strf = '%(id)d:%(user)s %(name)s\n'


class dbObject:
  _table = ''
  _attribs = []
  _key = ('')
  _serialkey = False     #True if the primary key for this table is an autoincrementing sequence
  _reprf = ''
  _strf = ''
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname


  def getall(cls, db=None):
    "Return a list of all objects in the given database."
    curs=db.cursor()
    klist = []
    for k in cls._key:
      klist.append(cls._nmap[k])
    curs.execute("select " + ','.join(klist) + " from " + cls._table)
    c=curs.fetchall()
    olist=[]
    for row in c:
      olist.append(cls(tuple(row),db=db))
    return olist
  getall = classmethod(getall)

  def getdict(cls, db=None):
    """DLK:  Return a dictionary of all objects in the given database."""
    curs=db.cursor()
    klist = []
    for k in cls._key:
      klist.append(cls._nmap[k])
    curs.execute("select " + ','.join(klist) + " from " + cls._table)
    c=curs.fetchall()
    olist={}
    try:
      for row in c:
        # I think this should correctly handle multi-part keys
        if (len(row)>1):
          keyname="_".join([str(s) for s in row])
        else:
          keyname=row[0]
        olist[keyname]=cls(tuple(row),db=db)
      return olist
    except:
      return {}
  getdict = classmethod(getdict)

  def verifyfields(cls, db=None):
    passed = True
    curs=db.cursor()
    lfields =[]
    for lf in cls._attribs:
      lfields.append(lf[1])
    curs.execute("select * from " + cls._table + " limit 1")
    fields = {}
    for f in curs.description:
      fields[f[0]] = (f[1],f[3])
      if f[0] not in lfields:
        print "New field '"+f[0]+"':"+f[1]+" in database, not in class definition for " + cls._table
        passed = False
    for f in lfields:
      if f not in fields.keys():
        print "Field '"+f+"' in class definition not present in database table " + cls._table
        passed = False
    return passed
  verifyfields = classmethod(verifyfields)


  def tr_d2o(self,name,value):
    """Subclass this function to implement a translate function from data in
       the SQL result to the format required for python object attribute.
       The 'name' parameter is the python object attribute name.
    """
    return value

  def tr_o2d(self,name,value):
    """Subclass this function to implement a translate function from data in
       the python object to the format required for the SQL call.
       The 'name' parameter is the python object attribute name.
    """
    return value

  def empty(self):
    """Make all attributes in the object have their default empty value"""
    for oname,dname,dval in self._attribs:
      self.__dict__[oname] = dval
    klist = []
    for k in self._key:
      klist.append(self.__dict__[k])
    self.origkey = tuple(klist)

  def __init__(self, keyval=(), db=None):
    """Create an object with the given key value. If the key given exists
       in the database, load that record, instantiate the object, and return
       it. If not, create a new empty record and return it, with the boolean 
       attribute 'new' having a True value.
    """
    curs = db.cursor()
    if not keyval:
      self.empty()
      self.new = True
    else:
      if type(keyval) <> type(()):
        keyval = (keyval,)
      clist = []
      for oname,dname,dval in self._attribs:
        clist.append(dname)
      klist = []
      for k,v in zip(self._key,keyval):
        if type(v) == type(''):
          klist.append(" ("+self._nmap[k]+"='"+dblib.escape_string(v)+"') ")
        else:
          klist.append(" ("+self._nmap[k]+"="+str(v)+") ")
      curs.execute("select " + ", ".join(clist) + " from " + self._table +
                   " where " + " and ".join(klist))
      
      if not curs.rowcount:
        self.empty()
        for k,v in zip(self._key,keyval):
          self.__dict__[k] = v
        self.new = True
        return
      else:
        c = curs.fetchall()[0]
        i = 0
        for oname,dname,dval in self._attribs:
          self.__dict__[oname] = self.tr_d2o(oname,c[i])
          i += 1
        klist = []
        for k in self._key:
          klist.append(self.__dict__[k])
        self.origkey = tuple(klist)
        self.new = False


  def display(self):
    """Subclass this to, for example, return an HTML representation
       of the object.
    """
    print self._strf % self.__dict__

  def __repr__(self):
    """This is called by python itself when the object is converted
       to a string automatically, or using the `` operation.
    """
    return self._reprf % self.__dict__

  def __str__(self):
    """This is called by python itself when the object is converted to
       a string using the str() function.
    """
    return self._strf % self.__dict__

  def save(self,ask=1,force=0, db=None, commit=1, verbose=1):
    """Save the object to the database, calling the translate functions as 
       required, and ignoring any attributes listed in the _readonly list.
    """
    curs=db.cursor()
    emptykey = True
    for k in self._key:
      if self.__dict__[k]:
        emptykey = False
    if emptykey and (not self._serialkey):
      print "Empty key value in self."+`self._key`+", can't save object."
      return 0

    new = False
    if emptykey:
      new = True
    else:
      klist = []
      for k in self._key:
        if type(self.__dict__[k])==type(''):
          klist.append(" ("+self._nmap[k]+"='"+dblib.escape_string(self.__dict__[k])+"') ")
        else:
          klist.append(" ("+self._nmap[k]+"="+str(self.__dict__[k])+") ")
      curs.execute("select * from "+self._table+" where " + " and ".join(klist))
      if not curs.rowcount:
        new = True

    if new:
      clist = []
      vlist = []
      for oname,dname,dval in self._attribs:
        if oname not in self._readonly:
          clist.append(dname)
          if oname not in self._key:
            odata = self.tr_o2d(oname,self.__dict__[oname])
          else:
            odata = self.__dict__[oname]
          if type(odata) == type(''):
            vlist.append("'"+dblib.escape_string(odata)+"'")
          elif odata is None:
            vlist.append("NULL")
          else:
            vlist.append(str(odata))
      curs.execute("insert into " + self._table + " " +
                   "(" + ", ".join(clist)+") "+
         "values (" + ", ".join(vlist) + ") ")
#      if self.origkey.upper()<>self.__dict__[self._key[0]].upper():
#        if self.origkey<>'':
#          curs.execute("delete from "+self._table+" where "+self._key[1]+"='"+self.origkey+"'")
    else:
      if ask:
        print "Object already exists, do you want to replace it?"
        ans=raw_input("y/n (default n): ").strip().lower()[:1]
        if ans<>'y':
          print "Object not overwritten."
          return 0
      else:
        if not force:
          print "Object <%s> with key=%s exists and force=0; object not overwritten." % (self.__class__, klist)
          return 0
      clist = []
      for oname,dname,dval in self._attribs:
        if oname not in self._readonly:
          if oname not in self._key:
            odata = self.tr_o2d(oname,self.__dict__[oname])
          else:
            odata = self.__dict__[oname]
          if type(odata) == type(''):
            clist.append(dname+"='"+dblib.escape_string(odata)+"'")
          elif odata is None:
            clist.append(dname+"=NULL")
          else:
            clist.append(dname+"="+str(odata))
      klist = []
      for k in self._key:
        if type(self.__dict__[k])==type(''):
          klist.append(" ("+self._nmap[k]+"='"+dblib.escape_string(self.__dict__[k])+"') ")
        else:
          klist.append(" ("+self._nmap[k]+"="+str(self.__dict__[k])+") ")
      curs.execute("update " + self._table + " set " +
         ", ".join(clist) + 
         " where " + " and ".join(klist))

    if commit:
      db.commit()
    if verbose:
      print "Object <%s> saved." % self.__class__
    return 1


  def delete(self, ask=1, db=None, commit=1):
    """Delete the given object from the database.
    """
    curs=db.cursor()
    emptykey = True
    for k in self._key:
      if self.__dict__[k]:
        emptykey = False
    if emptykey:
      print "Empty key value in self."+`self._key`+", can't delete object."
      return 0
    klist = []
    for k in self._key:
      if type(self.__dict__[k])==type(''):
        klist.append(" ("+self._nmap[k]+"='"+dblib.escape_string(self.__dict__[k])+"') ")
      else:
        klist.append(" ("+self._nmap[k]+"="+str(self.__dict__[k])+") ")
    curs.execute("select * from " + self._table + " where " + " and ".join(klist))
    if not curs.rowcount:
      print "Object not found in database."
      return 0
    if ask:
      print "Are you sure you want to delete object?"
      ans=raw_input("y/n (default n): ").strip().lower()[:1]
      if ans<>'y':
        print "Object not deleted."
        return 0
    curs.execute("delete from " + self._table + " where " + " and ".join(klist))
    #print "Object deleted from database."
    if commit:
      db.commit()
    return 1


def execute(execstr='', db=None):
  curs = db.cursor()
  curs.execute(execstr)
  if curs.description is None:
    return curs.rowcount    #We've executed an SQL command that doesn't return any rows (eg 'update')
  else:
    return map(tuple,curs.fetchall())
  

def getdb(user=None, password=None, host=None, database=None):
  if INTERFACE == 'mysqldb':
    dbob = dblib.connect(user=user, passwd=password, host=host)
  elif INTERFACE == 'pgdb':
    dbob = dblib.connect(user=user, password=password, host=host, database=database)
  return dbob



