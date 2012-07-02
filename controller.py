#! /usr/local/bin/python2.7
# coding=latin1

# Copyright © Bit Plantation Pty Ltd (ACN 152 088 634). All Rights Reserved.
# This file is internal, confidential source code and is protected by
# trade secret and copyright laws.

import select, struct, time, math, heapq
import usb1, libusb1

from twisted.internet import defer
from twisted.python import failure

# These are workarounds for omissions or bugs in python-libusb1; the author
# of the library has been notified about them:
def _patched_getUserData(self):
    return self._USBTransfer__transfer.contents.user_data

class _patched_Poller(object):
	def __init__(self, poller):
		self._poller = poller

	def register(self, fd, event_flags):
		self._poller.register(fd, event_flags)

	def unregister(self, fd):
		self._poller.unregister(fd)

	def poll(self, timeout_in_seconds):
		if timeout_in_seconds is not None:
			self._poller.poll(int(math.ceil(timeout_in_seconds * 1000)))
		else:
			self._poller.poll(None)

usb1.USBTransfer.getUserData = _patched_getUserData

TC_ISSUE_STATE_COMMAND = 0x00
TC_GET_VERSION = 0x01
TC_MC_CONFIGURE = 0x02
TC_GPIO_CONFIGURE = 0x03
TC_WRITE_OUTPUTS = 0x04
TC_ENQUEUE = 0x05
TC_GET_COUNTERS = 0x06

TC_STATE_COMMAND_RESET_QUEUE = 0x00
TC_STATE_COMMAND_SHUTDOWN = 0x01
TC_STATE_COMMAND_RESET_IO = 0x02
TC_STATE_COMMAND_ENABLE_GUIDER = 0x03
TC_STATE_COMMAND_DISABLE_GUIDER = 0x04
TC_STATE_COMMAND_FORCE_INTERRUPT = 0x05

TC_STATE_IDLE = 0x00
TC_STATE_RUNNING = 0x01
TC_STATE_EXCEPTION = 0x02

TC_EXCEPTION_NONE = 0x00000000
TC_EXCEPTION_QUEUE_UNDERFLOW = 0x00000001
TC_EXCEPTION_QUEUE_NONSEQUENTIAL_FRAME_NUMBER = 0x00000002
TC_EXCEPTION_ACCELERATION_LIMIT_EXCEEDED = 0x00000003
TC_EXCEPTION_VELOCITY_LIMIT_EXCEEDED = 0x00000004
TC_EXCEPTION_DIRECTION_CHANGE_AT_NONZERO_VELOCITY = 0x00000005
TC_EXCEPTION_SHUTDOWN_REQUESTED = 0x00000006
TC_EXCEPTION_INVALID_CONFIGURATION = 0x00000007
TC_EXCEPTION_INTERNAL_UNDERRUN = 0x00000008
TC_EXCEPTION_INTERNAL_ERROR = 0x00000009
TC_EXCEPTION_MCA_POSITIVE_LIMITED = 0x0000000a
TC_EXCEPTION_MCA_NEGATIVE_LIMITED = 0x0000000b
TC_EXCEPTION_MCB_POSITIVE_LIMITED = 0x0000000c
TC_EXCEPTION_MCB_NEGATIVE_LIMITED = 0x0000000d

