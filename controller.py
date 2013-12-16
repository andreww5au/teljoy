#! /usr/local/bin/python2.7
# coding=latin1

# Copyright © Bit Plantation Pty Ltd (ACN 152 088 634). All Rights Reserved.
# This file is internal, confidential source code and is protected by
# trade secret and copyright laws.

import select, struct, time, math, heapq, sys
import usb1, libusb1

from twisted.internet import defer
from twisted.python import failure

module_version = (0, 6)

# These are workarounds for omissions or bugs in python-libusb1; the author
# of the library has been notified about them:
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

assert getattr(usb1.USBTransfer, "getUserData") is not None, \
  "A newer version of the python-libusb1 library is required."

TC_ISSUE_STATE_COMMAND = 0x00
TC_GET_VERSION = 0x01
TC_MC_CONFIGURE = 0x02
TC_GPIO_CONFIGURE = 0x03
TC_SAFETY_CONFIGURE = 0x04
TC_WRITE_OUTPUTS = 0x05
TC_ENQUEUE = 0x06
TC_GET_COUNTERS = 0x07
TC_GET_DEBUG_REGISTERS = 0x08
TC_SET_GUIDER_VALUES = 0x09
TC_GET_GUIDER_RESULT = 0x0a
TC_GET_EXCEPTION_DETAILS_LENGTH = 0x0b
TC_GET_EXCEPTION_DETAILS = 0x0c
TC_GET_EXCEPTION = 0x0d
TC_CLEAR_EXCEPTION = 0x0e

TC_STATE_COMMAND_SHUTDOWN = 0x01
TC_STATE_COMMAND_RESET_IO = 0x02
TC_STATE_COMMAND_ENABLE_GUIDER = 0x03
TC_STATE_COMMAND_DISABLE_GUIDER = 0x04
TC_STATE_COMMAND_FORCE_INTERRUPT = 0x05

TC_STATE_IDLE = 0x00
TC_STATE_RUNNING = 0x01
TC_STATE_STOPPING = 0x02
TC_STATE_EXCEPTION = 0x03

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
TC_EXCEPTION_QUEUE_INTERRUPT_UNEXPECTED = 0x0000000e
TC_EXCEPTION_INVALID_FPGA_EXCEPTION_BITMAP = 0x0000000f
TC_EXCEPTION_IO_SUPPLY_ERROR = 0x00000010
TC_EXCEPTION_STEP_COMPUTATION_OVERFLOW = 0x00000011
TC_EXCEPTION_SHUTDOWN_INPUT_TRIGGERED = 0x00000012
TC_EXCEPTION_UNEXPECTED_FPGA_RESET = 0x00000013
TC_EXCEPTION_FPGA_READBACK_ERROR = 0x00000014
TC_EXCEPTION_UNEXPECTED_STEPPER_STOP = 0x00000015
TC_EXCEPTION_CLEARING_EXCEPTION_FAILED = 0x00000016

clearable_exceptions = [ \
  TC_EXCEPTION_QUEUE_UNDERFLOW,
  TC_EXCEPTION_SHUTDOWN_REQUESTED,
  TC_EXCEPTION_MCA_POSITIVE_LIMITED,
  TC_EXCEPTION_MCA_NEGATIVE_LIMITED,
  TC_EXCEPTION_MCB_POSITIVE_LIMITED,
  TC_EXCEPTION_MCB_NEGATIVE_LIMITED,
  TC_EXCEPTION_SHUTDOWN_INPUT_TRIGGERED]

TC_DETAIL_KIND_AXIS_TRACE = 0x00000001
TC_DETAIL_KIND_FPGA_ERRORS = 0x00000002

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

GUIDER_RUN_AT_NEXT_AVAILABLE_FRAME = 1
GUIDER_RUN_AT_FRAME = 2
GUIDER_RUN_AT_NOT_BEFORE_FRAME = 3

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
  "ERROR_BIT_ISOLATOR_ERROR", \
  "ERROR_BIT_CONFIGURATION_LOCK_ERROR", \
  "ERROR_BIT_SHUTDOWN_INPUT_TRIGGERED", \
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
  "TC_EXCEPTION_MCB_NEGATIVE_LIMITED", \
  "TC_EXCEPTION_QUEUE_INTERRUPT_UNEXPECTED", \
  "TC_EXCEPTION_INVALID_FPGA_EXCEPTION_BITMAP", \
  "TC_EXCEPTION_IO_SUPPLY_ERROR", \
  "TC_EXCEPTION_STEP_COMPUTATION_OVERFLOW", \
  "TC_EXCEPTION_SHUTDOWN_INPUT_TRIGGERED", \
  "TC_EXCEPTION_UNEXPECTED_FPGA_RESET"]

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
    self.report_input = False

