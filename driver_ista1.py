# -*- coding: utf-8 -*-
"""
ISTA Sensonic 3 Heat Meter için sürücü.
"""

from driver_base import WMBusDriverBase
import logging
import binascii
import traceback

logger = logging.getLogger("ista_driver")

class IstaDriver(WMBusDriverBase):
    MANUFACTURER_ID = "0x495354"  # IST (ASCII kodları)

    def matches(self, manufacturer_id, device_type):
        """Sürücünün eşleşme kriterlerini tanımla"""
        try:
            return manufacturer_id == self.MANUFACTURER_ID
        except Exception as e:
            logger.warning(f"Eşleşme kontrolünde hata: {e}")
            return False

    def matches_ci(self, ci_field):
        """CI alanı kontrolü"""
        try:
            return ci_field == "0xa9"  # Dokümanda belirtilen CI alanı
        except Exception as e:
            logger.warning(f"CI alanı kontrolünde hata: {e}")
            return False

    def parse(self):
        """Telgraf verilerini çözümle"""
        try:
            # Temel bilgileri ayarla
            self.result["media"] = "heat"
            self.result["meter"] = "istaheat"

            # Payload'ı çıkar
            payload = self.extract_payload()
            
            if not payload:
                logger.warning("Payload bulunamadı!")
                return self.result

            # Toplam enerji ve diğer detayları çıkar
            # Bu kısım örnek telgraflara göre detaylandırılmalı
            # Dokümanda verilen test telgraflarındaki hex değerlerden çıkarılabilir
            
            # Örnek bir çözümleme (test telgraflarına göre)
            if len(payload) >= 20:
                # Toplam enerji için muhtemel yerler
                # Bu değerler kesin değil, test telgraflarına göre ayarlanmalı
                try:
                    # Muhtemel toplam enerji çözümleme (örnek)
                    # Dikkat: Bu kısım test telgraflarına göre doğrulanmalı
                    total_kwh_bytes = payload[14:18]  # Örnek konum
                    total_kwh = int.from_bytes(total_kwh_bytes, byteorder='little') / 10.0

                    self.result["total_kwh"] = total_kwh
                    logger.info(f"ISTA çözümlendi: toplam={total_kwh}")
                except Exception as detail_error:
                    logger.error(f"Detay çözümleme hatası: {detail_error}")

            return self.result
        except Exception as e:
            logger.error(f"ISTA çözümleme hatası: {e}")
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