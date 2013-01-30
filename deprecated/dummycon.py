
import time
import Queue
import threading
import traceback
import cPickle

from globals import *

"""This module emulates the low-level stepper motor control hardware - it maintains a 
   queue for velocity pairs. The external interface consists of two functions:
     send() is called by motion.MotorControl.TimeInt, and stuffs a pair of velocity values
            into the motor queue.
     QueueLow() returns True if the motor control queue has less that three velocity pairs,
                which represent 150ms of telescope motion.
                
   When the init() function is called, a background thread is started to run 'runtel', which 
   consumes a pair of velocity values every 50ms. 
   
   Internal state (current virtual motor position and timing data for the dummy control loop) 
   is pickled and written at regular intervals to a status file for monitoring.
"""

TICK = 0.05      #50ms tick time for pulling values off the queue
#TICK = 1.0

SAVEINTERVAL = 1.0   #Interval in seconds between saves of the status record to disk

conthread = None

class Status:
  """Maintain status of the virtual telescope hardware.
  """
  def __init__(self):
    self.savetime = 0.0                  #Time that the status was last pickled and saved
    self.RApos, self.DECpos = 0, 0       #Virtual motor position, in steps, for each axis
    self.RAvel, self.DECvel = 0.0, 0.0   #Last velocity value parsed for each axis
    self.delay = TICK                    #Loop delay, dynamically adjusted to maintain 50ms loop time
    self.intervals = [0.0]*100           #Last 100 loop times, for timing statistics
  def __repr__(self):
    return "%s - HA: %s DEC: %s d=%6.4f, meani=%6.4f, maxi=%6.4f" % (time.ctime(self.savetime), 
                       sexstring(float(self.RApos)/20/3600/15, fixed=True),
                       sexstring(float(self.DECpos)/20/3600, fixed=True), 
                       self.delay, sum(self.intervals)/100, max(self.intervals))
  def updated(self):
    """Called when values have been changed. Pickles and saves the state if
       enough time has passed since the last save.
    """
    now = time.time()
    if (now - self.savetime) > SAVEINTERVAL:
      self.savetime = now
      self.save()
  def save(self):
    """Crude, but not worth anything fancier as this code won't last long.
    """
    f = open('/tmp/dummy.status','w')
    cPickle.dump(self,f)
    f.close()    
    

def tohex(a):
  """Convert velocity value to a signed, 16-bit hex string.
  """
  if a < 0:
    return "%04x" % (65536+a,)
  else:
    return "%04x" % a


def toval(a):
  """Convert signed, 16-bit hex string back to a velocity value
  """
  if a > 32767:
    return a - 65536
  else:
    return a


def process(res):
  """Do something with the velocity pair we've just pulled from the queue.
     Update internal positions, and update last velocity values.
  """
  global RApos,DECpos
  ras,decs = res.strip().split(',')
  try:
    ra = toval(int(ras,16))
    dec = toval(int(decs,16))
  except ValueError:
    logfile.write("Corrupt value/s: '%s,%s\n'" % (ras,decs))
    logfile.flush()
  status.RApos += ra
  status.DECpos += dec
  status.RAvel, status.DECvel = ra, dec
    

def send(rasteps, decsteps):
  """Called by motion.MotorControl.TimeInt to send a pair of velocity values to the 
     (dummy) hardware.
  
     Arguments are a pair of distances (one for each axis) to move during a 50ms 'tick'.
     These values are stuffed into the virtual motor queue.
     
     Flag a critical error if the velocity values are out of spec.
  """
  if ( rasteps > 32768 or rasteps < -32767 or
       decsteps > 32768 or decsteps < -32767 ):
    logger.critical('dummycon.send: Velocity too high - aborting')
    raise ValueError
  telqueue.put(tohex(rasteps)+','+tohex(decsteps)+'\n')


def runtel():
  """Dummy controller hardware. Runs continuously, and should be started in its own
     thread. 
     
     This code pulls a pair of velocity values from the queue every 50ms, and processes
     them to maintain an internal dummy motor position for each axis. Flag a critical
     error if the queue is empty - this means motion.MotorControl.TimeInt has failed
     to keep the queue full.
     
     Dynamically adjusts the delay time to maintain a 50ms loop time as processor
     load varies.
  """
  global running
  running = True
  lastT = time.time()
  time.sleep(TICK)
  try:
    while True:
      try:
        res = telqueue.get(block=False)
      except Queue.Empty:
        logfile.write('Queue Empty\n')
        logfile.flush()
        logger.critical('dummycon.runtel: Queue Empty!')
        running = False
        break
      process(res)
      telqueue.task_done()
      now = time.time()
      interval = now - lastT
      lastT = now
      status.intervals.append(interval)
      status.intervals = status.intervals[1:]
      status.delay = status.delay + 0.1*(TICK-interval)   #Add 10% of the last loop time error, for a damped response.
      time.sleep(status.delay)
      status.updated()
  except:
    traceback.print_exc()
    running = False
    

def QueueLow():
  """Returns True if the virtual motor queue has less than 150ms worth of movement data.
  """
  return telqueue.qsize() < 3
  
  
def init():
  """Start the dummy controller in a background thread.
  """
  global conthread, logfile
  logfile = open('/tmp/dummy.log','w')
  for i in range(10):
    send(0,0)   #Pre-fill queue with 500ms worth of (stationary) data
  conthread = threading.Thread(target=runtel, name='runtel-thread')
  conthread.daemon = True
  conthread.start()
  logger.debug("dummycon.init: Queue Size=%d" % telqueue.qsize() )
  

logfile = None
status = Status()
running = False
telqueue = Queue.Queue()

  
