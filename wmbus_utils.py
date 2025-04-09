# -*- coding: utf-8 -*-

"""
wM-Bus Yardımcı İşlevler
Bu modül, wM-Bus telgrafları işlemek için gerekli yardımcı işlevleri içerir.
"""

import binascii
import struct
from datetime import datetime
from Crypto.Cipher import AES

def decode_integer(data, length):
    """İnteger verilerini çözümle"""
    if length == 1:
        return data[0]
    elif length == 2:
        return data[0] | (data[1] << 8)
    elif length == 3:
        return data[0] | (data[1] << 8) | (data[2] << 16)
    elif length == 4:
        return data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24)
    elif length == 6:
        return data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24) | (data[4] << 32) | (data[5] << 40)
    elif length == 8:
        return data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24) | \
               (data[4] << 32) | (data[5] << 40) | (data[6] << 48) | (data[7] << 56)
    return None

def decode_bcd(data, length):
    """BCD verilerini çözümle"""
    value = 0
    multiplier = 1
    for i in range(length):
        byte = data[i]
        low_digit = byte & 0x0F
        high_digit = (byte >> 4) & 0x0F

        if low_digit > 9 or high_digit > 9:  # Geçersiz BCD
            return None

        value += (low_digit * multiplier)
        multiplier *= 10
        value += (high_digit * multiplier)
        multiplier *= 10

    result = value / 1000  # 3904 * 100 = 390400 yusufbab burayla oynadı 
    return result

def decode_real(data):
    
    """32 bit gerçek sayı (float) verilerini çözümle"""
    if len(data) != 4:
        return None
    return struct.unpack('<f', bytes(data))[0]

def decode_date(data):
    """Tarih verisini çözümle (EN 13757-3 Type G)"""
    if len(data) != 2:
        return None

    day = data[0] & 0x1F
    month = ((data[1] & 0x0F) | ((data[0] & 0xE0) >> 5))
    year = 2000 + ((data[1] & 0xF0) >> 4)

    return f"{day:02d}/{month:02d}/{year}"

def decode_time(data):
    """Zaman verisini çözümle"""
    if len(data) != 4:
        return None

    minute = data[0] & 0x3F
    hour = data[1] & 0x1F
    day = data[2] & 0x1F
    month = data[3] & 0x0F
    year = 2000 + ((data[3] & 0xF0) >> 4)

    try:
        dt = datetime(year, month, day, hour, minute)
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return f"{day:02d}/{month:02d}/{year} {hour:02d}:{minute:02d}"

def calculate_iv(manufacturer, id_bytes, access_nr, frame_count=0):
    """
    AES-CBC için IV (Initialization Vector) hesapla
    
    manufacturer: 2 byte üretici kodu
    id_bytes: 4 byte sayaç ID'si
    access_nr: 1 byte erişim numarası
    frame_count: 2 byte çerçeve sayısı (opsiyonel)
    """
    iv = bytearray(16)
    
    # Üretici kodunu ters çevir (little endian)
    iv[0] = manufacturer & 0xFF
    iv[1] = (manufacturer >> 8) & 0xFF
    
    # Sayaç ID'si
    for i in range(min(4, len(id_bytes))):
        iv[2+i] = id_bytes[i]
    
    # Erişim numarası
    iv[6] = access_nr
    
    # Çerçeve sayısı
    iv[7] = frame_count & 0xFF
    iv[8] = (frame_count >> 8) & 0xFF
    
    # Geri kalan kısım
    for i in range(9, 16):
        iv[i] = 0x00
    
    return iv

def decrypt_aes_cbc_iv(encrypted_data, key, iv=None):
    """AES-CBC şifresini çöz"""
    if iv is None:
        # IV yoksa, genellikle ilk 16 bayt IV olarak kullanılır
        iv = b'\x00' * 16  # Veya başka bir varsayılan IV
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypted_data)
    
    # PKCS#7 padding'i kaldır
    padding_len = decrypted[-1]
    if padding_len > 16:
        return decrypted  # Padding yok
    
    return decrypted[:-padding_len]

def encrypt_aes_cbc_iv(plain_data, key, iv):
    """AES-CBC ile veri şifrele"""
    # 16 baytın katlarına tamamla (PKCS#7 padding)
    padding_len = 16 - (len(plain_data) % 16)
    padded_data = plain_data + bytes([padding_len] * padding_len)
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(padded_data)
    
    return encrypted

def format_manufacturer_code(code):
    """Üretici kodunu EN 13757-3 formatına dönüştür (ASCII)"""
    m1 = ((code >> 10) & 0x1F) + 64
    m2 = ((code >> 5) & 0x1F) + 64
    m3 = (code & 0x1F) + 64
    return chr(m1) + chr(m2) + chr(m3)

