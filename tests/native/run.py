from pathlib import Path
import argparse
import subprocess
import tempfile
import runpy


root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--disable-assertions", action="store_true")
arguments = parser.parse_args()
compile_flags = ["-DNDEBUG"] if arguments.disable_assertions else []
common = root / "components" / "wmbus_common"
drivers = ["tauronkpl", "apator162"]
linker_flags = runpy.run_path(str(common / "driver_registry.py"))["driver_linker_flags"](drivers)
sources = sorted(path for path in common.glob("*.cc") if path.name.startswith("driver_") is False)
sources += [common / f"driver_{driver}.cc" for driver in drivers]

with tempfile.TemporaryDirectory(prefix="wmbus-native-") as temporary:
    build = Path(temporary)
    includes = build / "include"
    (includes / "esphome").mkdir(parents=True)
    (includes / "esphome" / "components").symlink_to(root / "components", target_is_directory=True)
    sources.append(root / "components" / "wmbus_meter" / "wmbus_meter.cpp")
    objects = []
    for source in sources:
        target = build / f"{source.stem}.o"
        subprocess.run(
            ["g++", "-std=c++17", *compile_flags, "-ffunction-sections", "-fdata-sections",
             "-I", str(root / "tests" / "native" / "stubs"),
             "-I", str(includes),
             "-I", str(common), "-c", str(source), "-o", str(target)],
            check=True,
        )
        objects.append(str(target))

    archive = build / "libwmbus.a"
    subprocess.run(["ar", "rcs", str(archive), *objects], check=True)
    for test in ["driver_registration", "meter_lifecycle"]:
        executable = build / test
        subprocess.run(
            ["g++", "-std=c++17", "-I", str(root / "tests" / "native" / "stubs"),
             "-I", str(includes), "-I", str(common),
             "-I", str(root / "components" / "wmbus_meter"),
             str(root / "tests" / "native" / f"{test}.cpp"),
             str(archive), "-Wl,--gc-sections", *linker_flags, "-o", str(executable)],
            check=True,
        )
        subprocess.run([str(executable)], check=True)