class ControllerException(Exception):
  pass

class ControllerUsageException(Exception):
  pass

class ControllerVersionException(Exception):
  pass

class ControllerConfigurationException(ControllerException):
  pass

class ControllerNotConnectedException(ControllerException):
  pass

class MultipleControllersConnectedException(ControllerException):
  pass

class InterruptTransferFailedException(ControllerException):
  pass

class ControllerConfiguration(object):
  def __init__(self, controller):
    self._controller = controller

    self.mc_prefill_frames = 8
    self.mc_pin_flags = 0
    self.mc_a_shutdown_acceleration = 0
    self.mc_b_shutdown_acceleration = 0
    self.mc_a_acceleration_limit = 500
    self.mc_b_acceleration_limit = 500
    self.mc_a_velocity_limit = 7600
    self.mc_b_velocity_limit = 7600
    self.mc_frame_period = 1200000
    self.mc_pulse_width = 120
    self.mc_pulse_minimum_off_time = None
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

    self.shutdown_0_input = None
    self.shutdown_1_input = None
    self.shutdown_2_input = None
    self.shutdown_3_input = None

    self.pins = []

    for i in range(64):
      self.pins.append(ControllerPin(i))

  def _validate(self):
    if self.mc_prefill_frames < 2:
      raise ControllerConfigurationException( \
        "The mc_prefill_frames property can not be less than two.")

    if self.mc_a_shutdown_acceleration < 1:
      raise ControllerConfigurationException( \
        "The mc_a_shutdown_acceleration property must be greater than zero.")

    if self.mc_b_shutdown_acceleration < 1:
      raise ControllerConfigurationException( \
        "The mc_b_shutdown_acceleration property must be greater than zero.")

    if self.mc_frame_period < self._controller.clock_frequency / 100:
      raise ControllerConfigurationException( \
        "The mc_frame_period property must be set to give a frame of at least 10 " \
        "milliseconds.")

    if self.mc_pulse_width < 1:
      raise ControllerConfigurationException( \
        "The mc_pulse_width property must not be less than one.")

    if self.mc_pulse_minimum_off_time is None:
      raise ControllerConfigurationException( \
        "The mc_pulse_minimum_off_time must be specified.")

    a_full_frame_cycles = (self.mc_pulse_width + self.mc_pulse_minimum_off_time) * \
      self.mc_a_velocity_limit

    b_full_frame_cycles = (self.mc_pulse_width + self.mc_pulse_minimum_off_time) * \
      self.mc_b_velocity_limit

    if a_full_frame_cycles > self.mc_frame_period or \
      b_full_frame_cycles > self.mc_frame_period:
      raise ControllerConfigurationException( \
        "The minimum off time (mc_pulse_minimum_off_time) will be violated at " \
        "the currently configured velocity limits. Reduce the maximum velocity " \
        "or adjust the pulse on or off times.")

  def encode_gpio(self):
    self._validate()

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

  def encode_safety(self):
    self._validate()

    return struct.pack("<BBBB", \
      self._encode_input(self.shutdown_0_input),
      self._encode_input(self.shutdown_1_input),
      self._encode_input(self.shutdown_2_input),
      self._encode_input(self.shutdown_3_input))

  def _encode_input(self, value):
    if value is None:
      return TC_MC_UNUSED_INPUT
    elif 0 <= value <= 64:
      return value
    else:
      raise ControllerConfigurationException( \
        "An invalid input was specified.")

  def encode_mc(self):
    self._validate()

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
  def __init__(self, command, status):
    self.command = command
    self.status = status

  def __repr__(self):
    return "<UsbTransferError %s (%s), command %s>" % \
      (libusb1.libusb_transfer_status(self.status), self.status, self.command)

class EnqueueDetails(object):
  def __init__(self, controller):
    self.last_transmitted_frame = controller._last_transmitted_frame
    self.last_enqueued_frame = controller._last_enqueued_frame
    self.last_dequeued_frame = controller._last_dequeued_frame

    self.frames_in_queue = \
      (self.last_transmitted_frame - self.last_dequeued_frame) % 0x100000000L
    self.frames_queue_capacity = controller.mc_frames_capacity

class ExceptionDetails(object):
  def __init__(self, exception, properties):
    self.exception = exception
    self.properties = properties

  def __repr__(self):
    if 0 <= self.exception <= len(exception_descriptions):
      description = exception_descriptions[self.exception]
    else:
      description = "(Unknown Exception Code)"

    return "<ExceptionDetails %s %s>" % (description, self.properties)

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
    elif self.state == TC_STATE_STOPPING:
      return "TC_STATE_STOPPING"
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

