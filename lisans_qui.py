import tkinter as tk
from tkinter import ttk, messagebox
import hashlib

class LicenseGenerator:
    def __init__(self, master):
        self.master = master
        master.title("EnerjiPayRF Lisans Üretici")
        master.geometry("600x300")

        frame = ttk.Frame(master, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Makine Kimliği (EnerjiPayRF-...):").pack(anchor=tk.W)
        self.machine_id_var = tk.StringVar()
        ttk.Entry(frame, width=70, textvariable=self.machine_id_var).pack(pady=5)

        ttk.Button(frame, text="Lisans Anahtarı Üret", command=self.generate_license).pack(pady=10)

        ttk.Label(frame, text="Lisans Anahtarı:").pack(anchor=tk.W)
        self.license_key_var = tk.StringVar()
        ttk.Entry(frame, width=40, textvariable=self.license_key_var, state="readonly").pack(pady=5)

        ttk.Button(frame, text="Panoya Kopyala", command=self.copy_to_clipboard).pack(pady=5)

    def generate_license(self):
        machine_id = self.machine_id_var.get().strip()
        if not machine_id or not machine_id.startswith("EnerjiPayRF-"):
            messagebox.showerror("Hata", "Geçerli bir makine kimliği girin (EnerjiPayRF- ile başlamalı)")
            return

        hashed = hashlib.sha256(machine_id.encode()).hexdigest().upper()[:16]
        self.license_key_var.set(hashed)

    def copy_to_clipboard(self):
        key = self.license_key_var.get()
        if key:
            self.master.clipboard_clear()
            self.master.clipboard_append(key)
            messagebox.showinfo("Kopyalandı", "Lisans anahtarı panoya kopyalandı.")

if __name__ == "__main__":
    root = tk.Tk()
    app = LicenseGenerator(root)
    root.mainloop()