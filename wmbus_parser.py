# -*- coding: utf-8 -*-

import binascii
import struct
import logging
import argparse
from datetime import datetime
import json
# Loglama ayarları
import logging
logger = logging.getLogger("wmbus_driver_manager")

try:
    import driver_manager
    DRIVERS_AVAILABLE = True
    logger.info("wM-Bus cihaz sürücüleri kullanılabilir.")
except ImportError:
    DRIVERS_AVAILABLE = False
    logger.info("wM-Bus cihaz sürücüleri bulunamadı.")

# AES şifre çözme için pycryptodome kütüphanesini kullanıyoruz
from Crypto.Cipher import AES

# Sabit değerleri içe aktar
from wmbus_constants import (
    MANUFACTURER_CODES, 
    DEVICE_TYPES, 
    DIF_TYPES, 
    DIF_FUNCTION_TYPES,
    VIF_TYPES,
    VIFE_TYPES
)

# Yardımcı fonksiyonları içe aktar
from wmbus_utils import (
    decode_integer,
    decode_bcd,
    decode_real,
    decode_date,
    decode_time,
    calculate_iv,
    decrypt_aes_cbc_iv,
    format_manufacturer_code,
    add_measurement_block
)

# Loglama ayarları
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('wmbus_parser')

def parse_dif(dif_byte):
    """DIF (Data Information Field) alanını çözümle"""
    data_field = dif_byte & 0x0F  # Alt 4 bit
    function_field = (dif_byte & 0x30) >> 4  # 5-6. bitler
    storage_number = (dif_byte & 0x40) >> 6  # 7. bit
    extension_bit = (dif_byte & 0x80) >> 7  # 8. bit (uzantı biti)
    
    # Veri tipini ve uzunluğunu al
    dif_info = DIF_TYPES.get(data_field, {"length": 0, "description": "Bilinmeyen"})
    data_length = dif_info["length"]
    data_type = dif_info["description"]
    
    # Fonksiyon tipini al
    function_type = DIF_FUNCTION_TYPES.get(function_field, "Bilinmeyen")
    
    return {
        "data_field": data_field,
        "function_field": function_field,
        "storage_number": storage_number,
        "extension_bit": extension_bit,
        "data_length": data_length,
        "data_type": data_type,
        "function_type": function_type
    }

def parse_vif(vif_byte):
    """VIF (Value Information Field) alanını çözümle"""
    vif_value = vif_byte & 0x7F  # En yüksek biti çıkar (uzantı biti)
    extension_bit = (vif_byte & 0x80) >> 7  # Uzantı biti
    
    # VIF tipini ve çarpanını al
    vif_info = VIF_TYPES.get(vif_value, {"unit": "Bilinmeyen", "multiplier": 1, "description": "Bilinmeyen"})
    
    return {
        "vif_value": vif_value,
        "extension_bit": extension_bit,
        "unit": vif_info["unit"],
        "multiplier": vif_info["multiplier"],
        "description": vif_info["description"]
    }

def parse_vife(vife_byte):
    """VIFE (VIF Extension) alanını çözümle"""
    vife_value = vife_byte & 0x7F
    extension_bit = (vife_byte & 0x80) >> 7
    
    # VIFE tanımını al
    description = VIFE_TYPES.get(vife_value, f"Bilinmeyen VIFE (0x{vife_value:02x})")
    
    return {
        "vife_value": vife_value,
        "extension_bit": extension_bit,
        "description": description
    }

