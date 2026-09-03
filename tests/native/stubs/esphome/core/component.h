#pragma once

#include <functional>
#include <string>

namespace esphome
{
    class Component
    {
    public:
        virtual ~Component() = default;
        virtual void setup() {}
        virtual void dump_config() {}
        void mark_failed() { failed_ = true; }
        bool is_failed() const { return failed_; }
        void defer(std::function<void()> callback) { callback(); }

    private:
        bool failed_ = false;
    };

    struct TestApplication
    {
        std::string get_friendly_name() { return "native-test"; }
    };

    inline TestApplication App;
}
