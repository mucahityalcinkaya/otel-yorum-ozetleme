# -*- coding: utf-8 -*-
"""
Otel Yorum Analizi Pipeline + OLLAMA
Çıktı formatı: aspect_summary (pozitif/negatif/notr + neden1/neden2) + Özet

Kullanım:
    Terminal 1: python api_server.py
    Terminal 2: ollama serve (arka planda çalışıyor olabilir)
    Terminal 3: python otel_pipeline_with_ollama.py
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions
import requests
import time
import tempfile
import os
import random
import re
import json
from datetime import datetime
from collections import defaultdict, Counter

# Ollama modülünü import et
try:
    from ollama_ozet import generate_summary, check_ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    print("⚠️  ollama_ozet.py bulunamadı! Özet üretilmeyecek.")
    OLLAMA_AVAILABLE = False

# ============================================
# AYARLAR
# ============================================
API_URL = "http://localhost:8000"

# Aspect isimleri (index 0-24)
ASPECT_NAMES = [
    "temizlik", "konum", "oda_kalitesi", "uyku_yatak_kalitesi", "gurultu",
    "personel", "fiyat_performans", "yemek_kalitesi", "yemek_cesitliligi", "havuz",
    "spa_hamam", "plaj", "cocuk_dostu", "wifi", "banyo_tuvalet",
    "klima_isitma", "resepsiyon", "otopark", "guvenlik", "manzara",
    "oda_servisi", "fitness_spor", "mini_bar", "balkon_teras", "aktivite_zenginligi"
]

# Neden kodları
NEDEN_MAP = {
    1: "yokluk",
    2: "kalite", 
    3: "erisim",
    4: "servis",
    5: "fiyat",
    6: "olumlu_kalite",
    7: "notr_bilgi"
}

def decode_class_id(class_id):
    """
    Class ID'den duygu ve neden çıkar
    class_id = 1 + (duygu-1)*7 + (neden-1)
    
    Returns: (duygu, neden) veya (None, None) if class_id == 0
    duygu: 1=olumsuz, 2=notr, 3=olumlu
    neden: 1-7
    """
    if class_id == 0:
        return None, None
    
    # Tersine hesapla
    # class_id - 1 = (duygu-1)*7 + (neden-1)
    idx = class_id - 1
    duygu = (idx // 7) + 1  # 1, 2, 3
    neden = (idx % 7) + 1   # 1-7
    
    return duygu, neden

def get_top_nedenler(neden_list, top_n=2):
    """En sık geçen nedenleri döndür"""
    if not neden_list:
        return [None] * top_n
    
    counter = Counter(neden_list)
    most_common = counter.most_common(top_n)
    
    result = []
    for i in range(top_n):
        if i < len(most_common):
            neden_code = most_common[i][0]
            result.append(NEDEN_MAP.get(neden_code))
        else:
            result.append(None)
    
    return result

def build_aspect_summary(predictions_list):
    """
    Tüm yorumların tahminlerinden aspect_summary oluştur
    
    predictions_list: [[0,2,16,0,...], [0,0,16,0,...], ...] 
                      Her biri 25 elemanlı dizi
    
    Returns: aspect_summary dict
    """
    # Her aspect için istatistikleri topla
    aspect_stats = {}
    
    for aspect_idx in range(25):
        aspect_name = ASPECT_NAMES[aspect_idx]
        
        pozitif_count = 0
        negatif_count = 0
        notr_count = 0
        
        poz_nedenler = []
        neg_nedenler = []
        
        # Tüm yorumları tara
        for preds in predictions_list:
            class_id = preds[aspect_idx]
            
            if class_id == 0:
                continue
            
            duygu, neden = decode_class_id(class_id)
            
            if duygu == 3:  # olumlu
                pozitif_count += 1
                poz_nedenler.append(neden)
            elif duygu == 1:  # olumsuz
                negatif_count += 1
                neg_nedenler.append(neden)
            elif duygu == 2:  # notr
                notr_count += 1
        
        # En az 1 mention varsa ekle
        total = pozitif_count + negatif_count + notr_count
        if total > 0:
            poz_top = get_top_nedenler(poz_nedenler, 2)
            neg_top = get_top_nedenler(neg_nedenler, 2)
            
            aspect_stats[aspect_name] = {
                "pozitif": pozitif_count,
                "negatif": negatif_count,
                "notr": notr_count,
                "poz_neden1": poz_top[0],
                "poz_neden2": poz_top[1],
                "neg_neden1": neg_top[0],
                "neg_neden2": neg_top[1]
            }
    
    return aspect_stats

# ============================================
# TEMİZLEME
# ============================================
emoji_pattern = re.compile("[" u"\U0001F600-\U0001F64F" u"\U0001F300-\U0001F5FF" 
    u"\U0001F680-\U0001F6FF" u"\U0001F1E0-\U0001F1FF" u"\U00002702-\U000027B0" 
    u"\U000024C2-\U0001F251" "]+", flags=re.UNICODE)
html_pattern = re.compile(r"<.*?>", flags=re.DOTALL)
url_pattern = re.compile(r"(https?://\S+|www\.\S+)", flags=re.IGNORECASE)
email_pattern = re.compile(r"\S+@\S+")
phone_pattern = re.compile(r"(\+?\d[\d\s\-]{8,}\d)")
symbol_pattern = re.compile(r"[^0-9a-zA-ZçğıöşüÇĞİÖŞÜ\s\.\,\!\?\;\:\(\)\'\"\-]")
multi_punct = re.compile(r"([!?.,;:])\1+")
repeat_char = re.compile(r"(\S)\1{2,}")

def clean_text(text):
    if not text: return ""
    t = str(text).lower()
    t = html_pattern.sub(" ", t)
    t = emoji_pattern.sub(" ", t)
    t = url_pattern.sub(" ", t)
    t = email_pattern.sub(" ", t)
    t = phone_pattern.sub(" ", t)
    t = symbol_pattern.sub(" ", t)
    t = repeat_char.sub(r"\1\1", t)
    t = multi_punct.sub(r"\1", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

# ============================================
# SCRAPER
# ============================================
def _try_accept_consent(driver):
    try:
        for fr in driver.find_elements(By.CSS_SELECTOR, "iframe")[:5]:
            try:
                driver.switch_to.frame(fr)
                btns = driver.find_elements(By.XPATH, "//button//*[contains(., 'Kabul')]/ancestor::button")
                if btns:
                    driver.execute_script("arguments[0].click();", btns[0])
                    driver.switch_to.default_content()
                    return
                driver.switch_to.default_content()
            except:
                driver.switch_to.default_content()
        for btn in driver.find_elements(By.XPATH, "//button[contains(., 'Kabul')]")[:2]:
            driver.execute_script("arguments[0].click();", btn)
            return
    except:
        pass

def select_en_yeni(driver):
    print("🔄 'En yeni' seçiliyor...")
    try:
        for sel in ["//button[contains(@aria-label, 'En alakalı')]", "//button[contains(@class, 'HQzyZ')]"]:
            try:
                btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, sel)))
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1)
                break
            except:
                continue
        
        for sel in ["//div[contains(text(), 'En yeni')]"]:
            try:
                btn = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, sel)))
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(2)
                print("   ✅ 'En yeni' seçildi!")
                return True
            except:
                continue
        
        for item in driver.find_elements(By.CSS_SELECTOR, "div.fontBodyLarge"):
            if "En yeni" in item.text:
                driver.execute_script("arguments[0].click();", item)
                time.sleep(2)
                return True
    except:
        pass
    return False

def scrape_reviews(otel_adi, max_yorum=50):
    print(f"\n{'='*60}")
    print(f"🔍 '{otel_adi}' yorumları çekiliyor...")
    print(f"{'='*60}\n")

    opts = ChromeOptions()
    opts.add_argument("--lang=tr-TR")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    
    profile = os.path.join(tempfile.gettempdir(), f"gm_{int(time.time())}")
    opts.add_argument(f"--user-data-dir={profile}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=opts)
    
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"})
    except:
        pass

    yorumlar = []

    try:
        driver.get("https://www.google.com/maps?hl=tr")
        time.sleep(2)
        _try_accept_consent(driver)

        driver.get(f"https://www.google.com/maps/search/{otel_adi.replace(' ', '+')}?hl=tr")
        time.sleep(3)

        try:
            results = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
            if results:
                results[0].click()
                time.sleep(3)
        except:
            pass

        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Yorum') or contains(., 'İnceleme')]")))
            btn.click()
            time.sleep(3)
        except:
            pass

        select_en_yeni(driver)

        scroll_div = None
        for sel in ["div.m6QErb.DxyBCb.kA9KIf.dS8AEf", "div.m6QErb.DxyBCb", "div.m6QErb"]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if driver.execute_script("return arguments[0].scrollHeight > arguments[0].clientHeight", el):
                    scroll_div = el
                    break
            except:
                continue

        if not scroll_div:
            print("❌ Scroll alanı bulunamadı")
            driver.quit()
            return []

        SECICI = None
        for s in ["div.jftiEf", "div[data-review-id]"]:
            if driver.find_elements(By.CSS_SELECTOR, s):
                SECICI = s
                break

        if not SECICI:
            print("❌ Yorum bulunamadı")
            driver.quit()
            return []

        print(f"📊 {max_yorum} yorum çekiliyor...")
        
        prev = 0
        stag = 0
        for _ in range(30):
            for _ in range(10):
                driver.execute_script("arguments[0].scrollTop += 1000;", scroll_div)
            time.sleep(0.5)
            
            for btn in driver.find_elements(By.XPATH, "//button[contains(., 'Daha fazla')]")[:5]:
                try: driver.execute_script("arguments[0].click();", btn)
                except: pass
            
            elems = driver.find_elements(By.CSS_SELECTOR, SECICI)
            cur = len(elems)
            
            if cur >= max_yorum:
                break
            if cur == prev:
                stag += 1
                if stag >= 3:
                    break
            else:
                stag = 0
                prev = cur

        for elem in driver.find_elements(By.CSS_SELECTOR, SECICI)[:max_yorum]:
            try:
                txt = elem.find_element(By.CSS_SELECTOR, "span.wiI7pd").text
                if txt and txt.strip():
                    yorumlar.append(txt.strip())
            except:
                pass

        print(f"✅ {len(yorumlar)} yorum çekildi!")

    except Exception as e:
        print(f"❌ Hata: {e}")
    finally:
        driver.quit()
        try:
            import shutil
            shutil.rmtree(profile, ignore_errors=True)
        except:
            pass

    return yorumlar

# ============================================
# API
# ============================================
def check_api():
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        return r.status_code == 200
    except:
        return False

def predict_batch(texts):
    try:
        r = requests.post(f"{API_URL}/predict_batch", json={"texts": texts}, timeout=120)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"❌ API hatası: {e}")
    return None

# ============================================
# MAIN
# ============================================
def main():
    print(r"""
    ╔══════════════════════════════════════════════════════════════╗
    ║   Otel Yorum Analizi + OLLAMA                                ║
    ║   BERT: Aspect extraction | Ollama: Özet üretimi             ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # API kontrol
    print("🔌 BERT API kontrol ediliyor...")
    if not check_api():
        print("❌ API çalışmıyor! Önce: python api_server.py")
        return
    print("✅ BERT API OK!")
    
    # Ollama kontrol
    if OLLAMA_AVAILABLE:
        print("🔌 Ollama kontrol ediliyor...")
        if check_ollama():
            print("✅ Ollama OK!\n")
            ollama_ok = True
        else:
            print("⚠️  Ollama çalışmıyor! Özet üretilmeyecek.\n")
            ollama_ok = False
    else:
        print("⚠️  Ollama modülü yok! Özet üretilmeyecek.\n")
        ollama_ok = False
    
    # Input
    otel_adi = input("🏨 Otel adı: ").strip()
    if not otel_adi:
        print("❌ Boş olamaz!")
        return
    
    # Dosya adları
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in otel_adi).replace(" ", "_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Scrape
    yorumlar_raw = scrape_reviews(otel_adi, max_yorum=50)
    if not yorumlar_raw:
        print("❌ Yorum bulunamadı!")
        return
    
    # 2. Temizle
    print("\n🧹 Temizleniyor...")
    yorumlar = [clean_text(y) for y in yorumlar_raw]
    yorumlar = [y for y in yorumlar if y and len(y) >= 10]
    print(f"   Ham: {len(yorumlar_raw)} | Temiz: {len(yorumlar)}")
    
    if not yorumlar:
        print("❌ Temizleme sonrası yorum kalmadı!")
        return
    
    # 3. API'ye gönder
    print(f"\n🚀 API'ye gönderiliyor ({len(yorumlar)} yorum)...")
    start = time.time()
    predictions = predict_batch(yorumlar)
    elapsed = time.time() - start
    
    if not predictions:
        print("❌ API yanıt vermedi!")
        return
    
    print(f"✅ Tahminler alındı! ({elapsed:.2f} sn)")
    
    # 4. Aspect Summary oluştur
    print("\n📊 Aspect summary oluşturuluyor...")
    aspect_summary = build_aspect_summary(predictions)
    
    # 5. Ollama ile özet üret
    llama_result = None
    if ollama_ok:
        llama_result = generate_summary(otel_adi, aspect_summary)
    
    # 6. Final JSON
    output_json = f"{safe}_analiz_{ts}.json"
    
    final_output = {
        "otel_adi": otel_adi,
        "yorum_sayisi": len(yorumlar),
        "aspect_summary": aspect_summary,
        "status": "success"
    }
    
    if llama_result and llama_result.get("success"):
        final_output["aspect_text"] = llama_result["aspect_text"]
        final_output["ozet"] = llama_result["summary"]
    
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
    
    # 7. Ekrana yazdır
    print(f"\n{'='*70}")
    print("✅ ANALİZ TAMAMLANDI!")
    print(f"{'='*70}")
    print(f"\n🏨 Otel: {otel_adi}")
    print(f"📊 Yorum sayısı: {len(yorumlar)}")
    print(f"⏱️  Süre: {elapsed:.2f} sn")
    
    print(f"\n📌 ASPECT SUMMARY:")
    print("-" * 70)
    
    # Sıralı göster (toplam mention sayısına göre)
    sorted_aspects = sorted(
        aspect_summary.items(), 
        key=lambda x: x[1]["pozitif"] + x[1]["negatif"] + x[1]["notr"],
        reverse=True
    )
    
    for aspect, stats in sorted_aspects:
        total = stats["pozitif"] + stats["negatif"] + stats["notr"]
        print(f"\n  📍 {aspect.upper()}")
        print(f"     Pozitif: {stats['pozitif']} | Negatif: {stats['negatif']} | Nötr: {stats['notr']}")
        print(f"     Poz nedenler: {stats['poz_neden1']}, {stats['poz_neden2']}")
        print(f"     Neg nedenler: {stats['neg_neden1']}, {stats['neg_neden2']}")
    
    # Ollama özeti varsa göster
    if llama_result and llama_result.get("success"):
        print(f"\n{'='*70}")
        print("📋 ASPECT DEĞERLENDİRMELERİ:")
        print(f"{'='*70}")
        print(llama_result["aspect_text"])
        
        print(f"\n{'='*70}")
        print("✍️  OTEL ÖZETİ (OLLAMA):")
        print(f"{'='*70}")
        print(llama_result["summary"])
        print(f"{'='*70}")
    
    print(f"\n📁 DOSYA: {output_json}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()