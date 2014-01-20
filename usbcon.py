
"""Low level interface to the USB motion controller code.
"""

import controller
import digio
from globals import *


def binstring(v):
  """Convert a longint into a human readable binary string.
  """
  bs = bin(v)[2:].rjust(64,'0')
  return "%s %s %s %s | %s %s %s %s" % ( bs[0:8], bs[8:16], bs[16:24], bs[24:32],
                                         bs[32:40], bs[40:48], bs[48:56], bs[56:64])


class DriverException(Exception):
  pass


class LimitStatus(object):
  """Class to represent the hardware limit state/s.

     Only used for New Zealand telescopes, no limit state can be read in Perth. This code largely
     ported as-is, and has never actually been used on the NZ telescope.
  """
  _reprf = ( '<LimitStatus: %(HWLimit)s   [PowerOff=%(PowerOff)s, ' +
             'Horiz=%(HorizLim)s, Mesh=%(MeshLim)s, East=%(EastLim)s, West=%(WestLim)s]>')
  _strf = ( 'HWLimits=%(HWLimit)s [PowerOff=%(PowerOff)s, ' +
            'Horiz=%(HorizLim)s, Mesh=%(MeshLim)s, East=%(EastLim)s, West=%(WestLim)s]')

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

  def __init__(self):
    self.HWLimit = False          # True if any of the hardware limits are active. Should be method, not attribute
    self.OldLim = False           # ?
    self.PowerOff = False         # True if the telescope power is off (eg, switched off at the telescope)
    self.HorizLim = False         # True if the mercury switch 'nest' horizon limit has tripper
    self.MeshLim = False          # ?
    self.EastLim = False          # RA axis eastward limit reached
    self.WestLim = False          # RA axis westward limit reached
    self.LimitOnTime = 0          # Timestamp marking the last time we tripped a hardware limit.
    self.LimOverride = False      # True if the limit has been overridden in software

  def __getstate__(self):
    """Can't pickle the __setattr__ function when saving state
    """
    d = {}
    for n in ['HWLimit', 'PowerOff', 'HorizLim', 'MeshLim', 'EastLim', 'WestLim', 'LimOverride']:
      d[n] = self.__dict__[n]
    return d

  def CanEast(self):
    """Returns True if there is no limit set, or the West limit is set but
       we can still move East to escape the limit.
    """
    return (not self.HWLimit) or (self.LimOverride and self.WestLim)

  def CanWest(self):
    """Returns True if there is no limit set, or the East limit is set but
       we can still move West to escape the limit.
    """
    return (not self.HWLimit) or (self.LimOverride and self.EastLim)

  def check(self, inputs=None):
    """Test the limit states asynchronously, in the motor control thread, as we are notified
       about changed inputs. This function can SET the global limit flag (self.HWLimit), but
       not clear it - this flag can only be cleared at a higher level, when not jumping,
       slewing with the paddle, etc.
    """
    limits = digio.ReadLimit(inputs=inputs)
    self.PowerOff = ('POWER' in limits)
    if not self.PowerOff:
      self.EastLim = ('EAST' in limits)
      self.WestLim = ('WEST' in limits)
      self.MeshLim = ('MESH' in limits)
      self.HorizLim = ('HORIZON' in limits)

    if self.EastLim or self.WestLim or self.MeshLim or self.HorizLim or self.PowerOff:
      self.HWLimit = True  # The global limit flag can be set here, but only cleared
                           # in detevent when it's safe (no jump/paddle motion)
    if (not self.OldLim) and (self.HWLimit):
      if self.PowerOff:
        logger.info('Telescope switched off.')
      else:
        logger.critical("Hardware limit reached!")
      self.OldLim = True
      self.LimitOnTime = time.time()   # Timestamp of the last time we hit a hardware limit