PIN_GPIO_0 = 0
PIN_GPIO_1 = 1
PIN_GPIO_2 = 2
PIN_GPIO_3 = 3
PIN_GPIO_4 = 4
PIN_GPIO_5 = 5
PIN_GPIO_6 = 6
PIN_GPIO_7 = 7
PIN_GPIO_8 = 8
PIN_GPIO_9 = 9
PIN_GPIO_10 = 10
PIN_GPIO_11 = 11
PIN_GPIO_12 = 12
PIN_GPIO_13 = 13
PIN_GPIO_14 = 14
PIN_GPIO_15 = 15
PIN_GPIO_16 = 16
PIN_GPIO_17 = 17
PIN_GPIO_18 = 18
PIN_GPIO_19 = 19
PIN_GPIO_20 = 20
PIN_GPIO_21 = 21
PIN_GPIO_22 = 22
PIN_GPIO_23 = 23
PIN_GPIO_24 = 24
PIN_GPIO_25 = 25
PIN_GPIO_26 = 26
PIN_GPIO_27 = 27
PIN_GPIO_28 = 28
PIN_GPIO_29 = 29
PIN_GPIO_30 = 30
PIN_GPIO_31 = 31
PIN_GPIO_32 = 32
PIN_GPIO_33 = 33
PIN_GPIO_34 = 34
PIN_GPIO_35 = 35
PIN_GPIO_36 = 36
PIN_GPIO_37 = 37
PIN_GPIO_38 = 38
PIN_GPIO_39 = 39
PIN_GPIO_40 = 40
PIN_GPIO_41 = 41
PIN_GPIO_42 = 42
PIN_GPIO_43 = 43
PIN_GPIO_44 = 44
PIN_GPIO_45 = 45
PIN_GPIO_46 = 46
PIN_GPIO_47 = 47
PIN_MCA_SP = 48
PIN_MCA_SN = 49
PIN_MCA_DP = 50
PIN_MCA_DN = 51
PIN_MCA_OP = 52
PIN_MCA_ON = 53
PIN_MCB_SP = 54
PIN_MCB_SN = 55
PIN_MCB_DP = 56
PIN_MCB_DN = 57
PIN_MCB_OP = 58
PIN_MCB_ON = 59
PIN_MCA_QA = 60
PIN_MCA_QB = 61
PIN_MCB_QA = 62
PIN_MCB_QB = 63

TC_MC_UNUSED_INPUT = 0xff

MC_PIN_FLAG_INVERT_MCA_SP = (1 << 0)
MC_PIN_FLAG_INVERT_MCA_SN = (1 << 1)
MC_PIN_FLAG_INVERT_MCA_DP = (1 << 2)
MC_PIN_FLAG_INVERT_MCA_DN = (1 << 3)
MC_PIN_FLAG_INVERT_MCA_OP = (1 << 4)
MC_PIN_FLAG_INVERT_MCA_ON = (1 << 5)
MC_PIN_FLAG_INVERT_MCB_SP = (1 << 6)
MC_PIN_FLAG_INVERT_MCB_SN = (1 << 7)
MC_PIN_FLAG_INVERT_MCB_DP = (1 << 8)
MC_PIN_FLAG_INVERT_MCB_DN = (1 << 9)
MC_PIN_FLAG_INVERT_MCB_OP = (1 << 10)
MC_PIN_FLAG_INVERT_MCB_ON = (1 << 11)

MC_PIN_FLAG_MCA_O_FUNCTION_LOW = (0 << 12)
MC_PIN_FLAG_MCA_O_FUNCTION_HIGH = (1 << 12)
MC_PIN_FLAG_MCA_O_FUNCTION_RUNNING = (2 << 12)
MC_PIN_FLAG_MCA_O_FUNCTION_FRAME_CLOCK = (3 << 12)

MC_PIN_FLAG_MCB_O_FUNCTION_LOW = (0 << 14)
MC_PIN_FLAG_MCB_O_FUNCTION_HIGH = (1 << 14)
MC_PIN_FLAG_MCB_O_FUNCTION_RUNNING = (2 << 14)
MC_PIN_FLAG_MCB_O_FUNCTION_FRAME_CLOCK = (3 << 14)

fpga_control_bit_descriptions = [ \
	"CONTROL_BIT_ENABLE_MC", \
	"CONTROL_BIT_ENABLE_IO", \
	"CONTROL_BIT_ERRORS_PENDING", \
	"CONTROL_BIT_INPUTS_CHANGED", \
	"CONTROL_BIT_SLOTS_EMPTY", \
	"CONTROL_BIT_SLOTS_EMPTIED", \
	"CONTROL_BIT_INDICATOR_BITS_CHANGED", \
	"CONTROL_BIT_ERRORS_CHANGED", \
	"CONTROL_BIT_POWERED_ON", \
	"CONTROL_BIT_IO_READY", \
	"CONTROL_BIT_CONFIGURED"]

