from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'components/wmbus_radio/transceiver.cpp').read_text()
method = source[source.index('        bool RadioTransceiver::read_in_task'):source.index('        void RadioTransceiver::set_reset_pin')]
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
unsigned ulTaskNotifyTake(int, int) {
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
'''
suffix = r'''
int main() {
    for (size_t received : {size_t{0}, size_t{1}, size_t{32}, size_t{33}, size_t{64}}) {
        logs.clear();
        RadioTransceiver radio;
        radio.remaining = received;
        std::vector<uint8_t> buffer(65, 0xFF);
        assert(radio.read_in_task(buffer.data(), buffer.size()) == false);
        assert(logs.size() == 1 + (received + 31) / 32);
        assert(logs[0] == "Incomplete radio read: received " + std::to_string(received) + "/65 bytes");
        size_t offset = 0;
        for (size_t i = 1; i < logs.size(); ++i) {
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
    std::puts("PASS: partial-read diagnostics and reception after notification timeout.");
}
'''
with tempfile.TemporaryDirectory() as temporary:
    path = Path(temporary)
    (path / 'verify.cpp').write_text(prefix + method + suffix)
    subprocess.run(['g++', '-std=c++17', '-fsanitize=address,undefined', '-fno-pie', '-no-pie', str(path / 'verify.cpp'), '-o', str(path / 'verify')], check=True)
    subprocess.run([str(path / 'verify')], check=True, timeout=10)
