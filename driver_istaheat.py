# -*- coding: utf-8 -*-
"""
ISTA Heat Meter için WMBus sürücüsü
"""

import logging
import binascii
import traceback
from driver_base import WMBusDriverBase

logger = logging.getLogger("istaheat_driver")

class IstaHeatDriver(WMBusDriverBase):
    MANUFACTURER_ID = "0x2674"  # Çıktıdaki gerçek üretici kodu
    DETECT_MVT = ["0x04"]  # Cihaz tipi

    @classmethod
    def detect(cls, telegram_data):
        """Cihaz algılama metodu"""
        try:
            manufacturer_code = telegram_data.get("manufacturer_code")
            mvt = telegram_data.get("device_type_code")
            ci_field = telegram_data.get("ci_field")
            version = telegram_data.get("version")

            # Algılama kriterleri
            conditions = [
                manufacturer_code == cls.MANUFACTURER_ID,
                any(mvt == m for m in cls.DETECT_MVT),
                version == 0xa9,  # Versiyonu kontrol et
                ci_field == "0x8c"  # CI alanını kontrol et
            ]

            result = all(conditions)
            logger.info(f"ISTA Heat Driver Detect: {result}")
            logger.info(f"Kontrol parametreleri: manufacturer={manufacturer_code}, mvt={mvt}, version={version}, ci_field={ci_field}")
            return result
        except Exception as e:
            logger.error(f"Detect hatası: {e}")
            return False

    def matches(self, manufacturer_id, device_type):
        """Eşleşme kontrolü"""
        return manufacturer_id == self.MANUFACTURER_ID

    def parse(self):
        """Telgraf verilerini çözümle"""
        try:
            from wmbus_constants import DIF_TYPES, VIF_TYPES

            # Temel bilgileri ayarla
            self.result["media"] = "heat"
            self.result["meter"] = "istaheat"

            # Payload'ı çıkar
            payload = self.extract_payload()
            
            if not payload:
                logger.warning("Payload bulunamadı!")
                return self.result

            # Payload içinden DIF ve VIF'i bul
            for i in range(len(payload)):
                if payload[i] in [0x0C] and i+1 < len(payload) and payload[i+1] in [0x05]:
                    dif = payload[i]
                    vif = payload[i+1]
                    
                    logger.info(f"DIF: 0x{dif:02x} - {DIF_TYPES.get(dif, 'Bilinmeyen')}")
                    logger.info(f"VIF: 0x{vif:02x} - {VIF_TYPES.get(vif, 'Bilinmeyen')}")
                    
                    # DIF ve VIF'e göre veri uzunluğunu belirle
                    data_length = DIF_TYPES.get(dif, {"length": 0})["length"]
                    
                    if data_length > 0 and i+2+data_length <= len(payload):
                        # Veriyi çıkar
                        data = payload[i+2:i+2+data_length]
                        
                        # BCD formatında tersten oku
                        total_energy = int(data[::-1].hex())
                        
                        # VIF'e göre çarpanı belirle
                        multiplier = VIF_TYPES.get(vif, {"multiplier": 1})["multiplier"]
                        
                        # Toplam enerjiyi hassas şekilde hesapla
                        total_kwh = float(f"{total_energy / 10:.1f}")
                        
                        logger.info(f"Ham Veri: {data.hex()}")
                        logger.info(f"Toplam Enerji: {total_energy}")
                        logger.info(f"Çarpan: {multiplier}")
                        logger.info(f"Toplam kWh: {total_kwh}")
                        
                        self.result["total_kwh"] = total_kwh
                        break

            return self.result
        except Exception as e:
            logger.error(f"ISTA Heat çözümleme hatası: {e}")
            logger.error(traceback.format_exc())
            return self.result


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