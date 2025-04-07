# -*- coding: utf-8 -*-
"""
wM-Bus cihaz sürücüleri için temel sınıf.
Her cihaz sürücüsü bu sınıftan türetilmelidir.
"""

from abc import ABC, abstractmethod
from datetime import datetime

class WMBusDriverBase(ABC):
    """
    wM-Bus sürücülerinin temel sınıfı.
    Tüm cihaz sürücüleri bu sınıftan türetilmelidir.
    """
    # Sürücü bilgileri - alt sınıflar tarafından tanımlanmalı
    MANUFACTURER_ID = None  # Üretici kodu (örn: "0x4493")
    DEVICE_TYPE = None      # Cihaz tipi (örn: 0x08)
    
    def __init__(self, telegram_parser):
        """
        Args:
            telegram_parser: Telegram çözümleyicisi instance'ı
        """
        self.telegram_parser = telegram_parser
        self.telegram_info = {}
        self.data_blocks = []
        self.result = {}
    
    def matches(self, manufacturer_id, device_type):
        """
        Bu sürücünün belirtilen üretici ve cihaz tipiyle eşleşip eşleşmediğini kontrol eder.
        
        Args:
            manufacturer_id: Telegram içindeki üretici ID'si (örn: "0x4493")
            device_type: Telegram içindeki cihaz tipi (örn: 0x08)
            
        Returns:
            bool: Eşleşme varsa True, yoksa False
        """
        # Alt sınıf belirli bir üretici ve cihaz tipi tanımlamışsa
        if self.MANUFACTURER_ID and self.DEVICE_TYPE:
            return self.MANUFACTURER_ID == manufacturer_id and self.DEVICE_TYPE == device_type
        
        # Sadece üretici ID'si tanımlanmışsa
        if self.MANUFACTURER_ID and not self.DEVICE_TYPE:
            return self.MANUFACTURER_ID == manufacturer_id
        
        # Sadece cihaz tipi tanımlanmışsa
        if not self.MANUFACTURER_ID and self.DEVICE_TYPE:
            return self.DEVICE_TYPE == device_type
            
        # Hiçbiri tanımlanmamışsa
        return False
    
    def parse_telegram(self, telegram_data):
        """
        Telgrafı çözümle ve dönüştür.
        
        Args:
            telegram_data: wmbus_parser tarafından çözülmüş telgraf verisi
            
        Returns:
            dict: Dönüştürülmüş ve yorumlanmış veri
        """
        # Sürücü-spesifik değişkenleri ayarla
        self.telegram_info = telegram_data.get("telegram_info", {})
        self.data_blocks = telegram_data.get("data_blocks", [])
        
        # Temel bilgileri ekle
        self.generate_basic_info()
        
        # Alt sınıfın çözümleme metodunu çağır
        self.parse()
        
        return self.result
    
    def generate_basic_info(self):
        """Temel telgraf bilgilerini oluşturur."""
        self.result.update({
            "_": "telegram",
            "id": self.telegram_info.get("address", ""),
            "manufacturer": self.telegram_info.get("manufacturer", ""),
            "status": "OK",
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        })
    
    @abstractmethod
    def parse(self):
        """
        Telgraf içindeki verileri çözümler.
        Her sürücü kendi veri yorumlama mantığını uygulamalıdır.
        Alt sınıflar tarafından uygulanmalıdır.
        """
        pass
    
    def find_block(self, dif, vif, dife=None):
        """
        Belirli bir DIF/VIF kombinasyonuna sahip veri bloğunu bulur.
        
        Args:
            dif: DIF değeri (örn: "0x0b")
            vif: VIF değeri (örn: "0x6e")
            dife: DIFE değeri (opsiyonel)
            
        Returns:
            dict or None: Bulunan veri bloğu veya hiçbiri bulunamazsa None
        """
        for block in self.data_blocks:
            if block["dif"]["byte"] == dif and block["vif"]["byte"] == vif:
                # DIFE kontrolü (eğer belirtilmişse)
                if dife:
                    if "dife" in block and any(d["byte"] == dife for d in block["dife"]):
                        return block
                else:
                    # DIFE kontrolü istenmiyorsa veya blokta DIFE yoksa
                    if "dife" not in block or not block["dife"]:
                        return block
        return None
    
    def get_block_value(self, dif, vif, dife=None, default=None):
        """
        Belirli bir DIF/VIF kombinasyonuna sahip bloğun değerini döndürür.
        
        Args:
            dif: DIF değeri (örn: "0x0b")
            vif: VIF değeri (örn: "0x6e")
            dife: DIFE değeri (opsiyonel)
            default: Blok bulunamazsa dönecek varsayılan değer
            
        Returns:
            Bloğun değeri veya blok bulunamazsa default değeri
        """
        block = self.find_block(dif, vif, dife)
        if block:
            return block["value"]
        return default
    
    def format_date(self, date_str, default=""):
        """
        wM-Bus tarih formatını ISO tarih formatına dönüştürür.
        
        Args:
            date_str: wM-Bus tarih dizesi (örn: "31/12/2022")
            default: Dönüştürme başarısız olursa dönecek varsayılan değer
            
        Returns:
            str: ISO formatında tarih veya işlem başarısız olursa default değeri
        """
        try:
            day, month, year = date_str.split('/')
            return f"{year}-{month}-{day}"
        except:
            return default