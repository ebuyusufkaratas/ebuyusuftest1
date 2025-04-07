# wmbus_crypto.py - wM-Bus şifreleme ve şifre çözme işlemleri
from Crypto.Cipher import AES

def decrypt_aes_cbc_iv(encrypted_data, key, iv=None):
    """
    AES-CBC şifresini çöz
    
    encrypted_data: Şifrelenmiş veri
    key: 16 baytlık AES anahtarı
    iv: 16 baytlık Initialization Vector
    """
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
    """
    AES-CBC ile şifrele
    
    plain_data: Şifrelenecek veri
    key: 16 baytlık AES anahtarı
    iv: 16 baytlık Initialization Vector
    """
    # 16 baytın katlarına tamamla (PKCS#7 padding)
    padding_len = 16 - (len(plain_data) % 16)
    padded_data = plain_data + bytes([padding_len] * padding_len)
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(padded_data)
    
    return encrypted