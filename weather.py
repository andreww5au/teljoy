"""Weather station interface module.

   Reads current weather data from misc.weather table in database, and keeps status object
   up to date.

   Only used in Perth system, no weather sensors available at Mt John in New Zealand.
"""

from globals import *

try:
    import MySQLdb as dblib
except ImportError:
    dblib = None

weather = None
db = None
b_db = None
status = None

# These are the initial defaults, copied to the status object on module init.
_SkyOpenTemp = -26  # Open if skytemp < this for more than WeatherOpenDelay sec
_SkyCloseTemp = -25  # Close is skytemp > this or raining
_WeatherOpenDelay = 1800  # Wait for 1800 sec of no-rain and cloud < CloudOpenLevel
_CloudCloseDelay = 150  # Wait until at least two cloud readings (1/2min) are 'cloudy'


def _unyv(arg=0):
    if arg == 0:
        return "?"
    elif arg == 1:
        return "No"
    elif arg == 2:
        return "Yes"
    elif arg == 3:
        return "VERY!"
    else:
        return "error."


def _yn(arg=0):
    if arg:
        return "Yes"
    else:
        return "No"


def render(v, dig=4, dp=1):
    """If v is None, return 'NULL' as a string. Otherwise return
       the value in v formatted nicely as a number, with the given
       number of digits in total, and after the decimal point.
    """
    if v is None:
        return "NULL"
    else:
        return ('%' + repr(dig) + '.' + repr(dp) + 'f') % v


