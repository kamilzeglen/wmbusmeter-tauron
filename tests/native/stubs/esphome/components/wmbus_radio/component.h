#pragma once

#include "wmbus.h"
#include <functional>

namespace esphome::wmbus_radio
{
    class Frame
    {
    public:
        LinkMode link_mode() { return LinkMode::T1; }
        int rssi() { return -50; }
        std::vector<uchar> &data() { return data_; }
        void mark_as_handled() {}

    private:
        std::vector<uchar> data_;
    };

    class Radio
    {
    public:
        void add_frame_handler(std::function<void(Frame *)> callback) {}
    };
}
