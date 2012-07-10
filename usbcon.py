#! /usr/bin/python

import time

import controller
from globals import *

DIVIDER = 20   #Scale down step values for testing with non-microstepped driver boards

def binstring(v):
  """Convert a longint into a human readable binary string.
  """
  bs = bin(v)[2:].rjust(64,'0')
  return "%s %s %s %s | %s %s %s %s" % ( bs[0:8], bs[8:16], bs[16:24], bs[24:32],
                                         bs[32:40], bs[40:48], bs[48:56], bs[56:64])

class Driver(controller.Driver):
  # To use the controller, a driver class with callbacks must be
  # defined to handle the asynchronous events:
  def __init__(self, getframe=None):
    # (Keep some values to generate test steps)
    self._getframe = getframe
    self.frame_number = 0
    self.inputs = 0L

  def get_expected_controller_version(self):
    return (0, 3)

  def initialise(self, state_details):
    # Print out controller version details:
    logger.info("* Initialising %s" % (self.host.mcu_version,))
    logger.info("    MCU Firmware Version: %s" % (self.host.mcu_version,))
    logger.info("FPGA Firmware Version: %s" % (self.host.fpga_version,))
    logger.info("Clock Frequency: %s" % (self.host.clock_frequency,))
    logger.info("Queue Capacity: %s" % (self.host.mc_frames_capacity,))

    logger.info("* Initial Run State:")
    logger.info(`state_details`)

    # First, reset the queue. If the controller was previously running this
    # will set the expected frame number back to zero:
    d = self.host.reset_queue()

    d.addCallback(self._initialise_queue_reset)
    d.addErrback(self._initialise_error_occurred)

  def _initialise_queue_reset(self, _):
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

    # Set the deceleration (in steps per frame per frame) to use when shutting down:
    configuration.mc_a_shutdown_acceleration = 5
    configuration.mc_b_shutdown_acceleration = 5

    # Set the acceleration limit (in steps per frame per frame) on each axis:
    configuration.mc_a_acceleration_limit = 5
    configuration.mc_b_acceleration_limit = 5

    # Set the velocity limit (in steps per frame) on each axis:
    configuration.mc_a_velocity_limit = 100
    configuration.mc_b_velocity_limit = 100

    configuration.mc_pulse_minimum_off_time = 1

    # Set the length of a frame, in cycles of the controller clock frequency. In
    # this example a frame is 50ms, or 1/20th of a second:
    configuration.mc_frame_period = self.host.clock_frequency / 20

    # Set the pulse width, in cycles of the controller clock frequency. In this
    # example the pulse width is 500us:
    configuration.mc_pulse_width = self.host.clock_frequency / 2000

    # Invert all the GPIO inputs, so they are active when pulled low:
    for pin in configuration.pins[0:48]:
      pin.invert_input = True

    # Set all of the motor control pins to motor control instead of just GPIO:
    for pin in configuration.pins[48:60]:
      pin.function = controller.CONTROLLER_PIN_FUNCTION_SPECIAL

    # Set the limit switch inputs to the specific pins they are connected to:
    configuration.mc_a_positive_limit_input = controller.PIN_GPIO_0
    configuration.mc_a_negative_limit_input = controller.PIN_GPIO_1
    configuration.mc_b_positive_limit_input = controller.PIN_GPIO_2
    configuration.mc_b_negative_limit_input = controller.PIN_GPIO_3

    # Set the guider input pins:
    configuration.mc_a_positive_guider_input = controller.PIN_GPIO_4
    configuration.mc_a_negative_guider_input = controller.PIN_GPIO_5
    configuration.mc_b_positive_guider_input = controller.PIN_GPIO_6
    configuration.mc_b_negative_guider_input = controller.PIN_GPIO_7

    # Set the guider sample interval, in cycles of the controller clock frequency.
    # In this example, the guider is polled every 1ms, giving a maximum of
    # 100 for the guider value in each 100ms frame:
    self.mc_guider_counter_divider = self.host.clock_frequency / 1000

    # Each guider value is multiplied by a fractional scale factor to get
    # the number of steps. The resulting value then has a maximum applied before
    # being added to the next available frame:
    configuration.mc_guider_a_numerator = 1
    configuration.mc_guider_a_denominator = 10
    configuration.mc_guider_a_limit = 20
    configuration.mc_guider_b_numerator = 1
    configuration.mc_guider_b_denominator = 10
    configuration.mc_guider_b_limit = 20

    # Set eight pins to an output:
    for pin in configuration.pins[8:16]:
      pin.direction = controller.CONTROLLER_PIN_INPUT
      pin.report_input = True

    # Send the configuration to the controller:
    d = self.host.configure(configuration)

    # Set one input pin so that any changes are reported by
    # calling inputs_changed on this driver class:
#    configuration.pins[controller.PIN_GPIO_9].report_input = True

    # The deferred is completed once the configuration is written:
    d.addCallback(self._initialise_configuration_written)
    d.addErrback(self._initialise_error_occurred)

    return d

  def _initialise_configuration_written(self, configuration):
    logger.info("* Successfully Configured")

    # Schedule the first call of a timer that will toggle the output every second:
#    self.host.add_timer(1.0, self._turn_output_on)

    # Schedule a timer to check the counters:
    self.host.add_timer(1.0, self._check_counters)

  def initialisation_error(self, failure):
      logger.error("* Initialisation Error: %s" % failure.getErrorMessage())
      logger.error(failure.getTraceback())

  def _initialise_error_occurred(self, failure):
    logger.error("* Configuration Failed:")
    logger.error(failure.getTraceback())
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
    d = self.host.get_counters()
    d.addCallback(self._complete_check_counters)

  def _complete_check_counters(self, counters):
    logger.info("* Frame %s, (%s, %s) total steps, (%s, %s) guider steps, (%s, %s) measured." %
                  (counters.reference_frame_number,
                   counters.a_total_steps,
                   counters.b_total_steps,
                   counters.a_guider_steps,
                   counters.b_guider_steps,
                   counters.a_measured_steps,
                   counters.b_measured_steps))

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
      # Ramp the velocity up and down:
      va,vb = self._getframe()
      va,vb = va/DIVIDER, vb/DIVIDER
      self.frame_number = self.host.enqueue_frame(va, vb)
  
      # Every "frame" of step data has a unique number, starting with
      # zero. Step counts and guider step counts when queried are
      # also associated with a frame number:
      if self.frame_number % 360 == 0:
        print "* Enqueued Frame (%s = %d, %d)" % (self.frame_number, va, vb)

  def state_changed(self, details):
    logger.info("* Run State Change:")
    logger.info(`details`)

    if details.state == controller.TC_STATE_EXCEPTION:
      self.host.stop()

  def inputs_changed(self, inputs):
    logger.info("* %s" % binstring(inputs))
    if inputs & (1 << 23):
      print "RED pressed"
    if inputs & (1 << 22):
      print "GREEN pressed"
    if inputs & (1 << 21):
      print "BLUE pressed"
    if inputs & (1 << 20):
      print "YELLOW pressed"
    if inputs & (1 << 19):
      print "WHITE pressed"
    self.inputs = inputs

  def run(self):
    """Enter the polling loop. The default poller (returned by select.poll) can
       also be replaced with any object implementing the methods required by libusb1:

       This function doesn't exit.
    """
    controller.run(driver=self)


