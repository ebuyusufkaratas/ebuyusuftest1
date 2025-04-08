# -*- coding: utf-8 -*-
"""
Techem Compact V ısı sayacı için sürücü.
"""

from driver_base import WMBusDriverBase
import binascii
import logging
import traceback

# Loglama ayarları
logger = logging.getLogger("techem_driver")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

class TechemCompactDriver(WMBusDriverBase):
    MANUFACTURER_ID = "0x5068"

    def matches_ci(self, ci_field):
        try:
            # CI alanını ve versiyonu güvenli bir şekilde kontrol et
            ci_field_int = int(ci_field, 16) if isinstance(ci_field, str) else ci_field
            version = self.telegram_info.get("version")
            
            version_int = version if isinstance(version, int) else int(str(version), 0)
            
            # Hem CI alanı hem versiyon kontrolü
            result = (ci_field_int == 0xa2) and (version_int == 0x39)
            
            logger.info(f"[MATCH-CI] TCH check: ci_field={ci_field} ({ci_field_int}), version={version} ({version_int}) -> {result}")
            return result
        except Exception as e:
            logger.warning(f"[MATCH-CI] Exception: {e}")
            return False    


    
    def matches(self, manufacturer_id, device_type):
        try:
            # Üretici ID kontrolü
            if manufacturer_id != self.MANUFACTURER_ID:
                return False

            # Versiyon kontrolü: sadece 0x39 olanlar bu sürücüye girsin
            version = self.telegram_info.get("version")
            if version != 0x39:
                return False

            # Cihaz tipi kontrolü (isteğe bağlı, istersen bu kısmı silebilirsin)
            if device_type is not None:
                try:
                    device_type_int = int(device_type, 16) if isinstance(device_type, str) and device_type.startswith("0x") else int(device_type)
                    return device_type_int in [0x43, 0x45, 0x39]
                except Exception as e:
                    logger.warning(f"[MATCH-DEVICE] Cihaz tipi dönüştürülemedi: {e}")
                    return False

            return True
        except Exception as e:
            logger.warning(f"[MATCH-MAIN] Exception: {e}")
        return False

    
    def extract_payload(self, data=None):
        try:
            if data is not None:
                logger.info(f"Ham veri doğrudan verildi: {len(data)} bayt")
                return data
            raw_payload = None
            if hasattr(self, 'telegram_data') and isinstance(self.telegram_data, dict):
                if 'raw_payload' in self.telegram_data:
                    raw_data = self.telegram_data['raw_payload']
                    logger.info(f"telegram_data'dan raw_payload alındı: {type(raw_data)}")
                    if isinstance(raw_data, bytes):
                        raw_payload = raw_data
                    else:
                        try:
                            raw_payload = binascii.unhexlify(raw_data)
                            logger.info(f"raw_payload hex stringden dönüştürüldü, uzunluk: {len(raw_payload)}")
                        except:
                            logger.error("raw_payload hex stringden dönüştürülemedi")
            if raw_payload is None and hasattr(self, 'data_blocks'):
                if isinstance(self.data_blocks, list) and len(self.data_blocks) > 0:
                    first_block = self.data_blocks[0]
                    if isinstance(first_block, dict) and 'raw_data' in first_block:
                        raw_hex = first_block['raw_data']
                        logger.info(f"İlk bloktan raw_data alındı: {raw_hex[:20] if len(raw_hex) > 20 else raw_hex}...")
                        try:
                            raw_payload = binascii.unhexlify(raw_hex)
                            logger.info(f"Blok verisinden payload alındı, uzunluk: {len(raw_payload)}")
                        except:
                            logger.error("Blok verisi dönüştürülemedi")
            if raw_payload is not None:
                logger.info(f"PAYLOAD BYTES: {binascii.hexlify(raw_payload).decode()}")
                logger.info(f"BYTE LENGTH: {len(raw_payload)}")
                return raw_payload
            logger.warning("Payload için hiçbir kaynak bulunamadı!")
            return None
        except Exception as e:
            logger.error(f"Payload çıkarma hatası: {e}")
            logger.error(traceback.format_exc())
            return None

    def parse(self):
        try:
            self.result["media"] = "heat"
            self.result["meter"] = "compact5"
            payload = self.extract_payload()
            if not payload:
                logger.warning("Techem payload bulunamadı!")
                return self.result
            telegram_format = self.determine_telegram_format(payload)
            logger.info(f"Techem telgraf formatı: {telegram_format}")
            if telegram_format == "standard":
                self.parse_standard_format(payload)
            elif telegram_format == "extended":
                self.parse_extended_format(payload)
            elif telegram_format == "variant":
                self.parse_variant_format(payload)
            else:
                logger.warning(f"Bilinmeyen Techem format: 0x{payload[0]:02x}. Varyant formatı olarak deneniyor.")
                self.parse_variant_format(payload)
            logger.info(f"Techem çözümleme sonucu: {self.result}")
            return self.result
        except Exception as e:
            logger.error(f"Techem çözümleme hatası: {e}")
            logger.error(traceback.format_exc())
            return self.result

    def determine_telegram_format(self, payload):
        if len(payload) < 1:
            return "unknown"
        first_byte = payload[0]
        logger.info(f"Format belirleme: İlk bayt 0x{first_byte:02x}")
        if first_byte == 0x9F:
            return "standard"
        elif first_byte == 0xAF:
            return "extended"
        elif first_byte == 0x10:
            if len(payload) > 1:
                second_byte = payload[1]
                logger.info(f"Varyant format kontrolü: İkinci bayt 0x{second_byte:02x}")
                if second_byte == 0x9F or second_byte == 0x67:
                    return "variant"
        logger.warning(f"Bilinmeyen format: İlk bayt 0x{first_byte:02x}")
        return "unknown"

    
    def parse_standard_format(self, payload):
        """Standart Techem Compact V formatını çözümle."""
        try:
            if len(payload) < 9:
                logger.warning(f"Standart format için veri çok kısa: {len(payload)} bayt")
                return
                
            # Önceki dönem değeri (3-4. baytlar)
            prev_lo = payload[3] if len(payload) > 3 else 0
            prev_hi = payload[4] if len(payload) > 4 else 0
            prev_energy = (256.0 * prev_hi + prev_lo)
            
            # Mevcut dönem değeri (7-8. baytlar)
            curr_lo = payload[7] if len(payload) > 7 else 0
            curr_hi = payload[8] if len(payload) > 8 else 0
            curr_energy = (256.0 * curr_hi + curr_lo)
            
            logger.info(f"Prev: {prev_hi:02x}{prev_lo:02x} = {prev_energy}")
            logger.info(f"Curr: {curr_hi:02x}{curr_lo:02x} = {curr_energy}")
            
            # Toplam enerji hesaplaması
            total_energy = prev_energy + curr_energy
            
            # Sonuçları kaydet
            self.result["total_kwh"] = total_energy
            self.result["current_kwh"] = curr_energy
            self.result["previous_kwh"] = prev_energy
            
            logger.info(f"Standart format çözümlendi: toplam={total_energy}, mevcut={curr_energy}, önceki={prev_energy}")
            
        except Exception as e:
            logger.error(f"Standart format çözümleme hatası: {e}")
            logger.error(traceback.format_exc())


    def parse_extended_format(self, payload):
        try:
            if len(payload) < 20:
                logger.warning(f"Genişletilmiş format için veri çok kısa: {len(payload)} bayt")
                return
            curr_energy = int.from_bytes(payload[9:13], byteorder='little')
            prev_energy = int.from_bytes(payload[13:17], byteorder='little')
            total_energy = curr_energy + prev_energy
            self.result["total_kwh"] = total_energy
            self.result["current_kwh"] = curr_energy
            self.result["previous_kwh"] = prev_energy
            logger.info(f"Extended format çözümlendi: toplam={total_energy}, mevcut={curr_energy}, önceki={prev_energy}")
        except Exception as e:
            logger.error(f"Extended format çözümleme hatası: {e}")
            logger.error(traceback.format_exc())

    def parse_variant_format(self, payload):

        
        try:
            logger.info("Varyant format çözümlemesi başlatılıyor...")

            # 🟢 DÜZGÜN OFFSET = 6
            
            offset = 0

            prev_lo = payload[offset + 3]   # 0x86
            prev_hi = payload[offset + 4]   # 0x61
            previous_kwh = prev_hi * 256 + prev_lo  # 24966

            curr_lo = payload[offset + 7]   # 0x1c
            curr_hi = payload[offset + 8]   # 0x01

            self.curr_lo = curr_lo
            self.curr_hi = curr_hi
            self.prev_lo = prev_lo
            self.prev_hi = prev_hi


            current_kwh = curr_hi * 256 + curr_lo  # 284


            logger.info(f"curr_lo: 0x{curr_lo:02x}, curr_hi: 0x{curr_hi:02x}")
            logger.info(f"prev_lo: 0x{prev_lo:02x}, prev_hi: 0x{prev_hi:02x}")

            total_kwh = current_kwh + previous_kwh

            self.result["total_kwh"] = total_kwh
            self.result["current_kwh"] = current_kwh
            self.result["previous_kwh"] = previous_kwh
            




            logger.info(f"Varyant formatı çözümlendi: toplam={total_kwh}, mevcut={current_kwh}, önceki={previous_kwh}")
        except Exception as e:
            logger.error(f"Varyant format çözümleme hatası: {e}")
            logger.error(traceback.format_exc())





    def parse_telegram(self, telegram_data):
        """
        Driver Manager tarafından çağrılır. Telgrafı çözümleyip sonucu döndürür.
        """
        self.telegram_info = telegram_data.get("telegram_info", {})
        self.data_blocks = telegram_data.get("data_blocks", [])
        self.telegram_data = telegram_data  # extract_payload için
        self.generate_basic_info()
        return self.parse()
