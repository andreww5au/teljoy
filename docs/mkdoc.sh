#!/bin/sh
export PYTHONPATH=..:../extras:../cgi/secure
cp ../teljoy.ini .
pydoc -w ../controller.py
pydoc -w ../correct.py
pydoc -w ../detevent.py
pydoc -w ../digio.py
pydoc -w ../globals.py
pydoc -w ../handpaddles.py
pydoc -w ../motion.py
pydoc -w ../nzdome.py
pydoc -w ../pdome.py
pydoc -w ../pyephem.py
pydoc -w ../sqlint.py
pydoc -w ../teljoy.py
pydoc -w ../tjserver.py
pydoc -w ../usbcon.py
pydoc -w ../utils.py
pydoc -w ../weather.py
pydoc -w ../extras/reset.py
pydoc -w ../extras/tjclient.py
pydoc -w ../extras/tjguide.py
pydoc -w ../extras/tjjump.py
pydoc -w ../extras/tjoffset.py
pydoc -w ../extras/tjpos.py
pydoc -w ../extras/tjreset.py