def parse_wmbus_telegram(hex_data, key=None, verbose=True, output_format="text", use_drivers=True):
    """Tam bir wM-Bus telgrafını çözümle"""
    # Hex string'i bayt dizisine dönüştür
    try:
        data = binascii.unhexlify(hex_data)
    except binascii.Error as e:
        logger.error(f"Geçersiz hex string: {e}")
        return None
    
    if len(data) < 10:
        logger.error(f"Telgraf çok kısa (en az 10 bayt olmalı): {len(data)} bayt")
        return None
    
    result = {
        "telegram_info": {},
        "data_blocks": []
    }
    
    # Temel DLL (Veri Bağlantı Katmanı) bilgilerini çıkar
    length = data[0]
    c_field = data[1]
    m_field = (data[3] << 8) | data[2]  # Üretici kodu
    
    # Sayaç adresi/ID'si - bayt sırasını ters çevir (little endian)
    address_bytes = data[4:8]
    # wM-Bus protokolünde adres genellikle BCD formatında kodlanmış
    # ve her bayt ters çevrilmiş olarak okunmalıdır
    address_str = ""
    for i in range(len(address_bytes)-1, -1, -1):
        address_str += f"{address_bytes[i]:02x}"
    
    version = data[8]
    type = data[9]  # Medya/cihaz türü
    
    manufacturer_name = MANUFACTURER_CODES.get(m_field, "Bilinmeyen")
    device_type = DEVICE_TYPES.get(type, "Bilinmeyen")
    
    result["telegram_info"] = {
        "length": length,
        "c_field": c_field,
        "manufacturer_code": f"0x{m_field:04x}",
        "manufacturer": manufacturer_name,
        "address": address_str,
        "version": version,
        "device_type_code": type,
        "device_type": device_type,
    }
    
    if verbose and output_format == "text":
        print(f"Telegram uzunluğu: {length} bayt")
        print(f"C alanı: 0x{c_field:02x}")
        print(f"Üretici: 0x{m_field:04x} ({manufacturer_name})")
        print(f"Adres: {address_str}")
        print(f"Versiyon: 0x{version:02x}")
        print(f"Tip: 0x{type:02x} ({device_type})")
    
    # CI alanı ve sonraki veri
    if len(data) <= 10:
        logger.warning("Veri yok veya çok kısa")
        return result
    
    ci_field = data[10]
    result["telegram_info"]["ci_field"] = f"0x{ci_field:02x}"
    
    if verbose and output_format == "text":
        print(f"CI alanı: 0x{ci_field:02x}")
    
    # TPL güvenlik kontrolü (şifrelenmiş olabilir)
    is_encrypted = False
    tpl_start = 11
    
    # CI alanına göre TPL yapısını belirle
    if ci_field == 0x72:  # Uzun başlık
        if len(data) < tpl_start + 12:
            logger.warning("TPL verisi çok kısa")
            return result
        
        tpl_id = data[tpl_start:tpl_start+4]
        tpl_mfct = (data[tpl_start+5] << 8) | data[tpl_start+4]
        tpl_version = data[tpl_start+6]
        tpl_type = data[tpl_start+7]
        tpl_acc = data[tpl_start+8]
        tpl_sts = data[tpl_start+9]
        tpl_cfg = (data[tpl_start+11] << 8) | data[tpl_start+10]
        
        result["telegram_info"]["tpl"] = {
            "id": binascii.hexlify(tpl_id).decode(),
            "manufacturer": f"0x{tpl_mfct:04x}",
            "version": f"0x{tpl_version:02x}",
            "type": f"0x{tpl_type:02x}",
            "access_number": tpl_acc,
            "status": f"0x{tpl_sts:02x}",
            "configuration": f"0x{tpl_cfg:04x}"
        }
        
        if verbose and output_format == "text":
            print(f"TPL ID: {binascii.hexlify(tpl_id).decode()}")
            print(f"TPL Üretici: 0x{tpl_mfct:04x}")
            print(f"TPL Versiyon: 0x{tpl_version:02x}")
            print(f"TPL Tip: 0x{tpl_type:02x}")
            print(f"TPL Erişim Nr: 0x{tpl_acc:02x}")
            print(f"TPL Durum: 0x{tpl_sts:02x}")
            print(f"TPL Konfigürasyon: 0x{tpl_cfg:04x}")
        
        # Güvenlik modu (TPL şifreleme) kontrolü
        sec_mode = (tpl_cfg >> 8) & 0x1F
        if sec_mode == 5:  # AES-CBC with IV
            is_encrypted = True
            result["telegram_info"]["security"] = {
                "mode": "AES-CBC with IV",
                "status": "Şifrelenmiş"
            }
            if verbose and output_format == "text":
                print("Telgraf AES-CBC IV ile şifrelenmiş")
            payload_start = tpl_start + 12
        elif sec_mode == 7:  # AES-CBC without IV
            is_encrypted = True
            result["telegram_info"]["security"] = {
                "mode": "AES-CBC without IV",
                "status": "Şifrelenmiş"
            }
            if verbose and output_format == "text":
                print("Telgraf AES-CBC (IV'siz) ile şifrelenmiş")
            payload_start = tpl_start + 12
        else:
            result["telegram_info"]["security"] = {
                "mode": f"0x{sec_mode:02x}",
                "status": "Şifrelenmemiş"
            }
            payload_start = tpl_start + 12
    
    elif ci_field == 0x7A:  # Kısa başlık
        if len(data) < tpl_start + 4:
            logger.warning("TPL verisi çok kısa")
            return result
        
        tpl_acc = data[tpl_start]
        tpl_sts = data[tpl_start+1]
        tpl_cfg = (data[tpl_start+3] << 8) | data[tpl_start+2]
        
        result["telegram_info"]["tpl"] = {
            "access_number": tpl_acc,
            "status": f"0x{tpl_sts:02x}",
            "configuration": f"0x{tpl_cfg:04x}"
        }
        
        if verbose and output_format == "text":
            print(f"TPL Erişim Nr: 0x{tpl_acc:02x}")
            print(f"TPL Durum: 0x{tpl_sts:02x}")
            print(f"TPL Konfigürasyon: 0x{tpl_cfg:04x}")
        
        # Güvenlik modu kontrolü
        sec_mode = (tpl_cfg >> 8) & 0x1F
        if sec_mode == 5 or sec_mode == 7:
            is_encrypted = True
            result["telegram_info"]["security"] = {
                "mode": f"AES-CBC mode {sec_mode}",
                "status": "Şifrelenmiş"
            }
            if verbose and output_format == "text":
                print(f"Telgraf AES-CBC ile şifrelenmiş (mod {sec_mode})")
            payload_start = tpl_start + 4
        else:
            result["telegram_info"]["security"] = {
                "mode": f"0x{sec_mode:02x}",
                "status": "Şifrelenmemiş"
            }
            payload_start = tpl_start + 4
    
    else:
        payload_start = tpl_start
    
    # Veri kısmı
    if len(data) <= payload_start:
        logger.warning("Veri kısmı yok")
        return result
    
    payload = data[payload_start:]
    
    # Şifre çözme
    if is_encrypted and key:
        try:
            key_bytes = binascii.unhexlify(key)
            if len(key_bytes) != 16:
                logger.error(f"Geçersiz anahtar uzunluğu: {len(key_bytes)} bayt (16 bayt olmalı)")
                return result
            
            # IV hesapla (daha gelişmiş bir şekilde)
            if 'tpl' in result["telegram_info"] and 'access_number' in result["telegram_info"]["tpl"]:
                iv = calculate_iv(
                    m_field,
                    address_bytes,
                    result["telegram_info"]["tpl"]["access_number"]
                )
            else:
                iv = None
            
            # Şifrelenmiş veriyi çöz
            decrypted = decrypt_aes_cbc_iv(payload, key_bytes, iv)
            
            # Kontrol et (genellikle ilk 2 bayt 0x2F2F olmalı)
            decrypt_check_offset = 2
            if len(decrypted) >= 2 and decrypted[0] == 0x2F and decrypted[1] == 0x2F:
                result["telegram_info"]["security"]["status"] = "Çözüldü"
                if verbose and output_format == "text":
                    print("Şifre çözme başarılı! (0x2F2F kontrol baytları doğrulandı)")
                payload = decrypted[decrypt_check_offset:]  # Kontrol baytlarını atla
            else:
                result["telegram_info"]["security"]["status"] = "Çözülemedi"
                if verbose and output_format == "text":
                    print("Şifre çözme başarısız veya yanlış anahtar!")
                return result
        except Exception as e:
            logger.error(f"Şifre çözme hatası: {e}")
            return result
    
    # Veri blokları (DIF/VIF yapısı)
    if verbose and output_format == "text":
        print("\nVeri blokları:")
    
    pos = 0
    while pos < len(payload):
        if pos + 1 >= len(payload):
            break
        
        data_block = {}
        
        # DIF
        dif_byte = payload[pos]
        dif_info = parse_dif(dif_byte)
        data_block["dif"] = {
            "byte": f"0x{dif_byte:02x}",
            "info": dif_info
        }
        pos += 1
        
        # DIFE (DIF uzantıları)
        dife_list = []
        while dif_info["extension_bit"] and pos < len(payload):
            dife_byte = payload[pos]
            storage_number_bit = (dife_byte & 0x40) >> 6
            tariff_bit = (dife_byte & 0x30) >> 4
            device_unit_bit = dife_byte & 0x0F
            extension_bit = (dife_byte & 0x80) >> 7
            
            dife_info = {
                "byte": f"0x{dife_byte:02x}",
                "storage_number_bit": storage_number_bit,
                "tariff_bit": tariff_bit,
                "device_unit_bit": device_unit_bit,
                "extension_bit": extension_bit
            }
            dife_list.append(dife_info)
            
            dif_info["storage_number"] |= storage_number_bit << (pos - 1)
            dif_info["extension_bit"] = extension_bit
            pos += 1
            
            if not extension_bit:
                break
        
        if dife_list:
            data_block["dife"] = dife_list
        
        # VIF
        if pos >= len(payload):
            break
            
        vif_byte = payload[pos]
        vif_info = parse_vif(vif_byte)
        data_block["vif"] = {
            "byte": f"0x{vif_byte:02x}",
            "info": vif_info
        }
        pos += 1
        
        # VIFE (VIF uzantıları)
        vife_list = []
        while vif_info["extension_bit"] and pos < len(payload):
            vife_byte = payload[pos]
            vife_info = parse_vife(vife_byte)
            
            vife_list.append({
                "byte": f"0x{vife_byte:02x}",
                "info": vife_info
            })
            
            vif_info["extension_bit"] = vife_info["extension_bit"]
            pos += 1
            
            if not vife_info["extension_bit"]:
                break
        
        if vife_list:
            data_block["vife"] = vife_list
        
        # Veri uzunluğunu al
        data_length = dif_info["data_length"]
        if data_length == -1:  # Değişken uzunluk
            if pos >= len(payload):
                break
            data_length = payload[pos]
            pos += 1
        
        # Veriyi oku
        if pos + data_length > len(payload):
            logger.warning(f"Uyarı: Veri bloğu tamamlanmadan veri bitti. İhtiyaç: {data_length}, Kalan: {len(payload) - pos}")
            break
            
        data_bytes = payload[pos:pos+data_length]
        data_block["raw_data"] = binascii.hexlify(data_bytes).decode()
        pos += data_length
        
        # Veriyi çözümle
        value = None
        if "BCD" in dif_info["data_type"]:
            value = decode_bcd(data_bytes, data_length)
        elif "Real" in dif_info["data_type"]:
            value = decode_real(data_bytes)
        elif vif_info["unit"] == "Tarih":
            value = decode_date(data_bytes)
        elif vif_info["unit"] == "Tarih ve Zaman":
            value = decode_time(data_bytes)
        elif "Integer" in dif_info["data_type"]:
            value = decode_integer(data_bytes, data_length)
        
        # Değeri birimler ve çarpanlarla formatla
        formatted_value = "Bilinmeyen format"
        if value is not None:
            if vif_info["unit"] in ["Tarih", "Tarih ve Zaman"]:
                formatted_value = str(value)
            else:
                scaled_value = value * vif_info["multiplier"]
                formatted_value = f"{scaled_value} {vif_info['unit']}"
        
        data_block["value"] = value
        data_block["formatted_value"] = formatted_value
        
        if verbose and output_format == "text":
            print(f"DIF: 0x{dif_byte:02x} ({dif_info['data_type']}, {dif_info['function_type']})")
            print(f"VIF: 0x{vif_byte:02x} (Birim: {vif_info['unit']}, Çarpan: {vif_info['multiplier']})")
            if vife_list:
                vife_str = ', '.join([f"0x{v['byte']}" for v in vife_list])
                print(f"VIFE: {vife_str}")
            print(f"Veri: {binascii.hexlify(data_bytes).decode()}")
            print(f"Değer: {formatted_value}")
            print("-" * 40)
        
        result["data_blocks"].append(data_block)
    
    if output_format == "json":
        return json.dumps(result, indent=2)
    
    return result

    if DRIVERS_AVAILABLE and use_drivers:
        try:
            logger.debug("Sürücüyü uygulama denenecek")
            driver_result = driver_manager.apply_driver(result)
            if driver_result:
                logger.info("Sürücü başarıyla uygulandı")
                result = driver_result
        except Exception as e:
            logger.warning(f"Sürücü uygulanırken hata oluştu: {e}")

