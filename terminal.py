import tkinter as tk
import threading
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

class YoneticiAsistanAI:
    def __init__(self, root):
        self.root = root
        self.root.title("YÖNETİCİ ASISTAN AI - Terminal")
        
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = int(screen_w / 2)
        win_h = int(screen_h * 0.85)
        pos_x = screen_w - win_w
        pos_y = int((screen_h - win_h) / 2)
        self.root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.root.configure(bg="#0a0e27")

        # Free API - JinaAI (API key gerekli değil)
        self.API_URL = "https://api.jina.ai/v1/chat/completions"
        self.API_KEY = "jina_YOUR_API_KEY"  # Alternatif: Ollama kullan
        
        # Selenium Driver ve Yaddaş Değişkenleri
        self.driver = None
        self.found_inputs = []
        self.found_elements_5 = []
        self.copied_url = ""
        self.is_bruteforcing = False
        self.command_history = []

        self.setup_ui()

    def setup_ui(self):
        title = tk.Label(self.root, text="⚙️ YÖNETİCİ ASISTAN AI - TERMINAL", 
                        fg="#00ff88", bg="#0a0e27", font=("Consolas", 13, "bold"))
        title.pack(pady=8)

        self.console = tk.Text(self.root, bg="#0f1419", fg="#00ff88", 
                              insertbackground="white", font=("Consolas", 9), 
                              state=tk.DISABLED, relief=tk.FLAT, wrap=tk.WORD)
        self.console.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        input_frame = tk.Frame(self.root, bg="#0a0e27")
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        lbl = tk.Label(input_frame, text="AI > ", fg="#00ff88", bg="#0a0e27", 
                      font=("Consolas", 11, "bold"))
        lbl.pack(side=tk.LEFT)

        self.entry = tk.Entry(input_frame, bg="#1a2332", fg="#ffffff", 
                             insertbackground="#00ff88", font=("Consolas", 11))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self.parse_command())

        welcome = (
            "╔════════════════════════════════════════════════════╗\n"
            "║  🤖 YÖNETİCİ ASISTAN AI v2.0                       ║\n"
            "║  Hoş geldiniz! Her komut için AI rehberlik edecek  ║\n"
            "║  'help' yazarak komutları görebilirsiniz            ║\n"
            "╚════════════════════════════════════════════════════╝"
        )
        self.log_to_console(welcome)

    def log_to_console(self, text):
        self.console.config(state=tk.NORMAL)
        self.console.insert(tk.END, f"{text}\n")
        self.console.see(tk.END)
        self.console.config(state=tk.DISABLED)

    def ask_ai_free(self, question):
        """Ücretsiz AI API kullanarak soru sorar"""
        try:
            # OpenRouter Free API (API key gerekli değil bazı modellerde)
            url = "https://openrouter.ai/api/v1/chat/completions"
            
            headers = {
                "Content-Type": "application/json",
            }
            
            data = {
                "model": "mistral-7b-instruct",
                "messages": [
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
            
            # Fallback: Lokal yanıt ver
            return self.get_local_ai_response(question)
                
        except Exception as e:
            return self.get_local_ai_response(question)

    def get_local_ai_response(self, question):
        """Lokal AI yanıtı - internet olmadan çalışır"""
        question_lower = question.lower()
        
        responses = {
            "1-": "🌐 Web Tarayıcı Açıyorsunuz!\n📍 Komut: 1-<URL>\n✅ Örnek: 1-google.com\n💡 İpucu: Otomatik https:// ekler",
            "1": "🔗 Tüm Linkleri Listele\n📋 Sayfadaki bütün href linklerini gösterir\n✅ Koşul: Önce bir sayfa açmalısınız (1-url)",
            "2": "❌ Tarayıcı Kapatma\n🛑 Açık olan Chrome penceresi kapatılır\n✅ İşlemi sıfırlar ve yeni başlangıç sağlar",
            "3": "🔍 Input Alanları Bul\n📝 Formun tüm input ve textarea alanlarını listeler\n✅ Yazı yazmanız için hazırlık",
            "4": "📊 Tüm Inputlar\n📋 Detaylı input bilgisi: ad, id, tip\n✅ Hangisine yazacağınızı seçin",
            "5": "🎯 Sayfa Öğelerini Tara\n🔎 p, h1, h2, img, button, span vb. tüm öğeler\n✅ Sayfanın tam yapısını görün",
            "-find": "⭐ Öğeyi Vurgula\n💚 5 saniye yeşil çerçeve gösterir\n✅ Komut: <numara>-find (Örnek: 3-find)",
            "-write": "✏️ Input'a Yazı Yaz\n📝 Komut: <numara>-write(\"metin\")\n✅ Örnek: 1-write(\"deneme@email.com\")",
            "search-copy": "📋 URL'i Kopyala\n💾 Mevcut sayfanın URL'i yaddaşa kopyalanır",
            "search=": "🔄 Yeni Sayta Git\n🌐 Komut: search=<yeni_url>\n✅ Örnek: search=github.com",
            "search-demp": "📊 Site Bilgisi Al\n🏷️ Domain, başlık, açıklama otomatik çekilir",
            "help": "📖 Komut Rehberi\n✅ Tüm komutları tabloyla gösterir"
        }
        
        for keyword, response in responses.items():
            if keyword in question_lower:
                return response
        
        return "🤖 Komut Rehberi: 'help' yazıp tüm komutları görebilirsiniz.\n💡 Yardım: <komut>-help yazarak detay alabilirsiniz."

    def highlight_element(self, element):
        """Elementə səhifədə fokuslanır və 5 saniyəlik yaşıl çərçivə əlavə edir."""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            original_style = element.get_attribute("style") or ""
            highlight_style = "border: 4px solid #00FF00 !important; background-color: rgba(0, 255, 0, 0.2) !important;"
            self.driver.execute_script(f"arguments[0].setAttribute('style', '{original_style} {highlight_style}');", element)
            
            def reset_style():
                time.sleep(5)
                try:
                    self.driver.execute_script(f"arguments[0].setAttribute('style', '{original_style}');", element)
                except Exception:
                    pass

            threading.Thread(target=reset_style, daemon=True).start()
        except Exception as e:
            self.log_to_console(f"[❌] Element vurğulanamadı: {str(e)}")

    def parse_command(self):
        cmd = self.entry.get().strip()
        self.entry.delete(0, tk.END)
        if not cmd:
            return

        self.log_to_console(f"\n👤 Siz: {cmd}")
        self.command_history.append(cmd)
        threading.Thread(target=self.execute_command, args=(cmd,), daemon=True).start()

    def execute_command(self, cmd):
        # Her komut için AI tarafından rehberlik verilir
        self.log_to_console("\n🤖 AI Asistan:")
        
        if cmd.lower() == "help":
            help_text = (
                "╔════════════════════════════════════════════════╗\n"
                "║          📖 KOMUT LİSTESİ                      ║\n"
                "╠════════════════════════════════════════════════╣\n"
                "║ 1-url                  : Sayt aç              ║\n"
                "║ 1                      : Linkleri listele     ║\n"
                "║ 2                      : Tarayıcı kapat       ║\n"
                "║ 3                      : Input alanlarını bul ║\n"
                "║ 4                      : Tüm inputları göster ║\n"
                "║ 5                      : Sayfadaki tüm öğeler ║\n"
                "║ <no>-find              : Öğeyi vurgula (5s)   ║\n"
                "║ <no>-write(\"text\")    : Input'a yazı yaz    ║\n"
                "║ search-copy            : URL'i kopyala        ║\n"
                "║ search=<yeni_url>      : Yeni sayta git       ║\n"
                "║ search-demp            : Site bilgisi al      ║\n"
                "╚════════════════════════════════════════════════╝"
            )
            ai_response = self.get_local_ai_response("help")
            self.log_to_console(f"{ai_response}\n")
            self.log_to_console(help_text)

        elif cmd.startswith("1-") and not cmd.endswith("-find"):
            raw_target = cmd[2:].strip()
            url_part = raw_target.split("-")[0].strip()
            if not url_part.startswith(("http://", "https://")):
                url_part = "https://" + url_part

            ai_response = self.get_local_ai_response("1-")
            self.log_to_console(f"{ai_response}\n")
            self.log_to_console(f"[📱] Tarayıcı açılıyor: {url_part}")

            try:
                if not self.driver:
                    chrome_options = Options()
                    chrome_options.add_argument("--window-position=0,0")
                    chrome_options.add_argument("--window-size=960,1080")
                    self.driver = webdriver.Chrome(options=chrome_options)
                
                self.driver.get(url_part)
                self.log_to_console("[✅] Sayfa başarıyla açıldı.")
            except Exception as e:
                self.log_to_console(f"[❌] Sayfa açılamadı: {str(e)}")

        elif cmd == "1":
            ai_response = self.get_local_ai_response("1")
            self.log_to_console(f"{ai_response}\n")
            
            if not self.driver:
                self.log_to_console("[❌] Aktif tarayıcı yok!")
                return
            links = self.driver.find_elements(By.TAG_NAME, "a")
            unique_links = set(l.get_attribute("href") for l in links if l.get_attribute("href"))
            self.log_to_console(f"\n[🔗] Linkler ({len(unique_links)} adet):")
            for idx, link in enumerate(unique_links, 1):
                self.log_to_console(f"  {idx}. {link}")

        elif cmd == "2":
            ai_response = self.get_local_ai_response("2")
            self.log_to_console(f"{ai_response}\n")
            
            if self.driver:
                self.is_bruteforcing = False
                self.driver.quit()
                self.driver = None
                self.log_to_console("[✅] Tarayıcı kapatıldı.")
            else:
                self.log_to_console("[ℹ️] Kapatılacak tarayıcı yok.")

        elif cmd in ["3", "4"]:
            ai_response = self.get_local_ai_response("3")
            self.log_to_console(f"{ai_response}\n")
            
            if not self.driver:
                self.log_to_console("[❌] Aktif tarayıcı yok!")
                return
            self.log_to_console("[🔍] Input alanları aranıyor...")
            self.found_inputs = self.driver.find_elements(By.XPATH, "//input | //textarea")
            if not self.found_inputs:
                self.log_to_console("[❌] Input bulunamadı.")
            else:
                self.log_to_console(f"\n[✅] Input'lar ({len(self.found_inputs)} adet):")
                for idx, inp in enumerate(self.found_inputs, 1):
                    inp_name = inp.get_attribute("name") or inp.get_attribute("id") or inp.get_attribute("placeholder") or "Adsız"
                    inp_type = inp.get_attribute("type") or "textarea"
                    self.log_to_console(f"  [{idx}] {inp_name} | Tip: {inp_type}")

        elif cmd == "5":
            ai_response = self.get_local_ai_response("5")
            self.log_to_console(f"{ai_response}\n")
            
            if not self.driver:
                self.log_to_console("[❌] Aktif tarayıcı yok!")
                return
            self.log_to_console("[🔍] Sayfa taranıyor...")
            self.found_elements_5 = self.driver.find_elements(By.XPATH, 
                "//input | //textarea | //img | //p | //h1 | //h2 | //h3 | //span | //button | //a")
            self.found_elements_5 = [e for e in self.found_elements_5 if e.is_displayed()]
            
            self.log_to_console(f"\n[✅] Öğeler ({len(self.found_elements_5)} adet):")
            for idx, el in enumerate(self.found_elements_5, 1):
                tag = el.tag_name
                txt = el.text[:20].strip() if el.text else ""
                desc = txt or el.get_attribute("placeholder") or "..."
                self.log_to_console(f"  [{idx}] <{tag}> {desc}")

        elif cmd.endswith("-find"):
            ai_response = self.get_local_ai_response("-find")
            self.log_to_console(f"{ai_response}\n")
            
            try:
                num = int(cmd.split("-find")[0].strip()) - 1
                target_list = self.found_elements_5 if self.found_elements_5 else self.found_inputs
                
                if not target_list:
                    self.log_to_console("[❌] Önce 3, 4 veya 5 yazınız!")
                    return
                
                if 0 <= num < len(target_list):
                    element = target_list[num]
                    self.highlight_element(element)
                    self.log_to_console(f"[✅] [{num+1}] nömrəli element 5 saniye vurgulandı!")
                else:
                    self.log_to_console("[❌] Geçersiz numara!")
            except Exception as e:
                self.log_to_console(f"[❌] Hata: {str(e)}")

        elif cmd == "search-copy":
            ai_response = self.get_local_ai_response("search-copy")
            self.log_to_console(f"{ai_response}\n")
            
            if self.driver:
                self.copied_url = self.driver.current_url
                self.log_to_console(f"[✅] Kopyalandı: {self.copied_url}")
            else:
                self.log_to_console("[❌] Aktif sayfa yok.")

        elif cmd.startswith("search="):
            ai_response = self.get_local_ai_response("search=")
            self.log_to_console(f"{ai_response}\n")
            
            new_url = cmd.split("search=")[1].strip()
            if not new_url.startswith(("http://", "https://")):
                new_url = "https://" + new_url
            if self.driver:
                self.driver.get(new_url)
                self.log_to_console(f"[✅] {new_url} adresine gidiliyor...")
            else:
                self.log_to_console("[❌] Önce 1-url yazınız.")

        elif cmd == "search-demp":
            ai_response = self.get_local_ai_response("search-demp")
            self.log_to_console(f"{ai_response}\n")
            
            if self.driver:
                current_url = self.driver.current_url
                domain = current_url.split("//")[-1].split("/")[0]
                
                try:
                    title = self.driver.title
                    meta_desc = self.driver.execute_script(
                        "return document.querySelector('meta[name=\"description\"]')?.content || 'Açıklama bulunamadı'"
                    )
                except:
                    title = "Bilinmiyor"
                    meta_desc = "Bilinmiyor"
                
                demp_info = f"""[📊] SITE DEMOGRAFI:
  Domain: {domain}
  URL: {current_url}
  Başlık: {title}
  Açıklama: {meta_desc}"""
                self.log_to_console(demp_info)
            else:
                self.log_to_console("[❌] Aktif tarayıcı yok.")

        elif "-write(" in cmd and cmd.endswith(")"):
            ai_response = self.get_local_ai_response("-write")
            self.log_to_console(f"{ai_response}\n")
            
            if not self.driver or not self.found_inputs:
                self.log_to_console("[❌] Önce 3 veya 4 yazınız!")
                return
            try:
                parts = cmd.split("-write(")
                input_idx = int(parts[0].strip()) - 1
                val_param = parts[1][:-1].strip()

                if input_idx < 0 or input_idx >= len(self.found_inputs):
                    self.log_to_console("[❌] Geçersiz numara!")
                    return

                target_input = self.found_inputs[input_idx]
                self.highlight_element(target_input)

                text_to_write = val_param.strip('"').strip("'")
                target_input.clear()
                target_input.send_keys(text_to_write)
                self.log_to_console(f"[✅] [{input_idx+1}] nömrəli input'a yazıldı: {text_to_write}")

            except Exception as e:
                self.log_to_console(f"[❌] Hata: {str(e)}")

        else:
            ai_response = self.get_local_ai_response(cmd)
            self.log_to_console(f"{ai_response}")

if __name__ == "__main__":
    root = tk.Tk()
    app = YoneticiAsistanAI(root)
    root.mainloop()
