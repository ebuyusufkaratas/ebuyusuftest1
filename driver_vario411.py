# -*- coding: utf-8 -*-
"""
Techem Vario 411 sayaçları için özel sürücü.
CI alanı: 0x8C
Versiyon: 0x17
"""

import logging
from datetime import datetime
from driver_base import WMBusDriverBase as BaseDriver

logger = logging.getLogger("vario411_driver")

class TechemVario411Driver(BaseDriver):
    MANUFACTURER_ID = "0x5068"
    DEVICE_TYPE = 0x04

    def match_ci(self, telegram_data):
        try:
            ci_field = telegram_data.get("ci_field")
            version = telegram_data.get("version")
            logger.info(f"[MATCH-CI] TechemVario411Driver kontrol ediliyor: CI={ci_field}, Version={version}")
            return ci_field == "0x8c" and version == 0x17
        except Exception as e:
            logger.warning(f"[MATCH-CI] Exception: {e}")
            return False

    def parse(self):
        try:
            raw = self.telegram_data.get("raw_payload")
            if not raw:
                logger.error("Raw payload bulunamadı")
                return self.result

            payload = bytes.fromhex(raw)

            if len(payload) < 40:
                logger.warning("Payload çok kısa")
                return self.result

            # total_kwh (Wh olarak, 32-bit LE, offset 12)
            target_raw = payload[86:90]
            logger.info(f"target_raw: {target_raw.hex()}")  # target_raw log'a yazdırılıyor
            target_wh = int.from_bytes(target_raw, byteorder="little")
            total_kwh = target_wh 

            # target_date (BCD encoded date, offset 34-36)
            date_raw = payload[34:37]
            year = 2000 + (date_raw[0] & 0x7F)
            month = date_raw[1] & 0x0F
            day = date_raw[2] & 0x1F

            try:
                target_date = datetime(year, month, day).strftime("%Y-%m-%d")
            except Exception as e:
                logger.warning(f"Tarih ayrıştırılamadı: {e}")
                target_date = None

            # dll_version (1 byte, örneğin offset 17)
            dll_version = payload[17]

            self.result.update({
                "meter": "vario411",
                "total_kwh": total_kwh,
                "target_date": target_date,
                "dll_version": dll_version
            })

            logger.info(f"Techem Vario411 çözümleme: total_kwh={total_kwh}, target_date={target_date}, dll_version={dll_version}")

        except Exception as e:
            logger.error(f"Vario411 çözümleme hatası: {e}")
            import traceback
            logger.error(traceback.format_exc())

        return self.result
