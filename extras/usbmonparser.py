import sys

setup_request_descriptions = \
{
	0x00 : "TC_ISSUE_STATE_COMMAND",
	0x01 : "TC_GET_VERSION",
	0x02 : "TC_MC_CONFIGURE",
	0x03 : "TC_GPIO_CONFIGURE",
	0x04 : "TC_SAFETY_CONFIGURE",
	0x05 : "TC_WRITE_OUTPUTS",
	0x06 : "TC_ENQUEUE",
	0x07 : "TC_GET_COUNTERS",
	0x08 : "TC_GET_DEBUG_REGISTERS",
	0x09 : "TC_SET_GUIDER_VALUES",
	0x0a : "TC_GET_GUIDER_RESULT",
	0x0b : "TC_GET_EXCEPTION_DETAILS_LENGTH",
	0x0c : "TC_GET_EXCEPTION_DETAILS",
	0x0d : "TC_GET_EXCEPTION",
	0x0e : "TC_CLEAR_EXCEPTION"
}

USB_REQUEST_TYPE_DEVICE = 0
USB_REQUEST_TYPE_INTERFACE = 1
USB_REQUEST_TYPE_ENDPOINT = 2
USB_REQUEST_TYPE_OTHER = 3

USB_REQUEST_TYPE_STANDARD = 0
USB_REQUEST_TYPE_CLASS = 1
USB_REQUEST_TYPE_VENDOR = 2
USB_REQUEST_TYPE_RESERVED = 3

USB_REQUEST_TYPE_HOST_TO_DEVICE = 0
USB_REQUEST_TYPE_DEVICE_TO_HOST = 1

class Event(object):
	def __init__(self):
		pass

	def __repr__(self):
		line = "[%s] " % self.index

		if self.has_control_error:
			line += "{%s} " % self.urb_status

		line += "-> " if self.kind == "S" else "<- "

		if self.setup is not None:
			line += "%s %s " % (self.setup.request_type_description, \
				setup_request_descriptions.get(self.setup.request, "TC_UNKNOWN_" + str(self.setup.request)))

		line += "%s %s" % (self.address_kind, self.address_endpoint)

		line += " | "
		line += ' '.join(x.encode('hex') for x in self.data)

		return line

	@property
	def has_control_error(self):
		return self.kind == "C" and self.address_kind in ["Ci", "Co"] and self.urb_status != "0"

class EventSetup(object):
	def __init__(self):
		pass

	@property
	def request_type_direction(self):
		return (self.request_type & 0x80) >> 7

	@property
	def request_type_type(self):
		return (self.request_type & 0x60) >> 5

	@property
	def request_type_recipient(self):
		return self.request_type & 0x1f
	
	@property
	def request_type_description(self):
		recipient = ["Device", "Interface", "Endpoint", "Other"][self.request_type_recipient]
		kind = ["Standard", "Class", "Vendor", "Reserved"][self.request_type_type]
		direction = ["ToDevice", "ToHost"][self.request_type_direction]

		return "%s/%s/%s" % (direction, kind, recipient)

def main():
	next_index = 0
	indices_by_tag = {}

	while True:
		line = sys.stdin.readline()

		if line == "": break

		parts = line.split(" ")
	
		e = Event()

		e.tag = parts[0]
		e.timestamp = long(parts[1])
		e.kind = parts[2]

		address = parts[3].split(":")

		e.address_kind = address[0]
		e.address_bus = address[1]
		e.address_device = address[2]
		e.address_endpoint = address[3]

		e.urb_status = parts[4]

		if e.urb_status == "s":
				s = EventSetup()

				s.request_type = int(parts[5], 16)
				s.request = int(parts[6], 16)
				s.value = int(parts[7], 16)
				s.index = int(parts[8], 16)
				s.length = int(parts[9], 16)
				part_index = 10
		
				e.setup = s
		else:
				part_index = 5

				e.setup = None

		e.data_length = int(parts[part_index])
		part_index += 1

		e.data_words = []
		
		data = ""

		remaining = e.data_length
		
		if part_index < len(parts):
			e.data_tag = parts[part_index]
			part_index += 1

			while part_index < len(parts):
				word = parts[part_index]
				e.data_words.append(long(word, 16))

				if remaining >= 1: data += chr(int(word[0:2], 16))
				if remaining >= 2: data += chr(int(word[2:4], 16))
				if remaining >= 3: data += chr(int(word[4:6], 16))
				if remaining >= 4: data += chr(int(word[6:8], 16))

				remaining -= 4

				part_index += 1

		e.data = data

		if e.tag in indices_by_tag:
			e.index = indices_by_tag[e.tag]
		else:
			e.index = next_index
			indices_by_tag[e.tag] = e.index
			next_index += 1

		print e

if __name__ == "__main__":
	main()