fpga_error_bit_descriptions = [ \
	"ERROR_BIT_MCA_S_CONFIGURATION", \
	"ERROR_BIT_MCA_D_CONFIGURATION", \
	"ERROR_BIT_MCA_O_CONFIGURATION", \
	"ERROR_BIT_MCB_S_CONFIGURATION", \
	"ERROR_BIT_MCB_D_CONFIGURATION", \
	"ERROR_BIT_MCB_O_CONFIGURATION", \
	"ERROR_BIT_MCA_Q_CONFIGURATION", \
	"ERROR_BIT_MCB_Q_CONFIGURATION", \
	"ERROR_BIT_MC_SYNCHRONISATION_LOSS", \
	"ERROR_BIT_MCA_SLOTS_OVERUN", \
	"ERROR_BIT_MCA_SLOTS_UNDERRUN", \
	"ERROR_BIT_MCB_SLOTS_OVERUN", \
	"ERROR_BIT_MCB_SLOTS_UNDERRUN", \
	"ERROR_BIT_IO_SUPPLY_ERROR", \
	"ERROR_BIT_REGISTERS_MISO_UNDERRUN", \
	"ERROR_BIT_IO_SPI_OVERRUN", \
	"ERROR_BIT_MCA_POSITIVE_LIMITED", \
	"ERROR_BIT_MCA_NEGATIVE_LIMITED", \
	"ERROR_BIT_MCB_POSITIVE_LIMITED", \
	"ERROR_BIT_MCB_NEGATIVE_LIMITED", \
	"ERROR_BIT_LAST"]

exception_descriptions = [ \
	"TC_EXCEPTION_NONE", \
	"TC_EXCEPTION_QUEUE_UNDERFLOW", \
	"TC_EXCEPTION_QUEUE_NONSEQUENTIAL_FRAME_NUMBER", \
	"TC_EXCEPTION_ACCELERATION_LIMIT_EXCEEDED", \
	"TC_EXCEPTION_VELOCITY_LIMIT_EXCEEDED", \
	"TC_EXCEPTION_DIRECTION_CHANGE_AT_NONZERO_VELOCITY", \
	"TC_EXCEPTION_SHUTDOWN_REQUESTED", \
	"TC_EXCEPTION_INVALID_CONFIGURATION", \
	"TC_EXCEPTION_INTERNAL_UNDERRUN", \
	"TC_EXCEPTION_INTERNAL_ERROR", \
	"TC_EXCEPTION_MCA_POSITIVE_LIMITED", \
	"TC_EXCEPTION_MCA_NEGATIVE_LIMITED", \
	"TC_EXCEPTION_MCB_POSITIVE_LIMITED", \
	"TC_EXCEPTION_MCB_NEGATIVE_LIMITED"]

CONTROLLER_PIN_INPUT = 0
CONTROLLER_PIN_OUTPUT = 1

CONTROLLER_PIN_FUNCTION_GPIO = 0
CONTROLLER_PIN_FUNCTION_SPECIAL = 1

class ControllerPin(object):
	def __init__(self, number):
		self.number = number
		self.direction = CONTROLLER_PIN_INPUT
		self.function = CONTROLLER_PIN_FUNCTION_GPIO
		self.invert_input = False
		self.report_input = True

class ControllerException(Exception):
	pass

class ControllerConfigurationException(ControllerException):
	pass

class ControllerNotConnectedException(ControllerException):
	pass

class MultipleControllersConnectedException(ControllerException):
	pass

