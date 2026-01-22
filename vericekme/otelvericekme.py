"""
Google Maps Otel Yorumları Scraper - Akıllı Otomatik Versiyon (CHROME)
Bir TXT dosyasından otel isimlerini okur, her otel için yorumları toplar,
en sonda CSV dosyalarında birleştirir.
"""

# pip install selenium webdriver-manager pandas

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions
import time
import pandas as pd
from pathlib import Path

import tempfile
import os
import random

# ---- Global sayaç: yorumu olan otel sayısı ----
YORUMLU_OTEL_SAYACI = 0
YORUMLU_OTEL_HEDEF = 300  # 300 otele ulaşınca duracağız


def _try_accept_google_consent(driver, timeout=4):
    """
    Google 'Before you continue' / çerez onayı çıkarsa kapatmayı dener.
    Çıkmazsa sessizce devam eder.
    """
    try:
        # Bazen consent ekranı iframe içinde oluyor
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe")
        for fr in iframes[:8]:
            try:
                driver.switch_to.frame(fr)
                btns = driver.find_elements(
                    By.XPATH,
                    "//button//*[contains(., 'Kabul') or contains(., 'Accept') or contains(., 'I agree') "
                    "or contains(., 'Tümünü kabul') or contains(., 'Accept all')]/ancestor::button"
                )
                if btns:
                    driver.execute_script("arguments[0].click();", btns[0])
                    time.sleep(0.6)
                    driver.switch_to.default_content()
                    return True
                driver.switch_to.default_content()
            except:
                driver.switch_to.default_content()
                continue

        # iframe yoksa direkt sayfa üzerinde dene
        candidates = driver.find_elements(
            By.XPATH,
            "//button[contains(., 'Kabul') or contains(., 'Accept') or contains(., 'I agree') "
            "or contains(., 'Tümünü kabul') or contains(., 'Accept all')]"
        )
        if candidates:
            driver.execute_script("arguments[0].click();", candidates[0])
            time.sleep(0.6)
            return True

    except:
        pass

    return False


