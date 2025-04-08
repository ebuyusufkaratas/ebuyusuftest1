# Techem telgrafını doğrudan sürücü ile test et
from driver_tch import TechemCompactDriver
import binascii

# Test telgrafı
test_hex = "37446850792055673943a2109f2f13c500608f1d00008066e8a69B26988d335f6411450c564c5145145ca0f1da35B9dd37a1936BBf3d31d8"
data = binascii.unhexlify(test_hex)

# Temel telgraf bilgilerini çıkar
ci_pos = 10
telegram_info = {
    "manufacturer_code": "0x5068",
    "address": "67552079",
    "ci_field": "0xa2"
}

# Ham payload
payload = data[ci_pos+1:]

# Sürücüyü oluştur ve bilgileri ayarla
driver = TechemCompactDriver(None)
driver.telegram_info = telegram_info
driver.telegram_data = {"raw_payload": payload}
driver.generate_basic_info()

# Çözümle
result = driver.parse()
print(result)