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
logger.setLevel(logging.DEBUG)  # Debug seviyesinde logla

class TechemCompactDriver(WMBusDriverBase):
    """
    Techem Compact V ısı sayacı için özel sürücü.
    
    Üretici: Techem (0x5068)
    Cihaz tipi: Heat Cost Allocator (0x43 veya 0x45)
    
    Bu cihaz, özel bir protokol kullanır ve normal DIF/VIF yapısını izlemez.
    Veriler, CI (0xA2) alanıyla tamamen üretici-spesifik olarak işaretlenir.
    """
    MANUFACTURER_ID = "0x5068"  # Techem (TCH)
    # Techem farklı cihaz tiplerini destekler
    
    def matches_ci(self, ci_field):
        """
        CI alanına göre eşleşme kontrolü.
        Techem Compact V cihazları CI=0xA2 kullanır.
        """
        return ci_field == "0xa2"
    
    def matches(self, manufacturer_id, device_type):
        """
        Üretici ve cihaz tipine göre eşleşme kontrolü.
        """
        # Üretici Techem mi?
        if manufacturer_id != self.MANUFACTURER_ID:
            return False
            
        # CI alanını kontrol et
        if hasattr(self, 'telegram_info') and self.telegram_info.get("ci_field") == "0xa2":
            logger.info("CI alanı 0xa2, Techem formatı eşleşti")
            return True
        
        # Desteklenen cihaz tipleri
        supported_types = [0x04, 0xc3, 0x43, 0x45, 0x39, 0x22]
        
        # Cihaz tipini kontrol et
        if device_type is not None:
            try:
                # Hem hex string hem de int olarak kontrol et
                device_type_int = int(device_type, 16) if isinstance(device_type, str) and device_type.startswith("0x") else device_type
                return device_type_int in supported_types
            except:
                pass
                
        return False
    
    def extract_payload(self, data=None):
        """
        Telgraf verilerinden ham payload'ı çıkarır.
        
        Techem Compact V cihazları TPL'den sonra ve ilk veri
        bloğundan elde edilen veriyi kullanır.
        """
        try:
            # Eğer ham payload verilmişse onu kullan
            if data is not None:
                logger.info(f"Ham veri doğrudan verildi: {len(data)} bayt")
                return data
            
            # Telgraf içindeki raw_payload'ı kontrol et
            raw_payload = None
            
            # telegram_data parametresi varsa, ondaki raw_payload alanını kontrol et
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
                
                # CI alanı sonrası veriyi alabilmek için, telegram_info'daki original_telegram'ı kontrol et
                if 'telegram_info' in self.telegram_data and isinstance(self.telegram_data['telegram_info'], dict):
                    if '_original_telegram' in self.telegram_data['telegram_info']:
                        orig_hex = self.telegram_data['telegram_info']['_original_telegram']
                        logger.info(f"Orijinal telgraf bulundu: {orig_hex[:20]}...")
                        
                        try:
                            orig_data = binascii.unhexlify(orig_hex)
                            # CI alanını bul (genellikle 10. bayt)
                            ci_pos = 10
                            if len(orig_data) > ci_pos and orig_data[ci_pos] in (0xA1, 0xA2, 0xA3):
                                logger.info(f"CI alanı bulundu pozisyon {ci_pos}, sonrasındaki veri alınıyor")
                                raw_payload = orig_data[ci_pos+1:]
                        except:
                            logger.error("Orijinal telgraf dönüştürülemedi")
            
            # data_blocks'ı kontrol et
            if raw_payload is None and hasattr(self, 'data_blocks'):
                if isinstance(self.data_blocks, list) and len(self.data_blocks) > 0:
                    logger.info(f"data_blocks kontrol ediliyor: {len(self.data_blocks)} blok")
                    
                    # İlk bloğu dene
                    first_block = self.data_blocks[0]
                    if isinstance(first_block, dict) and 'raw_data' in first_block:
                        raw_hex = first_block['raw_data']
                        logger.info(f"İlk bloktan raw_data alındı: {raw_hex[:20] if len(raw_hex) > 20 else raw_hex}...")
                        
                        try:
                            raw_payload = binascii.unhexlify(raw_hex)
                            logger.info(f"Blok verisinden payload alındı, uzunluk: {len(raw_payload)}")
                        except:
                            logger.error("Blok verisi dönüştürülemedi")
            
            # telegram_info'daki ci_field ve raw veriyi alabilmek için doğrudan kontrol
            if raw_payload is None and hasattr(self, 'telegram_info'):
                info = self.telegram_info
                
                # CI alanını kontrol et
                if 'ci_field' in info and info['ci_field'] == '0xa2':
                    # Raw veriyi bul
                    if '_raw_telegram' in info:
                        raw_hex = info['_raw_telegram']
                        logger.info(f"_raw_telegram bulundu: {raw_hex[:20]}...")
                        
                        try:
                            orig_data = binascii.unhexlify(raw_hex)
                            # CI alanını bul (genellikle 10. bayt)
                            ci_pos = 10
                            if len(orig_data) > ci_pos and orig_data[ci_pos] == 0xA2:
                                logger.info(f"CI alanı bulundu, sonrasındaki veri alınıyor")
                                raw_payload = orig_data[ci_pos+1:]
                        except:
                            logger.error("_raw_telegram dönüştürülemedi")
            
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
        """Techem Compact V telgrafını çözümle."""
        try:
            # Cihaz tipini ve kimliğini belirle
            self.result["media"] = "heat"
            self.result["meter"] = "compact5"
            
            # Ham veriyi al
            payload = self.extract_payload()
            if not payload:
                logger.warning("Techem payload bulunamadı!")
                return self.result
            
            # Telgraf versiyonunu belirle
            telegram_format = self.determine_telegram_format(payload)
            logger.info(f"Techem telgraf formatı: {telegram_format}")
            
            # Format tipine göre çözümle
            if telegram_format == "standard":
                self.parse_standard_format(payload)
            elif telegram_format == "extended":
                self.parse_extended_format(payload)
            elif telegram_format == "variant":
                self.parse_variant_format(payload)
            else:
                # Bilinmeyen format - en azından varyant gibi çözümlemeyi deneyelim
                logger.warning(f"Bilinmeyen Techem format: 0x{payload[0]:02x}. Varyant formatı olarak deneniyor.")
                self.parse_variant_format(payload)
            
            # Çözümleme sonucunu logla
            logger.info(f"Techem çözümleme sonucu: {self.result}")
            
            return self.result
            
        except Exception as e:
            logger.error(f"Techem çözümleme hatası: {e}")
            logger.error(traceback.format_exc())
            return self.result
    
    def determine_telegram_format(self, payload):
        """
        Hangi Techem formatının kullanıldığını belirler.
        
        Techem cihazları farklı veri yapıları kullanabilir.
        """
        if len(payload) < 1:
            return "unknown"
        
        # Format belirleme
        first_byte = payload[0]
        logger.info(f"Format belirleme: İlk bayt 0x{first_byte:02x}")
        
        if first_byte == 0x9F:
            return "standard"  # Standart Compact V formatı
        elif first_byte == 0xAF:
            return "extended"  # Genişletilmiş format
        elif first_byte == 0x10:
            # Vario veya başka bir varyant
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
        """Genişletilmiş Techem formatını çözümle."""
        try:
            if len(payload) < 20:
                logger.warning(f"Genişletilmiş format için veri çok kısa: {len(payload)} bayt")
                return
            
            # Extended formatta farklı konumlarda değerler
            curr_energy_idx = 9
            prev_energy_idx = 13
            
            # Mevcut dönem değeri
            curr_energy = int.from_bytes(payload[curr_energy_idx:curr_energy_idx+4], byteorder='little')
            
            # Önceki dönem değeri
            prev_energy = int.from_bytes(payload[prev_energy_idx:prev_energy_idx+4], byteorder='little')
            
            # Toplam enerji
            total_energy = curr_energy + prev_energy
            
            # Sonuçları kaydet
            self.result["total_kwh"] = total_energy
            self.result["current_kwh"] = curr_energy
            self.result["previous_kwh"] = prev_energy
            
            # Ek bilgiler
            if len(payload) > 17:
                # Son okuma tarihi (örnek format)
                date_bytes = payload[17:19]
                try:
                    day = date_bytes[0] & 0x1F
                    month = ((date_bytes[0] & 0xE0) >> 5) | ((date_bytes[1] & 0x1) << 3)
                    year = 2000 + ((date_bytes[1] & 0xF0) >> 4)
                    self.result["reading_date"] = f"{year}-{month:02d}-{day:02d}"
                except:
                    pass
            
            logger.info(f"Extended format çözümlendi: toplam={total_energy}, mevcut={curr_energy}, önceki={prev_energy}")
            
        except Exception as e:
            logger.error(f"Extended format çözümleme hatası: {e}")
            logger.error(traceback.format_exc())
    
    def parse_variant_format(self, payload):
        """Vario 3 varyantındaki Techem formatını çözümle."""
        try:
            logger.info("Varyant format çözümlemesi başlatılıyor...")
            
            # İlk baytın 0x10 olup olmadığını kontrol et
            offset = 0
            if len(payload) > 0 and payload[0] == 0x10:
                offset = 2  # 0x10 ve sonraki bir baytı atla
                logger.info(f"0x10 formatı tanındı, offset: {offset}")
                
                # İkinci bayt kontrol
                if len(payload) > 1:
                    logger.info(f"İkinci bayt: 0x{payload[1]:02x}")
            
            # Yeterli veri var mı?
            if len(payload) < offset + 9:
                logger.warning(f"Varyant format için veri çok kısa: {len(payload)} bayt, offset: {offset}")
                
                # Başarısız olursa alternatif bir yöntem dene
                if len(payload) >= 9:
                    # Offset'i 0 olarak dene
                    offset = 0
                    logger.info("Offset sıfırlanarak tekrar deneniyor")
                else:
                    return
            
            # Veri bloğundaki değerleri analiz et
            # Bayt düzenini ve pozisyonları kontrol et
            
            # wmbusmeters Techem kodunda, 0x67 ile başlayan ve offset=2 olan bir format için
            # 4,5 ve 8,9. baytlarda değerler var
            
            try:
                # İlk değerin konumu
                prev_pos = offset + 3
                # Önceki dönem değeri
                prev_lo = payload[prev_pos] if len(payload) > prev_pos else 0
                prev_hi = payload[prev_pos+1] if len(payload) > prev_pos+1 else 0
                prev_energy = (256.0 * prev_hi + prev_lo)
                
                # İkinci değerin konumu
                curr_pos = offset + 7
                # Mevcut dönem değeri
                curr_lo = payload[curr_pos] if len(payload) > curr_pos else 0
                curr_hi = payload[curr_pos+1] if len(payload) > curr_pos+1 else 0
                curr_energy = (256.0 * curr_hi + curr_lo)
                
                logger.info(f"Prev bytes: {prev_lo:02x} {prev_hi:02x} at pos {prev_pos}")
                logger.info(f"Curr bytes: {curr_lo:02x} {curr_hi:02x} at pos {curr_pos}")
                
                # Toplam enerji hesaplaması
                total_energy = prev_energy + curr_energy
                
                # Sonuçları kaydet
                self.result["total_kwh"] = total_energy
                self.result["current_kwh"] = curr_energy
                self.result["previous_kwh"] = prev_energy
                
                logger.info(f"Varyant formatı çözümlendi: toplam={total_energy}, mevcut={curr_energy}, önceki={prev_energy}")
                
            except Exception as e:
                logger.error(f"Varyant değer çıkarma hatası: {e}")
                logger.error(traceback.format_exc())
            
        except Exception as e:
            logger.error(f"Varyant format çözümleme hatası: {e}")
            logger.error(traceback.format_exc())