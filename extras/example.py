#!/usr/bin/python

import controller, time, random

from twisted.internet import defer

class ExampleException(Exception):
	pass

class Source(object):
	def __init__(self):
		# (Keep some values to generate test steps)
		self.velocity = 0
		self.acceleration = 20

	def next(self):
		# Ramp the velocity up and down:
		self.velocity += self.acceleration

		if self.velocity >= 80: self.acceleration = -20
		if self.velocity <= -80: self.acceleration = 20 

		return -self.velocity, self.velocity

class Driver(controller.Driver):
	# To use the controller, a driver class with callbacks must be
	# defined to handle the asynchronous events:
	def __init__(self, source):
		self.source = source

		self.input_count = 0

		self.last_log_time = time.time()

		self.last_enqueue_frame_number = None

	def log(self, *values):
		now = time.time()
		time_delta = now - self.last_log_time
		self.last_log_time = now
		
		print "(+%0.4f) %s" % (time_delta, " ".join(map(str, values)))

	def get_expected_controller_version(self):
		return (0, 7)

	def initialisation_error(self, failure):
		self.log("* Initialisation Error: %s" % failure.getErrorMessage())
		failure.printTraceback()

	def initialise(self, state_details):
		# Print out controller version details:
		self.log("* Initialising", self.host.mcu_version)
		self.log("    MCU Firmware Version:", self.host.mcu_version)
		self.log("    FPGA Firmware Version:", self.host.fpga_version)
		self.log("    Clock Frequency:", self.host.clock_frequency)
		self.log("    Queue Capacity:", self.host.mc_frames_capacity)

		self.log("* Initial Run State:")
		self.log(`state_details`)

		if state_details.state == controller.TC_STATE_EXCEPTION:
			d = self.host.get_exception()
			d.addCallback(self._initialisation_get_exception_details_completed)
			return d

		return self._initialise_configure(None)

	def _initialisation_get_next_exception_to_clear(self, _ = None):
		# Now that the exception state has been reached, get the details:
		d = self.host.get_exception()
		d.addCallback(self._initialisation_get_exception_details_completed)
		return d

	def _initialisation_get_exception_details_completed(self, details):
		if details is not None:
			if details.exception in controller.clearable_exceptions:
				self.log("* Clearing Exception:")
				self.log(`details`)

				# Exceptions should never be cleared without user interaction; in this
				# example, however, they are cleared on initialisation:
				d = self.host.clear_exception(details.exception)

				d.addCallback(self._initialisation_get_next_exception_to_clear)

				return d
			else:
				raise ExampleException( \
					"The exception %s is a serious unexpected error and can not be cleared." % details)
		else:
			self._initialise_configure(None)

	def state_changed(self, details):
		self.log("* Run State Change:")
		self.log(`details`)

		if details.state == controller.TC_STATE_EXCEPTION:
			d = self.host.get_exception()
			d.addCallback(self._get_exception_completed)

	def _initialise_configure(self, _):
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
		configuration.mc_a_shutdown_acceleration = 3
		configuration.mc_b_shutdown_acceleration = 3

		# Set the acceleration limit (in steps per frame per frame) on each axis:
		configuration.mc_a_acceleration_limit = 20
		configuration.mc_b_acceleration_limit = 20

		# Set the velocity limit (in steps per frame) on each axis:
		configuration.mc_a_velocity_limit = 90
		configuration.mc_b_velocity_limit = 90

		configuration.mc_pulse_minimum_off_time = 1

		# Set the length of a frame, in cycles of the controller clock freqency. In
		# this example a frame is 100ms, or 1/10th of a second:
		configuration.mc_frame_period = self.host.clock_frequency / 10

		# Set the pulse width, in cycles of the controller clock frequency. In this
		# example the pulse width is 1ms:
		configuration.mc_pulse_width = self.host.clock_frequency / 1000

		# Invert all the GPIO inputs, so they are active when pulled low:
		for pin in configuration.pins[0:48]:
			pin.invert_input = True

		# Set all of the motor control pins to motor control instead of just GPIO:
		for pin in configuration.pins[48:60]:
			pin.function = controller.CONTROLLER_PIN_FUNCTION_SPECIAL

		# Set the limit switch inputs to the specific pins they are connected to:
		# configuration.mc_a_positive_limit_input = controller.PIN_GPIO_0
		# configuration.mc_a_negative_limit_input = controller.PIN_GPIO_1
		# configuration.mc_b_positive_limit_input = controller.PIN_GPIO_2
		# configuration.mc_b_negative_limit_input = controller.PIN_GPIO_3

		# Set the guider input pins:
		# configuration.mc_a_positive_guider_input = controller.PIN_GPIO_4
		# configuration.mc_a_negative_guider_input = controller.PIN_GPIO_5
		# configuration.mc_b_positive_guider_input = controller.PIN_GPIO_6
		# configuration.mc_b_negative_guider_input = controller.PIN_GPIO_7

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
	
		# Set one pin to an output:
		#configuration.pins[controller.PIN_GPIO_8].direction = \
		#  controller.CONTROLLER_PIN_OUTPUT

		configuration.shutdown_0_input = controller.PIN_GPIO_0
		configuration.shutdown_1_input = controller.PIN_GPIO_1
		configuration.shutdown_2_input = controller.PIN_GPIO_2
		configuration.shutdown_3_input = controller.PIN_GPIO_3

		configuration.mc_a_positive_limit_input = controller.PIN_GPIO_4
		configuration.mc_a_negative_limit_input = controller.PIN_GPIO_5
		configuration.mc_b_positive_limit_input = controller.PIN_GPIO_6
		configuration.mc_b_negative_limit_input = controller.PIN_GPIO_7

		# Set the first input pins so that any changes are reported by
		# calling inputs_changed on this driver class:
		for pin in configuration.pins[:48]:
			pin.report_input = True

		# Send the configuration to the controller:
		d = self.host.configure(configuration)

		# The deferred is completed once the configuration is written:
		d.addCallback(self._initialise_configuration_written)
		d.addErrback(self._initialise_error_occurred)

		return d

	def _initialise_configuration_written(self, configuration):
		self.log("* Successfully Configured")

		# Schedule the first call of a timer that will toggle the output every second:
		self.host.add_timer(1.0, self._turn_output_on)

		# Schedule a timer to check the counters:
		self.host.add_timer(1.0, self._check_counters)

		# Schedule a guider set:
		# self.host.add_timer(1.0, self._set_guider_values)

	def _set_guider_values(self):
		d = self.host.set_guider_values(controller.GUIDER_RUN_AT_NEXT_AVAILABLE_FRAME, 0, \
		  [(5, -5), (10, -10), (15, -15), (15, -15), (10, -10), (5, -5)])

		d.addCallback(self._set_guider_values_completed)

	def _set_guider_values_completed(self, result):
		print "* Guider Result: Frame %s, Count %s" % (result.frame, result.count)

		self.host.add_timer(random.random() * 2, self._set_guider_values)

	def _initialise_error_occurred(self, failure):
		self.log("* Configuration Failed:")

		failure.printTraceback()

		self.host.stop()

	def _turn_output_on(self):
		# Turn the output on, and set the timer to turn it off later:
		self.host.set_outputs(1 << controller.PIN_GPIO_8)

		self.host.add_timer(1.0, self._turn_output_off)

	def _turn_output_off(self):
		# Turn the output off, and set the timer to turn it on later:
		self.host.clear_outputs(1 << controller.PIN_GPIO_8)

		self.host.add_timer(1.0, self._turn_output_on)

	def _check_counters(self):
		d = self.host.get_counters()
	
		d.addCallback(self._complete_check_counters)

		d = self.host.get_debug_registers()

		d.addCallback(self._get_debug_registers_completed)

		# Additional requests:
		d = self.host.get_debug_registers()

		d.addCallback(self._get_debug_registers_completed)

		d = self.host.get_debug_registers()

		d.addCallback(self._get_debug_registers_completed)

	def _get_debug_registers_completed(self, registers):
		last, worst = registers

	def _complete_check_counters(self, counters):
		self.log( \
		  "* Frame %s, (%s, %s) total steps, (%s, %s) guider steps, (%s, %s) measured." % ( \
		  counters.reference_frame_number, \
		  counters.a_total_steps, \
		  counters.b_total_steps, \
		  counters.a_guider_steps, \
		  counters.b_guider_steps, \
		  counters.a_measured_steps, \
		  counters.b_measured_steps))

		self.host.add_timer(1.0, self._check_counters)

	def enqueue_frame_available(self, details):
		if details.frames_in_queue < 12:
			a_steps, b_steps = source.next()

			frame_number = self.host.enqueue_frame(a_steps, b_steps)
	
			# Every "frame" of step data has a unique number, starting with
			# zero. Step counts and guider step counts when queried are
			# also associated with a frame number:
			if frame_number % 20 == 0:
				self.log("* Enqueued Frame (%s)" % frame_number)

			self.last_enqueue_frame_number = frame_number

			#self.log("*** Transmitted %s, (En %s, De %s), %s in queue." % \
			#  (details.last_transmitted_frame, details.last_enqueued_frame, \
			#  details.last_dequeued_frame, details.frames_in_queue))

	def _get_exception_completed(self, details):
		print "Exception Details: %s" % details

		self.host.stop()

	def inputs_changed(self, inputs):
		self.input_count += 1

		self.log("* Inputs Changed (currently %s, %s changes)" % \
		  (hex(inputs), self.input_count))
	
		if self.input_count % 100 == 0:
			self.log("* Inputs Changed (currently %s, %s changes)" % \
			  (hex(inputs), self.input_count))

if __name__ == "__main__":
	source = Source()
	driver = Driver(source)

	# Enter the polling loop. The default poller (returned by select.poll) can
	# also be replaced with any object implementing the methods required by libusb1:
	controller.run(driver = driver)

