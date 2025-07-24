import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
from bs4 import BeautifulSoup
import threading
import time
from datetime import datetime
import webbrowser
import sys
import os
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

class BacklinkChecker:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Backlink Checker v1.0")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Değişkenler
        self.checking = False
        self.background_active = False
        self.check_thread = None
        self.sites_to_check = []
        self.links_to_find = []
        self.check_interval = 5  # dakika
        self.minimize_to_tray = False
        self.tray_icon = None
        self.is_closing = False
        
        # Icon ayarla (isteğe bağlı)
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
            
        self.create_widgets()
        self.show_initial_dialog()
        
    def show_initial_dialog(self):
        """Başlangıç ayarları penceresi"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Backlink Checker - Başlangıç Ayarları")
        dialog.geometry("500x500")
        dialog.update_idletasks()
        dialog.minsize(dialog.winfo_reqwidth(), dialog.winfo_reqheight())
        dialog.resizable(False, False)
        dialog.grab_set()  # Modal pencere
        
        # Ana frame
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Başlık
        title_label = ttk.Label(main_frame, text="🔗 Backlink Checker Ayarları", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Kontrol edilecek siteler
        sites_label = ttk.Label(main_frame, text="Kontrol Edilecek Siteler:")
        sites_label.pack(anchor='w', pady=(0, 5))
        
        sites_frame = ttk.Frame(main_frame)
        sites_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.sites_text = scrolledtext.ScrolledText(sites_frame, height=5, width=60)
        self.sites_text.pack(fill=tk.BOTH, expand=True)
        self.sites_text.insert('1.0', 'https://example.com')
        
        # Aranacak linkler
        links_label = ttk.Label(main_frame, text="Aranacak Backlink'ler:")
        links_label.pack(anchor='w', pady=(0, 5))
        
        links_frame = ttk.Frame(main_frame)
        links_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.links_text = scrolledtext.ScrolledText(links_frame, height=5, width=60)
        self.links_text.pack(fill=tk.BOTH, expand=True)
        self.links_text.insert('1.0', 'example-link.com')
        
        # Kontrol aralığı
        interval_frame = ttk.Frame(main_frame)
        interval_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(interval_frame, text="Kontrol Aralığı (dakika):").pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value="5")
        interval_spin = ttk.Spinbox(interval_frame, from_=1, to=120, 
                                   textvariable=self.interval_var, width=10)
        interval_spin.pack(side=tk.RIGHT)
        
        # Minimize to tray seçeneği
        tray_frame = ttk.Frame(main_frame)
        tray_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.tray_var = tk.BooleanVar()
        if TRAY_AVAILABLE:
            tray_check = ttk.Checkbutton(tray_frame, 
                                        text="Uygulama kapatıldığında sistem tepsisine küçült", 
                                        variable=self.tray_var)
            tray_check.pack(anchor='w')
        else:
            ttk.Label(tray_frame, 
                     text="⚠️ Sistem tepsisi için pystray ve Pillow kütüphaneleri gerekli", 
                     foreground="orange").pack(anchor='w')
        
        # Butonlar
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="İptal", 
                  command=self.root.quit).pack(side=tk.RIGHT, padx=(10, 0))
        
        ttk.Button(button_frame, text="Başlat", 
                  command=lambda: self.save_settings(dialog)).pack(side=tk.RIGHT)
        
        # Pencereyi ortala
        dialog.transient(self.root)
        dialog.protocol("WM_DELETE_WINDOW", self.root.quit)
        
    def save_settings(self, dialog):
        """Ayarları kaydet ve ana pencereyi başlat"""
        # Siteleri al
        sites_raw = self.sites_text.get('1.0', tk.END).strip()
        self.sites_to_check = [site.strip() for site in sites_raw.split('\n') 
                              if site.strip()]
        
        # Linkleri al
        links_raw = self.links_text.get('1.0', tk.END).strip()
        self.links_to_find = [link.strip() for link in links_raw.split('\n') 
                             if link.strip()]
        
        # Aralığı al
        try:
            self.check_interval = int(self.interval_var.get())
        except:
            self.check_interval = 5
            
        # Tray ayarını al
        self.minimize_to_tray = self.tray_var.get() if TRAY_AVAILABLE else False
            
        if not self.sites_to_check or not self.links_to_find:
            messagebox.showerror("Hata", "Lütfen en az bir site ve bir link girin!")
            return
            
        # Ayarları ana pencereye yansıt
        self.update_main_window()
        
        # Tray icon'u başlat (eğer seçildiyse)
        if self.minimize_to_tray:
            self.setup_tray_icon()
            
        dialog.destroy()
        
    def update_main_window(self):
        """Ana penceredeki bilgileri güncelle"""
        sites_text = "\n".join(self.sites_to_check)
        links_text = "\n".join(self.links_to_find)
        
        self.info_text.delete('1.0', tk.END)
        self.info_text.insert('1.0', 
            f"🎯 Kontrol Edilecek Siteler:\n{sites_text}\n\n"
            f"🔍 Aranacak Linkler:\n{links_text}\n\n"
            f"⏰ Kontrol Aralığı: {self.check_interval} dakika\n"
            f"🔽 Sistem Tepsisi: {'Aktif' if self.minimize_to_tray else 'Pasif'}")
        
    def create_widgets(self):
        """Ana pencere widget'larını oluştur"""
        # Ana container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Başlık
        title_frame = ttk.Frame(main_container)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = ttk.Label(title_frame, text="🔗 Backlink Checker", 
                               font=('Arial', 16, 'bold'))
        title_label.pack()
        
        # Bilgi paneli
        info_frame = ttk.LabelFrame(main_container, text="📋 Ayarlar", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.info_text = scrolledtext.ScrolledText(info_frame, height=8, 
                                                  font=('Consolas', 9))
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
        # Kontrol butonları
        control_frame = ttk.LabelFrame(main_container, text="🎮 Kontroller", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 15))
        
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(button_frame, text="🚀 Arkaplan Kontrol Başlat", 
                                   command=self.start_background_check)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.manual_btn = ttk.Button(button_frame, text="🔍 Manuel Kontrol", 
                                    command=self.manual_check)
        self.manual_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(button_frame, text="⏹️ Durdur", 
                                  command=self.stop_background_check, state='disabled')
        self.stop_btn.pack(side=tk.LEFT)
        
        # Ayarlar butonu
        self.settings_btn = ttk.Button(button_frame, text="⚙️ Ayarlar", 
                                      command=self.show_initial_dialog)
        self.settings_btn.pack(side=tk.RIGHT)
        
        # Durum paneli
        status_frame = ttk.LabelFrame(main_container, text="📊 Durum", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.status_label = ttk.Label(status_frame, text="Durum: Beklemede", 
                                     font=('Arial', 10, 'bold'))
        self.status_label.pack(anchor='w')
        
        self.last_check_label = ttk.Label(status_frame, text="Son Kontrol: -")
        self.last_check_label.pack(anchor='w')
        
        self.next_check_label = ttk.Label(status_frame, text="Sonraki Kontrol: -")
        self.next_check_label.pack(anchor='w')
        
        # Sonuçlar paneli
        results_frame = ttk.LabelFrame(main_container, text="📈 Sonuçlar", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Notebook (sekmeler)
        self.notebook = ttk.Notebook(results_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Bulundu sekmesi
        found_frame = ttk.Frame(self.notebook)
        self.notebook.add(found_frame, text="✅ Bulundu")
        
        self.found_text = scrolledtext.ScrolledText(found_frame, 
                                                   font=('Consolas', 9))
        self.found_text.pack(fill=tk.BOTH, expand=True)
        
        # Bulunamadı sekmesi
        not_found_frame = ttk.Frame(self.notebook)
        self.notebook.add(not_found_frame, text="❌ Bulunamadı")
        
        self.not_found_text = scrolledtext.ScrolledText(not_found_frame, 
                                                       font=('Consolas', 9))
        self.not_found_text.pack(fill=tk.BOTH, expand=True)
        
        # Log sekmesi
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="📝 Log")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, 
                                                 font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
    def log_message(self, message):
        """Log mesajı ekle"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
    def start_background_check(self):
        """Arkaplan kontrolünü başlat"""
        if self.background_active:
            messagebox.showwarning("Uyarı", "Arkaplan kontrol zaten çalışıyor!")
            return
            
        self.background_active = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.settings_btn.config(state='disabled')
        
        self.status_label.config(text="Durum: 🟢 Arkaplan Kontrolü Aktif")
        self.log_message("Arkaplan kontrol başlatıldı")
        
        # İlk kontrol hemen yap
        self.perform_check()
        
        # Periyodik kontrol başlat
        self.schedule_next_check()
        
    def stop_background_check(self):
        """Arkaplan kontrolünü durdur"""
        self.background_active = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.settings_btn.config(state='normal')
        
        self.status_label.config(text="Durum: ⏸️ Durduruldu")
        self.next_check_label.config(text="Sonraki Kontrol: -")
        self.log_message("Arkaplan kontrol durduruldu")
        
    def manual_check(self):
        """Manuel kontrol yap"""
        if self.checking:
            messagebox.showwarning("Uyarı", "Kontrol zaten devam ediyor!")
            return
            
        self.log_message("Manuel kontrol başlatıldı")
        self.perform_check()
        
    def schedule_next_check(self):
        """Sonraki kontrolü planla"""
        if not self.background_active:
            return
            
        next_time = datetime.now()
        next_time = next_time.replace(second=0, microsecond=0)
        next_time = next_time.replace(minute=next_time.minute + self.check_interval)
        
        self.next_check_label.config(text=f"Sonraki Kontrol: {next_time.strftime('%H:%M')}")
        
        # Timer ayarla
        self.root.after(self.check_interval * 60 * 1000, self.perform_check)
        
    def perform_check(self):
        """Backlink kontrolünü gerçekleştir"""
        if self.checking:
            return
            
        self.checking = True
        self.manual_btn.config(state='disabled')
        
        # Thread'de çalıştır (UI donmasın)
        self.check_thread = threading.Thread(target=self._check_worker)
        self.check_thread.daemon = True
        self.check_thread.start()
        
    def _check_worker(self):
        """Kontrol işlemini yapan worker thread"""
        try:
            self.root.after(0, lambda: self.status_label.config(text="Durum: 🔍 Kontrol Yapılıyor..."))
            
            found_results = []
            not_found_results = []
            total_found = 0
            
            for site in self.sites_to_check:
                self.root.after(0, lambda s=site: self.log_message(f"Kontrol ediliyor: {s}"))
                
                try:
                    # Site içeriğini al
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    response = requests.get(site, headers=headers, timeout=15)
                    response.raise_for_status()
                    
                    # HTML parse et
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_text = soup.get_text().lower()
                    page_html = str(soup).lower()
                    
                    # Her link için kontrol et
                    for link in self.links_to_find:
                        if link.lower() in page_text or link.lower() in page_html:
                            found_results.append(f"✅ {link} → {site}")
                            total_found += 1
                            self.root.after(0, lambda l=link, s=site: 
                                          self.log_message(f"BULUNDU: {l} → {s}"))
                        else:
                            not_found_results.append(f"❌ {link} → {site}")
                            
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    error_msg = f"❌ {site} → HATA: {str(e)}"
                    not_found_results.append(error_msg)
                    self.root.after(0, lambda e=error_msg: self.log_message(e))
                    
            # Sonuçları güncelle
            self.root.after(0, lambda: self._update_results(found_results, not_found_results, total_found))
            
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"Genel hata: {str(e)}"))
        finally:
            self.checking = False
            self.root.after(0, lambda: self.manual_btn.config(state='normal'))
            
            # Sonraki kontrolü planla (eğer arkaplan aktifse)
            if self.background_active:
                self.root.after(0, self.schedule_next_check)
                
    def _update_results(self, found_results, not_found_results, total_found):
        """Sonuçları UI'da güncelle"""
        # Bulundu sekmesi
        self.found_text.delete('1.0', tk.END)
        if found_results:
            self.found_text.insert('1.0', '\n'.join(found_results))
        else:
            self.found_text.insert('1.0', 'Hiçbir backlink bulunamadı.')
            
        # Bulunamadı sekmesi
        self.not_found_text.delete('1.0', tk.END)
        if not_found_results:
            self.not_found_text.insert('1.0', '\n'.join(not_found_results))
        else:
            self.not_found_text.insert('1.0', 'Tüm backlink\'ler bulundu!')
            
        # Durum güncelle
        now = datetime.now().strftime("%H:%M:%S")
        self.last_check_label.config(text=f"Son Kontrol: {now}")
        
        if total_found > 0:
            self.status_label.config(text=f"Durum: ✅ {total_found} backlink bulundu")
            self.log_message(f"Kontrol tamamlandı: {total_found} backlink bulundu")
        else:
            self.status_label.config(text="Durum: 🚨 UYARI: Backlink bulunamadı!")
            self.log_message("⚠️ UYARI: Hiçbir backlink bulunamadı!")
            
            # Uyarı popup'ı göster
            messagebox.showwarning("⚠️ BACKLINK UYARISI", 
                                 f"Hiçbir sitede backlink bulunamadı!\n\n"
                                 f"Kontrol edilen siteler: {len(self.sites_to_check)}\n"
                                 f"Aranan linkler: {len(self.links_to_find)}\n"
                                 f"Tarih: {now}")
                                 
        # Notebook'u bulundu sekmesine getir
        if total_found > 0:
            self.notebook.select(0)  # Bulundu sekmesi
        else:
            self.notebook.select(1)  # Bulunamadı sekmesi
    
    def setup_tray_icon(self):
        """Sistem tepsisi icon'unu ayarla"""
        if not TRAY_AVAILABLE:
            return
            
        # Basit bir icon oluştur
        def create_icon():
            image = Image.new('RGB', (64, 64), color='blue')
            draw = ImageDraw.Draw(image)
            draw.rectangle([10, 10, 54, 54], fill='white')
            draw.text((20, 25), "BL", fill='blue')
            return image
        
        # Menu oluştur
        menu = pystray.Menu(
            pystray.MenuItem("Backlink Checker", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Göster", self.show_from_tray),
            pystray.MenuItem("Manuel Kontrol", self.manual_check_from_tray),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Çıkış", self.quit_from_tray)
        )
        
        # Tray icon oluştur
        self.tray_icon = pystray.Icon(
            "backlink_checker",
            create_icon(),
            "Backlink Checker",
            menu
        )
    
    def show_from_tray(self, icon=None, item=None):
        """Tray'den pencereyi göster"""
        self.root.after(0, self._show_window)
    
    def _show_window(self):
        """Pencereyi göster (main thread'de)"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def manual_check_from_tray(self, icon=None, item=None):
        """Tray'den manuel kontrol"""
        self.root.after(0, self.manual_check)
    
    def quit_from_tray(self, icon=None, item=None):
        """Tray'den çıkış"""
        self.is_closing = True
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)
    
    def hide_to_tray(self):
        """Pencereyi tray'e gizle"""
        self.root.withdraw()
        if self.tray_icon and not self.tray_icon.visible:
            # Tray icon'u ayrı thread'de çalıştır
            tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            tray_thread.start()
            
    def run(self):
        """Uygulamayı çalıştır"""
        # Pencere kapatma olayı
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Ana döngü
        self.root.mainloop()
        
    def on_closing(self):
        """Pencere kapatılırken"""
        if self.minimize_to_tray and not self.is_closing:
            # Tray'e küçült
            self.hide_to_tray()
            messagebox.showinfo("Bilgi", 
                              "Uygulama sistem tepsisine küçültüldü.\n"
                              "Çıkmak için tray icon'una sağ tıklayıp 'Çıkış' seçin.")
        else:
            # Normal çıkış
            if self.background_active:
                if messagebox.askokcancel("Çıkış", 
                                        "Arkaplan kontrol çalışıyor. Çıkmak istediğinizden emin misiniz?"):
                    self.background_active = False
                    if self.tray_icon:
                        self.tray_icon.stop()
                    self.root.destroy()
            else:
                if self.tray_icon:
                    self.tray_icon.stop()
                self.root.destroy()

if __name__ == "__main__":
    try:
        app = BacklinkChecker()
        app.run()
    except Exception as e:
        messagebox.showerror("Hata", f"Uygulama hatası: {str(e)}")
        sys.exit(1)