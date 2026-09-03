#pragma once

#include <cmath>
#include <functional>
#include <optional>
#include <vector>

namespace esphome
{
    using std::optional;

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