def parse_manufacturer_code(text):
    """
    3 karakterlik üretici kodunu sayısal değere dönüştür
    Örnek: "KAM" -> 0x0477 (Kamstrup)
    """
    if len(text) != 3:
        return None
    
    m1 = (ord(text[0]) - 64) << 10
    m2 = (ord(text[1]) - 64) << 5
    m3 = ord(text[2]) - 64
    
    return m1 | m2 | m3

def add_measurement_block(data_blocks=None, value=0, unit="Wh", is_current=True):
    """
    Ölçüm bloğu oluştur (DIF/VIF/Veri)
    
    data_blocks: Mevcut veri blokları dizisi (hex string)
    value: Ölçüm değeri
    unit: Birim ("Wh", "m3", "C" vb.)
    is_current: Anlık değer mi?
    """
    if data_blocks is None:
        data_blocks = b''
    elif isinstance(data_blocks, str):
        data_blocks = binascii.unhexlify(data_blocks)
    
    # DIF
    dif = 0
    data_bytes = b''
    
    # Değer tipine göre DIF belirle
    if isinstance(value, int):
        if value < 256:
            dif = 0x01  # 8-bit integer
            data_bytes = struct.pack("B", value)
        elif value < 65536:
            dif = 0x02  # 16-bit integer
            data_bytes = struct.pack("<H", value)
        elif value < 16777216:
            dif = 0x03  # 24-bit integer
            data_bytes = struct.pack("<I", value)[:3]
        else:
            dif = 0x04  # 32-bit integer
            data_bytes = struct.pack("<I", value)
    elif isinstance(value, float):
        dif = 0x05  # 32-bit float
        data_bytes = struct.pack("<f", value)
    
    # Fonksiyon tipi
    if not is_current:
        dif |= 0x10  # Maksimum değer
    
    # VIF
    vif = 0
    if unit == "Wh":
        # Ölçek faktörü belirle
        if value < 1000:
            vif = 0x00  # 10^-3 Wh = 1 Wh
        elif value < 1000000:
            vif = 0x01  # 10^-2 Wh = 10 Wh
        else:
            vif = 0x02  # 10^-1 Wh = 100 Wh
    elif unit == "m3":
        # Hacim birimi
        if value < 1000:
            vif = 0x10  # 10^-6 m3 = 0.001 m3
        else:
            vif = 0x11  # 10^-5 m3 = 0.01 m3
    elif unit == "C":
        # Sıcaklık
        vif = 0x58  # 10^-3 °C = 0.001 °C
    elif unit == "W":
        # Güç
        if value < 1000:
            vif = 0x28  # 10^-3 W = 1 W
        else:
            vif = 0x29  # 10^-2 W = 10 W
    
    # Bloğu oluştur
    result = bytearray()
    result.append(dif)
    result.append(vif)
    result.extend(data_bytes)
    
    # Mevcut bloklara ekle
    combined = bytearray(data_blocks)
    combined.extend(result)
    
    return binascii.hexlify(combined).decode()

def add_date_block(data_blocks=None, day=1, month=1, year=2023):
    """
    Tarih bloğu ekle
    
    data_blocks: Mevcut veri blokları dizisi (hex string)
    day: Gün (1-31)
    month: Ay (1-12)
    year: Yıl (2000-2255)
    """
    if data_blocks is None:
        data_blocks = b''
    elif isinstance(data_blocks, str):
        data_blocks = binascii.unhexlify(data_blocks)
    
    # DIF: 2 byte tarih
    dif = 0x02
    
    # VIF: Tarih (Type G)
    vif = 0x6C
    
    # Tarih formatı (EN 13757-3 Type G)
    # Bayt 1: EEEDDDDD E=month MSB, D=day
    # Bayt 2: YYYYMMMM Y=year, M=month LSB
    
    # Yıl: Sadece 2000 sonrası (son 6 bit)
    y = (year - 2000) & 0x3F
    
    # Ay: 5-8. bitler (4 bit)
    m_lsb = month & 0x0F
    m_msb = (month >> 4) & 0x01
    
    # Gün: 1-5. bitler (5 bit)
    d = day & 0x1F
    
    # Baytları oluştur
    byte1 = (m_msb << 5) | d
    byte2 = (y << 4) | m_lsb
    
    # Bloğu oluştur
    result = bytearray()
    result.append(dif)
    result.append(vif)
    result.append(byte1)
    result.append(byte2)
    
    # Mevcut bloklara ekle
    combined = bytearray(data_blocks)
    combined.extend(result)
    
    return binascii.hexlify(combined).decode()