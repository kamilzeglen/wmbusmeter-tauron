#include "packet.h"

#include <cassert>
#include <algorithm>
#include <iostream>

std::vector<uint8_t> encode_t1(const std::vector<uint8_t> &bytes)
{
    const uint8_t codes[] = {0x16, 0x0D, 0x0E, 0x0B, 0x1C, 0x19, 0x1A, 0x13,
                             0x2C, 0x25, 0x26, 0x23, 0x34, 0x31, 0x32, 0x29};
    std::vector<uint8_t> encoded((bytes.size() * 12 + 7) / 8, 0);
    size_t output_bit = 0;
    for (uint8_t byte : bytes)
    {
        for (uint8_t nibble : {static_cast<uint8_t>(byte >> 4), static_cast<uint8_t>(byte & 15)})
        {
            for (int bit = 5; bit >= 0; --bit)
            {
                encoded[output_bit / 8] |= ((codes[nibble] >> bit) & 1) << (7 - output_bit % 8);
                ++output_bit;
            }
        }
    }
    return encoded;
}

void verify_complete_telegram()
{
    const std::vector<uint8_t> telegram = {0x0B, 0x44, 0x01, 0x06, 0x78, 0x56,
                                          0x34, 0x12, 0x05, 0x07, 0x78, 0x00};
    std::vector<uint8_t> radio_bytes;
    for (const auto &block : {std::vector<uint8_t>(telegram.begin(), telegram.begin() + 10),
                              std::vector<uint8_t>(telegram.begin() + 10, telegram.end())})
    {
        auto bytes = block;
        const uint16_t crc = crc16_EN13757(bytes.data(), bytes.size());
        radio_bytes.insert(radio_bytes.end(), bytes.begin(), bytes.end());
        radio_bytes.push_back(crc >> 8);
        radio_bytes.push_back(crc & 255);
    }
    const auto encoded = encode_t1(radio_bytes);
    auto packet = new esphome::wmbus_radio::Packet();
    auto preamble = packet->prepare_rx_buffer();
    std::copy_n(encoded.begin(), preamble.size, preamble.data);
    assert(packet->calculate_payload_size());
    auto payload = packet->prepare_rx_buffer();
    assert(preamble.size + payload.size == encoded.size());
    std::copy(encoded.begin() + preamble.size, encoded.end(), payload.data);
    packet->set_rssi(-65);
    auto frame = packet->convert_to_frame();
    assert(frame.has_value());
    assert(frame->data() == telegram);
    assert(frame->link_mode() == LinkMode::T1);
    assert(frame->rssi() == -65);
}

class TestPacket : public esphome::wmbus_radio::Packet
{
public:
    void receive(ReceiveBuffer buffer, size_t offset, const std::vector<uint8_t> &bytes)
    {
        assert(buffer.size == bytes.size());
        assert(buffer.data == data_.data() + offset);
        assert(offset + buffer.size == data_.size());
        std::copy(bytes.begin(), bytes.end(), buffer.data);
    }

    void reserve_extra() { data_.reserve(100); }
    const std::vector<uint8_t> &bytes() const { return data_; }
};

int main()
{
    TestPacket packet;
    const std::vector<uint8_t> header = {0x5A, 0x37, 0x1C};
    packet.receive(packet.prepare_rx_buffer(), 0, header);
    assert(packet.calculate_payload_size());
    packet.reserve_extra();
    packet.receive(packet.prepare_rx_buffer(), 3, std::vector<uint8_t>(21, 0xA5));
    assert(packet.bytes().size() == 24);
    assert(std::equal(header.begin(), header.end(), packet.bytes().begin()));
    assert(packet.bytes().back() == 0xA5);
    verify_complete_telegram();
    std::cout << "PASS: receiver writes inside the packet buffer.\n";
}
