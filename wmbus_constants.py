# -*- coding: utf-8 -*-

# M-Bus üretici kodları sözlüğü
MANUFACTURER_CODES = {
    0x0477: "Kamstrup",
    0x04C4: "Itron",
    0x2D2C: "Diehl",
    0x2434: "Landis+Gyr",
    0x3068: "Sensus",
    0x40F0: "Honeywell",
    0x3412: "Elster",
    0x1349: "Siemens",
    0x1077: "Zenner",
    0x12E5: "Ista",
    0x1429: "Sontex",
    0x15AF: "Sappel",
    0x19EA: "Secure",
    0x1C73: "Axioma",
    0x2324: "EMH",
    0x2D45: "Danfoss",
    0x3033: "Carlo Gavazzi",
    0x4493: "QDS",
    0x3741: "Apator",
    0x5068: "TCH",
    0xA697: "ITW",
    0x2697: "ITW",
    0x2674: "IST"
    # Daha fazla üretici eklenebilir
}

# M-Bus cihaz tipleri
DEVICE_TYPES = {
    0x00: "Diğer",
    0x01: "Elektrik Sayacı",
    0x02: "Gaz Sayacı",
    0x03: "Isı Sayacı",
    0x04: "Isıtma/Soğutma Sayacı",
    0x06: "Sıcak Su Sayacı",
    0x07: "Su Sayacı",
    0x08: "Kesinti Sayacı",
    0x09: "Kredi Sayacı",
    0x0A: "Isı Dağıtım Ölçer",
    0x0B: "Gaz Tank Ölçer",
    0x0C: "Su Tank Ölçer",
    0x0D: "Isı Aktarım Sayacı",
    0x0E: "Sıcak/Soğuk Su Sayacı",
    0x0F: "Basınç Ölçer",
    0x15: "Buhar Ölçer",
    0x16: "Soğutma Ölçer",
    0x20: "Isı Kontrol Cihazı",
    0x28: "Gaz Kontrol Cihazı",
    0x29: "Soğutma Regülatörü",
    0x2A: "Isı Kontrol Vanası",
    0x2B: "Hidrolik Kontrol Vanası",
    0x2C: "Isı/Soğutma Kontrol Cihazı",
    0x31: "Tekrarlayıcı (Repeater)",
    0x40: "Multifonksiyonel Cihaz",
    # Daha fazla tip eklenebilir
}

# DIF bilgileri
DIF_TYPES = {
    0x0: {"length": 0, "description": "Veri yok"},
    0x1: {"length": 1, "description": "8 Bit Integer/Binary"},
    0x2: {"length": 2, "description": "16 Bit Integer/Binary"},
    0x3: {"length": 3, "description": "24 Bit Integer/Binary"},
    0x4: {"length": 4, "description": "32 Bit Integer/Binary"},
    0x5: {"length": 4, "description": "32 Bit Real"},
    0x6: {"length": 6, "description": "48 Bit Integer/Binary"},
    0x7: {"length": 8, "description": "64 Bit Integer/Binary"},
    0x9: {"length": 1, "description": "2 basamaklı BCD"},
    0xA: {"length": 2, "description": "4 basamaklı BCD"},
    0xB: {"length": 3, "description": "6 basamaklı BCD"},
    0xC: {"length": 4, "description": "8 basamaklı BCD"},
    0xD: {"length": -1, "description": "Değişken uzunluk"},
    0xE: {"length": 6, "description": "12 basamaklı BCD"},
    0xF: {"length": 8, "description": "Özel fonksiyon"}
}

# DIF fonksiyon tipleri
DIF_FUNCTION_TYPES = {
    0: "Anlık değer",
    1: "Maksimum değer",
    2: "Minimum değer",
    3: "Hata durumundaki değer"
}

