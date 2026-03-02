#!/bin/bash
/usr/bin/python3 run_socat.py &
/usr/bin/python3 -c "import time; time.sleep(3)"
chmod -R a+rw /dev/pts
nice -n 20 /usr/bin/python3 ../data_server/data_server.py
