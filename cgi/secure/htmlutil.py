
"""Module to generate HTML from a template string and a dictionary. Contains one
   function, subdict.
"""

import string
import types

def subdict(tplate='', vdict={}):
  """Takes the input string and replaces all occurences of ##key## with the value
     of that key in the dictionary vdict. Return the resulting string.
  """

  temps=tplate
  for k in vdict.keys():
    if type(vdict[k])==types.StringType:
      temps=string.replace(temps, '##'+k+'##', vdict[k])
    elif type(vdict[k])==types.FloatType:   #If a float, round to two dp
      temps=string.replace(temps, '##'+k+'##', '%6.2f' % vdict[k])
    else:         #Any other type, convert it to string first
      temps=string.replace(temps, '##'+k+'##', `vdict[k]`)

  return temps