class ControllerConfiguration(object):
	def __init__(self):
		self.mc_prefill_frames = 8
		self.mc_pin_flags = 0
		self.mc_a_shutdown_acceleration = 1
		self.mc_b_shutdown_acceleration = 1
		self.mc_a_acceleration_limit = 500
		self.mc_b_acceleration_limit = 500
		self.mc_a_velocity_limit = 7600
		self.mc_b_velocity_limit = 7600
		self.mc_frame_period = 1200000
		self.mc_pulse_width = 120
		self.mc_a_positive_limit_input = None
		self.mc_a_negative_limit_input = None
		self.mc_b_positive_limit_input = None
		self.mc_b_negative_limit_input = None
		self.mc_a_positive_guider_input = None
		self.mc_a_negative_guider_input = None
		self.mc_b_positive_guider_input = None
		self.mc_b_negative_guider_input = None

		self.mc_guider_counter_divider = 12000
		self.mc_guider_a_numerator = 1
		self.mc_guider_a_denominator = 10
		self.mc_guider_a_limit = 20
		self.mc_guider_b_numerator = 1
		self.mc_guider_b_denominator = 10
		self.mc_guider_b_limit = 20

		self.pins = []

		for i in range(64):
			self.pins.append(ControllerPin(i))

	def encode_gpio(self):
		direction = 0L
		function = 0L
		invert_input = 0L
		report_input = 0L

		for i in range(64):
			if self.pins[i].direction == CONTROLLER_PIN_OUTPUT:
				direction |= (1L << i)

			if self.pins[i].function == CONTROLLER_PIN_FUNCTION_SPECIAL:
				function |= (1L << i)

			if self.pins[i].invert_input:
				invert_input |= (1L << i)

			if self.pins[i].report_input:
				report_input |= (1L << i)

		return struct.pack("<QQQQ", \
		  direction, \
		  function, \
		  invert_input, \
		  report_input)

	def _encode_input(self, value):
		if value is None:
			return TC_MC_UNUSED_INPUT
		elif 0 <= value <= 64:
			return value
		else:
			raise ControllerConfigurationException( \
			  "An invalid input was specified.")

	def encode_mc(self):
		return struct.pack("<HHHHHHHHLLBBBBBBBBLHHHHHH", \
		  self.mc_prefill_frames, \
		  self.mc_pin_flags, \
		  self.mc_a_shutdown_acceleration, \
		  self.mc_b_shutdown_acceleration, \
		  self.mc_a_acceleration_limit, \
		  self.mc_b_acceleration_limit, \
		  self.mc_a_velocity_limit, \
		  self.mc_b_velocity_limit, \
		  self.mc_frame_period, \
		  self.mc_pulse_width, \
		  self._encode_input(self.mc_a_positive_limit_input), \
		  self._encode_input(self.mc_a_negative_limit_input), \
		  self._encode_input(self.mc_b_positive_limit_input), \
		  self._encode_input(self.mc_b_negative_limit_input), \
		  self._encode_input(self.mc_a_positive_guider_input), \
		  self._encode_input(self.mc_a_negative_guider_input), \
		  self._encode_input(self.mc_b_positive_guider_input), \
		  self._encode_input(self.mc_b_negative_guider_input), \
		  self.mc_guider_counter_divider, \
		  self.mc_guider_a_numerator, \
		  self.mc_guider_a_denominator, \
		  self.mc_guider_a_limit, \
		  self.mc_guider_b_numerator, \
		  self.mc_guider_b_denominator, \
		  self.mc_guider_b_limit)

class UsbTransferError(object):
	def __init__(self, status):
		self.status = status

class EnqueueDetails(object):
	def __init__(self, controller):
		self.last_transmitted_frame = controller._last_transmitted_frame
		self.last_enqueued_frame = controller._last_enqueued_frame
		self.last_dequeued_frame = controller._last_dequeued_frame

		self.frames_in_queue = \
		  (self.last_transmitted_frame - self.last_dequeued_frame) % 0x100000000L
		self.frames_queue_capacity = controller.mc_frames_capacity

class StateDetails(object):
	def __init__(self, controller, state, exception):
		self.state = state
		self.exception = exception

	def __repr__(self):
		if self.state == TC_STATE_EXCEPTION:
			return "<StateDetails %s (%s)>" % \
			  (self.state_description, self.exception_description)
		else:
			return "<StateDetails %s>" % self.state_description

	@property
	def state_description(self):
		if self.state == TC_STATE_IDLE:
			return "TC_STATE_IDLE"
		elif self.state == TC_STATE_RUNNING:
			return "TC_STATE_RUNNING"
		elif self.state == TC_STATE_EXCEPTION:
			return "TC_STATE_EXCEPTION"
		else:
			return "(Unknown State Code)"

	@property
	def exception_description(self):
		if 0 <= self.exception <= len(exception_descriptions):
			return exception_descriptions[self.exception]
		else:
			return "(Unknown Exception Code)"