def create_telegram(manufacturer, id_bytes, device_type, ci=0x72, payload=None, encrypted=False, key=None):
    """
    Yeni bir wM-Bus telgrafı oluştur
    
    manufacturer: 2 byte üretici kodu (int veya string olarak)
    id_bytes: 4 byte sayaç ID'si (hex string olarak)
    device_type: Cihaz tipi (1 byte)
    ci: CI alanı (1 byte)
    payload: Veri kısmı (hex string olarak)
    encrypted: Şifreleme kullanılacak mı?
    key: 16 byte AES anahtarı (hex string olarak)
    """
    # Üretici kodunu işle
    if isinstance(manufacturer, str) and len(manufacturer) == 3:
        # ASCII formatını sayısal değere dönüştür (EN 13757-3)
        m1 = (ord(manufacturer[0]) - 64) << 10
        m2 = (ord(manufacturer[1]) - 64) << 5
        m3 = ord(manufacturer[2]) - 64
        mfct = m1 | m2 | m3
    else:
        mfct = manufacturer
    
    # Sayaç ID'sini işle
    if isinstance(id_bytes, str):
        id_bytes = binascii.unhexlify(id_bytes)
    
    # Telgraf başlığını oluştur
    version = 1  # Versiyon
    access_nr = 1  # Erişim numarası
    
    # DLL katmanı
    telegram = bytearray()
    # Uzunluk, CI alanından sonra doldurulacak
    telegram.append(0)  # Length placeholder
    telegram.append(0x44)  # C-field: SND-NR
    telegram.append(mfct & 0xFF)  # Manufacturer LSB
    telegram.append((mfct >> 8) & 0xFF)  # Manufacturer MSB
    telegram.extend(id_bytes)  # ID bytes
    telegram.append(version)  # Version
    telegram.append(device_type)  # Device Type
    
    # CI Alanı
    telegram.append(ci)
    
    # TPL Katmanı (ci_field == 0x72 için uzun başlık)
    if ci == 0x72:
        # TPL başlığı - Kısa TPL ID olarak sayaç ID'sini kullan
        telegram.extend(id_bytes)
        # Üretici kodu
        telegram.append(mfct & 0xFF)
        telegram.append((mfct >> 8) & 0xFF)
        # Versiyon ve tip
        telegram.append(version)
        telegram.append(device_type)
        # Erişim numarası, durum ve yapılandırma
        telegram.append(access_nr)
        telegram.append(0)  # Status
        
        # Konfigürasyon: Güvenlik modu
        if encrypted:
            telegram.append(0x00)  # CFG LSB
            telegram.append(0x50)  # CFG MSB (Mod 5: AES-CBC with IV)
        else:
            telegram.append(0x00)
            telegram.append(0x00)
    
    # Veri kısmı
    if payload:
        # Payload'ı işle
        if isinstance(payload, str):
            payload_bytes = binascii.unhexlify(payload)
        else:
            payload_bytes = payload
        
        # Şifreleme
        if encrypted and key:
            if isinstance(key, str):
                key_bytes = binascii.unhexlify(key)
            else:
                key_bytes = key
            
            # IV hesapla
            iv = calculate_iv(mfct, id_bytes, access_nr)
            
            # 2F2F başlangıç kontrol baytlarını ekle
            payload_with_header = b'\x2F\x2F' + payload_bytes
            
            # AES-CBC Şifreleme
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
            # 16 baytın katlarına tamamla (PKCS#7 padding)
            padding_len = 16 - (len(payload_with_header) % 16)
            padded_payload = payload_with_header + bytes([padding_len] * padding_len)
            encrypted_payload = cipher.encrypt(padded_payload)
            
            telegram.extend(encrypted_payload)
        else:
            telegram.extend(payload_bytes)
    
    # Toplam uzunluğu ayarla (ilk bayt)
    telegram[0] = len(telegram) - 1
    
    return binascii.hexlify(telegram).decode()