class GuiderResult(object):
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
    self._last_state_details = None
    self._last_state_callback = None

    self._running = True

    self._timers_heap = []

    self._driver_initialised = False

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
      command, 0, 0, data, self._complete_control_write, (d, command))
    transfer.submit()

    return d

  def _complete_control_write(self, transfer):
    deferred, command = transfer.getUserData()

    status = transfer.getStatus()

    if status == libusb1.LIBUSB_TRANSFER_COMPLETED:
      written = transfer.getActualLength()

      transfer.close()

      deferred.callback(written)
    else:
      transfer.close()

      deferred.errback(UsbTransferError(command, status))

  def _control_read(self, command, data_length = 0):
    d = defer.Deferred()

    transfer = self._device_handle.getTransfer()
    transfer.setControl( \
      libusb1.LIBUSB_TYPE_VENDOR | \
      libusb1.LIBUSB_ENDPOINT_IN | \
      libusb1.LIBUSB_RECIPIENT_DEVICE, \
      command, 0, 0, data_length, self._complete_control_read, (d, command))
    transfer.submit()

    return d

  def _complete_control_read(self, transfer):
    deferred, command = transfer.getUserData()

    status = transfer.getStatus()

    if status == libusb1.LIBUSB_TRANSFER_COMPLETED:
      read = transfer.getBuffer()

      transfer.close()

      deferred.callback(read)
    else:
      transfer.close()

      deferred.errback(UsbTransferError(command, status))

  def _initiate_interrupt_read(self):
    transfer = self._device_handle.getTransfer()
    transfer.setInterrupt(
      0x81, 24, self._complete_interrupt_read)
    transfer.submit()

  def _complete_interrupt_read(self, transfer):
    try:
      if transfer.getStatus() == libusb1.LIBUSB_TRANSFER_COMPLETED:
        buffer = transfer.getBuffer()

        changed, state, flags, exception, inputs, \
          last_enqueued_frame, last_dequeued_frame = \
          struct.unpack("<BBHLQLL", buffer)

        self._last_enqueued_frame = last_enqueued_frame
        self._last_dequeued_frame = last_dequeued_frame

        if self._last_inputs != inputs:
          self._last_inputs = inputs

          if self._driver_initialised:
            self._driver.inputs_changed(inputs)

        if self._last_state != state:
          self._last_state = state

          self._last_state_details = StateDetails(self, state, exception)

          if self._last_state_callback is not None:
            callback = self._last_state_callback
            self._last_state_callback = None

            callback()

          if self._driver_initialised:
            self._driver.state_changed(self._last_state_details)

        self._initiate_interrupt_read()

        if not self._enqueue_in_progress:
          self._call_enqueue_available()

      else:
        self.stop()

        self._driver.runtime_error(failure.Failure(InterruptTransferFailedException( \
          "The USB interrupt transfer to the controller failed.", transfer.getStatus())))
    finally:
      transfer.close()

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

  def clear_exception(self, exception):
    """Clears the specified controller exception. The exception must be the current reported exception.

    Once the command returns the next exception should be available through the (synchronous) get
    exception control request.

    The returned deferred completes when the command has been issued; a state change exception to
    idle may be delivered before or after the deferred callbacks are run.
    """

    d = self._control_write(TC_CLEAR_EXCEPTION, \
      struct.pack("<L", exception))

    d.addCallback(self._state_command_completed)

    return d

  def _clear_exception_completed(self, bytes_written):
    return None

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

    d.addCallback(self._configure_gpio_completed, configuration)

    return d

  def _configure_gpio_completed(self, bytes_written, configuration):
    d = self._control_write(TC_SAFETY_CONFIGURE, \
      configuration.encode_safety())

    d.addCallback(self._configure_safety_completed, configuration)

    return d

  def _configure_safety_completed(self, bytes_written, configuration):
    return configuration

  def _handle_initialise_error(self, failure):
    self.stop()

    self._driver.initialisation_error(failure)

  def _initialise_internals(self):
    d = self._control_read(TC_GET_VERSION, 16)

    d.addCallback(self._initialise_internals_handle_version)
    d.addErrback(self._handle_initialise_error)

  def _initialise_internals_handle_version(self, buffer):
    mcu_minor, mcu_major, fpga_minor, fpga_major, \
      self.clock_frequency, self.mc_frames_capacity, reserved = \
      struct.unpack("<HHHHLHH", buffer)

    self.mcu_version = (mcu_major, mcu_minor)
    self.fpga_version = (fpga_major, fpga_minor)

    if self.mcu_version != self.fpga_version:
      raise ControllerVersionException("The version of the firmware in the " \
        "MCU (Version %s.%s) does not match the version of the firmware in " \
        "the FPGA (Version %s.%s)." % (mcu_major, mcu_minor, fpga_major, fpga_minor))

    if module_version != self.mcu_version:
      raise ControllerVersionException("The version of this Python module " \
        "(Version %s.%s) does not match the version of the firmware in " \
        "the MCU (Version %s.%s)." % \
        (module_version[0], module_version[1], fpga_major, fpga_minor))

    expected_version = self._driver.get_expected_controller_version()

    if expected_version != module_version:
      raise ControllerVersionException("Your code is expecting version " \
        "%s.%s of the controller module, but the controller module is " \
        "version %s.%s. Update the \"get_expected_controller_version\" " \
        "method in your driver class, and then carefully check any " \
        "release notes for this module and thoroughly test the new version." %
        (expected_version[0], expected_version[1], \
        module_version[0], module_version[1]))

    # Force an interrupt so that the driver can be provided with it:
    d = self._control_write(TC_ISSUE_STATE_COMMAND, \
      struct.pack("<L", TC_STATE_COMMAND_FORCE_INTERRUPT))

    d.addCallback(self._initialise_force_interrupt_completed)
    d.addErrback(self._handle_initialise_error)

  def _initialise_force_interrupt_completed(self, bytes_written):
    if self._last_state_details is not None:
      self._initialise_start_driver_initialise()
    else:
      self._last_state_callback = self._initialise_start_driver_initialise

  def _initialise_start_driver_initialise(self):
    if self._last_state == TC_STATE_RUNNING:
      d = self.shutdown()

      d.addCallback(self._initialise_wait_for_stop)
      d.addErrback(self._handle_initialise_error)
    elif self._last_state_details.state == TC_STATE_STOPPING:
      self._initialise_wait_for_stop()
    else:
      self._initialise_call_driver_initialise()

  def _initialise_wait_for_stop(self, _ = None):
    # Wait for the state to change to an exception:
    if self._last_state != TC_STATE_EXCEPTION:
      self._last_state_callback = self._initialise_wait_for_stop
    else:
      self._initialise_call_driver_initialise()

  def _initialise_call_driver_initialise(self):
    d = self._driver.initialise(self._last_state_details)

    if not isinstance(d, defer.Deferred):
      raise ControllerUsageException("The driver initialise method must return a deferred.")

    d.addCallback(self._driver_initialise_completed)
    d.addErrback(self._handle_initialise_error)

  def _driver_initialise_completed(self, _):
    self._driver_initialised = True

    # Give the driver the most recent status and inputs:
    self._driver.state_changed(self._last_state_details)
    self._driver.inputs_changed(self._last_inputs)

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

  def force_outputs(self, outputs):
    """Sets all GPIO bits to the specified value on the controller card.

    The outputs should be specified as a 64 bit long bitmask."""
    self._last_outputs = outputs

    d = self._control_write(TC_WRITE_OUTPUTS, struct.pack("<Q", self._last_outputs))

  def _handle_error(self, failure):
    failure.printTraceback()

    return failure

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
    d = self._control_read(TC_GET_COUNTERS, 28)

    d.addCallback(self._get_counters_completed)
    d.addErrback(self._handle_error)

    return d

  def get_debug_registers(self):
    d = self._control_read(TC_GET_DEBUG_REGISTERS, 8)

    d.addCallback(self._get_debug_registers_completed)
    d.addErrback(self._handle_error)

    return d

  def _get_debug_registers_completed(self, buffer):
    return struct.unpack("<LL", buffer)

  def _get_counters_completed(self, buffer):
    counters = CounterDetails()

    counters.reference_frame_number, \
    counters.a_total_steps, \
    counters.b_total_steps, \
    counters.a_guider_steps, \
    counters.b_guider_steps, \
    counters.a_measured_steps, \
    counters.b_measured_steps = struct.unpack("<Lllllll", buffer)

    return counters

  def set_guider_values(self, run_at, frame_number, values):
    reserved = 0

    if frame_number is None: frame_number = 0

    buffer = struct.pack("<BBHL", run_at, reserved, reserved, frame_number)

    for a_steps, b_steps in values:
      buffer += struct.pack("<hh", a_steps, b_steps)

    if len(buffer) > 64:
      raise ControllerUsageException("Too many guider values were specified.")

    d = self._control_write(TC_SET_GUIDER_VALUES, buffer)
    d.addCallback(self._handle_set_guider_values_completed)
    d.addErrback(self._handle_error)

    return d

  def _handle_set_guider_values_completed(self, bytes_written):
    d = self._control_read(TC_GET_GUIDER_RESULT, 8)
    d.addCallback(self._handle_convert_guider_result)
    d.addErrback(self._handle_error)

    return d

  def _handle_convert_guider_result(self, buffer):
    frame, count = struct.unpack("<LL", buffer)

    result = GuiderResult()
    result.frame = frame
    result.count = count

    return result

  def get_raw_exception_details(self):
    d = self._control_read(TC_GET_EXCEPTION_DETAILS_LENGTH, 4)
    d.addCallback(self._handle_get_exception_details_got_length)
    d.addErrback(self._handle_error)

    return d

  def _handle_get_exception_details_got_length(self, buffer):
    (length,) = struct.unpack("<L", buffer)

    if length > 0:
      d = self._control_read(TC_GET_EXCEPTION_DETAILS, length)
      d.addErrback(self._handle_error)

      return d
    else:
      return None

  def get_exception(self):
    d = self._control_read(TC_GET_EXCEPTION, 4)

    d.addCallback(self._handle_get_exception_completed)
    d.addErrback(self._handle_error)

    return d

  def _handle_get_exception_completed(self, buffer):
    (exception,) = struct.unpack("<L", buffer)

    if exception == TC_EXCEPTION_NONE:
      return None
    else:
      d = self.get_raw_exception_details()
      d.addCallback(self._handle_get_exception_details_completed, exception)
      d.addErrback(self._handle_error)

      return d

  def _handle_get_exception_details_completed(self, details_buffer, exception):
    properties = {}

    if details_buffer is not None:
      detail_kind = struct.unpack("<L", details_buffer[:4])[0]

      properties = {}

      properties["kind"] = detail_kind

      if detail_kind == TC_DETAIL_KIND_AXIS_TRACE:
        properties["kind_description"] = "TC_DETAIL_KIND_AXIS_TRACE"

        detail_kind, axis_index, steps, guider_steps, \
          previous_remainder_steps, current_remainder_steps, \
          previous_negative_direction, current_negative_direction, \
          reserved_a, reserved_b = struct.unpack("<LLiiiiBBBB", details_buffer)

        properties["axis_index"] = axis_index
        properties["steps"] = steps
        properties["guider_steps"] = guider_steps
        properties["previous_remainder_steps"] = previous_remainder_steps
        properties["current_remainder_steps"] = current_remainder_steps
        properties["previous_negative_direction"] = previous_negative_direction
        properties["current_negative_direction"] = current_negative_direction
      elif detail_kind == TC_DETAIL_KIND_FPGA_ERRORS:
        properties["kind_description"] = "TC_DETAIL_KIND_FPGA_ERRORS"

        detail_kind, fpga_error_bits = struct.unpack("<LL", details_buffer)

        properties["fpga_error_bits"] = fpga_error_bits

        descriptions = []

        for i in range(len(fpga_error_bit_descriptions)):
          if fpga_error_bits & (1 << i):
            descriptions.append(fpga_error_bit_descriptions[i])

        properties["fpga_error_bit_descriptions"] = descriptions
      else:
        properties["kind_description"] = "TC_DETAIL_KIND_UNKNOWN"

    return ExceptionDetails(exception, properties)