class Driver(controller.Driver):
  """To use the controller, a driver class with callbacks must be
     defined to handle the asynchronous events:
  """
  def __init__(self, getframe=None, limits=None):
    # (Keep some values to generate test steps)
    self._getframe = getframe
    self.frame_number = 0
    self.inputs = 0L
    self.configuration = None
    self.running = False
    self.exception = None
    self.FrameLog = []   # Log of the last few seconds of frame data, as a list of tuples
    self.dropped_frames = None
    self.limits = limits
    self.counters = None    # Last values read from the controller counters
    self.lock = threading.RLock()

  def get_expected_controller_version(self):
    """This code needs controller version 0.7
    """
    return (0, 7, 1)

  def initialise(self, state_details):
    """Initialise the controller, reset the queue so it starts
       the motion system and calling for more data,
       and print out controller version details.
    """
    logger.info("* Initialising %s" % (self.host.mcu_version,))
    logger.info("    MCU Firmware Version: %s" % (self.host.mcu_version,))
    logger.info("FPGA Firmware Version: %s" % (self.host.fpga_version,))
    logger.info("Clock Frequency: %s" % (self.host.clock_frequency,))
    logger.info("Queue Capacity: %s" % (self.host.mc_frames_capacity,))

    logger.info("* Initial Run State:")
    logger.info(`state_details`)

    logger.debug('acq in initialise():')
    self.lock.acquire()   # Keep other threads grubby hands away while we configure the controller
    logger.debug('acq in initialise() success')

    if state_details.state == controller.TC_STATE_EXCEPTION:
      d = self.host.get_exception()
      d.addCallback(self._initialisation_get_exception_details_completed)
      return d

    return self._initialise_configure(None)

  def _initialisation_exception_wait_completed(self):
    # Now that the exception state has been reached, get the details:
    d = self._initialisation_get_next_exception_to_clear()
    return d

  def _initialisation_get_next_exception_to_clear(self, _ = None):
    # Now that the exception state has been reached, get the details:
    d = self.host.get_exception()
    d.addCallback(self._initialisation_get_exception_details_completed)
    return d

  def _initialisation_get_exception_details_completed(self, details):
    if details is not None:
      if details.exception in controller.clearable_exceptions:
        logger.info("* Clearing Exception:")
        logger.info(`details`)

        # Exceptions should never be cleared without user interaction; in this
        # example, however, they are cleared on initialisation:
        d = self.host.clear_exception(details.exception)

        d.addCallback(self._initialisation_get_next_exception_to_clear)

        return d
      else:
        raise DriverException( \
          "The exception %s is a serious unexpected error and can not be cleared." % details)
    else:
      self._initialise_configure(None)

  def _initialise_configure(self, _):
    """Set all the configuration data for the controller (pin
       assignments, etc).
    """
    # Create a configuration for the controller:
    configuration = controller.ControllerConfiguration(self.host)

    # The motor controller will start once 8 frames are enqueued:
    configuration.mc_prefill_frames = 8

    # Set the motor control output pin polarities and the function of the
    # "other" or "shutdown" pin. The other pin can be forced high or low
    # permanently, or set to output a clock pulse on each frame or
    # to go high when the controller is running:
    configuration.mc_pin_flags = \
      controller.MC_PIN_FLAG_INVERT_MCA_SP | \
      controller.MC_PIN_FLAG_INVERT_MCA_DP | \
      controller.MC_PIN_FLAG_INVERT_MCB_SP | \
      controller.MC_PIN_FLAG_INVERT_MCB_DP | \
      controller.MC_PIN_FLAG_MCA_O_FUNCTION_LOW | \
      controller.MC_PIN_FLAG_MCB_O_FUNCTION_LOW

    # Set the length of a frame, in cycles of the controller clock frequency. In
    # this example a frame is 50ms, or 1/20th of a second:
    configuration.mc_frame_period = self.host.clock_frequency / 20

    # Set the velocity limit (in steps per frame) on each axis:
    configuration.mc_a_velocity_limit = 6000
    configuration.mc_b_velocity_limit = 6000

    # Set the acceleration limit (in steps per frame per frame) on each axis:
    configuration.mc_a_acceleration_limit = 800   #Should be at least three times the maximum add_to_vel,
    configuration.mc_b_acceleration_limit = 800   #  so up to six times MOTOR_ACCEL

    # Set the deceleration (in steps per frame per frame) to use when shutting down:
    configuration.mc_a_shutdown_acceleration = 250
    configuration.mc_b_shutdown_acceleration = 250

    # Set the pulse width, in cycles of the clock frequency (12MHz). In this
    # example the pulse width is 50 clock cycles, and the off time is 50 clock
    # cycles, for a 100 clock cycle period. At the maximum velocity of 6000
    # steps per frame, this would be a 120kHz square wave:
    configuration.mc_pulse_width = self.host.clock_frequency / 240000
    configuration.mc_pulse_minimum_off_time = self.host.clock_frequency / 240000

    # Invert all the GPIO inputs, so they are active when pulled low:
    for pin in configuration.pins[0:40]:
      pin.invert_input = True

    # Set all of the motor control pins to motor control instead of just GPIO:
    for pin in configuration.pins[48:60]:
      pin.function = controller.CONTROLLER_PIN_FUNCTION_SPECIAL

    # Set the limit switch inputs to the specific pins they are connected to:
    # configuration.mc_a_positive_limit_input = controller.PIN_GPIO_0
    # configuration.mc_a_negative_limit_input = controller.PIN_GPIO_1
    # configuration.mc_b_positive_limit_input = controller.PIN_GPIO_2
    # configuration.mc_b_negative_limit_input = controller.PIN_GPIO_3

    # Set the guider input pins. The SBIG socket has pins: 1=+RA, 2=+DEC, 3=-DEC, 4=-RA, 5=ground:
    configuration.mc_a_positive_guider_input = controller.PIN_GPIO_32     # +RA
    configuration.mc_a_negative_guider_input = controller.PIN_GPIO_35     # -RA
    configuration.mc_b_positive_guider_input = controller.PIN_GPIO_33     # +DEC
    configuration.mc_b_negative_guider_input = controller.PIN_GPIO_34     # -DEC

    # Set the guider sample interval, in cycles of the controller clock frequency.
    # In this example, the guider is polled every 1ms, giving a maximum of
    # 100 for the guider value in each 100ms frame:
    self.mc_guider_counter_divider = self.host.clock_frequency / 1000

    # Each guider value is multiplied by a fractional scale factor to get
    # the number of steps. The resulting value then has a maximum applied before
    # being added to the next available frame:
    configuration.mc_guider_a_numerator = 4
    configuration.mc_guider_a_denominator = 50   #4 steps per 50ms slot
    configuration.mc_guider_a_limit = 20
    configuration.mc_guider_b_numerator = 4
    configuration.mc_guider_b_denominator = 50
    configuration.mc_guider_b_limit = 20

    if SITE == 'NZ':
      # Set 8 pins to outputs, the rest to inputs, with values reported (paddles, limits, power state):
      for pin in configuration.pins[0:8] + configuration.pins[16:48]:
        pin.direction = controller.CONTROLLER_PIN_INPUT
        pin.report_input = True
      for pin in configuration.pins[8:16]:
        pin.direction = controller.CONTROLLER_PIN_OUTPUT
        pin.report_input = False
      for pin_number in [16,17,18, 21,22]:   # Pin numbers for limit inputs, which (unlike paddles) are active HIGH
        configuration.pins[pin_number].invert_input = False   # Normally all inputs to be inverted, see top of this method