def print_help():
    """Yardım mesajını yazdır"""
    print("wM-Bus Telgraf Çözümleyici")
    print("Kullanım: python wmbus_parser.py [seçenekler] <telgraf_hex>")
    print("")
    print("Seçenekler:")
    print("  -h, --help             Bu yardım mesajını göster")
    print("  -k, --key KEY          AES şifreleme anahtarı (16 bayt, hex string)")
    print("  -o, --output FORMAT    Çıktı formatı: text veya json")
    print("  -v, --verbose          Detaylı çıktı")
    print("  -c, --create           Telgraf oluştur (örnekler için README'ye bakın)")
    print("  -d, --drivers          Cihaz sürücülerini kullan (varsayılan: Evet)")
    print("")
    print("Örnek:")
    print("  python wmbus_parser.py 314493446287133136087a250000200B6e1500004B6e000000426cffffcB086e000000c2086cdf2c326cffff046d3712f221")
    print("  python wmbus_parser.py -k A1B2C3D4E5F6A1B2C3D4E5F6A1B2C3D4 314493446287133136087a250000200B6e1500004B6e000000426cffffcB086e000000c2086cdf2c326cffff046d3712f221")
# ---------------------------------------
def main():
    parser = argparse.ArgumentParser(description="wM-Bus Telgraf Çözümleyici")
    parser.add_argument("telegram", nargs="?", help="Çözümlenecek wM-Bus telgrafı (hex string)")
    parser.add_argument("-k", "--key", help="AES şifreleme anahtarı (16 bayt, hex string)")
    parser.add_argument("-o", "--output", choices=["text", "json"], default="text", help="Çıktı formatı")
    parser.add_argument("-v", "--verbose", action="store_true", help="Detaylı çıktı")
    parser.add_argument("-c", "--create", action="store_true", help="Telgraf oluştur")
    parser.add_argument("-d", "--drivers", action="store_true", default=True, help="Cihaz sürücülerini kullan (varsayılan: Evet)")
    
    args = parser.parse_args()
    
    if args.create:
        # Örnek telgraf oluştur
        mfct = 0x0477  # Kamstrup
        id_bytes = binascii.unhexlify("12345678")
        device_type = 0x07  # Su sayacı
        
        # Veri bloğu: Tüketim değeri 12345 Wh
        data_blocks = add_measurement_block(None, 12345, "Wh")
        
        # Telgrafı oluştur
        telegram = create_telegram(
            manufacturer=mfct,
            id_bytes=id_bytes,
            device_type=device_type,
            ci=0x72,
            payload=data_blocks,
            encrypted=args.key is not None,
            key=args.key
        )
        
        print(f"Oluşturulan telgraf: {telegram}")
    
    elif args.telegram:
        # Telgrafı çözümle
        result = parse_wmbus_telegram(
        args.telegram,
        key=args.key,
        verbose=args.verbose,
        output_format=args.output,
        use_drivers=args.drivers
        )
        
        if args.output == "json" and result:
            print(result)
    else:
        print_help()

if __name__ == "__main__":
    main()