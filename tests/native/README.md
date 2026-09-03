# Native regression tests

Run from the repository root on Linux with Python 3, g++, and ar:

```sh
python3 tests/native/run.py
python3 tests/native/run.py --disable-assertions
```

The tests compile the real wmbus common sources, Tauron and Apator drivers,
and the ESPHome meter wrapper into a static archive. They check that the
linker retains the selected drivers, both meters can be created, and a
missing driver does not crash startup or diagnostic accessors.

The second command disables assertions in production sources while keeping
test assertions enabled. This checks that registry initialization does not
depend on assertion side effects.

The stubs replace ESPHome logging, scheduling, and radio interfaces only.
These tests do not validate ESP32 hardware, radio reception, or OTA updates.
