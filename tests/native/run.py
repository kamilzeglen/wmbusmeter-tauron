from pathlib import Path
import argparse
import subprocess
import tempfile
import runpy


root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--disable-assertions", action="store_true")
parser.add_argument("--sanitize", action="store_true")
parser.add_argument("--test", choices=["driver_registration", "meter_lifecycle", "packet_buffer"])
arguments = parser.parse_args()
compile_flags = ["-DNDEBUG"] if arguments.disable_assertions else []
sanitizer_flags = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie", "-g"] if arguments.sanitize else []
common = root / "components" / "wmbus_common"
drivers = ["tauronkpl", "apator162"]
linker_flags = runpy.run_path(str(common / "driver_registry.py"))["driver_linker_flags"](drivers)
sources = sorted(path for path in common.glob("*.cc") if path.name.startswith("driver_") is False)
sources += [common / f"driver_{driver}.cc" for driver in drivers]
sources += [root / "components" / "wmbus_radio" / name for name in ["packet.cpp", "decode3of6.cpp"]]

with tempfile.TemporaryDirectory(prefix="wmbus-native-") as temporary:
    build = Path(temporary)
    includes = build / "include"
    (includes / "esphome").mkdir(parents=True)
    (includes / "esphome" / "components").symlink_to(root / "components", target_is_directory=True)
    if arguments.test != "packet_buffer":
        sources.append(root / "components" / "wmbus_meter" / "wmbus_meter.cpp")
    objects = []
    for source in sources:
        target = build / f"{source.stem}.o"
        subprocess.run(
            ["g++", "-std=c++17", *compile_flags, *sanitizer_flags, "-ffunction-sections", "-fdata-sections",
             "-I", str(root / "tests" / "native" / "stubs"),
             "-I", str(includes),
             "-I", str(common), "-c", str(source), "-o", str(target)],
            check=True,
        )
        objects.append(str(target))

    archive = build / "libwmbus.a"
    subprocess.run(["ar", "rcs", str(archive), *objects], check=True)
    tests = [arguments.test] if arguments.test else ["driver_registration", "meter_lifecycle", "packet_buffer"]
    for test in tests:
        executable = build / test
        test_linker_flags = [] if test == "packet_buffer" else linker_flags
        subprocess.run(
            ["g++", "-std=c++17", *sanitizer_flags, "-I", str(root / "tests" / "native" / "stubs"),
             "-I", str(includes), "-I", str(common),
             "-I", str(root / "components" / "wmbus_meter"),
             "-I", str(root / "components" / "wmbus_radio"),
             str(root / "tests" / "native" / f"{test}.cpp"),
             str(archive), "-Wl,--gc-sections", *test_linker_flags, "-o", str(executable)],
            check=True,
        )
        subprocess.run([str(executable)], check=True, timeout=10)
