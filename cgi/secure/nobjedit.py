
"""Code to handle creation of new objects, or editing existing ones. This implements the 'page'
   function called by the 'nobjedit' script stub.
"""

import cgi
import os
import traceback
import sys

sys.path.append('/home/mjuo')

import htmlutil
from teljoy.cgi import objects
import nobjedithtml

   
 
def page(form=None):
  """Returns a single string, the complete web page, given a CGI form object as an argument. If
     the event name field is given when first called, an existing event is edited instead.
     Note that if an existing event is edited and the name is changed, it is _changed_ for that
     event, it's not duplicated and added as a new name.
  """
  if form.has_key('ObjID'):
    ObjID=form['ObjID'].value
  else:
    ObjID=''

  ob = objects.Object(ObjID)
  if not ob.ObjRA:
    newobject = 1
    ob.ObjEpoch = 2000
  else:
    newobject = 0

  #newobject is true if the oject is a newly created blank object that must be added to the list
  #later. If newobject isn't true, the object returned isn't a copy, any changes will affect
  #the actual object list when saved to the file.

  #build up a list of strings in 'output' to join together as a return value
  #Concating a list of strings once is much quicker than adding them one by one.
  output=[ htmlutil.subdict(nobjedithtml.header, {'ObjID':ObjID} ) ]

  #If someone has entered details for a new object and clicked 'save', ask if they are sure
  if form.has_key('save'):
    try:
      d={}
      for field in ['ObjID', 'name', 'ObjRA', 'ObjDec', 'ObjEpoch', 'filtnames', 'exptimes',
                    'XYpos_X', 'XYpos_Y', 'type', 'period', 'comment']:
        try:
          d[field]=form[field].value
        except:
          d[field]=' '

      d['XYpos_X'], d['XYpos_Y'] = '%d' % (ob.XYpos[0],), '%d' % (ob.XYpos[1],)

      output.append( htmlutil.subdict(nobjedithtml.confirmobject, d))

      output.append( nobjedithtml.trailer )
      return ''.join(output)
    except:
      output.append("Error parsing 'save new object' form.\n" + nobjedithtml.trailer)
      e = traceback.format_exception(sys.exc_type,sys.exc_value, sys.exc_traceback)
      for l in e:
        output.append((cgi.escape(l)+'<p>').replace('\n', '<br>'))

      return ''.join(output)

  #If someone has said 'Yes, I'm sure I want to save this object', add it to the list
  if form.has_key('Yes'):
    try:
      ob.ObjID=form['ObjID'].value
      ob.name=form['name'].value
      ob.ObjRA=form['ObjRA'].value
      ob.ObjDec=form['ObjDec'].value
      ob.ObjEpoch=float(form['ObjEpoch'].value)
      filtnames=form['filtnames'].value
      exptimes=form['exptimes'].value
      ob.subframes,ob.sublist = objects.psl(filtnames,exptimes)
      ob.XYpos = ( float(form['XYpos_X'].value), float(form['XYpos_Y'].value) )
      ob.type=form['type'].value
      ob.period=float(form['period'].value)
      ob.comment=form['comment'].value
      
      ob.save(ask=0, force=1)

      imgname = form['imgname'].value
      os.remove(imgname)

      output.append(nobjedithtml.savedmessage)
      output.append(nobjedithtml.trailer)

      return ''.join(output)
    except ValueError:
      output.append("Error parsing data for new object.")
      e = traceback.format_exception(sys.exc_type,sys.exc_value, sys.exc_traceback)
      for l in e:
        output.append((cgi.escape(l)+'<p>').replace('\n','<br>'))
      output.append(nobjedithtml.trailer)
      return ''.join(output)

  #If we aren't saving an object, or confirming a save, just show boxes for all 
  #the details, either blank for a new event or filled in to edit an existing one
  d={}
  for field in ['ObjID', 'name', 'ObjRA', 'ObjDec', 'ObjEpoch',
                'XYpos_X', 'XYpos_Y', 'type', 'period', 'comment']:
    try:
      d[field]=ob.__dict__[field]
    except:
      d[field]=' '
  d['filtnames'],d['exptimes'] = objects.pls(ob.sublist)

  output.append(htmlutil.subdict(nobjedithtml.newobject, d))
  output.append(nobjedithtml.trailer)
  return ''.join(output)

