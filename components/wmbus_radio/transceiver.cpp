#include "transceiver.h"

#include <algorithm>

#include "esphome/core/log.h"
#include "esphome/core/helpers.h"
#include "esphome/core/hal.h"

#include "freertos/FreeRTOS.h"

namespace esphome
{
    namespace wmbus_radio
    {
        static const char *TAG = "wmbus.transceiver";

        bool RadioTransceiver::read_in_task(uint8_t *buffer, size_t length)
        {
            constexpr uint32_t idle_timeout_us = 1000;
            const uint8_t *buffer_start = buffer;
            const uint8_t *buffer_end = buffer + length;
            size_t recovered_bytes = 0;
            const uint32_t started_us = micros();
            uint32_t last_byte_us = started_us;

            while (buffer != buffer_end)
            {
                auto byte = this->read();
                if (byte.has_value())
                {
                    *buffer++ = *byte;
                    last_byte_us = micros();
                    continue;
                }
                const uint32_t wait_started_us = micros();
                const auto notification_count = ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(1));
                const uint32_t wait_finished_us = micros();
                if (notification_count == 0)
                {
                    auto pending_byte = this->read();
                    if (pending_byte.has_value())
                    {
                        *buffer++ = *pending_byte;
                        ++recovered_bytes;
                        last_byte_us = micros();
                        continue;
                    }
                    const size_t received = buffer - buffer_start;
                    const uint32_t failed_us = micros();
                    if (uint32_t(failed_us - last_byte_us) < idle_timeout_us)
                    {
                        continue;
                    }
                    this->log_rx_failure();
                    ESP_LOGD(TAG, "Incomplete radio read: received %zu/%zu bytes", received, length);
                    ESP_LOGD(TAG, "RX timing: elapsed_us=%lu idle_us=%lu wait_us=%lu timeout_ticks=%lu recovered=%zu",
                             static_cast<unsigned long>(failed_us - started_us),
                             static_cast<unsigned long>(failed_us - last_byte_us),
                             static_cast<unsigned long>(wait_finished_us - wait_started_us),
                             static_cast<unsigned long>(pdMS_TO_TICKS(1)), recovered_bytes);
                    for (size_t offset = 0; offset < received; offset += 32)
                    {
                        const size_t chunk_size = std::min(size_t{32}, received - offset);
                        ESP_LOGD(TAG, "RAW[%zu]: %s", offset,
                                 format_hex(buffer_start + offset, chunk_size).c_str());
                    }
                    return false;
                }
            }

            if (recovered_bytes > 0)
            {
                ESP_LOGD(TAG, "Radio read completed: recovered %zu bytes after notification timeout", recovered_bytes);
            }
            return true;
        }

        void RadioTransceiver::set_reset_pin(InternalGPIOPin *reset_pin)
        {
            this->reset_pin_ = reset_pin;
        }

        void RadioTransceiver::set_irq_pin(InternalGPIOPin *irq_pin)
        {
            this->irq_pin_ = irq_pin;
        }

        void RadioTransceiver::reset()
        {
            this->reset_pin_->digital_write(0);
            delay(5);
            this->reset_pin_->digital_write(1);
            delay(5);
        }

        void RadioTransceiver::common_setup()
        {
            this->reset_pin_->setup();
            this->irq_pin_->setup();
            this->spi_setup();
        }

        uint8_t RadioTransceiver::spi_transaction(uint8_t operation, uint8_t address, std::initializer_list<uint8_t> data)
        {
            this->delegate_->begin_transaction();
            auto rval = this->delegate_->transfer(operation | address);
            for (auto byte : data)
                rval = this->delegate_->transfer(byte);
            this->delegate_->end_transaction();
            return rval;
        }

        uint8_t RadioTransceiver::spi_read(uint8_t address)
        {
            return this->spi_transaction(0x00, address, {0});
        }

        void RadioTransceiver::spi_write(uint8_t address, std::initializer_list<uint8_t> data)
        {
            this->spi_transaction(0x80, address, data);
        }

        void RadioTransceiver::spi_write(uint8_t address, uint8_t data)
        {
            this->spi_write(address, {data});
        }

        void RadioTransceiver::dump_config()
        {
            ESP_LOGCONFIG(TAG, "Transceiver: %s", this->get_name());
            LOG_PIN("  Reset Pin: ", this->reset_pin_);
            LOG_PIN("  IRQ Pin: ", this->irq_pin_);
        }
    }
}