def google_maps_yorum_cek_otomatik(otel_adi, max_yorum=50):
    """
    Google Maps'ten otel yorumlarını tamamen otomatik çeker
    """
    global YORUMLU_OTEL_SAYACI, YORUMLU_OTEL_HEDEF

    print(f"\n🔍 '{otel_adi}' için otomatik yorum çekme başlıyor...\n")

    # --- CHROME ayarları (Gerekli iyileştirmeler: temiz profil + automation izi azalt) ---
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--lang=tr-TR")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # A) Temiz profil klasörü (her çalıştırmada yeni)
    profile_dir = os.path.join(
        tempfile.gettempdir(),
        f"gmaps_selenium_profile_{int(time.time())}"
    )
    chrome_options.add_argument(f"--user-data-dir={profile_dir}")

    # (ÖNEMLİ) --guest + --user-data-dir aynı anda sıkıntı çıkarabiliyor.
    # Bu yüzden guest'i kaldırdım. Temiz user-data-dir zaten yeterli.
    # chrome_options.add_argument("--guest")

    # Automation izlerini azalt (çok kritik değil ama kapanma/engelleme ihtimalini düşürür)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Basit UA döndürme (bazen fayda ediyor)
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

    # Headless istersen aç:
    # chrome_options.add_argument("--headless=new")

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=chrome_options
    )

    # navigator.webdriver izini azalt
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """
            },
        )
    except:
        pass

    yorumlar = []

    try:
        # B) Önce Maps ana sayfasını aç, sonra arama yap
        print("🗺️ 0. Adım: Google Maps ana sayfası açılıyor...")
        driver.get("https://www.google.com/maps?hl=tr")
        time.sleep(2)

        # Consent/çerez ekranı varsa kapatmayı dene
        _try_accept_google_consent(driver, timeout=4)

        time.sleep(1)

        # 1. Google Maps'te ara
        print("📍 1. Adım: Google Maps'te otel aranıyor...")
        arama_url = f"https://www.google.com/maps/search/{otel_adi.replace(' ', '+')}?hl=tr"
        driver.get(arama_url)
        time.sleep(3)

        # 2. Sayfa tipini kontrol et (tek sonuç mu, arama sonuçları mı?)
        print("🏨 2. Adım: Sayfa tipi kontrol ediliyor...")
        time.sleep(2)

        yorumlar_butonu_var = False
        arama_sonuclari_var = False

        try:
            arama_sonuclari = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
            if len(arama_sonuclari) > 0:
                arama_sonuclari_var = True
        except:
            pass

        try:
            driver.find_element(
                By.XPATH,
                "//button[contains(., 'Yorum') or contains(., 'İnceleme') or contains(@aria-label, 'Yorum')]"
            )
            yorumlar_butonu_var = True
        except:
            pass

        if yorumlar_butonu_var and not arama_sonuclari_var:
            print("   ✅ Direkt otel sayfasına gidildi (tek sonuç)")
        elif arama_sonuclari_var:
            print("   📋 Arama sonuçları sayfasında - İlk sonuca tıklanıyor...")
            try:
                ilk_sonuc = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.hfpxzc"))
                )
                ilk_sonuc.click()
                time.sleep(3)
                print("   ✅ Otel sayfası açıldı!")
            except Exception as e:
                print(f"   ❌ İlk sonuca tıklanamadı: {e}")
        else:
            print("   ⚠️ Sayfa durumu belirsiz, devam ediliyor...")

        # 3. Popup'ları kapat (devre dışı)
        print("🚫 3. Adım: Popup kontrolü atlanıyor...")
        time.sleep(1)

        # 4. Yorumlar butonunu bul ve tıkla
        print("💬 4. Adım: Yorumlar sekmesine gidiliyor...")
        try:
            yorum_butonu_bulundu = False

            # Yöntem 1: "Yorumlar" / "İnceleme" yazısı
            try:
                yorumlar_buton = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH,
                        "//button[contains(., 'Yorum') or contains(., 'İnceleme')]"))
                )
                yorumlar_buton.click()
                yorum_butonu_bulundu = True
                print("   ✅ Yorumlar butonuna tıklandı! (Yöntem 1)")
            except Exception as e:
                print(f"   ⚠️ Yöntem 1 başarısız: {e}")

            # Yöntem 2: Tab sistemi
            if not yorum_butonu_bulundu:
                try:
                    tab_butonlari = driver.find_elements(By.CSS_SELECTOR, "button.hh2c6")
                    for tab in tab_butonlari:
                        if "Yorum" in tab.text or "yorum" in tab.text:
                            tab.click()
                            yorum_butonu_bulundu = True
                            print("   ✅ Yorumlar sekmesine tıklandı! (Yöntem 2)")
                            break
                except Exception as e:
                    print(f"   ⚠️ Yöntem 2 başarısız: {e}")

            # Yöntem 3: aria-label
            if not yorum_butonu_bulundu:
                try:
                    yorum_btn = driver.find_element(
                        By.XPATH,
                        "//button[contains(@aria-label, 'Yorum') or contains(@aria-label, 'İnceleme')]"
                    )
                    yorum_btn.click()
                    yorum_butonu_bulundu = True
                    print("   ✅ Yorumlar butonuna tıklandı! (Yöntem 3)")
                except Exception as e:
                    print(f"   ⚠️ Yöntem 3 başarısız: {e}")

            if not yorum_butonu_bulundu:
                print("   ⚠️  Yorumlar butonu bulunamadı, yine de devam ediliyor...")

            time.sleep(3)

        except Exception as e:
            print(f"   ⚠️  Yorumlar butonuna tıklanamadı: {e}")
            print("   ℹ️  Yine de devam ediliyor...")

        # 5. Scrollable alanı bul
        print("📜 5. Adım: Scroll alanı bulunuyor...")
        scrollable_div = None

        # Önce doğrulama metnine tıkla
        try:
            dogrulama_text = driver.find_element(
                By.XPATH,
                "//div[contains(text(), 'Yorumlar doğrulanmamıştır')]"
            )
            driver.execute_script("arguments[0].click();", dogrulama_text)
            print("   ✅ 'Yorumlar doğrulanmamıştır' metnine tıklandı")
            time.sleep(1)
        except:
            print("   ℹ️  Doğrulama metni bulunamadı, devam ediliyor...")

        scroll_yontemleri = [
            ("div.m6QErb.DxyBCb.kA9KIf.dS8AEf", "CSS", "DxyBCb kA9KIf dS8AEf (DOĞRU)"),
            ("//div[contains(@class, 'DxyBCb') and contains(@class, 'kA9KIf')]", "XPATH", "DxyBCb ve kA9KIf"),
            ("div.m6QErb.DxyBCb", "CSS", "m6QErb DxyBCb"),
            ("//div[@role='main']//div[contains(@class, 'm6QErb')]", "XPATH", "main içindeki m6QErb"),
            ("div.m6QErb", "CSS", "sadece m6QErb"),
        ]

        for selector, method, name in scroll_yontemleri:
            try:
                if method == "CSS":
                    test_elem = driver.find_element(By.CSS_SELECTOR, selector)
                else:
                    test_elem = driver.find_element(By.XPATH, selector)

                scroll_height = driver.execute_script("return arguments[0].scrollHeight", test_elem)
                client_height = driver.execute_script("return arguments[0].clientHeight", test_elem)

                if scroll_height > client_height:
                    scrollable_div = test_elem
                    print(f"   ✅ Scroll alanı bulundu: {name} (scrollHeight: {scroll_height})")
                    break
                else:
                    print(f"   ⚠️ '{name}' scrollable değil (h:{scroll_height})")
            except:
                print(f"   ⚠️ '{name}' bulunamadı")
                continue

        if not scrollable_div:
            print("   ❌ Scroll alanı bulunamadı!")
            time.sleep(2)
            driver.quit()
            return pd.DataFrame()

        # 6. Yorumların yüklenmesini bekle
        print("⏳ 6. Adım: Yorumlar yükleniyor...")

        for _ in range(5):
            driver.execute_script('arguments[0].scrollTop += 300', scrollable_div)
            time.sleep(0.3)

        driver.execute_script('arguments[0].scrollTop = 0', scrollable_div)
        time.sleep(1)

        # 7. Yorum seçiciyi belirle
        print("🔎 7. Adım: Yorum elemanları aranıyor...")
        YORUM_SECICI = None

        secici_listesi = [
            ("div.jftiEf", "jftiEf class"),
            ("div[data-review-id]", "data-review-id"),
            ("div.fontBodyMedium[aria-label]", "fontBodyMedium"),
        ]

        for secici, isim in secici_listesi:
            test_yorumlar = driver.find_elements(By.CSS_SELECTOR, secici)
            if len(test_yorumlar) > 0:
                print(f"   ✅ '{isim}' ile {len(test_yorumlar)} yorum bulundu!")
                YORUM_SECICI = secici
                break

        if not YORUM_SECICI:
            print("   ❌ Yorum elemanları bulunamadı!")
            time.sleep(2)
            driver.quit()
            return pd.DataFrame()

        # 8. Yorumları çek
        print(f"\n📊 8. Adım: {max_yorum} yorum çekiliyor...\n")

        def butonu_genislet():
            try:
                daha_fazla_butonlar = driver.find_elements(
                    By.XPATH,
                    "//button[contains(@aria-label, 'Daha fazla') or contains(., 'Daha fazla')]"
                )
                for buton in daha_fazla_butonlar[:10]:
                    try:
                        driver.execute_script("arguments[0].click();", buton)
                        time.sleep(0.1)
                    except:
                        pass
            except:
                pass

        eski_yorum_sayisi = 0
        dongu_sayaci = 0
        max_dongu = 50

        print("   🔄 Scroll başlıyor... (wheel + hızlı)")

        # küçük helper: scrollTop’u sona basıp gerçekten değişti mi kontrol
        def _fast_scroll_burst():
            # 1 burst içinde arka arkaya hızlı scroll
            for _ in range(12):  # hızlı hızlı
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollTop + 1200;", scrollable_div)

            # bazen set scrollTop yutuluyor -> bir de wheel dispatch et
            try:
                driver.execute_script("""
                    const el = arguments[0];
                    el.dispatchEvent(new WheelEvent('wheel', {deltaY: 2000, bubbles: true}));
                    el.dispatchEvent(new WheelEvent('wheel', {deltaY: 2000, bubbles: true}));
                """, scrollable_div)
            except:
                pass

        # “artmıyor” durumunda hemen kırma; 3 deneme şansı ver
        stagnation_hits = 0

        while dongu_sayaci < max_dongu:
            # hızlı burst
            _fast_scroll_burst()

            # UI’nin nefes alması lazım, yoksa yeni batch hiç gelmiyor.
            time.sleep(0.25)

            butonu_genislet()
            time.sleep(0.25)

            yorum_elemanlari = driver.find_elements(By.CSS_SELECTOR, YORUM_SECICI)
            cur = len(yorum_elemanlari)

            if cur >= max_yorum:
                print("   ✅ Hedef yorum sayısına ulaşıldı!")
                break

            if cur == eski_yorum_sayisi:
                stagnation_hits += 1
                if stagnation_hits >= 3:
                    print("   ⚠️  3 denemede de yeni yorum gelmedi, duruyor.")
                    break
            else:
                stagnation_hits = 0
                eski_yorum_sayisi = cur

            dongu_sayaci += 1

            if dongu_sayaci % 3 == 0:
                print(f"   📝 Çekilen: {cur} yorum...")


        print(f"\n✅ Toplam {len(yorum_elemanlari)} yorum bulundu!")
        print("📝 Yorumlar işleniyor...\n")

        # 9. Yorumları parse et - SADECE YORUM METNİ
        for elem in yorum_elemanlari[:max_yorum]:
            try:
                yorum_metni = ""
                try:
                    yorum_metni = elem.find_element(By.CSS_SELECTOR, "span.wiI7pd").text
                except:
                    try:
                        yorum_metni = elem.find_element(By.CSS_SELECTOR, "div.MyEned span.wiI7pd").text
                    except:
                        yorum_metni = ""

                if yorum_metni:
                    yorumlar.append({"otel_adi": otel_adi, "yorum": yorum_metni})

            except Exception:
                continue

        print(f"✅ {len(yorumlar)} yorum başarıyla işlendi!\n")

        # Sayaç
        if len(yorumlar) > 0:
            YORUMLU_OTEL_SAYACI += 1
            print(f"🔢 Şu ana kadar yorumu olan otel sayısı: {YORUMLU_OTEL_SAYACI}")
            if YORUMLU_OTEL_SAYACI >= YORUMLU_OTEL_HEDEF:
                print(f"🚫 Hedefe ulaşıldı ({YORUMLU_OTEL_HEDEF} otel).")

    except Exception as e:
        print(f"❌ Hata oluştu: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("🔒 Tarayıcı kapatılıyor...")
        time.sleep(1)
        driver.quit()

        # Temiz profil klasörünü silmeyi dene (kilitli olursa sorun etme)
        try:
            import shutil
            shutil.rmtree(profile_dir, ignore_errors=True)
        except:
            pass

    return pd.DataFrame(yorumlar)


# Diğer fonksiyonların aynı kalsın:
def tum_otelleri_txtten_cek(
    all_hotels_txt=r"C:\Users\Acer\Desktop\mucahit\nlp\nlpdersiproje\otelk.txt",
    filtered_txt=r"C:\Users\Acer\Desktop\mucahit\nlp\nlpdersiproje\otelk_filtered.txt",
    max_yorum=50,
    output_csv=r"C:\Users\Acer\Desktop\mucahit\nlp\nlpdersiproje\tum_oteller_yorumlar3.csv"
):
    global YORUMLU_OTEL_SAYACI, YORUMLU_OTEL_HEDEF

    all_hotels_path = Path(all_hotels_txt)
    filtered_path = Path(filtered_txt)

    if not all_hotels_path.exists():
        print(f"❌ Tüm oteller TXT dosyası bulunamadı: {all_hotels_path}")
        return

    if not filtered_path.exists():
        print(f"❌ Filtre TXT dosyası bulunamadı: {filtered_path}")
        return

    with open(filtered_path, "r", encoding="utf-8") as f:
        filtered_lines = {line.strip() for line in f.readlines() if line.strip()}

    all_dfs = []
    YORUMLU_OTEL_SAYACI = 0

    with open(all_hotels_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line in filtered_lines:
                continue

            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 0:
                continue

            otel_adi = parts[0]

            if len(parts) > 1:
                il = parts[-1]
                if il == "Adana":
                    continue

            if YORUMLU_OTEL_SAYACI >= YORUMLU_OTEL_HEDEF:
                print(f"✅ Zaten {YORUMLU_OTEL_HEDEF} otelin yorumu alındı, döngü sonlandırılıyor.")
                break

            df_otel = google_maps_yorum_cek_otomatik(otel_adi=otel_adi, max_yorum=max_yorum)

            if not df_otel.empty:
                all_dfs.append(df_otel)

            if YORUMLU_OTEL_SAYACI >= YORUMLU_OTEL_HEDEF:
                print(f"✅ {YORUMLU_OTEL_HEDEF} otelin yorumu alındı, döngü durduruluyor.")
                break

    if not all_dfs:
        print("❌ Hiç otelden veri gelmedi.")
        return

    combined_df = pd.concat(all_dfs, ignore_index=True)

    output_csv = Path(output_csv)
    base_dir = output_csv.parent
    base_stem = output_csv.stem

    csv_tum_yorumlar = base_dir / f"{base_stem}_tum_yorumlar3.csv"
    combined_df.to_csv(csv_tum_yorumlar, index=False, encoding="utf-8-sig")

    unique_hotels = combined_df["otel_adi"].dropna().unique()
    df_hotels = pd.DataFrame({"otel_adi": unique_hotels})
    csv_otel_listesi = base_dir / f"{base_stem}_otel_listesi.csv"
    df_hotels.to_csv(csv_otel_listesi, index=False, encoding="utf-8-sig")

    df_counts = combined_df.groupby("otel_adi").size().reset_index(name="yorum_sayisi")
    csv_otel_sayim = base_dir / f"{base_stem}_otel_yorum_sayilari.csv"
    df_counts.to_csv(csv_otel_sayim, index=False, encoding="utf-8-sig")

    print("\n✅ TOPLU İŞLEM BİTTİ")
    print(f"   Yorumu olan otel sayısı: {YORUMLU_OTEL_SAYACI}")
    print(f"   Toplam yorum sayısı: {len(combined_df)}")
    print(f"   CSV 1 (tüm yorumlar):    {csv_tum_yorumlar}")
    print(f"   CSV 2 (otel listesi):    {csv_otel_listesi}")
    print(f"   CSV 3 (yorum sayıları):  {csv_otel_sayim}")

    return combined_df


if __name__ == "__main__":
    print(r"""
    ╔═══════════════════════════════════════════════════════╗
    ║   Google Maps Otel Yorumları Scraper (CHROME)        ║
    ║   TXT'den Otel Listesi - Toplu Çekim                 ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    tum_otelleri_txtten_cek()
