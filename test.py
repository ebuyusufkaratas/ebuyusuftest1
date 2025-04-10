# -*- coding: utf-8 -*-
"""
Techem Compact V telgrafı için test scripti.
"""

import binascii
import json
from driver_tch import TechemCompactDriver

# Test telgrafı
techem_telegram_hex = "37446850336633663943a210672c866100181c01000480794435d50000000000000000000000000000000000000000000000000000000000"

# Telgrafı manuel olarak çözümle
def parse_techem_telegram(hex_data):
    data = binascii.unhexlify(hex_data.replace("_", ""))
    
    # Temel telgraf bilgilerini çıkar
    length = data[0]
    c_field = data[1]
    m_field = (data[3] << 8) | data[2]  # Üretici kodu (Techem: 0x5068)
    
    # Sayaç adresi/ID'si (ters çevrilmiş olarak)
    id_bytes = data[4:8]
    id_str = ""
    for i in range(len(id_bytes)-1, -1, -1):
        id_str += f"{id_bytes[i]:02x}"
    
    version = data[8]
    type = data[9]  # Cihaz tipi
    ci_field = data[10]  # CI alanı (Techem için genellikle 0xA2)
    
    # Payload kısmını çıkar (11. bayttan itibaren)
    payload = data[11:]
    
    # Simüle edilmiş telgraf bilgisi
    telegram_info = {
        "telegram_info": {
            "length": length,
            "c_field": c_field,
            "manufacturer_code": f"0x{m_field:04x}",
            "manufacturer": "Techem",
            "address": id_str,
            "version": version,
            "device_type_code": type,
            "device_type": "Heat Cost Allocator",
            "ci_field": f"0x{ci_field:02x}",
        },
        "data_blocks": [
            {
                "raw_data": binascii.hexlify(payload).decode()
            }
        ]
    }
    
    # Techem sürücüsünü oluştur ve çözümle
    driver = TechemCompactDriver(None)
    driver.telegram_info = telegram_info["telegram_info"]
    driver.data_blocks = telegram_info["data_blocks"]
    driver.generate_basic_info()
    
    # Çözümle
    result = driver.parse()

    # Ek olarak iç değerleri de sonucu görebilmek için:
    if hasattr(driver, "curr_lo"):
        print(f"curr_lo: 0x{driver.curr_lo:02x}")
    if hasattr(driver, "curr_hi"):
        print(f"curr_hi: 0x{driver.curr_hi:02x}")
    if hasattr(driver, "prev_lo"):
        print(f"prev_lo: 0x{driver.prev_lo:02x}")
    if hasattr(driver, "prev_hi"):
        print(f"prev_hi: 0x{driver.prev_hi:02x}")

    return result

# Ana çalıştırma kodu
if __name__ == "__main__":
    print("Techem Compact V telgrafı çözümleniyor...")
    print(f"Telgraf: {techem_telegram_hex}")
    print("-" * 50)
    
    result = parse_techem_telegram(techem_telegram_hex)
    
    if result:
        print("Çözümleme sonucu:")
        formatted_json = json.dumps(result, indent=2)
        print(formatted_json)
        
        print("-" * 50)
        print(f"ID: {result.get('id')}")
        print(f"Üretici: {result.get('manufacturer')}")
        print(f"Toplam enerji: {result.get('total_kwh')} kWh")
        print(f"Mevcut dönem enerji: {result.get('current_kwh')} kWh")
        print(f"Önceki dönem enerji: {result.get('previous_kwh')} kWh")
    else:
        print("Telgraf çözümlenemedi!")
