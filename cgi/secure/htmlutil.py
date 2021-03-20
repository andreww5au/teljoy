"""Module to generate HTML from a template string and a dictionary. Contains one
   function, subdict.
"""


def subdict(tplate='', vdict=None):
    """Takes the input string and replaces all occurrences of ##key## with the value
       of that key in the dictionary vdict. Return the resulting string.
    """
    if vdict is None:
        vdict = {}
    temps = tplate
    for k in vdict.keys():
        if type(vdict[k]) == str:
            temps = temps.replace('##' + k + '##', vdict[k])
        elif type(vdict[k]) == float:  # If a float, round to two dp
            temps = temps.replace('##' + k + '##', '%6.2f' % vdict[k])
        else:  # Any other type, convert it to string first
            temps = temps.replace('##' + k + '##', repr(vdict[k]))

    return temps
