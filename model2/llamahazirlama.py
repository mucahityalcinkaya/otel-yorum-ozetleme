import os
import json
import random
from pathlib import Path

# =========================
# Ayarlar (senin yolların)
# =========================
INPUT_JSON = r"C:\Users\Acer\Desktop\mucahit\nlp\nlpdersiproje\model2\oteller_ozet.json"
OUT_DIR   = r"C:\Users\Acer\Desktop\mucahit\nlp\nlpdersiproje\model2\verimodel2"

TRAIN_NAME = "train.jsonl"
VALID_NAME = "valid.jsonl"

VALID_RATIO = 0.10      # %10 valid
SEED = 42

# =========================
# Llama-3.1 için prompt
# =========================
SYSTEM_PROMPT = (
    "Sen otel yorumlarından çıkarılan aspect değerlendirmelerine göre, otel için Türkçe genel bir özet yazan bir asistansın.\n"
    "Kurallar:\n"
    "- Sayısal değerleri (pozitif/negatif sayıları vb.) aynen yazma, sayısız/niteliksel anlat.\n"
    "- Güçlü yönleri ve geliştirilmesi gereken alanları dengeli şekilde belirt.\n"
    "- 3-4 paragraf, akıcı ve doğal bir dil kullan.\n"
    "- Gereksiz tekrar yapma.\n"
)

USER_INSTRUCTION = (
    "Aşağıdaki aspect değerlendirmelerine göre otel için genel bir özet yaz.\n"
    "Not: Sayısal değerleri metne taşımadan, niteliksel ifadelerle anlat.\n"
)

# =========================
# Aspect isimlerini insanlaştırma
# =========================
ASPECT_NAME_MAP = {
    "temizlik": "Temizlik",
    "konum": "Konum",
    "oda_kalitesi": "Oda kalitesi",
    "uyku_yatak_kalitesi": "Uyku ve yatak konforu",
    "gurultu": "Sessizlik / gürültü durumu",   # burada pozitif = sessiz/sakin anlamına gelebilir
    "personel": "Personel",
    "fiyat_performans": "Fiyat-performans",
    "yemek_kalitesi": "Yemek kalitesi",
    "yemek_çeşitliligi": "Yemek çeşitliliği",
    "wifi": "Wi-Fi",
    "banyo_tuvalet": "Banyo ve tuvalet",
    "klima_isitma": "Klima / ısıtma",
    "resepsiyon": "Resepsiyon",
    "otopark": "Otopark",
    "mini_bar": "Mini bar",
    "manzara": "Manzara",
    "aktivite_zenginligi": "Aktivite olanakları",
    "balkon_teras": "Balkon / teras",
    "fitness_spor": "Fitness / spor",
    "guvenlik": "Güvenlik",
    "spa_hamam": "Spa / hamam",
    # sende varsa ekle:
    "havuz": "Havuz",
    "cocuk_uygunlugu": "Çocuklara uygunluk",
    "ulasim": "Ulaşım",
}

def humanize_aspect_key(k: str) -> str:
    # Map'te yoksa: snake_case -> Title Case gibi bir şey yapalım
    if k in ASPECT_NAME_MAP:
        return ASPECT_NAME_MAP[k]
    return k.replace("_", " ").strip().capitalize()

# =========================
# Yardımcı fonksiyonlar
# =========================
def safe_str(x):
    return "" if x is None else str(x)

def score_to_label(poz, neg, notr):
    """
    Sayılardan niteliksel etiket üretir.
    Amaç: modelin görmesi için sayıları değil, 'Ağırlıklı olumlu' gibi sınıfları vermek.
    """
    total = (poz or 0) + (neg or 0) + (notr or 0)
    if total == 0:
        return "Belirsiz"

    p = (poz or 0) / total
    n = (neg or 0) / total

    if p >= 0.80 and (poz or 0) >= 3:
        return "Çok olumlu"
    if n >= 0.80 and (neg or 0) >= 3:
        return "Çok olumsuz"

    if p >= 0.60 and (poz or 0) >= 2:
        return "Ağırlıklı olumlu"
    if n >= 0.60 and (neg or 0) >= 2:
        return "Ağırlıklı olumsuz"

    if abs(p - n) <= 0.20 and ((poz or 0) + (neg or 0)) >= 2:
        return "Karışık"

    if (notr or 0) >= max((poz or 0), (neg or 0)) and (notr or 0) >= 2:
        return "Nötr / kararsız"

    return "Karışık"

