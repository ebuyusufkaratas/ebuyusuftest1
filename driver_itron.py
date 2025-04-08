# -*- coding: utf-8 -*-
"""
ITRON Su Sayacı için WMBus Sürücüsü
"""

import logging
import binascii
import traceback
from driver_base import WMBusDriverBase

logger = logging.getLogger("itron_driver")

class ItronDriver(WMBusDriverBase):
    MANUFACTURER_ID = "0x2697"  # ITW (ASCII kodları)
    DETECT_MVT = ["0x00", "0x03", "0x07", "0x16", "0x33"]  # Algılama kodları



    @classmethod
    def detect(cls, telegram_data):
        """Cihaz algılama metodu"""
        try:
            manufacturer_code = telegram_data.get("manufacturer_code")
            mvt = telegram_data.get("device_type_code")
            version = telegram_data.get("version")
            ci_field = telegram_data.get("ci_field")

            # Tüm detayları logla
            logger.info(f"Detect için tüm veriler: {telegram_data}")
            logger.info(f"Manufacturer Code (hex): {manufacturer_code}")
            logger.info(f"Manufacturer Code (int): {int(manufacturer_code, 16)}")
            logger.info(f"MVT: {mvt}")
            logger.info(f"Version: {version}")
            logger.info(f"CI Field: {ci_field}")

            # Algılama kriterleri
            conditions = [
                int(manufacturer_code, 16) == int("0x2697", 16),  # Üretici kodu
                str(mvt) in cls.DETECT_MVT,  # Cihaz tipi
            ]

            result = all(conditions)
            logger.info(f"Detect Sonucu: {result}")
            logger.info(f"Koşullar: {conditions}")
            
            return result
        except Exception as e:
            logger.error(f"Detect hatası: {e}")
            logger.error(traceback.format_exc())
            return False

    def matches(self, manufacturer_id, device_type):
        """Eşleşme kontrolü"""
        return manufacturer_id == self.MANUFACTURER_ID

    def parse(self):
        """Telgraf verilerini çözümle"""
        try:
            from wmbus_constants import DIF_TYPES, VIF_TYPES

            # Temel bilgileri ayarla
            self.result["media"] = "water"
            self.result["meter"] = "itron"

            # Payload'ı çıkar
            payload = self.extract_payload()
            
            if not payload:
                logger.warning("Payload bulunamadı!")
                return self.result

            # Farklı alan çözümleme yaklaşımları
            total_m3_parsers = [
                self._parse_total_volume_with_vif_13,
                self._parse_total_volume_with_vif_02,
            ]

            for parser in total_m3_parsers:
                total_m3 = parser(payload)
                if total_m3 is not None:
                    self.result["total_m3"] = total_m3
                    break

            return self.result
        except Exception as e:
            logger.error(f"ITRON çözümleme hatası: {e}")
            logger.error(traceback.format_exc())
            return self.result

    def _parse_total_volume_with_vif_13(self, payload):
        """Volume VIF (0x13) ile toplam hacim çözümleme"""
        try:
            # 0x04 (32-bit integer) ve 0x13 (Volume) kombinasyonunu ara
            for i in range(len(payload)):
                if payload[i] == 0x04 and payload[i+1] == 0x13:
                    total_volume_bytes = payload[i+2:i+6]
                    total_volume = int.from_bytes(total_volume_bytes, byteorder='little')
                    total_m3 = total_volume / 1000.0
                    
                    logger.info(f"VIF 0x13 ile Toplam Hacim: {total_volume}, m³: {total_m3}")
                    return total_m3
        except Exception as e:
            logger.warning(f"VIF 0x13 çözümleme hatası: {e}")
        return None

    def _parse_total_volume_with_vif_02(self, payload):
        """Enerji VIF (0x02) ile toplam hacim çözümleme"""
        try:
            # 0x0C (8 basamaklı BCD) ve 0x02 (Enerji) kombinasyonunu ara
            for i in range(len(payload)):
                if payload[i] == 0x0C and payload[i+1] == 0x02:
                    total_volume_bytes = payload[i+2:i+6]
                    
                    # BCD formatında tersten oku
                    total_volume = int(total_volume_bytes[::-1].hex(), 16)
                    total_m3 = total_volume / 10.0
                    
                    logger.info(f"VIF 0x02 ile Toplam Hacim: {total_volume}, m³: {total_m3}")
                    return total_m3
        except Exception as e:
            logger.warning(f"VIF 0x02 çözümleme hatası: {e}")
        return None

    def extract_payload(self):
        """Payload çıkarma işlevi"""
        try:
            raw_payload = None
            if hasattr(self, 'telegram_data') and isinstance(self.telegram_data, dict):
                raw_payload = self.telegram_data.get('raw_payload')
                if raw_payload and isinstance(raw_payload, str):
                    return binascii.unhexlify(raw_payload)
            return None
        except Exception as e:
            logger.error(f"Payload çıkarma hatası: {e}")
            return None