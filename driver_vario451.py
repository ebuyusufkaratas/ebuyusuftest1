import logging
import traceback
import binascii
from driver_base import WMBusDriverBase

logger = logging.getLogger("vario451_driver")

class TechemVario451Driver(WMBusDriverBase):
    MANUFACTURER_ID = "0x5068"

    def match_ci(self, telegram_data):
        try:
            ci_field = telegram_data.get("ci_field")
            version = telegram_data.get("version")
            
            # CI alanı kontrolü yapılırken None değerleri kontrol edilsin
            if ci_field is None or version is None:
                logger.warning(f"[MATCH-CI] Geçersiz veri: CI veya versiyon None")
                return False

            logger.info(f"[MATCH-CI] TechemVario451Driver kontrol ediliyor: CI={ci_field}, Version={version}")

            # Eğer versiyon 0x39 ise, bu sürücü devreye girmemeli
            if version == 0x39:
                logger.info(f"[MATCH-CI] Versiyon 0x39, TechemVario451Driver devreye girmiyor.")
                return False
            
            # CI alanı ve versiyonun doğru olması durumunda sürücü devreye girecek
            return ci_field == "0xa2" and version == 0x17
        except Exception as e:
            logger.warning(f"[MATCH-CI] Exception: {e}")
            return False






    def matches(self, manufacturer_id, device_type):
        return manufacturer_id == self.MANUFACTURER_ID

    def parse(self):
        try:
            self.result["media"] = "heat"
            self.result["meter"] = "vario451"

            raw_payload = None
            if hasattr(self, "telegram_data") and isinstance(self.telegram_data, dict):
                raw_payload = self.telegram_data.get("raw_payload")
                if raw_payload and isinstance(raw_payload, str):
                    payload = binascii.unhexlify(raw_payload)
                else:
                    logger.error("Payload boş veya yanlış formatta.")
                    return self.result
            else:
                logger.error("telegram_data eksik.")
                return self.result

            if len(payload) < 9:
                logger.warning("Payload çok kısa.")
                return self.result

            # previous: byte[3], byte[4]
            prev_lo = payload[3]
            prev_hi = payload[4]
            previous_gj = (256.0 * prev_hi + prev_lo) / 1000

            # current: byte[7], byte[8]
            curr_lo = payload[7]
            curr_hi = payload[8]
            current_gj = (256.0 * curr_hi + curr_lo) / 1000

            total_gj = current_gj + previous_gj
            total_kwh = total_gj * 277.7778
            current_kwh = current_gj * 277.7778
            previous_kwh = previous_gj * 277.7778

            self.result["total_kwh"] = round(total_kwh, 3)
            self.result["current_kwh"] = round(current_kwh, 3)
            self.result["previous_kwh"] = round(previous_kwh, 3)

            logger.info(f"Vario451 çözümlendi: toplam={total_kwh}, mevcut={current_kwh}, önceki={previous_kwh}")
            return self.result

        except Exception as e:
            logger.error(f"Vario451 çözümleme hatası: {e}")
            logger.error(traceback.format_exc())
            return self.result
