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
        try:
            driver_files = [f for f in os.listdir('.') if f.startswith('driver_') and f.endswith('.py') and f != 'driver_base.py' and f != 'driver_manager.py']
            logger.info(f"Bulunan sürücü dosyaları: {driver_files}")
        except Exception as e:
            logger.error(f"Sürücü dosyaları listelenirken hata: {e}")
            driver_files = []
        
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
        
        logger.info(f"Toplam {len(self.drivers)} sürücü yüklendi")
    
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
        ci_field = telegram_info.get("ci_field")
        
        logger.info(f"Sürücü aranıyor: Üretici={manufacturer_id}, Cihaz Tipi={device_type}, CI={ci_field}")
        
        # Yeni detect mekanizması
        for driver_class in self.drivers:
            try:
                # Eğer sınıfta detect metodu varsa kullan
                if hasattr(driver_class, 'detect'):
                    driver = driver_class(None)
                    driver.telegram_info = telegram_info
                    
                    # Cihaz algılama metodunu çağır
                    if driver.detect(telegram_info):
                        logger.info(f"Detect metoduyla sürücü bulundu: {driver_class.__name__}")
                        return driver
            except Exception as e:
                logger.error(f"Detect kontrolünde hata: {driver_class.__name__} - {e}")
        
        # CI alanı özel sürücüleri kontrol et (eğer CI alanı varsa)
        if ci_field and ci_field in ("0xa1", "0xa2", "0xa3"):
            matching_drivers = []
            for driver_class in self.drivers:
                try:
                    # Driver sınıfının örneğini oluştur
                    driver = driver_class(None)
                    
                    # Telegram bilgisini sürücüye ekle
                    driver.telegram_info = telegram_info
                    
                    # CI alanına göre eşleşme kontrolü yap
                    if hasattr(driver, 'matches_ci') and driver.matches_ci(ci_field):
                        matching_drivers.append(driver)
                        logger.info(f"CI eşleşmeli sürücü bulundu: {driver_class.__name__}")
                except Exception as e:
                    logger.error(f"CI eşleşme kontrolünde hata: {driver_class.__name__} - {e}")
            
            # Birden fazla eşleşen sürücü varsa, ilkini seç
            if matching_drivers:
                if len(matching_drivers) > 1:
                    logger.warning(f"Birden fazla sürücü bulundu: {[d.__class__.__name__ for d in matching_drivers]}")
                return matching_drivers[0]
        
        # Tam eşleşme bulmaya çalış
        for driver_class in self.drivers:
            try:
                # Driver sınıfının örneğini oluştur
                driver = driver_class(None)
                
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
        Çözümlenmiş telgraf verilerine uygun sürücüyü uygular.
        
        Args:
            telegram_data: wmbus_parser'dan gelen çözümlenmiş veri
            
        Returns:
            Güncellenmiş telegram_data (driver çıktıları dahil)
        """
        if not telegram_data:
            logger.warning("Telgraf verisi boş, sürücü uygulanamadı")
            return telegram_data

        telegram_info = telegram_data.get("telegram_info", {})
        logger.info(f"Sürücü uygulanacak telgraf: {telegram_info.get('manufacturer_code')}, {telegram_info.get('device_type_code')}")

        # CI alanı kontrolü (özel format için)
        ci_field = telegram_info.get("ci_field")
        if ci_field in ("0xa1", "0xa2", "0xa3"):
            logger.info(f"Özel CI alanı tespit edildi: {ci_field}")

        driver = self.find_driver(telegram_info)

        if driver:
            logger.info(f"Sürücü bulundu ve uygulanıyor: {driver.__class__.__name__}")
            try:
                result = driver.parse_telegram(telegram_data)

                if result:
                    logger.info("Sürücü çözümlemesi başarılı")

                    # 🔧 Sürücü çıktısını telegram_data'ya entegre et
                    if isinstance(result, dict):
                        telegram_data.update(result)

                    return telegram_data
                else:
                    logger.warning("Sürücü boş sonuç döndürdü")
            except Exception as e:
                logger.error(f"Sürücü çözümleme hatası: {driver.__class__.__name__} - {e}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.warning("Uygun sürücü bulunamadı")

        return telegram_data

# Singleton Driver Manager örneği - hemen başlat
_driver_manager = DriverManager()

def get_driver_manager():
    """
    DriverManager singleton örneğini döndürür.
    
    Returns:
        DriverManager: Global driver manager örneği
    """
    global _driver_manager
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
    manager = get_driver_manager()
    return manager.apply_driver(telegram_data)