import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
from bs4 import BeautifulSoup
import threading
import time
from datetime import datetime, timedelta
import webbrowser
import sys
import os
import json

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

class BacklinkChecker:
    def __init__(self):
        # Ana pencere
        self.root = tk.Tk()
        self.root.title("Backlink Checker v1.0")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # Ayar dosyası yolu
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.settings_file = os.path.join(script_dir, 'settings.json')

        # Varsayılan değerler
        self.sites_to_check = []
        self.links_to_find = []
        self.check_interval = 5  # dakika
        self.minimize_to_tray = False

        # Durum değişkenleri
        self.checking = False
        self.background_active = False
        self.check_thread = None
        self.tray_icon = None
        self.is_closing = False

        # Ayarları yükle (varsa)
        self.load_settings()
        self.create_widgets()
        # UI oluştur ve modal başlangıç ayarlarını göster
        if os.path.exists(self.settings_file) and self.sites_to_check and self.links_to_find:
            self.update_main_window()
        else:
            self.show_initial_dialog()

    def load_settings(self):
        """settings.json dosyasından önceki ayarları yükle."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.sites_to_check = data.get('sites', [])
                self.links_to_find = data.get('links', [])
                self.check_interval = data.get('interval', 5)
                self.minimize_to_tray = data.get('minimize_to_tray', False)
            except Exception as e:
                print(f"Ayarlar yüklenirken hata: {e}")

    def save_settings_to_file(self):
        """Mevcut ayarları settings.json dosyasına kaydet."""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'sites': self.sites_to_check,
                    'links': self.links_to_find,
                    'interval': self.check_interval,
                    'minimize_to_tray': self.minimize_to_tray
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Hata", f"Ayarlar kaydedilemedi: {e}")

    def show_initial_dialog(self):
        """Başlangıç ayarları modal penceresi."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Backlink Checker - Başlangıç Ayarları")
        dialog.geometry("500x500")
        dialog.resizable(False, False)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="🔗 Backlink Checker Ayarları", font=('Arial', 14, 'bold')).pack(pady=(0, 20))

        # Siteler
        ttk.Label(main_frame, text="Kontrol Edilecek Siteler:").pack(anchor='w')
        self.sites_text = scrolledtext.ScrolledText(main_frame, height=5)
        self.sites_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        if self.sites_to_check:
            self.sites_text.insert('1.0', '\n'.join(self.sites_to_check))
        else:
            self.sites_text.insert('1.0', 'https://example.com')

        # Linkler
        ttk.Label(main_frame, text="Aranacak Backlink'ler:").pack(anchor='w')
        self.links_text = scrolledtext.ScrolledText(main_frame, height=5)
        self.links_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        if self.links_to_find:
            self.links_text.insert('1.0', '\n'.join(self.links_to_find))
        else:
            self.links_text.insert('1.0', 'example-link.com')

        # Aralık
        interval_frame = ttk.Frame(main_frame)
        interval_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(interval_frame, text="Kontrol Aralığı (dakika):").pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value=str(self.check_interval))
        ttk.Spinbox(interval_frame, from_=1, to=1440, textvariable=self.interval_var, width=10).pack(side=tk.RIGHT)

        # Tepsi modu
        tray_frame = ttk.Frame(main_frame)
        tray_frame.pack(fill=tk.X, pady=(0, 20))
        self.tray_var = tk.BooleanVar(value=self.minimize_to_tray)
        if TRAY_AVAILABLE:
            ttk.Checkbutton(tray_frame,
                            text="Uygulama kapatıldığında sistem tepsisine küçült",
                            variable=self.tray_var).pack(anchor='w')
        else:
            ttk.Label(tray_frame,
                      text="⚠️ pystray ve Pillow kütüphaneleri gerekli",
                      foreground="orange").pack(anchor='w')

        # Butonlar
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        ttk.Button(button_frame, text="İptal", command=dialog.destroy).pack(side=tk.RIGHT, padx=(10,0))
        ttk.Button(button_frame, text="Başlat",
                   command=lambda: self.save_settings(dialog)).pack(side=tk.RIGHT)

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.transient(self.root)

    def save_settings(self, dialog):
        """Kullanıcı ayarlarını al, kaydet, ve ana pencereyi başlat."""
        sites_raw = self.sites_text.get('1.0', tk.END).strip()
        self.sites_to_check = [s.strip() for s in sites_raw.split('\n') if s.strip()]

        links_raw = self.links_text.get('1.0', tk.END).strip()
        self.links_to_find = [l.strip() for l in links_raw.split('\n') if l.strip()]

        try:
            self.check_interval = int(self.interval_var.get())
        except ValueError:
            self.check_interval = 5

        self.minimize_to_tray = self.tray_var.get() if TRAY_AVAILABLE else False

        if not self.sites_to_check or not self.links_to_find:
            messagebox.showerror("Hata", "Lütfen en az bir site ve bir link girin!")
            return

        self.save_settings_to_file()
        self.update_main_window()

        if self.minimize_to_tray:
            self.setup_tray_icon()

        dialog.destroy()

    def update_main_window(self):
        sites_text = "\n".join(self.sites_to_check)
        links_text = "\n".join(self.links_to_find)
        self.info_text.delete('1.0', tk.END)
        self.info_text.insert('1.0',
            f"🎯 Kontrol Edilecek Siteler:\n{sites_text}\n\n"
            f"🔍 Aranacak Linkler:\n{links_text}\n\n"
            f"⏰ Kontrol Aralığı: {self.check_interval} dakika\n"
            f"🔽 Sistem Tepsisi: {'Aktif' if self.minimize_to_tray else 'Pasif'}"
        )

    def create_widgets(self):
        main = ttk.Frame(self.root, padding="10")
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="🔗 Backlink Checker", font=('Arial',16,'bold')).pack(pady=(0,10))

        info_frame = ttk.LabelFrame(main, text="📋 Ayarlar", padding="10")
        info_frame.pack(fill=tk.X, pady=(0,10))
        self.info_text = scrolledtext.ScrolledText(info_frame, height=8, font=('Consolas',9))
        self.info_text.pack(fill=tk.BOTH, expand=True)

        control_frame = ttk.LabelFrame(main, text="🎮 Kontroller", padding="10")
        control_frame.pack(fill=tk.X, pady=(0,10))
        cf = ttk.Frame(control_frame)
        cf.pack(fill=tk.X)
        self.start_btn = ttk.Button(cf, text="🚀 Arkaplan Kontrol Başlat", command=self.start_background_check)
        self.start_btn.pack(side=tk.LEFT, padx=(0,10))
        self.manual_btn = ttk.Button(cf, text="🔍 Manuel Kontrol", command=self.manual_check)
        self.manual_btn.pack(side=tk.LEFT, padx=(0,10))
        self.stop_btn = ttk.Button(cf, text="⏹️ Durdur", command=self.stop_background_check, state='disabled')
        self.stop_btn.pack(side=tk.LEFT)
        self.settings_btn = ttk.Button(cf, text="⚙️ Ayarlar", command=self.show_initial_dialog)
        self.settings_btn.pack(side=tk.RIGHT)

        status_frame = ttk.LabelFrame(main, text="📊 Durum", padding="10")
        status_frame.pack(fill=tk.X, pady=(0,10))
        self.status_label = ttk.Label(status_frame, text="Durum: Beklemede", font=('Arial',10,'bold'))
        self.status_label.pack(anchor='w')
        self.last_check_label = ttk.Label(status_frame, text="Son Kontrol: -")
        self.last_check_label.pack(anchor='w')
        self.next_check_label = ttk.Label(status_frame, text="Sonraki Kontrol: -")
        self.next_check_label.pack(anchor='w')

        results_frame = ttk.LabelFrame(main, text="📈 Sonuçlar", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True)
        self.notebook = ttk.Notebook(results_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        found_frame = ttk.Frame(self.notebook)
        self.notebook.add(found_frame, text="✅ Bulundu")
        self.found_text = scrolledtext.ScrolledText(found_frame, font=('Consolas',9))
        self.found_text.pack(fill=tk.BOTH, expand=True)

        nf_frame = ttk.Frame(self.notebook)
        self.notebook.add(nf_frame, text="❌ Bulunamadı")
        self.not_found_text = scrolledtext.ScrolledText(nf_frame, font=('Consolas',9))
        self.not_found_text.pack(fill=tk.BOTH, expand=True)

        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="📝 Log")
        self.log_text = scrolledtext.ScrolledText(log_frame, font=('Consolas',9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log_message(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {message}\n")
        self.log_text.see(tk.END)

    def start_background_check(self):
        if self.background_active:
            messagebox.showwarning("Uyarı", "Arkaplan kontrol zaten çalışıyor!")
            return
        self.background_active = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.settings_btn.config(state='disabled')
        self.status_label.config(text="Durum: 🟢 Arkaplan Kontrolü Aktif")
        self.log_message("Arkaplan kontrol başlatıldı")
        self.perform_check()
        self.schedule_next_check()

    def stop_background_check(self):
        self.background_active = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.settings_btn.config(state='normal')
        self.status_label.config(text="Durum: ⏸️ Durduruldu")
        self.next_check_label.config(text="Sonraki Kontrol: -")
        self.log_message("Arkaplan kontrol durduruldu")

    def manual_check(self):
        if self.checking:
            messagebox.showwarning("Uyarı", "Kontrol zaten devam ediyor!")
            return
        self.log_message("Manuel kontrol başlatıldı")
        self.perform_check()

    def schedule_next_check(self):
        if not self.background_active:
            return
        next_time = datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=self.check_interval)
        self.next_check_label.config(text=f"Sonraki Kontrol: {next_time.strftime('%H:%M')}")
        self.root.after(self.check_interval * 60 * 1000, self.perform_check)

    def perform_check(self):
        if self.checking:
            return
        self.checking = True
        self.manual_btn.config(state='disabled')
        self.check_thread = threading.Thread(target=self._check_worker, daemon=True)
        self.check_thread.start()

    def _check_worker(self):
        try:
            self.root.after(0, lambda: self.status_label.config(text="Durum: 🔍 Kontrol Yapılıyor..."))
            found = []
            not_found = []
            total = 0
            for site in self.sites_to_check:
                self.root.after(0, lambda s=site: self.log_message(f"Kontrol ediliyor: {s}"))
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    resp = requests.get(site, headers=headers, timeout=15)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    txt = soup.get_text().lower()
                    html = str(soup).lower()
                    for link in self.links_to_find:
                        if link.lower() in txt or link.lower() in html:
                            found.append(f"✅ {link} → {site}")
                            total += 1
                            self.root.after(0, lambda l=link,s=site: self.log_message(f"BULUNDU: {l} → {s}"))
                        else:
                            not_found.append(f"❌ {link} → {site}")
                    time.sleep(1)
                except Exception as e:
                    err = f"❌ {site} → HATA: {e}"
                    not_found.append(err)
                    self.root.after(0, lambda e=err: self.log_message(e))

            self.root.after(0, lambda: self._update_results(found, not_found, total))
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"Genel hata: {e}"))
        finally:
            self.checking = False
            self.root.after(0, lambda: self.manual_btn.config(state='normal'))
            if self.background_active:
                self.root.after(0, self.schedule_next_check)

    def _update_results(self, found, not_found, total):
        self.found_text.delete('1.0', tk.END)
        self.not_found_text.delete('1.0', tk.END)

        self.found_text.insert('1.0', '\n'.join(found) if found else 'Hiçbir backlink bulunamadı.')
        self.not_found_text.insert('1.0', '\n'.join(not_found) if not_found else 'Tüm backlink\'ler bulundu!')

        now = datetime.now().strftime("%H:%M:%S")
        self.last_check_label.config(text=f"Son Kontrol: {now}")

        if total > 0:
            self.status_label.config(text=f"Durum: ✅ {total} backlink bulundu")
            self.log_message(f"Kontrol tamamlandı: {total} backlink bulundu")
            self.notebook.select(0)
        else:
            self.status_label.config(text="Durum: 🚨 BACKLINK UYARISI")
            self.log_message("⚠️ Hiçbir backlink bulunamadı!")
            messagebox.showwarning("⚠️ BACKLINK UYARISI",
                                   f"Hiçbir sitede backlink bulunamadı!\n\n"
                                   f"Siteler: {len(self.sites_to_check)}\n"
                                   f"Linkler: {len(self.links_to_find)}\n"
                                   f"Tarih: {now}")
            self.notebook.select(1)

    def setup_tray_icon(self):
        if not TRAY_AVAILABLE:
            return
        def create_icon():
            img = Image.new('RGB', (64,64), color='blue')
            d = ImageDraw.Draw(img)
            d.rectangle([10,10,54,54], fill='white')
            d.text((20,25), "BL", fill='blue')
            return img

        menu = pystray.Menu(
            pystray.MenuItem("Backlink Checker", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Göster", self.show_from_tray),
            pystray.MenuItem("Manuel Kontrol", self.manual_check_from_tray),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Çıkış", self.quit_from_tray)
        )
        self.tray_icon = pystray.Icon("backlink_checker", create_icon(), "Backlink Checker", menu)

    def show_from_tray(self, icon=None, item=None):
        self.root.after(0, self._show_window)

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def manual_check_from_tray(self, icon=None, item=None):
        self.root.after(0, self.manual_check)

    def quit_from_tray(self, icon=None, item=None):
        self.is_closing = True
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)

    def hide_to_tray(self):
        self.root.withdraw()
        if self.tray_icon and not self.tray_icon.visible:
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def on_closing(self):
        if self.minimize_to_tray and not self.is_closing:
            self.hide_to_tray()
            messagebox.showinfo("Bilgi",
                                "Uygulama sistem tepsisine küçültüldü.\n"
                                "Çıkmak için tray icon'una sağ tıklayıp 'Çıkış' seçin.")
        else:
            if self.background_active:
                if messagebox.askokcancel("Çıkış", "Arkaplan kontrol çalışıyor. Çıkmak istediğinize emin misiniz?"):
                    self.background_active = False
                    if self.tray_icon:
                        self.tray_icon.stop()
                    self.root.destroy()
            else:
                if self.tray_icon:
                    self.tray_icon.stop()
                self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

if __name__ == "__main__":
    try:
        app = BacklinkChecker()
        app.run()
    except Exception as e:
        messagebox.showerror("Hata", f"Uygulama hatası: {e}")
        sys.exit(1)