#      configuration.shutdown_0_input = 21    # The 'Power' input triggers a hardware shutdown if it goes active
    elif SITE == 'PERTH':
      for pin in configuration.pins[0:48]:   # Set all pins to inputs with values reported (paddles)
        pin.direction = controller.CONTROLLER_PIN_INPUT
        pin.report_input = True
      #Set the actual hand-paddle bits to NOT inverted, as they are active high.
      for pin_number in [24,25,26,27,28, 40,41,42,43,44, 0,1,2,3]:      #[0,1,2,3,4, 16,17,18,19,20, 24,25,26,27]
        configuration.pins[pin_number].invert_input = False      # Normally all inputs to be inverted, see top of this method

    # Set the shutdown pins to outputs:
    for pin_number in (52, 53, 58, 59):
      configuration.pins[pin_number].direction = controller.CONTROLLER_PIN_OUTPUT
      configuration.pins[pin_number].function = controller.CONTROLLER_PIN_FUNCTION_GPIO

    # Send the configuration to the controller:
    d = self.host.configure(configuration)
    self.configuration = configuration     # Save the configuration for later reference.

    # The deferred is completed once the configuration is written:
    d.addCallback(self._initialise_configuration_written)
    d.addErrback(self._initialise_error_occurred)

    return d

  def _initialise_configuration_written(self, configuration):
    """Called when the configuration data has been successfully written
       to the controller. We can now set any outputs on startup.

       Initialise a couple of outputs to define the motor power state
       as 'ON'.
    """
    # Set the shutdown pin values:
    d = self.host.set_outputs((1 << 52) | (1 << 58))
    d.addCallback(self._initialise_finished)
    d.addErrback(self._initialise_error_occurred)

  def _initialise_finished(self, _):
    """Called when the configuration is saved and the output pins have
       been set.
    """
    logger.info("* Successfully Configured")
    self.running = True
    self.lock.release()
    logger.debug('release in _initialise_finished')
    # Schedule a timer to check the counters:
    self.host.add_timer(1.0, self._check_counters)

  def initialisation_error(self, failure):
    """Called by the controller.Controller object, not sure exactly when...
    """
    logger.error("* Initialisation Error: %s" % failure.getErrorMessage())
    logger.error(failure.getTraceback())
    self.lock.release()
    logger.debug('release in initialise_error()')

  def _initialise_error_occurred(self, failure):
    """Called when the initialisation/configuration functions defined above generate an error.
    """
    logger.error("* Configuration Failed:")
    logger.error(failure.getTraceback())
    self.lock.release()
    logger.debug('release in initialise_error_occurred()')
    self.host.stop()

