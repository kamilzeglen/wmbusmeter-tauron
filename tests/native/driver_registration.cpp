#include "meters.h"

#include <iostream>

int main()
{
    for (const std::string driver : {"tauronkpl", "apator162"})
    {
        MeterInfo info;
        if (info.parse("test", driver, "12345678", "") == false)
        {
            std::cerr << "Driver unavailable: " << driver << '\n';
            return 1;
        }

        auto meter = createMeter(&info);
        if (meter == nullptr)
        {
            std::cerr << "Meter creation failed: " << driver << '\n';
            return 1;
        }

        if (meter->driverName().str() != driver)
        {
            return 1;
        }

        const auto &addresses = meter->addressExpressions();
        if (addresses.size() != 1 || addresses[0].id != "12345678")
        {
            return 1;
        }
    }

    std::cout << "PASS: Tauron and Apator drivers create meters after archive linking.\n";
}
