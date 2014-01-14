#!/usr/bin/python

import controller

from twisted.internet import defer

if __name__ == "__main__":
	instance = controller.Controller(None)
	instance.force_hardware_reset()

