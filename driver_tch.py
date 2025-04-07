# -*- coding: utf-8 -*-
"""
Techem Compact V ısı sayacı için sürücü.
"""

from driver_base import WMBusDriverBase
import binascii

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
    # DEVICE_TYPE = None  # Cihaz tipi kontrolünü kapat, üretici kodu yeterli
    
    def parse(self):
        """Techem Compact V telgrafını çözümle."""
        # Cihaz tipini belirle
        self.result["media"] = "heat"
        self.result["meter"] = "compact5"  # Veya başka bir model adı
        self.result["name"] = ""  # İstenirse özelleştirilebilir
        
        # Telgramın CI alanını kontrol et - Techem A2 kullanır
        if "ci_field" in self.telegram_info:
            ci_field = self.telegram_info["ci_field"]
            if ci_field != "0xa2":
                # Bu Techem Compact V protokolü değil
                # Normal wM-Bus çözümlemesini kullan
                return None
        
        # Techem Compact V için ham veriyi al
        # Bu cihazlar standart wM-Bus DIF/VIF yapısını 
        # kullanmadığından ham payload verisi üzerinde çalışmalıyız
        
        # Tüm veri bloklarını gez ve TPL (Transport Layer) sonrası
        # ilk veri bloğunu bul
        raw_payload = None
        
        # Ham payload'ı doğrudan telgraf bilgisine bakarak özel olarak çıkar
        if "tpl" in self.telegram_info:
            # TPL yapısı varsa, erişim numarasını kontrol et
            # Bu cihazlar genellikle specific data sonrası gelen ilk 9 baytı kullanır
            if len(self.data_blocks) > 0:
                # İlk veri bloğunun ham verisini al
                first_block = self.data_blocks[0]
                if "raw_data" in first_block:
                    raw_payload = first_block["raw_data"]
        
        # Eğer ham veri bulunamadıysa, bu cihaz için uygun değil
        if not raw_payload:
            return None
        
        try:
            # Ham veriyi byte dizisine dönüştür
            payload_bytes = binascii.unhexlify(raw_payload)
            
            # wmbusmeters'ın yaptığı gibi, 3-5 ve 7-9 konumlarındaki verileri kontrol et
            if len(payload_bytes) >= 9:
                # Önceki dönem değeri (3-4. baytlar)
                prev_lo = payload_bytes[3] if len(payload_bytes) > 3 else 0
                prev_hi = payload_bytes[4] if len(payload_bytes) > 4 else 0
                prev_energy = (256.0 * prev_hi + prev_lo)
                
                # Mevcut dönem değeri (7-8. baytlar)
                curr_lo = payload_bytes[7] if len(payload_bytes) > 7 else 0
                curr_hi = payload_bytes[8] if len(payload_bytes) > 8 else 0
                curr_energy = (256.0 * curr_hi + curr_lo)
                
                # Toplam enerji hesaplaması
                total_energy = prev_energy + curr_energy
                
                # Sonuçları kaydet
                self.result["total_kwh"] = total_energy
                self.result["current_kwh"] = curr_energy
                self.result["previous_kwh"] = prev_energy
                
                return self.result
            else:
                # Yeterli veri yok
                return None
        except Exception as e:
            print(f"Techem veri çözümleme hatası: {e}")
            return None
            
    def matches(self, manufacturer_id, device_type):
        """
        Techem cihazlarını tanımlamak için özel eşleşme mantığı
        """
        # Üretici Techem mi?
        if manufacturer_id != self.MANUFACTURER_ID:
            return False
            
        # CI alanı A2 mi?
        if "ci_field" in self.telegram_info:
            ci_field = self.telegram_info["ci_field"]
            if ci_field == "0xa2":
                return True
                
        # Desteklenen cihaz tipleri
        supported_types = [0x04, 0xc3, 0x43, 0x45, 0x39]
        
        # Cihaz tipini kontrol et
        if device_type is not None:
            # Hem hex string hem de int olarak kontrol et
            try:
                device_type_int = int(device_type, 16) if isinstance(device_type, str) and device_type.startswith("0x") else device_type
                return device_type_int in supported_types
            except:
                pass
                
        return False