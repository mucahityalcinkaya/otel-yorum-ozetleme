# -*- coding: utf-8 -*-
"""
Ollama Özet Modülü
Aspect summary'den özet üretir

Kullanım:
    from ollama_ozet import generate_summary
    ozet = generate_summary(otel_adi, aspect_summary)
"""

import requests

# ============================================
# AYARLAR
# ============================================
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "otel-ozet"

ASPECT_DISPLAY_NAMES = {
    "temizlik": "Temizlik",
    "konum": "Konum",
    "oda_kalitesi": "Oda kalitesi",
    "uyku_yatak_kalitesi": "Uyku ve yatak konforu",
    "gurultu": "Sessizlik / gürültü durumu",
    "personel": "Personel",
    "fiyat_performans": "Fiyat-performans",
    "yemek_kalitesi": "Yemek kalitesi",
    "yemek_cesitliligi": "Yemek çeşitliliği",
    "havuz": "Havuz",
    "spa_hamam": "Spa / hamam",
    "plaj": "Plaj",
    "cocuk_dostu": "Çocuk dostu",
    "wifi": "Wi-Fi",
    "banyo_tuvalet": "Banyo ve tuvalet",
    "klima_isitma": "Klima / ısıtma",
    "resepsiyon": "Resepsiyon",
    "otopark": "Otopark",
    "guvenlik": "Güvenlik",
    "manzara": "Manzara",
    "oda_servisi": "Oda servisi",
    "fitness_spor": "Fitness / spor",
    "mini_bar": "Mini bar",
    "balkon_teras": "Balkon / teras",
    "aktivite_zenginligi": "Aktivite olanakları"
}

def check_ollama():
    """Ollama çalışıyor mu kontrol et"""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return r.status_code == 200
    except:
        return False

def aspect_summary_to_text(aspect_summary):
    """Aspect summary'yi Llama için formatla"""
    lines = []
    for aspect_key, stats in aspect_summary.items():
        aspect_name = ASPECT_DISPLAY_NAMES.get(aspect_key, aspect_key)
        total = stats["pozitif"] + stats["negatif"] + stats["notr"]
        if total == 0:
            continue
        
        poz = stats["pozitif"]
        neg = stats["negatif"]
        
        if poz > neg * 2 and poz >= 5:
            genel = "Çok olumlu"
        elif poz > neg * 1.5:
            genel = "Ağırlıklı olumlu"
        elif neg > poz * 2 and neg >= 5:
            genel = "Çok olumsuz"
        elif neg > poz * 1.5:
            genel = "Ağırlıklı olumsuz"
        else:
            genel = "Karışık"
        
        ovulen = []
        if stats["poz_neden1"]:
            ovulen.append(stats["poz_neden1"])
        if stats["poz_neden2"] and stats["poz_neden2"] != stats["poz_neden1"]:
            ovulen.append(stats["poz_neden2"])
        
        sikayet = []
        if stats["neg_neden1"]:
            sikayet.append(stats["neg_neden1"])
        if stats["neg_neden2"] and stats["neg_neden2"] != stats["neg_neden1"]:
            sikayet.append(stats["neg_neden2"])
        
        parts = [f"- {aspect_name}: {genel}"]
        if ovulen and sikayet:
            parts.append(f"(övülen: {', '.join(ovulen)} | şikayet: {', '.join(sikayet)})")
        elif ovulen:
            parts.append(f"(övülen: {', '.join(ovulen)})")
        elif sikayet:
            parts.append(f"(şikayet: {', '.join(sikayet)})")
        
        lines.append(" ".join(parts))
    
    return "\n".join(lines)

def generate_summary(otel_adi, aspect_summary):
    """
    Ollama ile özet üret
    
    Args:
        otel_adi: Otel adı
        aspect_summary: build_aspect_summary() fonksiyonundan dönen dict
    
    Returns:
        dict: {
            "aspect_text": str,  # Formatlanmış aspect metni
            "summary": str,      # Üretilen özet
            "success": bool      # Başarılı mı?
        }
        veya None (hata durumunda)
    """
    
    if not check_ollama():
        print("⚠️  Ollama çalışmıyor!")
        return None
    
    # Aspect text oluştur
    aspect_text = aspect_summary_to_text(aspect_summary)
    
    # System prompt
    system_prompt = """Sen otel yorumlarından çıkarılan aspect değerlendirmelerine göre, otel için Türkçe genel bir özet yazan bir asistansın.
Kurallar:
- Sayısal değerleri (pozitif/negatif sayıları vb.) aynen yazma, sayısız/niteliksel anlat.
- Güçlü yönleri ve geliştirilmesi gereken alanları dengeli şekilde belirt.
- 3-4 paragraf, akıcı ve doğal bir dil kullan.
- Gereksiz tekrar yapma."""
    
    user_prompt = f"""Otel: {otel_adi}

Aspect değerlendirmeleri:
{aspect_text}

Aşağıdaki aspect değerlendirmelerine göre otel için genel bir özet yaz.
Not: Sayısal değerleri metne taşımadan, niteliksel ifadelerle anlat."""
    
    try:
        print("✍️  Ollama ile özet üretiliyor...")
        
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 1024,
                    "repeat_penalty": 1.08
                }
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            summary = result["message"]["content"].strip()
            print(f"✅ Özet üretildi! ({len(summary)} karakter)")
            
            return {
                "aspect_text": aspect_text,
                "summary": summary,
                "success": True
            }
        else:
            print(f"❌ Ollama API hatası: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Özet üretme hatası: {e}")
        return None


if __name__ == "__main__":
    # Test amaçlı
    print("Ollama Özet Modülü")
    print("=" * 50)
    
    if check_ollama():
        print(f"✅ Ollama çalışıyor! Model: {OLLAMA_MODEL}")
    else:
        print("❌ Ollama çalışmıyor!")