# VIF birimleri ve tanımları
VIF_TYPES = {

    # HCA (Isı Dağıtım Birimi)
    0x6E: {"unit": "HCA", "multiplier": 1, "description": "Isı Dağıtım Birimi (Heat Cost Allocator)"},

    # Diğer özel VIF değerleri
    0x7B: {"unit": "Pulse", "multiplier": 1, "description": "Pulse değeri"},
    0x7D: {"unit": "FW", "multiplier": 1, "description": "Firmware sürümü"},

    # Enerji (Wh)
    0x00: {"unit": "Wh", "multiplier": 1e-3, "description": "Enerji"},
    0x01: {"unit": "Wh", "multiplier": 1e-2, "description": "Enerji"},
    0x02: {"unit": "Wh", "multiplier": 1e-1, "description": "Enerji"},
    0x03: {"unit": "Wh", "multiplier": 1, "description": "Enerji"},
    0x04: {"unit": "Wh", "multiplier": 1e1, "description": "Enerji"},
    0x05: {"unit": "Wh", "multiplier": 1e2, "description": "Enerji"},
    0x06: {"unit": "Wh", "multiplier": 1e3, "description": "Enerji"},
    0x07: {"unit": "Wh", "multiplier": 1e4, "description": "Enerji"},
    
    # Enerji (J)
    0x08: {"unit": "J", "multiplier": 1e0, "description": "Enerji"},
    0x09: {"unit": "J", "multiplier": 1e1, "description": "Enerji"},
    0x0A: {"unit": "J", "multiplier": 1e2, "description": "Enerji"},
    0x0B: {"unit": "J", "multiplier": 1e3, "description": "Enerji"},
    0x0C: {"unit": "J", "multiplier": 1e4, "description": "Enerji"},
    0x0D: {"unit": "J", "multiplier": 1e5, "description": "Enerji"},
    0x0E: {"unit": "J", "multiplier": 1e6, "description": "Enerji"},
    0x0F: {"unit": "J", "multiplier": 1e7, "description": "Enerji"},
    
    # Hacim
    0x10: {"unit": "m³", "multiplier": 1e-6, "description": "Hacim"},
    0x11: {"unit": "m³", "multiplier": 1e-5, "description": "Hacim"},
    0x12: {"unit": "m³", "multiplier": 1e-4, "description": "Hacim"},
    0x13: {"unit": "m³", "multiplier": 1e-3, "description": "Hacim"},
    0x14: {"unit": "m³", "multiplier": 1e-2, "description": "Hacim"},
    0x15: {"unit": "m³", "multiplier": 1e-1, "description": "Hacim"},
    0x16: {"unit": "m³", "multiplier": 1e0, "description": "Hacim"},
    0x17: {"unit": "m³", "multiplier": 1e1, "description": "Hacim"},
    
    # Kütle
    0x18: {"unit": "kg", "multiplier": 1e-3, "description": "Kütle"},
    0x19: {"unit": "kg", "multiplier": 1e-2, "description": "Kütle"},
    0x1A: {"unit": "kg", "multiplier": 1e-1, "description": "Kütle"},
    0x1B: {"unit": "kg", "multiplier": 1e0, "description": "Kütle"},
    0x1C: {"unit": "kg", "multiplier": 1e1, "description": "Kütle"},
    0x1D: {"unit": "kg", "multiplier": 1e2, "description": "Kütle"},
    0x1E: {"unit": "kg", "multiplier": 1e3, "description": "Kütle"},
    0x1F: {"unit": "kg", "multiplier": 1e4, "description": "Kütle"},
    
    # Güç
    0x28: {"unit": "W", "multiplier": 1e-3, "description": "Güç"},
    0x29: {"unit": "W", "multiplier": 1e-2, "description": "Güç"},
    0x2A: {"unit": "W", "multiplier": 1e-1, "description": "Güç"},
    0x2B: {"unit": "W", "multiplier": 1e0, "description": "Güç"},
    0x2C: {"unit": "W", "multiplier": 1e1, "description": "Güç"},
    0x2D: {"unit": "W", "multiplier": 1e2, "description": "Güç"},
    0x2E: {"unit": "W", "multiplier": 1e3, "description": "Güç"},
    0x2F: {"unit": "W", "multiplier": 1e4, "description": "Güç"},
    
    # Hacimsel akış
    0x38: {"unit": "m³/h", "multiplier": 1e-6, "description": "Hacimsel akış"},
    0x39: {"unit": "m³/h", "multiplier": 1e-5, "description": "Hacimsel akış"},
    0x3A: {"unit": "m³/h", "multiplier": 1e-4, "description": "Hacimsel akış"},
    0x3B: {"unit": "m³/h", "multiplier": 1e-3, "description": "Hacimsel akış"},
    0x3C: {"unit": "m³/h", "multiplier": 1e-2, "description": "Hacimsel akış"},
    0x3D: {"unit": "m³/h", "multiplier": 1e-1, "description": "Hacimsel akış"},
    0x3E: {"unit": "m³/h", "multiplier": 1e0, "description": "Hacimsel akış"},
    0x3F: {"unit": "m³/h", "multiplier": 1e1, "description": "Hacimsel akış"},
    
    # Akış sıcaklığı
    0x58: {"unit": "°C", "multiplier": 1e-3, "description": "Akış sıcaklığı"},
    0x59: {"unit": "°C", "multiplier": 1e-2, "description": "Akış sıcaklığı"},
    0x5A: {"unit": "°C", "multiplier": 1e-1, "description": "Akış sıcaklığı"},
    0x5B: {"unit": "°C", "multiplier": 1e0, "description": "Akış sıcaklığı"},
    
    # Geri dönüş sıcaklığı
    0x5C: {"unit": "°C", "multiplier": 1e-3, "description": "Geri dönüş sıcaklığı"},
    0x5D: {"unit": "°C", "multiplier": 1e-2, "description": "Geri dönüş sıcaklığı"},
    0x5E: {"unit": "°C", "multiplier": 1e-1, "description": "Geri dönüş sıcaklığı"},
    0x5F: {"unit": "°C", "multiplier": 1e0, "description": "Geri dönüş sıcaklığı"},
    
    # Sıcaklık farkı
    0x60: {"unit": "K", "multiplier": 1e-3, "description": "Sıcaklık farkı"},
    0x61: {"unit": "K", "multiplier": 1e-2, "description": "Sıcaklık farkı"},
    0x62: {"unit": "K", "multiplier": 1e-1, "description": "Sıcaklık farkı"},
    0x63: {"unit": "K", "multiplier": 1e0, "description": "Sıcaklık farkı"},
    
    # Dış sıcaklık
    0x64: {"unit": "°C", "multiplier": 1e-3, "description": "Dış sıcaklık"},
    0x65: {"unit": "°C", "multiplier": 1e-2, "description": "Dış sıcaklık"},
    0x66: {"unit": "°C", "multiplier": 1e-1, "description": "Dış sıcaklık"},
    0x67: {"unit": "°C", "multiplier": 1e0, "description": "Dış sıcaklık"},
    
    # Basınç
    0x68: {"unit": "bar", "multiplier": 1e-3, "description": "Basınç"},
    0x69: {"unit": "bar", "multiplier": 1e-2, "description": "Basınç"},
    0x6A: {"unit": "bar", "multiplier": 1e-1, "description": "Basınç"},
    0x6B: {"unit": "bar", "multiplier": 1e0, "description": "Basınç"},
    
    # Tarih ve zaman
    0x6C: {"unit": "Tarih", "multiplier": 1, "description": "Tarih"},
    0x6D: {"unit": "Tarih ve Zaman", "multiplier": 1, "description": "Tarih ve Zaman"},
    
    # Diğer
    0x74: {"unit": "saat", "multiplier": 1, "description": "Çalışma Süresi"}
}

# VIFE bilgileri
VIFE_TYPES = {
    0x00: "Kredi",
    0x01: "Borç",
    0x08: "Erişim No",
    0x09: "Orta",
    0x0A: "Üretici",
    0x0B: "Parametre seti ID",
    0x0C: "Model/Versiyon",
    0x0D: "Donanım versiyon #",
    0x0E: "Firmware versiyon #",
    0x0F: "Yazılım versiyon #",
    0x10: "Müşteri",
    0x11: "Müşteri konum",
    0x14: "Tarifeli Ücret",
    0x15: "Cihaz Modu",
    0x16: "Reset Sayacı",
    0x17: "Sıfırlama Alt Sayacı",
    0x1F: "Birim fiyatı",
    0x20: "İşaret dönüştürme faktörü",
    0x21: "Süre nesnesi sayacı",
    0x22: "Gerçek kalite süresi",
    0x23: "Arıza süresi",
    0x24: "Eşik süresi"
}