class Weather(object):
    """Cloud and rain detector status
    """

    def __init__(self):
        """called by on instantiation, or manually using the empty() method to clear status
        """
        self.lastmod = -1
        self.skytemp = 0.0
        self.cloudf, self.windf, self.rainf, self.dayf = 0, 0, 0, 0
        self.rain = False
        self.temp = 0.0
        self.windspeed = 0.0
        self.humidity = 0.0
        self.dewpoint = 0.0
        self.skylight = 0.0
        self.rainhit, self.wethead = False, False
        self.senstemp = 0.0
        self.weathererror = ""
        self.SkyCloseTemp = _SkyCloseTemp
        self.SkyOpenTemp = _SkyOpenTemp
        self.WeatherOpenDelay = _WeatherOpenDelay
        self.CloudCloseDelay = _CloudCloseDelay  # No interface for setting this at runtime
        self.OKforsec = 86400  # Assume it's clear when we start up
        self.CloudyForSec = 0
        self.clear = True

    def empty(self):
        self.__init__()
        self.update()

    def GetState(self):
        d = {}
        for n in ['lastmod', 'skytemp', 'cloudf', 'windf', 'rainf', 'dayf', 'rain', 'temp', 'windspeed', 'humidity',
                  'dewpoint',
                  'skylight', 'rainhit', 'wethead', 'senstemp', 'weathererror', 'SkyCloseTemp', 'SkyOpenTemp',
                  'WeatherOpenDelay',
                  'CloudCloseDelay', 'OKforsec', 'CloudyForSec', 'clear']:
            d[n] = self.__dict__.get(n)
        return d

    def __str__(self):
        """Tells the status object to display itself
        """
        # noinspection PyListCreation
        mesg = []
        mesg.append("Sky Temp:  %s" % self.skytemp)
        mesg.append("Cloudy:    %s" % _unyv(self.cloudf))
        mesg.append("Windy:     %s" % _unyv(self.windf))
        mesg.append("Raining:   %s" % _unyv(self.rainf))
        mesg.append("Daylight:  %s" % _unyv(self.dayf))
        mesg.append("Last weather entry: %s seconds ago." % self.lastmod)
        mesg.append("Air temp:  %s" % render(self.temp, 4, 1))
        mesg.append("Avg wind:  %s" % render(self.windspeed, 3, 0))
        mesg.append("Humidity:  %s" % render(self.humidity, 2, 0))
        mesg.append("Dew point: %s" % render(self.dewpoint, 4, 1))
        mesg.append("Raindrops: %s" % _yn(self.rainhit))
        mesg.append("Wet sensor:%s" % _yn(self.wethead))
        mesg.append("Sens. Temp:%s" % render(self.senstemp, 4, 1))
        mesg.append("\nBecomes 'not clear' if skytemp warmer than %d C" % self.SkyCloseTemp)
        mesg.append("Becomes 'clear' if skytemp colder than %d C for %d seconds or more" %
                    (self.SkyOpenTemp, self.WeatherOpenDelay))
        if self.weathererror:
            mesg.append("Error: %s" % self.weathererror)
        if self.clear:
            mesg.append("\nCurrent Status: Clear")
        else:
            mesg.append("\nCurrent Status: Not Clear, conditions have been acceptable for %d seconds." % self.OKforsec)
        return '\n'.join(mesg) + '\n'

    def __repr__(self):
        return self.__str__()

    def checkweather(self):
        """Monitor Cloud and Rain data, and take action if necessary
        """
        if SITE == 'NZ':
            self.clear = True
            return  # No weather sensor connection yet, in NZ

        if self.rainf != 1:  # 0 is unknown, 1 is not raining, 2 is 'wet', 3 is raining.
            self.rain = True
        else:
            self.rain = False
        if self.weathererror:
            self.clear = False
            self.OKforsec = False
        else:
            if not self.clear:
                if (self.skytemp <= self.SkyOpenTemp) and (not self.rain):
                    self.OKforsec = self.OKforsec + 5
                else:
                    self.OKforsec = 0
                if self.OKforsec > self.WeatherOpenDelay:
                    self.clear = True
            else:
                if (self.skytemp >= self.SkyCloseTemp):
                    self.CloudyForSec = self.CloudyForSec + 5
                else:
                    self.CloudyForSec = 0
                if (self.CloudyForSec > self.CloudCloseDelay) or self.rain:
                    self.clear = False
                    self.OKforsec = 0

    def update(self, u_curs=None):
        """Connect to the database to update fields
        """
        if db is None:
            return

        self.weathererror = ""

        if not u_curs:
            u_curs = db.cursor()
        try:
            u_curs.execute('select unix_timestamp(now())-unix_timestamp(time) as lastmod, ' +
                           'skytemp, cloudf, windf, rainf, dayf, temp, windspeed, humidity, dewpoint, ' +
                           'skylight, rainhit, wethead, senstemp from misc.weather order by time desc ' +
                           'limit 1')
            # Read the contents of the
            # 'weather status' table to find
            # cloud voltage and rain status
            row = u_curs.fetchall()[0]
            self.lastmod = row[0]
            self.skytemp = row[1]
            self.cloudf = row[2]
            self.windf = row[3]
            self.rainf = row[4]
            self.dayf = row[5]
            self.temp = row[6]
            self.windspeed = row[7]
            self.humidity = row[8]
            self.dewpoint = row[9]
            self.skylight = row[10]
            self.rainhit = row[11]
            self.wethead = row[12]
            self.senstemp = row[13]
        except:
            self.weathererror = "Weather database not OK, can't get current values"
        if self.lastmod > 540:
            self.weathererror = "Weather database not updated for " + repr(self.lastmod) + " seconds."

        self.checkweather()


def _background():
    """Function to be run in the background, updates the status object.
    """
    if b_db is None:
        return

    b_curs = b_db.cursor()
    try:
        status.update(b_curs)
    except:
        print("a weather exception")


def Init():
    """Set up the database connection to access the weather data.
    """
    global db, b_db, status

    if dblib is None:
        return

    db = None
    b_db = None
    try:
        db = dblib.Connection(host='mysql', user='honcho', passwd='', db='misc')
        b_db = dblib.Connection(host='mysql', user='honcho', passwd='', db='misc')
    except:
        print("DANGER - no weather sensor available, disabling weather monitoring")
    status = Weather()
    status.update()