#  def _turn_output_on(self):
#    # Turn the output on, and set the timer to turn it off later:
#    self.host.set_outputs(1 << controller.PIN_GPIO_8)
#
#    self.host.add_timer(1.0, self._turn_output_off)

#  def _turn_output_off(self):
    # Turn the output off, and set the timer to turn it on later:
#    self.host.clear_outputs(1 << controller.PIN_GPIO_8)

#    self.host.add_timer(1.0, self._turn_output_on)

  def _check_counters(self):
    """Grab the counter data, and call _complete_check_counters when the
       data becomes available.

       Called every 60 seconds, using a timer set up for the first time in
       _initialise_outputs_set above, and re-called by _complete_check_counters
       below.
    """
    logger.debug('acq in _check_counters:')
    self.lock.acquire()
    logger.debug('acq in _check_counters success')
    if self.host._running:
      d = self.host.get_counters()
      d.addCallback(self._complete_check_counters)
    else:
      self.lock.release()
      logger.debug('release in _check_counters - host is not running')

  def _complete_check_counters(self, counters):
    """Update the counter log data using the values returned from the controller.
       Set up another call to update the counters in 60 seconds.
    """
    self.lock.release()
    logger.debug('release in _complete_check_counters')
    if DEBUG:
      logger.debug("* Frame %s, (%s, %s) total steps, (%s, %s) guider steps, (%s, %s) measured." %
                  (counters.reference_frame_number,
                   counters.a_total_steps,
                   counters.b_total_steps,
                   counters.a_guider_steps,
                   counters.b_guider_steps,
                   counters.a_measured_steps,
                   counters.b_measured_steps))
    self.counters = counters

    self.host.add_timer(60.0, self._check_counters)

  def enqueue_frame_available(self, details):
    """This method is called when the queue changes (for example, when 
       a frame is dequeued, or when a previous call to enqueue_frame on the
       controller completes). It should check the state of the queue,
       and if required, enqueue at most one frame; once the frame is 
       enqueued, the controller will immediately call this method
       to enqueue another.
    """
    if details.frames_in_queue < 12:
      #Get the next velocity value pair from the motion control system
      va,vb = self._getframe()
      #And add those values to the hardware queue.