class Driver(object):
  def internal_attach_host(self, host):
    self.host = host

  def initialise(self, state_details):
    """Called when the controller first starts the event loop.

    During initialisation, the driver can check the current state of the controller,
    read counters from previous runs, and reset the queue or hardware. A deferred must be
    returned. When the deferred completes, state and input events start being forwarded.

    The host ensures the controller will either be in TC_STATE_IDLE or TC_STATE_EXCEPTION
    on initialisation.
    """
    pass

  def initialisation_error(self, failure):
    """Called when the controller fails to initialise.

    The run loop will exit immediately on an initialisation failure.
    """
    pass

  def runtime_error(self, failure):
    """Called when an error has caused the run loop to stop."""
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
    - controller.TC_STATE_STOPPING
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
    - controller.TC_EXCEPTION_QUEUE_INTERRUPT_UNEXPECTED
    - controller.TC_EXCEPTION_INVALID_FPGA_EXCEPTION_BITMAP
    - controller.TC_EXCEPTION_IO_SUPPLY_ERROR
    - controller.TC_EXCEPTION_STEP_COMPUTATION_OVERFLOW
    - controller.TC_EXCEPTION_SHUTDOWN_INPUT_TRIGGERED
    - controller.TC_EXCEPTION_UNEXPECTED_FPGA_RESET

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