class CounterDetails(object):
	pass

class ControllerTimer(object):
	def __init__(self, controller, expiry_time, callback):
		self._controller = controller
		self._expiry_time = expiry_time
		self._callback = callback
		self._cancelled = False

	def __cmp__(self, rhs):
		return cmp(self._expiry_time, rhs._expiry_time)

class Controller(object):
	def __init__(self, driver):
		# Keep a reference to the driver:
		self._driver = driver

		# Open and set the USB configuration of the controller:
		self._context = usb1.LibUSBContext()
		self._device_handle = self._find_and_open_device()
		self._device = self._device_handle.getDevice()

		self._configuration = self._device[0]
		self._interface = self._configuration[0]
		self._setting = self._interface[0]

		self._device_handle.setConfiguration( \
		  self._configuration.getConfigurationValue())

		self._device_handle.claimInterface(0)

		# Initialise state:
		self._last_transmitted_frame = 0xffffffffL
		self._last_enqueued_frame = 0xffffffffL
		self._last_dequeued_frame = 0xffffffffL

		self._enqueue_in_progress = False

		self._last_inputs = 0L
		self._last_outputs = 0L
		self._last_state = None

		self._running = True

		self._timers_heap = []

	def _find_and_open_device(self):
		device_handles = []

		vendor_id = 0x1bad
		product_id = 0xbeef

		# Build a list of the connected controllers:
		for device_handle in self._context.getDeviceList():
			if device_handle.getVendorID() == vendor_id and \
			  device_handle.getProductID() == product_id:
				device_handles.append(device_handle)
				break

		# Complain if we don't have exactly one:
		if len(device_handles) == 0:
			raise ControllerNotConnectedException( \
			  "No controllers were found.")
		elif len(device_handles) > 1:
			raise MultipleControllersConnectedException( \
			  "More than one controller was found, and using multiple " \
			  "controllers is not currently supported.")

		# Open and return it:
		return device_handle.open()

	def _close(self):
		self._device_handle.close()

		self._context.exit()

	def _control_write(self, command, data = ""):
		d = defer.Deferred()

		transfer = self._device_handle.getTransfer()
		transfer.setControl( \
			libusb1.LIBUSB_TYPE_VENDOR | \
			libusb1.LIBUSB_ENDPOINT_OUT | \
			libusb1.LIBUSB_RECIPIENT_DEVICE, \
			command, 0, 0, data, self._complete_control_write, d)
		transfer.submit()

		return d

	def _complete_control_write(self, transfer):
		deferred = transfer.getUserData()

		status = transfer.getStatus()

		if status == libusb1.LIBUSB_TRANSFER_COMPLETED:
			written = transfer.getActualLength()

			transfer.close()

			deferred.callback(written)
		else:
			transfer.close()

			deferred.errback(UsbTransferError(status))

	def _control_read(self, command, data_length = 0):
		d = defer.Deferred()

		transfer = self._device_handle.getTransfer()
		transfer.setControl( \
			libusb1.LIBUSB_TYPE_VENDOR | \
			libusb1.LIBUSB_ENDPOINT_IN | \
			libusb1.LIBUSB_RECIPIENT_DEVICE, \
			command, 0, 0, data_length, self._complete_control_read, d)
		transfer.submit()

		return d

	def _complete_control_read(self, transfer):
		deferred = transfer.getUserData()

		status = transfer.getStatus()

		if status == libusb1.LIBUSB_TRANSFER_COMPLETED:
			read = transfer.getBuffer()

			transfer.close()

			deferred.callback(read)
		else:
			transfer.close()

			deferred.errback(UsbTransferError(status))

	def _initiate_interrupt_read(self):
		transfer = self._device_handle.getTransfer()
		transfer.setInterrupt(
			0x81, 24, self._complete_interrupt_read)
		transfer.submit()

	def _complete_interrupt_read(self, transfer):
		if transfer.getStatus() == libusb1.LIBUSB_TRANSFER_COMPLETED:
			buffer = transfer.getBuffer()

			changed, state, flags, exception, inputs, \
			  last_enqueued_frame, last_dequeued_frame = \
			  struct.unpack("<BBHLQLL", buffer)

			self._last_enqueued_frame = last_enqueued_frame
			self._last_dequeued_frame = last_dequeued_frame

			if self._last_state != state:
				self._last_state = state

				self._driver.state_changed(StateDetails(self, state, exception))

			if self._last_inputs != inputs:
				self._last_inputs = inputs

				self._driver.inputs_changed(inputs)

			if False:
				print "FRAMES:", last_enqueued_frame, last_dequeued_frame

				for i, description in enumerate(control_bit_descriptions):
					if control & (1 << i): print description

				for i, description in enumerate(error_bit_descriptions):
					if errors & (1 << i): print description

			self._initiate_interrupt_read()

			if not self._enqueue_in_progress:
				self._call_enqueue_available()
				
		else:
			print "Interrupt transfer failed", `transfer.getStatus()`

		transfer.close()

	def reset_queue(self):
		"""Resets the queue while leaving the controller configured.

		Resetting the queue:

		- Returns the controller to idle,
		- Resets the frame numbering so that the next expected frame number is zero.
		- Clears the step counters.

		The configuration and output states are unchanged.

		Resetting the queue while the motor control outputs are active will fail.

		The returned deferred completes when the controller has been successfully
		reset.
		"""
		d = self._control_write(TC_ISSUE_STATE_COMMAND, \
		  struct.pack("<L", TC_STATE_COMMAND_RESET_QUEUE))

		d.addCallback(self._state_command_completed)

		return d

	def shutdown(self):
		"""Raises a controller exception that causes the controller to start a ramped shutdown.

		After running this command, the exception state will be reported with the
		controller.TC_EXCEPTION_SHUTDOWN_REQUESTED exception. To use the controller again
		a queue reset must be issued.

		The returned deferred completes when the command has been issued; the shutdown exception
		may be delivered before or after the deferred callbacks are run.
		"""

		d = self._control_write(TC_ISSUE_STATE_COMMAND, \
		  struct.pack("<L", TC_STATE_COMMAND_SHUTDOWN))

		d.addCallback(self._state_command_completed)

		return d

	def enable_guider(self):
		"""Starts adding guider steps to the motor control frames.

		The returned deferred completes when the command has been successfully issued.
		"""

		d = self._control_write(TC_ISSUE_STATE_COMMAND, \
		  struct.pack("<L", TC_STATE_COMMAND_ENABLE_GUIDER))

		d.addCallback(self._state_command_completed)

		return d

	def disable_guider(self):
		"""Stops adding guider steps to the motor control frames.

		The returned deferred completes when the command has been successfully issued.
		"""

		d = self._control_write(TC_ISSUE_STATE_COMMAND, \
		  struct.pack("<L", TC_STATE_COMMAND_DISABLE_GUIDER))

		d.addCallback(self._state_command_completed)

		return d

	def _state_command_completed(self, bytes_written):
		return None

	def configure(self, configuration):
		"""Writes a configuration to the controller.

		The returned deferred completes when the configuration has been
		successfully written.
		"""
		d = self._control_write(TC_MC_CONFIGURE, \
		  configuration.encode_mc())

		d.addCallback(self._configure_mc_completed, configuration)

		return d

	def _configure_mc_completed(self, bytes_written, configuration):
		d = self._control_write(TC_GPIO_CONFIGURE, \
		  configuration.encode_gpio())

		d.addCallback(self._configure_both_completed, configuration)

		return d

	def _configure_both_completed(self, bytes_written, configuration):
		return configuration

	def _initialise_internals(self):
		d = self._control_read(TC_GET_VERSION, 16)

		d.addCallback(self._initialise_internals_handle_version)
		d.addErrback(self._handle_error)

	def _initialise_internals_handle_version(self, buffer):
		mcu_minor, mcu_major, fpga_minor, fpga_major, \
		  self.clock_frequency, self.mc_frames_capacity, reserved = \
		  struct.unpack("<HHHHLHH", buffer)

		self.mcu_version = (mcu_major, mcu_minor)
		self.fpga_version = (fpga_major, fpga_minor)

		d = self._control_write(TC_ISSUE_STATE_COMMAND, \
		  struct.pack("<L", TC_STATE_COMMAND_FORCE_INTERRUPT))

		d.addCallback(self._initialise_internals_completed)
		d.addErrback(self._handle_error)

	def _initialise_internals_completed(self, bytes_written):
		self._driver.initialise()

	def add_timer(self, seconds, callback):
		"""Schedules a (once off) call to the callback function.

		The returned handle can be passed to cancel_timer to cancel the callback before
		it has occurred.""" 
		timer = ControllerTimer(self, time.time() + seconds, callback)

		heapq.heappush(self._timers_heap, timer)

		return timer

	def cancel_timer(self, timer):
		"""Cancels a callback."""
		timer._cancelled = True

	def _run_timer_callbacks(self):
		now = time.time()

		while len(self._timers_heap) >= 1:
			timer = self._timers_heap[0]

			if now > timer._expiry_time:
				heapq.heappop(self._timers_heap)

				if not timer._cancelled:
					timer._callback()
			else:
				break

	def run(self, system_poller):
		"""Runs the event loop, after calling the driver initialisation method.

		Driver event handlers and timers are handled by the event loop. Optionally, a
		user supplied poller can be passed in. The poller must implement the interface
		described in the python-libusb1 library."""
		poller = usb1.USBPoller(self._context, system_poller)

		self._initiate_interrupt_read()

		self._initialise_internals()

		self._running = True

		while self._running:
			if len(self._timers_heap) >= 1:
				# There are timers to eventually call:
				next_timer = self._timers_heap[0]

				next_timer_time = next_timer._expiry_time - time.time()

				if next_timer_time < 0.0: next_timer_time = 0.0

				poller.poll(next_timer_time)

				self._run_timer_callbacks()
			else:
				# No timers, just wait for file events:
				poller.poll()

		self._close()

	def stop(self):
		"""Called in event handlers or timers to stop the event loop."""
		self._running = False

	def set_outputs(self, outputs):
		"""Sets the specified GPIO bits high on the controller card.

		The outputs should be specified as a 64 bit long bitmask. Bits not in the 
		bitmask are left in their current state."""
		self._last_outputs = self._last_outputs | outputs

		d = self._control_write(TC_WRITE_OUTPUTS, struct.pack("<Q", self._last_outputs))

		return d

	def clear_outputs(self, outputs):
		"""Sets the specified GPIO bits low on the controller card.

		The outputs should be specified as a 64 bit long bitmask. Bits not in the 
		bitmask are left in their current state."""
		self._last_outputs = self._last_outputs & ~outputs

		d = self._control_write(TC_WRITE_OUTPUTS, struct.pack("<Q", self._last_outputs))

	def _handle_error(self, failure):
		failure.printTraceback()

	def enqueue_frame(self, a_steps, b_steps):
		"""Enqueues a frame and returns the frame number of the enqueued frame.

		This method should only be called from within the enqueue_frame_available driver
		event, and should only be called once per call to enqueue_frame_available. Once 
		the frame has been successfully enqueued another call to enqueue_frame_available is
		made, allowing more frames to be enqueued if required."""
		assert not self._enqueue_in_progress 

		self._enqueue_in_progress = True

		self._last_transmitted_frame = \
			(self._last_transmitted_frame + 1) % 0x100000000L

		frame_number = self._last_transmitted_frame

		assert -32768 <= a_steps <= 32767
		assert -32768 <= b_steps <= 32767

		control_data = struct.pack("<Lhh", frame_number, a_steps, b_steps)

		d = self._control_write(TC_ENQUEUE, control_data)
		d.addCallback(self._handle_enqueue_completed)
		d.addErrback(self._handle_error)

		return frame_number

	def _handle_enqueue_completed(self, bytes_written):
		self._enqueue_in_progress = False

		self._call_enqueue_available()

	def _handle_enqueue_error(self, failure):
		self._enqueue_in_progress = False

		failure.printTraceback()

	def _call_enqueue_available(self):
		details = EnqueueDetails(self)

		self._driver.enqueue_frame_available(details)

	def get_counters(self):
		d = self._control_read(TC_GET_COUNTERS, 20)

		d.addCallback(self._get_counters_completed)
		d.addErrback(self._handle_error)

		return d

	def _get_counters_completed(self, buffer):
		counters = CounterDetails()

		counters.at_start_of_frame_number, \
		counters.a_total_steps, \
		counters.b_total_steps, \
		counters.a_guider_steps, \
		counters.b_guider_steps = struct.unpack("<Lllll", buffer)

		return counters

