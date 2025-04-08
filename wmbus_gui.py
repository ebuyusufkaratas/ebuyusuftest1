# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import binascii
import json
import threading
import time
import sys

# wM-Bus modüllerini içe aktar
from wmbus_parser import parse_wmbus_telegram, create_telegram
from wmbus_utils import add_measurement_block

class WMBusGUI:
    def __init__(self, master):
        self.master = master
        master.title("wM-Bus Telgraf Çözümleyici")
        master.geometry("800x600")
        
        # Ana çerçeve
        main_frame = ttk.Frame(master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sekme kontrolü oluştur
        tab_control = ttk.Notebook(main_frame)
        
        # Sekmeleri oluştur
        tab1 = ttk.Frame(tab_control)
        tab2 = ttk.Frame(tab_control)
        
        tab_control.add(tab1, text='Telgraf Çözümle')
        tab_control.add(tab2, text='Telgraf Oluştur')
        tab_control.pack(expand=1, fill="both")
        
        # ======== Telgraf Çözümle Sekmesi ========
        # Giriş alanı
        frame_input = ttk.LabelFrame(tab1, text="Telgraf Verileri", padding="10")
        frame_input.pack(fill=tk.BOTH, padx=5, pady=5)
        
        ttk.Label(frame_input, text="Hexadecimal Telgraf Verisi:").grid(column=0, row=0, sticky=tk.W)
        self.hex_data = tk.StringVar()
        ttk.Entry(frame_input, width=80, textvariable=self.hex_data).grid(column=0, row=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(frame_input, text="AES Anahtarı (opsiyonel):").grid(column=0, row=2, sticky=tk.W)
        self.aes_key = tk.StringVar()
        ttk.Entry(frame_input, width=50, textvariable=self.aes_key).grid(column=0, row=3, padx=5, pady=5, sticky=tk.W)
        
        # Çıktı formatı
        self.output_format = tk.StringVar(value="text")
        ttk.Label(frame_input, text="Çıktı Formatı:").grid(column=0, row=4, sticky=tk.W)
        ttk.Radiobutton(frame_input, text="Metin", variable=self.output_format, value="text").grid(column=0, row=5, sticky=tk.W, padx=(20, 0))
        ttk.Radiobutton(frame_input, text="JSON", variable=self.output_format, value="json").grid(column=0, row=6, sticky=tk.W, padx=(20, 0))
        
        # Butonlar
        button_frame = ttk.Frame(tab1)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Çözümle", command=self.parse_telegram).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Temizle", command=self.clear_output).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Dosyadan Yükle", command=self.load_from_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Sonucu Kaydet", command=self.save_output).pack(side=tk.LEFT, padx=5)
        
        # Çıktı alanı
        output_frame = ttk.LabelFrame(tab1, text="Çözümleme Sonucu", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, width=80, height=20)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # ======== Telgraf Oluştur Sekmesi ========
        # Üretici bilgileri
        manufacturer_frame = ttk.LabelFrame(tab2, text="Üretici Bilgileri", padding="10")
        manufacturer_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(manufacturer_frame, text="Üretici Kodu (hex, örn: 0477):").grid(column=0, row=0, sticky=tk.W)
        self.manufacturer_code = tk.StringVar(value="0477")
        ttk.Entry(manufacturer_frame, width=10, textvariable=self.manufacturer_code).grid(column=1, row=0, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(manufacturer_frame, text="Cihaz ID (hex, örn: 12345678):").grid(column=0, row=1, sticky=tk.W)
        self.device_id = tk.StringVar(value="12345678")
        ttk.Entry(manufacturer_frame, width=20, textvariable=self.device_id).grid(column=1, row=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(manufacturer_frame, text="Cihaz Tipi:").grid(column=0, row=2, sticky=tk.W)
        self.device_type = tk.StringVar(value="07")
        device_types = ["01 - Elektrik Sayacı", "02 - Gaz Sayacı", "03 - Isı Sayacı", "07 - Su Sayacı", "0F - Basınç Ölçer"]
        ttk.Combobox(manufacturer_frame, textvariable=self.device_type, values=device_types, width=30).grid(column=1, row=2, padx=5, pady=5, sticky=tk.W)
        
        # Ölçüm değerleri
        measurement_frame = ttk.LabelFrame(tab2, text="Ölçüm Değerleri", padding="10")
        measurement_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(measurement_frame, text="Değer:").grid(column=0, row=0, sticky=tk.W)
        self.measurement_value = tk.StringVar(value="12345")
        ttk.Entry(measurement_frame, width=20, textvariable=self.measurement_value).grid(column=1, row=0, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(measurement_frame, text="Birim:").grid(column=0, row=1, sticky=tk.W)
        self.measurement_unit = tk.StringVar(value="Wh")
        units = ["Wh", "m3", "C", "W"]
        ttk.Combobox(measurement_frame, textvariable=self.measurement_unit, values=units, width=10).grid(column=1, row=1, padx=5, pady=5, sticky=tk.W)
        
        # Şifreleme
        encryption_frame = ttk.LabelFrame(tab2, text="Şifreleme", padding="10")
        encryption_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.encrypt_telegram = tk.BooleanVar(value=False)
        ttk.Checkbutton(encryption_frame, text="Telgrafı Şifrele", variable=self.encrypt_telegram).grid(column=0, row=0, sticky=tk.W)
        
        ttk.Label(encryption_frame, text="AES Anahtarı:").grid(column=0, row=1, sticky=tk.W)
        self.create_aes_key = tk.StringVar()
        ttk.Entry(encryption_frame, width=50, textvariable=self.create_aes_key).grid(column=0, row=2, padx=5, pady=5, sticky=tk.W)
        
        # Butonlar
        create_button_frame = ttk.Frame(tab2)
        create_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(create_button_frame, text="Telgraf Oluştur", command=self.create_telegram).pack(side=tk.LEFT, padx=5)
        ttk.Button(create_button_frame, text="Temizle", command=self.clear_create_output).pack(side=tk.LEFT, padx=5)
        ttk.Button(create_button_frame, text="Sonucu Kaydet", command=self.save_create_output).pack(side=tk.LEFT, padx=5)
        
        # Çıktı alanı
        create_output_frame = ttk.LabelFrame(tab2, text="Oluşturulan Telgraf", padding="10")
        create_output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.create_output_text = scrolledtext.ScrolledText(create_output_frame, width=80, height=10)
        self.create_output_text.pack(fill=tk.BOTH, expand=True)
        
        # Durum çubuğu
        self.status_var = tk.StringVar()
        self.status_var.set("Hazır")
        status_bar = ttk.Label(master, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def parse_telegram(self):
        """Telgrafı çözümle"""
        self.status_var.set("Çözümleniyor...")
        self.master.update_idletasks()
        
        hex_data = self.hex_data.get().strip()
        hex_data = hex_data.replace(" ", "").replace("\n", "").lower()

        aes_key = self.aes_key.get().strip()
        output_format = self.output_format.get()
        
        if not hex_data:
            messagebox.showerror("Hata", "Telgraf verisi boş olamaz!")
            self.status_var.set("Hazır")
            return
        
        # Farklı bir thread'de çözümleme yap
        threading.Thread(target=self._parse_telegram_thread, 
                         args=(hex_data, aes_key, output_format)).start()
    
    def _parse_telegram_thread(self, hex_data, aes_key, output_format):
        """Telgraf çözümleme işini arka planda yap"""
        try:
            # Çözümleme işlemi
            result = parse_wmbus_telegram(
                hex_data,
                key=aes_key if aes_key else None,
                verbose=False,
                output_format=output_format
            )

            # JSON formatında ise string döner, dict'e çevir
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except Exception as e:
                    self.master.after(0, lambda: messagebox.showerror("Hata", f"JSON çözümlenemedi: {e}"))
                    self.master.after(0, lambda: self.status_var.set("Hazır"))
                    return

            if not result or not isinstance(result, dict):
                self.master.after(0, lambda: messagebox.showerror("Hata", "Telgraf çözümlenemedi!"))
                self.master.after(0, lambda: self.status_var.set("Hazır"))
                return


            from driver_manager import apply_driver
            
            result = apply_driver(result)

            
            if not result:
                self.master.after(0, lambda: messagebox.showerror("Hata", "Telgraf çözümlenemedi!"))
                self.master.after(0, lambda: self.status_var.set("Hazır"))
                return
            
            # Çıktıyı göster
            if output_format == "json":
                # JSON ise güzelleştir
                if isinstance(result, str):
                    # Zaten JSON string ise
                    json_obj = json.loads(result)
                    formatted_json = json.dumps(json_obj, indent=2, ensure_ascii=False)
                    self.master.after(0, lambda: self.output_text.delete(1.0, tk.END))
                    self.master.after(0, lambda: self.output_text.insert(tk.END, formatted_json))
                else:
                    # Obje ise JSON'a dönüştür
                    formatted_json = json.dumps(result, indent=2, ensure_ascii=False)
                    self.master.after(0, lambda: self.output_text.delete(1.0, tk.END))
                    self.master.after(0, lambda: self.output_text.insert(tk.END, formatted_json))
            else:
                # Metin formatı için özel bir gösterim yap
                self.master.after(0, lambda: self.output_text.delete(1.0, tk.END))
                if "telegram_info" not in result:
                    self.master.after(0, lambda: messagebox.showerror("Hata", "Telgraf geçerli değil veya tanınamadı."))
                    self.master.after(0, lambda: self.status_var.set("Hazır"))
                    return
                
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except Exception as e:
                        self.master.after(0, lambda: messagebox.showerror("Hata", f"JSON çözümleme hatası: {e}"))
                        return

                
                # Telegram bilgilerini yazdır
                telegram_info = result["telegram_info"]
                info_text = (
                    f"Telegram Bilgileri:\n"
                    f"----------------\n"
                    f"Uzunluk: {telegram_info['length']} bayt\n"
                    f"C Alanı: 0x{telegram_info['c_field']:02x}\n"
                    f"Üretici: {telegram_info['manufacturer_code']} ({telegram_info['manufacturer']})\n"
                    f"Adres: {telegram_info['address']}\n"
                    f"Versiyon: 0x{telegram_info['version']:02x}\n"
                    f"Cihaz Tipi: 0x{telegram_info['device_type_code']:02x} ({telegram_info['device_type']})\n"
                    f"CI Alanı: {telegram_info['ci_field']}\n\n"
                )
                
                # TPL bilgilerini yazdır (varsa)
                if "tpl" in telegram_info:
                    tpl = telegram_info["tpl"]
                    info_text += "TPL Bilgileri:\n----------------\n"
                    for key, value in tpl.items():
                        info_text += f"{key}: {value}\n"
                    info_text += "\n"
                
                # Güvenlik bilgilerini yazdır (varsa)
                if "security" in telegram_info:
                    security = telegram_info["security"]
                    info_text += "Güvenlik Bilgileri:\n----------------\n"
                    for key, value in security.items():
                        info_text += f"{key}: {value}\n"
                    info_text += "\n"
                
                # Veri bloklarını yazdır
                if "total_kwh" in result or "current_kwh" in result or "previous_kwh" in result:
                    info_text += "Sürücü Özel Çıktısı:\n----------------\n"
                    if "previous_kwh" in result:
                        info_text += f"Önceki Dönem Enerji: {result['previous_kwh']} kWh\n"
                    if "current_kwh" in result:
                        info_text += f"Mevcut Dönem Enerji: {result['current_kwh']} kWh\n"
                    if "total_kwh" in result:
                        info_text += f"Toplam Enerji: {result['total_kwh']} kWh\n"
                    info_text += "\n"
                
                data_blocks = result["data_blocks"]
                info_text += f"Veri Blokları ({len(data_blocks)}):\n----------------\n"
                
                for i, block in enumerate(data_blocks):
                    info_text += f"Blok {i+1}:\n"
                    
                    # DIF
                    dif = block["dif"]
                    info_text += f"DIF: {dif['byte']} ({dif['info']['data_type']}, {dif['info']['function_type']})\n"
                    
                    # DIFE (varsa)
                    if "dife" in block:
                        dife_text = ", ".join([f"{d['byte']}" for d in block["dife"]])
                        info_text += f"DIFE: {dife_text}\n"
                    
                    # VIF
                    vif = block["vif"]
                    info_text += f"VIF: {vif['byte']} (Birim: {vif['info']['unit']}, Çarpan: {vif['info']['multiplier']})\n"
                    
                    # VIFE (varsa)
                    if "vife" in block:
                        vife_text = ", ".join([f"{v['byte']}" for v in block["vife"]])
                        info_text += f"VIFE: {vife_text}\n"
                    
                    # Veri ve değer
                    info_text += f"Veri: {block['raw_data']}\n"
                    info_text += f"Değer: {block['formatted_value']}\n"
                    info_text += "----------------\n"
                
                self.master.after(0, lambda: self.output_text.insert(tk.END, info_text))
            
            self.master.after(0, lambda: self.status_var.set("Çözümleme tamamlandı"))
        
        except Exception as e:
            error_msg = f"Hata oluştu: {str(e)}"
            self.master.after(0, lambda: messagebox.showerror("Hata", error_msg))
            self.master.after(0, lambda: self.status_var.set("Hata oluştu"))
    
    def create_telegram(self):
        """Yeni bir telgraf oluştur"""
        self.status_var.set("Telgraf oluşturuluyor...")
        self.master.update_idletasks()
        
        # Değerleri al
        try:
            manufacturer_code = int(self.manufacturer_code.get().strip(), 16)
            device_id = self.device_id.get().strip()
            device_type = int(self.device_type.get().split(" - ")[0].strip(), 16)
            
            # Sayıya dönüştür
            measurement_value = int(self.measurement_value.get().strip())
            measurement_unit = self.measurement_unit.get()
            
            # Şifreleme bilgileri
            encrypt = self.encrypt_telegram.get()
            aes_key = self.create_aes_key.get().strip() if encrypt else None
            
            # Şifreleme seçildi ama anahtar yok
            if encrypt and not aes_key:
                messagebox.showerror("Hata", "Şifreleme seçildi ama AES anahtarı verilmedi!")
                self.status_var.set("Hazır")
                return
            
            # Veri bloğu oluştur
            data_blocks = add_measurement_block(None, measurement_value, measurement_unit)
            
            # Telgrafı oluştur
            telegram = create_telegram(
                manufacturer=manufacturer_code,
                id_bytes=device_id,
                device_type=device_type,
                ci=0x72,
                payload=data_blocks,
                encrypted=encrypt,
                key=aes_key if encrypt else None
            )
            
            # Sonucu göster
            self.create_output_text.delete(1.0, tk.END)
            self.create_output_text.insert(tk.END, telegram)
            
            # Durum bilgisini güncelle
            if encrypt:
                self.status_var.set(f"Şifreli telgraf oluşturuldu ({len(telegram)//2} bayt)")
            else:
                self.status_var.set(f"Telgraf oluşturuldu ({len(telegram)//2} bayt)")
        
        except ValueError as e:
            messagebox.showerror("Değer Hatası", f"Geçersiz değer: {str(e)}")
            self.status_var.set("Hata oluştu")
        except Exception as e:
            messagebox.showerror("Hata", f"Telgraf oluşturulurken hata: {str(e)}")
            self.status_var.set("Hata oluştu")
    
    def clear_output(self):
        """Çözümleme çıktısını temizle"""
        self.output_text.delete(1.0, tk.END)
        self.status_var.set("Çıktı temizlendi")
    
    def clear_create_output(self):
        """Oluşturma çıktısını temizle"""
        self.create_output_text.delete(1.0, tk.END)
        self.status_var.set("Çıktı temizlendi")
    
    def load_from_file(self):
        """Dosyadan telgraf verisi yükle"""
        file_path = filedialog.askopenfilename(
            title="Telgraf Verisi Yükle",
            filetypes=[("Metin Dosyaları", "*.txt"), ("Tüm Dosyalar", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r') as file:
                data = file.read().strip()
                self.hex_data.set(data)
                self.status_var.set(f"Veri yüklendi: {file_path}")
        except Exception as e:
            messagebox.showerror("Yükleme Hatası", f"Dosya yüklenirken hata: {str(e)}")
            self.status_var.set("Yükleme hatası")
    
    def save_output(self):
        """Çözümleme sonucunu dosyaya kaydet"""
        if not self.output_text.get(1.0, tk.END).strip():
            messagebox.showwarning("Uyarı", "Kaydedilecek çıktı yok!")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Çözümleme Sonucunu Kaydet",
            defaultextension=".txt",
            filetypes=[("Metin Dosyaları", "*.txt"), ("JSON Dosyaları", "*.json"), ("Tüm Dosyalar", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(self.output_text.get(1.0, tk.END))
                self.status_var.set(f"Sonuç kaydedildi: {file_path}")
        except Exception as e:
            messagebox.showerror("Kaydetme Hatası", f"Dosya kaydedilirken hata: {str(e)}")
            self.status_var.set("Kaydetme hatası")
    
    def save_create_output(self):
        """Oluşturulan telgrafı dosyaya kaydet"""
        if not self.create_output_text.get(1.0, tk.END).strip():
            messagebox.showwarning("Uyarı", "Kaydedilecek telgraf yok!")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Telgrafı Kaydet",
            defaultextension=".txt",
            filetypes=[("Metin Dosyaları", "*.txt"), ("Tüm Dosyalar", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w') as file:
                file.write(self.create_output_text.get(1.0, tk.END))
                self.status_var.set(f"Telgraf kaydedildi: {file_path}")
        except Exception as e:
            messagebox.showerror("Kaydetme Hatası", f"Dosya kaydedilirken hata: {str(e)}")
            self.status_var.set("Kaydetme hatası")

def main():
    root = tk.Tk()
    app = WMBusGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()