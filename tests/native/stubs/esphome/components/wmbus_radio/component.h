#pragma once

#include "esphome/components/wmbus_radio/packet.h"
#include <functional>

namespace esphome::wmbus_radio
{
    class Radio
    {
    public:
        void add_frame_handler(std::function<void(Frame *)> callback) {}
    };
}