class Driver(object):
	def internal_attach_host(self, host):
		self.host = host

	def initialise(self):
		"""Called when the controller first starts the event loop.

		During initialisation, the driver can check the current state of the controller,
		read counters from previous runs, and reset the queue or hardware.
		"""
		pass

	def enqueue_frame_available(self, details):
		"""Called when the frame queue changes.

		This method is called when the queue changes (for example, when
		a frame is dequeued, or when a previous enqueue completes). It should 
		check the state of the queue and, if required, enqueue at most one frame. 
		Once the frame is enqueued the controller will immediately call this method
		to allow another to be enqueued.

		The driver is expected to manage the level of the queue itself, by setting
		the frame prefill to the desired level and by only enqueuing frames when 
		necessary to maintain the desired queue level.

		An instance of controller.EnqueueDetails is passed in, providing:

		- last_transmitted_frame, the last frame number that this module transmitted
		  to the controller.
		- last_enqueued_frame, the last frame number the controller has reported to have
		  received. This may be an earlier frame than last_transmitted_frame (because the
		  controller reports this field asynchronously) and should not be used to estimate
		  the number of frames in the queue.
		- last_dequeued_frame, the last frame number that was dequeued and loaded on to the
		  FPGA for generation of steps.
		- frames_in_queue, the number of frames currently either in the queue or being
		  enqueued. This count is the difference between last_transmitted_frame and
		  last_dequeued_frame. Since the dequeuing process runs independently from the
		  enqueuing process, frames_in_queue may include an extra count from a frame that
		  has been dequeued on the controller but not yet reported as dequeued.
		- frames_queue_capacity, the maximum number of frames that can be enqueued. The
		  queue level is typically maintained below the capacity to minimise control latency.
		"""

	def state_changed(self, details):
		"""Called when the state of the controller changes.

		An instance of controller.StateDetails is passed in, providing the
		state field which is one of the following values:

		- controller.TC_STATE_IDLE
		- controller.TC_STATE_RUNNING
		- controller.TC_STATE_EXCEPTION

		And the exception field, which is one of the following values:

		- controller.TC_EXCEPTION_QUEUE_UNDERFLOW
		- controller.TC_EXCEPTION_QUEUE_NONSEQUENTIAL_FRAME_NUMBER
		- controller.TC_EXCEPTION_ACCELERATION_LIMIT_EXCEEDED
		- controller.TC_EXCEPTION_VELOCITY_LIMIT_EXCEEDED
		- controller.TC_EXCEPTION_DIRECTION_CHANGE_AT_NONZERO_VELOCITY
		- controller.TC_EXCEPTION_SHUTDOWN_REQUESTED
		- controller.TC_EXCEPTION_INVALID_CONFIGURATION
		- controller.TC_EXCEPTION_INTERNAL_UNDERRUN
		- controller.TC_EXCEPTION_INTERNAL_ERROR
		- controller.TC_EXCEPTION_MCA_POSITIVE_LIMITED
		- controller.TC_EXCEPTION_MCA_NEGATIVE_LIMITED
		- controller.TC_EXCEPTION_MCB_POSITIVE_LIMITED
		- controller.TC_EXCEPTION_MCB_NEGATIVE_LIMITED

		For printing state details, use the state_description and exception_description properties.
		"""

	def inputs_changed(self, inputs):
		"""Called when any of the reportable inputs have changed.

		The reportable inputs are set in the configuration. The inputs are passed in as
		a long integer bit mask.
		"""
		pass

def run(driver, system_poller = None):
	instance = Controller(driver)

	driver.internal_attach_host(instance)

	if system_poller is None:
		system_poller = _patched_Poller(select.poll())

	instance.run(system_poller)

