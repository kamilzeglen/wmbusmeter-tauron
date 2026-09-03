#include "wmbus_meter.h"

#include <cassert>
#include <iostream>

class TestMeter : public esphome::wmbus_meter::Meter
{
public:
    using Meter::handle_frame;
};

int main()
{
    TestMeter unavailable;
    unavailable.set_meter_params("12345678", "missing_driver", "", {LinkMode::T1});
    unavailable.setup();
    unavailable.dump_config();
    unavailable.handle_frame(nullptr);
    assert(unavailable.is_failed());
    assert(unavailable.get_id() == "12345678");
    assert(unavailable.get_driver() == "missing_driver");
    assert(unavailable.get_key() == "unavailable");
    assert(unavailable.as_json() == "{}");
    assert(unavailable.get_numeric_field("total_m3").has_value() == false);
    assert(unavailable.get_string_field("timestamp").has_value() == false);

    for (const std::string driver : {"tauronkpl", "apator162"})
    {
        TestMeter available;
        available.set_meter_params("12345678", driver, "", {LinkMode::T1});
        available.setup();
        available.dump_config();
        assert(available.is_failed() == false);
        assert(available.get_id() == "12345678");
        assert(available.get_driver() == driver);
    }

    std::cout << "PASS: meter startup and diagnostics tolerate a missing driver.\n";
}
