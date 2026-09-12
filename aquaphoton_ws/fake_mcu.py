#!/usr/bin/env python3
"""
Stands in for the car's microcontroller during development.

Speaks the real serial protocol over a virtual port: transmits telemetry
frames at 10 Hz and prints any command frames it receives.
"""

import math
import sys
import time

import serial


def checksum(payload):
    result = 0
    for char in payload:
        result ^= ord(char)
    return '%02X' % result


def build_frame(payload):
    return '<%s*%s>\n' % (payload, checksum(payload))


def parse_frame(line):
    line = line.strip()
    if not line.startswith('<') or not line.endswith('>'):
        return None
    body = line[1:-1]
    if '*' not in body:
        return None
    payload, received = body.rsplit('*', 1)
    if checksum(payload) != received.upper():
        return None
    return payload.split(',')


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB0'
    link = serial.Serial(port, 115200, timeout=0)
    print('fake MCU listening on %s' % port)

    mode = direction = speed = 0
    elapsed = 0.0
    last_send = 0.0

    while True:
        line = link.readline().decode('ascii', errors='ignore')
        if line:
            fields = parse_frame(line)
            if fields and fields[0] == 'C' and len(fields) == 4:
                mode, direction, speed = (int(f) for f in fields[1:])
                print('command received: mode=%d dir=%d speed=%d'
                      % (mode, direction, speed))
            elif line.strip():
                print('discarded: %r' % line.strip())

        now = time.time()
        if now - last_send >= 0.1:
            last_send = now
            elapsed += 0.1
            payload = 'T,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%d,%d,%d,%d' % (
                11.60 + math.sin(elapsed) * 0.30,
                1.20 + math.sin(elapsed * 1.7) * 0.40,
                math.sin(elapsed), math.cos(elapsed), 0.98,
                0.0, 0.0, math.sin(elapsed * 0.5) * 5.0,
                mode, direction, speed, 1)
            link.write(build_frame(payload).encode('ascii'))

        time.sleep(0.01)


if __name__ == '__main__':
    main()

