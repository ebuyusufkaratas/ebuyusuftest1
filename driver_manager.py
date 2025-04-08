# -*- coding: utf-8 -*-
"""
wM-Bus cihaz sürücülerini yöneten modül.
"""

import os
import sys
import importlib
import inspect
import logging
from driver_base import WMBusDriverBase

# Loglama
logger = logging.getLogger("wmbus_driver_manager")

class DriverManager:
    """
    wM-Bus cihaz sürücülerini yönetme sınıfı.
    Tüm kayıtlı sürücüleri takip eder ve telgraflara uygun sürücüyü bulur.
    """
    def __init__(self):
        self.drivers = []
        self.load_drivers()
    
    def load_drivers(self):
        """Tüm kullanılabilir sürücüleri yükler."""
        # Mevcut dizindeki tüm driver_* dosyalarını bul
        driver_files = [f for f in os.listdir('.') if f.startswith('driver_') and f.endswith('.py') and f != 'driver_base.py' and f != 'driver_manager.py']
        
        for file in driver_files:
            try:
                # .py uzantısını kaldır
                module_name = file[:-3]
                
                # Modülü dinamik olarak içe aktar
                module = importlib.import_module(module_name)
                
                # Modüldeki tüm sınıfları bul
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # WMBusDriverBase'den türetilmiş ve aynı sınıf değilse
                    if issubclass(obj, WMBusDriverBase) and obj != WMBusDriverBase:
                        logger.info(f"Sürücü yüklendi: {name} ({module_name})")
                        # Sürücüyü listeye ekle (sınıf olarak, instance değil)
                        self.drivers.append(obj)
            except Exception as e:
                logger.error(f"Sürücü yüklenirken hata: {file} - {e}")
    
    def find_driver(self, telegram_info):
        """
        Telgraf bilgilerine göre uygun sürücüyü bulur.
        
        Args:
            telegram_info: Çözümlenmiş telgraf bilgisi
            
        Returns:
            WMBusDriverBase instance veya None
        """
        manufacturer_id = telegram_info.get("manufacturer_code")
        device_type = telegram_info.get("device_type_code")
        
        if not manufacturer_id or not device_type:
            logger.warning("Telgrafta üretici kodu veya cihaz tipi eksik")
            return None
        
        # Tam eşleşme bulmaya çalış
        for driver_class in self.drivers:
            try:
                # Driver sınıfının örneğini oluştur
                driver = driver_class(None)  # None yerine telegram_parser instance'ı gelebilir
                
                # Eşleşme kontrolü
                if driver.matches(manufacturer_id, device_type):
                    logger.info(f"Sürücü bulundu: {driver_class.__name__}")
                    return driver
            except Exception as e:
                logger.error(f"Sürücü eşleşme kontrolünde hata: {driver_class.__name__} - {e}")
        
        # Sadece üretici ID'sine göre bulamazsak
        for driver_class in self.drivers:
            try:
                driver = driver_class(None)
                if driver.matches(manufacturer_id, None):
                    logger.info(f"Üretici eşleşmeli sürücü bulundu: {driver_class.__name__}")
                    return driver
            except Exception as e:
                logger.error(f"Üretici eşleşme kontrolünde hata: {driver_class.__name__} - {e}")
        
        # Sadece cihaz tipine göre bulamazsak
        for driver_class in self.drivers:
            try:
                driver = driver_class(None)
                if driver.matches(None, device_type):
                    logger.info(f"Cihaz tipi eşleşmeli sürücü bulundu: {driver_class.__name__}")
                    return driver
            except Exception as e:
                logger.error(f"Cihaz tipi eşleşme kontrolünde hata: {driver_class.__name__} - {e}")
        
        logger.warning(f"Uygun sürücü bulunamadı: {manufacturer_id}, {device_type}")
        return None
    
    def apply_driver(self, telegram_data):
        
        """
        print("Debug: Telegram Bilgileri", telegram_data.get("telegram_info"))
        Çözümlenmiş telgraf verilerine uygun sürücüyü uygular.
        
        Args:
            telegram_data: wmbus_parser'dan gelen çözümlenmiş veri
            
        Returns:
            Sürücü tarafından oluşturulmuş cihaza özel veriler veya
            sürücü yoksa orijinal veriler
        """
        if not telegram_data:
            return telegram_data
        
        telegram_info = telegram_data.get("telegram_info", {})
        print(f"Debug: Manufacturer Code: {telegram_info.get('manufacturer_code')}")
        print(f"Debug: Device Type Code: {telegram_info.get('device_type_code')}")
        
        driver = self.find_driver(telegram_info)
        
        if driver:
            print(f"Debug: Bulunan Sürücü: {driver.__class__.__name__}")
            try:
                result = driver.parse_telegram(telegram_data)
                return result
            except Exception as e:
                logger.error(f"Sürücü çözümleme hatası: {driver.__class__.__name__} - {e}")
        
        return telegram_data

# Singleton Driver Manager örneği
_driver_manager = None

def get_driver_manager():
    """
    DriverManager singleton örneğini döndürür.
    
    Returns:
        DriverManager: Global driver manager örneği
    """
    global _driver_manager
    if _driver_manager is None:
        _driver_manager = DriverManager()
    return _driver_manager

def apply_driver(telegram_data):
    """
    Çözümlenmiş telgraf verilerine uygun sürücüyü uygular.
    
    Args:
        telegram_data: wmbus_parser'dan gelen çözümlenmiş veri
        
    Returns:
        Sürücü tarafından oluşturulmuş cihaza özel veriler veya
        sürücü yoksa orijinal veriler
    """
    return get_driver_manager().apply_driver(telegram_data)