def build_reason_text(poz_neden1, poz_neden2, neg_neden1, neg_neden2):
    """
    neden1/neden2 alanlarını kısa, tek satırda birleştir.
    """
    pos = [safe_str(poz_neden1).strip(), safe_str(poz_neden2).strip()]
    neg = [safe_str(neg_neden1).strip(), safe_str(neg_neden2).strip()]

    pos = [x for x in pos if x and x.lower() != "null"]
    neg = [x for x in neg if x and x.lower() != "null"]

    parts = []
    if pos:
        parts.append("övülen: " + ", ".join(pos))
    if neg:
        parts.append("şikayet: " + ", ".join(neg))

    return " | ".join(parts) if parts else ""

def aspect_line(aspect_key, info):
    poz = info.get("pozitif", 0)
    neg = info.get("negatif", 0)
    notr = info.get("notr", 0)

    label = score_to_label(poz, neg, notr)
    reasons = build_reason_text(
        info.get("poz_neden1"), info.get("poz_neden2"),
        info.get("neg_neden1"), info.get("neg_neden2")
    )

    aspect_name = humanize_aspect_key(aspect_key)

    # Sayıları yazmıyoruz; sadece nitelik + neden
    if reasons:
        return f"- {aspect_name}: {label} ({reasons})"
    return f"- {aspect_name}: {label}"

def make_user_prompt(item):
    otel_adi = safe_str(item.get("otel_adi")).replace("_yorumlar", "").replace("_", " ").strip()

    lines = []
    lines.append(f"Otel: {otel_adi}")
    lines.append("\nAspect değerlendirmeleri:")

    aspect_summary = item.get("aspect_summary", {}) or {}

    # Tutarlılık için aspect'leri alfabetik sırala
    for asp_key in sorted(aspect_summary.keys()):
        lines.append(aspect_line(asp_key, aspect_summary[asp_key]))

    lines.append("\n" + USER_INSTRUCTION)
    return "\n".join(lines)

def to_llama_chat_jsonl_record(item):
    """
    Llama-3.1 Instruct için standart chat formatı:
    {"messages":[{"role":"system","content":...},{"role":"user","content":...},{"role":"assistant","content":...}]}
    """
    user_prompt = make_user_prompt(item)
    assistant = item.get("ozet", "")
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant}
        ]
    }

def load_items(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], list):
            return data["data"]
        raise ValueError("JSON kökü dict ama liste bulunamadı. Beklenen kökte liste (list).")
    if not isinstance(data, list):
        raise ValueError("Beklenen format: kökte liste (list).")
    return data

def write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

# =========================
# Ana akış
# =========================
def main():
    random.seed(SEED)

    items = load_items(INPUT_JSON)

    # Sadece geçerli kayıtlar: status success + ozet var
    filtered = []
    for it in items:
        if (it.get("status") == "success") and it.get("ozet"):
            if it.get("aspect_summary"):
                filtered.append(it)

    if not filtered:
        raise RuntimeError("Filtre sonrası veri kalmadı. status/ozet/aspect_summary alanlarını kontrol et.")

    random.shuffle(filtered)

    n = len(filtered)
    n_valid = max(1, int(n * VALID_RATIO))
    valid_items = filtered[:n_valid]
    train_items = filtered[n_valid:]

    train_records = [to_llama_chat_jsonl_record(x) for x in train_items]
    valid_records = [to_llama_chat_jsonl_record(x) for x in valid_items]

    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

    train_path = os.path.join(OUT_DIR, TRAIN_NAME)
    valid_path = os.path.join(OUT_DIR, VALID_NAME)

    write_jsonl(train_path, train_records)
    write_jsonl(valid_path, valid_records)

    print("✅ Bitti")
    print(f"Toplam kayıt: {n}")
    print(f"Train: {len(train_records)} -> {train_path}")
    print(f"Valid: {len(valid_records)} -> {valid_path}")

if __name__ == "__main__":
    main()
