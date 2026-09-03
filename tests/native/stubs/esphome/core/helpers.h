#pragma once

#include <cmath>
#include <functional>
#include <optional>
#include <vector>
#include <string>
#include <cstdint>

namespace esphome
{
    using std::optional;

    inline std::string format_hex(const std::vector<uint8_t> &data)
    {
        const char *digits = "0123456789ABCDEF";
        std::string result;
        for (uint8_t byte : data)
        {
            result += digits[byte >> 4];
            result += digits[byte & 15];
        }
        return result;
    }

    template<typename Signature> class CallbackManager
    {
    public:
        void add(std::function<Signature> callback) { callbacks_.push_back(callback); }
        void operator()()
        {
            for (auto &callback : callbacks_)
            {
                callback();
            }
        }

    private:
        std::vector<std::function<Signature>> callbacks_;
    };
}
