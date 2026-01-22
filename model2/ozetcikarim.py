"""
Otel Özetleri Üretimi - DeepSeek API
Paralel batch işleme ile 560 otel için özet oluştur
"""

import json
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

# ==============================================================================
# AYARLAR
# ==============================================================================
BASE_DIR = r"C:\Users\Acer\Desktop\mucahit\nlp\nlpdersiproje\model2"
INPUT_JSON = os.path.join(BASE_DIR, "oteller_compact.json")
OUT_JSON = os.path.join(BASE_DIR, "oteller_ozet.json")
OUT_LOG = os.path.join(BASE_DIR, "ozet_hatalar.log")

MAX_WORKERS = 40  # Paralel işlem sayısı (DeepSeek için 10-40 arası)

# DeepSeek API
client = OpenAI(
    api_key="api-key",  # DeepSeek API key
    base_url="https://api.deepseek.com"
)

# ==============================================================================
# SYSTEM PROMPT
# ==============================================================================
SYSTEM_PROMPT = """Sen kullanıcılar için otel hakkında bilgi veren tarafsız bir yardımcısın.

Sana bir otelin aspect analizi verilecek. Her aspect için:
- Kaç pozitif yorum var
- Kaç negatif yorum var  
- En sık övülen/şikayet edilen neden

GÖREV:
Bu istatistiklere bakarak otelin genel durumunu özetle.

ÖNEMLİ KURALLAR:
1. Sayı ve istatistik KULLANMA (örn: "24 pozitif", "%80" gibi ifadeler yasak)
2. Niteliksel değerlendirme yap (örn: "Personel çok övülüyor", "Temizlik mükemmel")
3. İnsan gibi, profesyonel ama anlaşılır yaz
4. 200-300 kelime arası
5. 4 paragraf yapısı:
   - Genel değerlendirme (2-3 cümle)
   - En beğenilen yönler (açıklayıcı, detaylı)
   - Sorunlu alanlar (açıklayıcı, detaylı)

FORMAT: Düz metin (JSON değil, başlık yok, madde işaretleri var)
ÜsLup: Profesyonel, analitik, yapıcı, samimi

ÖRNEK ÇIKTI:
Otel genel olarak konuklarından yüksek memnuniyet alıyor. Hizmet kalitesi ve temizlik standartları öne çıkan güçlü yönler. Konum avantajı da misafirlerce takdir ediliyor.

Personelin tutumu otelin en parlak noktası. Çalışanlar ilgili, yardımsever ve güler yüzlü bulunuyor. Temizlik standartları mükemmel seviyede, konuklar odaların ve ortak alanların temizliğinden son derece memnun. Yemek kalitesi de genel olarak beğeniliyor, lezzetli ve çeşitli menü sunuluyor.

WiFi hizmeti en büyük şikayet konusu. Bağlantı yavaş ve sık sık kopuyor, bu özellikle iş seyahatinde olan konukları rahatsız ediyor. Otopark kapasitesi yetersiz bulunuyor. Fiyat-performans dengesi konusunda eleştiriler var.


"""

# ==============================================================================
# PROMPT OLUŞTURUCU
# ==============================================================================
def create_prompt(otel):
    """Her otel için API'ye gönderilecek prompt oluştur"""
    
    prompt = f"""Otel Adı: {otel['otel_adi']}
Analiz Edilen Yorum Sayısı: {otel['yorum_sayisi']}

ASPECT DEĞERLENDİRMELERİ:

"""
    
    # Aspect'leri pozitif/negatif dengesine göre sırala
    aspects = otel['aspect_summary']
    
    # Her aspect için durum belirle
    aspect_list = []
    for aspect_name, stats in aspects.items():
        poz = stats['pozitif']
        neg = stats['negatif']
        notr = stats['notr']
        total = poz + neg + notr
        
        if total == 0:
            continue
        
        # Durum belirle (daha detaylı)
        poz_oran = poz / total if total > 0 else 0
        neg_oran = neg / total if total > 0 else 0
        
        if poz_oran >= 0.8:
            durum = "Çok olumlu"
        elif poz_oran >= 0.6:
            durum = "Ağırlıklı olumlu"
        elif poz_oran >= 0.4:
            durum = "Karışık"
        elif neg_oran >= 0.6:
            durum = "Ağırlıklı olumsuz"
        else:
            durum = "Çok olumsuz"
        
        aspect_list.append({
            'name': aspect_name,
            'durum': durum,
            'poz': poz,
            'neg': neg,
            'poz_neden': stats['poz_neden'],
            'neg_neden': stats['neg_neden'],
            'net': poz - neg
        })
    
    # Net skoruna göre sırala (en iyi → en kötü)
    aspect_list.sort(key=lambda x: x['net'], reverse=True)
    
    # Prompt'a ekle
    for asp in aspect_list:
        line = f"{asp['name']}: {asp['durum']}"
        
        details = []
        if asp['poz_neden']:
            details.append(f"övülen {asp['poz_neden']}")
        if asp['neg_neden']:
            details.append(f"şikayet {asp['neg_neden']}")
        
        if details:
            line += f" ({', '.join(details)})"
        
        prompt += line + "\n"
    
    prompt += "\nLütfen yukarıdaki analizi kullanarak bu otelin genel durumunu özetle."
    
    return prompt

