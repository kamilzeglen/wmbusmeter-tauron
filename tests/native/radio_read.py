from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'components/wmbus_radio/transceiver.cpp').read_text()
method = source[source.index('        bool RadioTransceiver::read_in_task'):source.index('        void RadioTransceiver::set_reset_pin')]
sx_source = (root / 'components/wmbus_radio/transceiver_sx1276.cpp').read_text()
snapshot_method = sx_source[sx_source.index('        void SX1276::log_rx_failure'):sx_source.index('        void SX1276::restart_rx')]
prefix = r'''
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>
std::vector<std::string> logs;
template<typename... Args> void capture(const char *format, Args... args) {
    char text[256];
    std::snprintf(text, sizeof(text), format, args...);
    logs.emplace_back(text);
}
#define ESP_LOGD(tag, ...) capture(__VA_ARGS__)
#define pdTRUE 1
#define pdMS_TO_TICKS(x) (x)
bool wait_finished = false;
uint32_t clock_us = 0;
uint32_t micros() { return clock_us; }
unsigned ulTaskNotifyTake(int, int) {
    clock_us += 1000;
    wait_finished = true;
    return 0;
}
std::string format_hex(const uint8_t *data, size_t length) {
    std::string result;
    const char *digits = "0123456789ABCDEF";
    for (size_t i = 0; i < length; ++i) {
        result += digits[data[i] >> 4];
        result += digits[data[i] & 15];
    }
    return result;
}
class RadioTransceiver {
public:
    size_t remaining = 0;
    size_t delayed_bytes = 0;
    size_t snapshots = 0;
    void log_rx_failure() {
        assert(logs.empty());
        ++snapshots;
    }
    std::optional<uint8_t> read() {
        if (wait_finished && delayed_bytes > 0) {
            wait_finished = false;
            --delayed_bytes;
            return 0xCD;
        }
        if (remaining == 0) { return {}; }
        --remaining;
        return 0xAB;
    }
    bool read_in_task(uint8_t *buffer, size_t length);
};
struct FakePin {
    bool digital_read() { return true; }
};
class SX1276 {
public:
    FakePin pin;
    FakePin *irq_pin_ = &pin;
    uint8_t flags = 0;
    std::vector<uint8_t> addresses;
    uint8_t spi_read(uint8_t address) {
        assert(logs.empty());
        addresses.push_back(address);
        if (address == 0x3F) { return flags; }
        return 0;
    }
    int8_t get_rssi() {
        assert(logs.empty());
        return -59;
    }
    void log_rx_failure();
};
'''
suffix = r'''
int main() {
    for (size_t received : {size_t{0}, size_t{1}, size_t{32}, size_t{33}, size_t{64}}) {
        logs.clear();
        RadioTransceiver radio;
        radio.remaining = received;
        std::vector<uint8_t> buffer(65, 0xFF);
        assert(radio.read_in_task(buffer.data(), buffer.size()) == false);
        assert(radio.snapshots == 1);
        assert(logs.size() == 2 + (received + 31) / 32);
        assert(logs[0] == "Incomplete radio read: received " + std::to_string(received) + "/65 bytes");
        assert(logs[1] == "RX timing: elapsed_us=1000 idle_us=1000 wait_us=1000 timeout_ticks=1 recovered=0");
        size_t offset = 0;
        for (size_t i = 2; i < logs.size(); ++i) {
            const size_t count = std::min(size_t{32}, received - offset);
            assert(logs[i] == "RAW[" + std::to_string(offset) + "]: " + format_hex(buffer.data() + offset, count));
            offset += count;
        }
        assert(buffer[received] == 0xFF);
    }
    logs.clear();
    RadioTransceiver radio;
    radio.remaining = 3;
    uint8_t buffer[3];
    assert(radio.read_in_task(buffer, 3));
    assert(logs.empty());
    assert(radio.snapshots == 0);
    logs.clear();
    wait_finished = false;
    RadioTransceiver delayed;
    delayed.remaining = 1;
    delayed.delayed_bytes = 2;
    uint8_t recovered[3] = {};
    assert(delayed.read_in_task(recovered, 3));
    assert(recovered[0] == 0xAB);
    assert(recovered[1] == 0xCD);
    assert(recovered[2] == 0xCD);
    assert(delayed.snapshots == 0);
    for (const auto &test : std::vector<std::pair<uint8_t, std::string>>{
        {0x40, "FIFO: full=0 empty=1 overrun=0 IRQ_high=1"},
        {0x90, "FIFO: full=1 empty=0 overrun=1 IRQ_high=1"}}) {
        logs.clear();
        SX1276 sx;
        sx.flags = test.first;
        sx.log_rx_failure();
        assert(sx.addresses == std::vector<uint8_t>({0x3F, 0x3E, 0x01}));
        assert(logs.size() == 2);
        assert(logs[1] == test.second);
    }
    std::puts("PASS: partial reads, timeout recovery, timing and read-only SX1276 snapshots before logging.");
}
'''
with tempfile.TemporaryDirectory() as temporary:
    path = Path(temporary)
    (path / 'verify.cpp').write_text(prefix + method + snapshot_method + suffix)
    subprocess.run(['g++', '-std=c++17', '-fsanitize=address,undefined', '-fno-pie', '-no-pie', str(path / 'verify.cpp'), '-o', str(path / 'verify')], check=True)
    subprocess.run([str(path / 'verify')], check=True, timeout=10)
