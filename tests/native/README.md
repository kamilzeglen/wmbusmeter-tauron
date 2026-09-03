# Native regression tests

Run from the repository root on Linux with Python 3, g++, and ar:

```sh
python3 tests/native/run.py
python3 tests/native/run.py --disable-assertions
python3 tests/native/run.py --sanitize --test packet_buffer
```

The tests compile the real wmbus common sources, Tauron and Apator drivers,
and the ESPHome meter wrapper into a static archive. They check that the
linker retains the selected drivers, both meters can be created, and a
missing driver does not crash startup or diagnostic accessors. The packet
test checks receive buffer boundaries, retained preamble bytes, and decoding
a complete synthetic T1 telegram with CRCs using the real radio packet code.

The second command disables assertions in production sources while keeping
test assertions enabled. This checks that registry initialization does not
depend on assertion side effects.

The third command checks packet handling with AddressSanitizer and
UndefinedBehaviorSanitizer, including the three-byte preamble decoder.

The stubs replace ESPHome logging, scheduling, and radio interfaces only.
These tests do not validate ESP32 hardware, radio reception, or OTA updates.