#      logger.debug('acq in enqueue_frame_available:')
      self.lock.acquire()
#      logger.debug('acq in enqueue_frame_available success')
      self.frame_number = self.host.enqueue_frame(va, vb)
      self.lock.release()
#      logger.debug('release in enqueue_frame_available')

      self.FrameLog.append((self.frame_number, va, vb))
      if len(self.FrameLog) > 60:    # Log the last three seconds worth of frames
        self.FrameLog =  self.FrameLog[1:]

      # Every "frame" of step data has a unique number, starting with
      # zero. Step counts and guider step counts when queried are
      # also associated with a frame number:
      if DEBUG and (self.frame_number % 1200 == 0):
        logger.debug("* Enqueued Frame (%s = %d, %d)" % (self.frame_number, va, vb))

  def state_changed(self, details):
    """Called when the controller run state changes. This is usually either on
       startup when the queue processing starts, or on shutdown when we've told
       it to stop.
    """
    logger.info("* Run State Change:")
    logger.info(`details`)

    if details.state == controller.TC_STATE_STOPPING:
      logger.info('Hardware shutdown in progress, telescope decelerating.')
      self.running = False
    elif details.state == controller.TC_STATE_EXCEPTION:
      self.running = False
      logger.debug('acq in state_changed:')
      self.lock.acquire()
      logger.debug('acq in state_changed() success')
      d = self.host.get_exception()
      d.addCallback(self._get_exception_completed)

  def enable_guider(self):
    """Calls self.host.enable_guider with locking. Turns on the autoguider.
    """
    self.lock.acquire()
    d = self.host.enable_guider()
    d.addCallback(self._guiderenable_done)

  def _guiderenable_done(self, _):
    """The call to enable the guider has completed, so we can release the lock.
    """
    self.lock.release()

  def disable_guider(self):
    """Calls self.host.disable_guider with locking. Turns off the autoguider.
    """
    self.lock.acquire()
    d = self.host.disable_guider()
    d.addCallback(self._guiderdisable_done)

  def _guiderdisable_done(self, _):
    """The call to disable the guider has completed, so we can release the lock.
    """
    self.lock.release()

  def _get_exception_completed(self, details):
    """Called when we have any exception details after a state change.
    """
    self.lock.release()
    logger.debug('release in get_exeption_completed')
    logger.info("Exception Details: %s" % details)
    self.exception = details
    # Get the counters to see the last frame before the shutdown began:
    logger.debug('acq in get_exception_completed:')
    self.lock.acquire()
    logger.debug('acq in get_exception_completed() success')
    d = self.host.get_counters()
    d.addCallback(self._get_counters_before_stop_completed)

  def _get_counters_before_stop_completed(self, counters):
    self.lock.release()
    logger.debug('release in _get_counters_before_stop_completed')
    logger.info("Shutdown after frame %s, (%s, %s) total steps before shutdown ramp." % (
       counters.reference_frame_number,
       counters.a_total_steps,
       counters.b_total_steps))

    # The controller--in 0.7--doesn't update these counters during shutdown, and after clearing
    # an exception the counters and frame number are reset. A future update will make the total
    # steps after a shutdown available too.

    # Add up the contents of the frames that were queued to the controller, but not actually
    # sent to the motors because of the shutdown:
    da, db = 0, 0    # Number of steps queued but not moved after the shutdown.
    lastframe = counters.reference_frame_number    # Last frame number actually sent to the motors
    fva, fvb = 0, 0
    for (n,va,vb) in self.FrameLog:
      if n == lastframe:
        fva, fvb = va, vb     # Record the final velocity in each axis at the last frame before the shutdown
      if n > lastframe:
        da += va
        db += vb    # Add the 'lost' velocities in each frame queued but not moved.

    # From this tally of dropped steps, subtract the number of steps taken by
    # the motor during the emergency shutdown, using the defined shutdown
    # accelleration in each axis.
    if fva > 0:   # We were moving in a positive direction before the shutdown
      while fva > self.configuration.mc_a_shutdown_acceleration:
        fva -= self.configuration.mc_a_shutdown_acceleration
        da -= self.configuration.mc_a_shutdown_acceleration
      da -= fva
    elif fva < 0:
      while fva < -self.configuration.mc_a_shutdown_acceleration:
        fva += self.configuration.mc_a_shutdown_acceleration
        da += self.configuration.mc_a_shutdown_acceleration
      da -= fva

    if fvb > 0:   # We were moving in a positive direction before the shutdown
      while fvb > self.configuration.mc_b_shutdown_acceleration:
        fvb -= self.configuration.mc_b_shutdown_acceleration
        db -= self.configuration.mc_b_shutdown_acceleration
      db -= fvb
    elif fvb < 0:
      while fvb < -self.configuration.mc_b_shutdown_acceleration:
        fvb += self.configuration.mc_b_shutdown_acceleration
        db += self.configuration.mc_b_shutdown_acceleration
      db -= fvb

    self.dropped_frames = (da,db)    # Need to adjust the position by this amount before restarting the queue.

  def inputs_changed(self, inputs):
    """Called whenever any of the 'notifiable' binary inputs have changed state.
    """
    if DEBUG:
      logger.info("* %s" % binstring(inputs))
    self.inputs = inputs
    self.limits.check(inputs=self.inputs)

  def set_outputs(self, bitfield):
    """Given a 64-bit number, turn ON the output bit corresponding to every bit equal to '1' in 'bitfield'.
    """
    d = self.host.set_outputs(bitfield)
    d.addCallback(self._set_outputs_done)

  def _set_outputs_done(self, _):
    """Output setting is finished, release the lock.
    """
    self.lock.release()

  def clear_outputs(self, bitfield):
    """Given a 64-bit number, turn OFF the output bit corresponding to every bit equal to '1' in 'bitfield'.
    """
    d = self.host.clear_outputs(bitfield)
    d.addCallback(self._clear_outputs_done)

  def _clear_outputs_done(self, _):
    """Output clearing is finished, release the lock.
    """
    self.lock.release()

  def stop(self):
    """Stop the controller loop, triggering creation of a new Driver and Controller.
    """
    logger.debug('acq in stop:')
    self.lock.acquire()
    logger.debug('acq in stop() success')
    self.host.stop()
    self.lock.release()
    logger.debug('release in stop()')

  def shutdown(self):
    """Do a clean shutdown, acquiring the lock first to make sure there's no transfer happening.
    """
    logger.debug('acq in shutdown:')
    self.lock.acquire()
    logger.debug('acq in shutdown() success')
    self.host.shutdown()
    self.lock.release()
    logger.debug('release in shutdown()')

  def run(self):
    """Enter the polling loop. The default poller (returned by select.poll) can
       also be replaced with any object implementing the methods required by libusb1:

       This function exits if stop() is called. If stop was passed an exception, it indicates an
       unrecoverable error that means the main program must exit, and that exception is raised
       by the run() method. If stop() had no arguments, the run() method returns normally.
    """
    controller.run(driver=self)



