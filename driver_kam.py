# -*- coding: utf-8 -*-
"""
Kamstrup Multical ısı sayacı için sürücü.
"""

from driver_base import WMBusDriverBase

class KamstrupMulticalDriver(WMBusDriverBase):
    """
    Kamstrup Multical ısı sayacı için özel sürücü.
    
    Üretici: Kamstrup (0x0477)
    Cihaz tipi: Heat Meter (0x03)
    
    Bu cihaz, binalarda ısıtma/soğutma enerjisi ölçümü için kullanılır.
    """
    MANUFACTURER_ID = "0x0477"  # Kamstrup
    DEVICE_TYPE = 0x03  # Heat Meter
    
    def parse(self):
        """Multical telgrafını çözümle."""
        # Cihaz tipini belirle
        self.result["media"] = "heat"
        self.result["meter"] = "multical"
        self.result["name"] = ""  # İstenirse özelleştirilebilir
        
        # Enerji değerlerini çözümle (Wh birimleri)
        for dif in ["0x01", "0x02", "0x03", "0x04"]:
            for vif in ["0x06", "0x05", "0x04"]:
                energy_block = self.find_block(dif, vif)
                if energy_block:
                    # kWh'a dönüştür
                    energy_value = energy_block["value"] * energy_block["vif"]["info"]["multiplier"] / 1000
                    self.result["total_energy_kwh"] = energy_value
                    break
        
        # Hacim değerlerini çözümle (m³)
        for dif in ["0x01", "0x02", "0x03", "0x04"]:
            for vif in ["0x13", "0x14", "0x15", "0x16"]:
                volume_block = self.find_block(dif, vif)
                if volume_block:
                    volume_value = volume_block["value"] * volume_block["vif"]["info"]["multiplier"]
                    self.result["total_volume_m3"] = volume_value
                    break
        
        # Akış sıcaklığını çözümle (°C)
        for dif in ["0x01", "0x02"]:
            for vif in ["0x5a", "0x5b"]:
                flow_temp_block = self.find_block(dif, vif)
                if flow_temp_block:
                    flow_temp = flow_temp_block["value"] * flow_temp_block["vif"]["info"]["multiplier"]
                    self.result["flow_temperature_c"] = flow_temp
                    break
        
        # Dönüş sıcaklığını çözümle (°C)
        for dif in ["0x01", "0x02"]:
            for vif in ["0x5e", "0x5f"]:
                return_temp_block = self.find_block(dif, vif)
                if return_temp_block:
                    return_temp = return_temp_block["value"] * return_temp_block["vif"]["info"]["multiplier"]
                    self.result["return_temperature_c"] = return_temp
                    break
        
        # Anlık akışı çözümle (m³/h)
        for dif in ["0x01", "0x02", "0x03", "0x04"]:
            for vif in ["0x3b", "0x3c", "0x3d", "0x3e"]:
                flow_block = self.find_block(dif, vif)
                if flow_block:
                    flow_value = flow_block["value"] * flow_block["vif"]["info"]["multiplier"]
                    self.result["flow_m3h"] = flow_value
                    break
        
        # Toplam çalışma saati
        hour_block = self.find_block("0x04", "0x74")
        if hour_block:
            self.result["operating_hours"] = hour_block["value"]
        
        # Güç değeri (W)
        for dif in ["0x01", "0x02", "0x03", "0x04"]:
            for vif in ["0x2b", "0x2c", "0x2d", "0x2e"]:
                power_block = self.find_block(dif, vif)
                if power_block:
                    power_value = power_block["value"] * power_block["vif"]["info"]["multiplier"]
                    self.result["power_w"] = power_value
                    break
        
        # Tarih ve zaman bilgisi
        datetime_block = self.find_block("0x04", "0x6d")
        if datetime_block:
            date_str = datetime_block["formatted_value"]
            self.result["device_date_time"] = date_str.replace("/", "-")
        
        # Cihaz durumu
        if "tpl" in self.telegram_info and "status" in self.telegram_info["tpl"]:
            status_byte = self.telegram_info["tpl"]["status"]
            status_int = int(status_byte, 16)
            
            if status_int == 0:
                self.result["status"] = "OK"
            else:
                error_codes = []
                
                # Kamstrup Multical sayaçları için hata kodları
                if status_int & 0x01:
                    error_codes.append("SENSOR_ERROR")
                if status_int & 0x02:
                    error_codes.append("FLOW_ERROR")
                if status_int & 0x04:
                    error_codes.append("TEMPERATURE_ERROR")
                if status_int & 0x08:
                    error_codes.append("BATTERY_LOW")
                if status_int & 0x10:
                    error_codes.append("POWER_FAILURE")
                if status_int & 0x20:
                    error_codes.append("LEAKAGE_DETECTED")
                if status_int & 0x40:
                    error_codes.append("BURST_DETECTED")
                if status_int & 0x80:
                    error_codes.append("FROST_DETECTED")
                
                if error_codes:
                    self.result["status"] = ", ".join(error_codes)
                else:
                    self.result["status"] = f"UNKNOWN_ERROR ({status_byte})"
        
        # Yıllık tüketim
        annual_block = self.find_block("0x42", "0x06")
        if annual_block:
            annual_energy = annual_block["value"] * annual_block["vif"]["info"]["multiplier"] / 1000
            self.result["annual_energy_kwh"] = annual_energy