# ==============================================================================
# TEK OTEL İŞLEME
# ==============================================================================
def process_otel(otel):
    """Bir otel için özet oluştur"""
    
    otel_id = otel['otel_id']
    otel_adi = otel['otel_adi']
    
    try:
        # Prompt oluştur
        prompt = create_prompt(otel)
        
        # DeepSeek API çağrısı
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Özet al
        ozet = response.choices[0].message.content.strip()
        
        # Sonuç
        result = {
            "otel_id": otel_id,
            "otel_adi": otel_adi,
            "yorum_sayisi": otel['yorum_sayisi'],
            "aspect_summary": otel['aspect_summary'],
            "ozet": ozet,
            "status": "success"
        }
        
        return result, None
        
    except Exception as e:
        # Hata durumu
        error_msg = f"Otel ID {otel_id} ({otel_adi}): {str(e)}"
        
        result = {
            "otel_id": otel_id,
            "otel_adi": otel_adi,
            "yorum_sayisi": otel['yorum_sayisi'],
            "aspect_summary": otel['aspect_summary'],
            "ozet": None,
            "status": "error",
            "error": str(e)
        }
        
        return result, error_msg

# ==============================================================================
# ANA PROGRAM
# ==============================================================================
if __name__ == "__main__":
    print("="*70)
    print("OTEL ÖZETLERİ ÜRETİMİ - DeepSeek API")
    print("="*70)
    
    # Klasör kontrolü
    if not os.path.exists(BASE_DIR):
        print(f"❌ HATA: {BASE_DIR} klasörü bulunamadı!")
        exit(1)
    
    # Otel verilerini yükle
    print(f"\nVeri yükleniyor: {INPUT_JSON}")
    
    if not os.path.exists(INPUT_JSON):
        print(f"❌ HATA: {INPUT_JSON} dosyası bulunamadı!")
        exit(1)
    
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        oteller = json.load(f)
    
    print(f"✅ {len(oteller)} otel yüklendi")
    
    # Log dosyasını temizle
    with open(OUT_LOG, "w", encoding="utf-8") as f:
        f.write("OTEL ÖZET ÜRETİMİ HATA LOGU\n")
        f.write("="*70 + "\n\n")
    
    # İstatistikler
    total_count = 0
    success_count = 0
    error_count = 0
    start_time = time.time()
    
    results = []
    
    print(f"\nParalel işlem başlıyor (MAX_WORKERS={MAX_WORKERS})...")
    print(f"Tahmin edilen süre: ~{len(oteller) * 5 / MAX_WORKERS / 60:.1f} dakika")
    print("="*70)
    
    # Paralel işleme
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Tüm otelleri gönder
        futures = {executor.submit(process_otel, otel): otel for otel in oteller}
        
        # Sonuçları topla
        for future in as_completed(futures):
            otel = futures[future]
            result, error = future.result()
            
            total_count += 1
            
            if error:
                # Hata logla
                error_count += 1
                print(f"❌ [{total_count}/{len(oteller)}] {otel['otel_adi'][:40]}... - HATA")
                
                with open(OUT_LOG, "a", encoding="utf-8") as f:
                    f.write(f"{error}\n")
            else:
                # Başarılı
                success_count += 1
                print(f"✅ [{total_count}/{len(oteller)}] {otel['otel_adi'][:40]}...")
            
            # Sonucu kaydet
            results.append(result)
            
            # Her 20 otelde bir ara kayıt
            if total_count % 20 == 0:
                with open(OUT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                elapsed = time.time() - start_time
                remaining = (len(oteller) - total_count) * (elapsed / total_count)
                print(f"💾 Ara kayıt yapıldı ({total_count}/{len(oteller)}) - Kalan süre: ~{remaining/60:.1f} dk")
    
    # Final kayıt
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    duration = time.time() - start_time
    
    # Özet
    print("\n" + "="*70)
    print("İŞLEM TAMAMLANDI!")
    print("="*70)
    print(f"Toplam otel: {len(oteller)}")
    print(f"Başarılı: {success_count}")
    print(f"Hatalı: {error_count}")
    print(f"Başarı oranı: %{(success_count/len(oteller))*100:.1f}")
    print(f"Süre: {duration:.2f} saniye ({duration/60:.1f} dakika)")
    print(f"\n✅ Sonuçlar: {OUT_JSON}")
    print(f"⚠️  Hatalar: {OUT_LOG}")
    print("="*70)
    
    # İlk 2 başarılı örnek göster
    successful_results = [r for r in results if r['status'] == 'success']
    
    if successful_results:
        print("\nİLK 2 BAŞARILI ÖRNEK:")
        print("="*70)
        
        for i, result in enumerate(successful_results[:2], 1):
            print(f"\n{i}. OTEL: {result['otel_adi']}")
            print(f"Yorum sayısı: {result['yorum_sayisi']}")
            print(f"\nÖZET:")
            print("-"*70)
            print(result['ozet'])
            print("-"*70)
    
    print("\n🎉 TÜM İŞLEM TAMAMLANDI!")
    print(f"📁 Sonuç dosyası: {OUT_JSON}")