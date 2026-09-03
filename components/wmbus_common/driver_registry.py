def driver_linker_flags(drivers):
    return [
        f"-Wl,--undefined=wmbus_driver_{driver.replace('-', '_')}"
        for driver in sorted(drivers)
    ]
