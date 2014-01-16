#!/usr/bin/python

import controller, sys

from twisted.internet import defer

if __name__ == "__main__":
	instance = controller.Controller(None)

	if "--force" in sys.argv:
		# Force ignores the controller state and will reset even when the
		# motor controller is running, causing an abrupt stop (or even
		# an uncontrolled stop or behaviour if any kind of braking is
		# electronically controlled:
		instance.force_hardware_reset()
	else:
		instance.hardware_reset()

