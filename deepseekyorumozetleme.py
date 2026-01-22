import pandas as pd
import json
import math
import re
from time import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

# ---------------- AYARLAR ----------------
EXCEL_IN  = r"C:\Users\Acer\Desktop\mucahit\nlp\nlpdersiproje\veri2\tum_oteller_tagged_merged.xlsx"
OUT_TXT   = r"C:\Users\Acer\Desktop\mucahit\nlp\nlpdersiproje\veriyeni\tum_oteller_sonuclar.txt"
OUT_LOG   = r"C:\Users\Acer\Desktop\mucahit\nlp\nlpdersiproje\veriyeni\tum_oteller_log.txt"

BATCH_SIZE    = 6
MAX_WORKERS   = 40
TOPLAM_YORUM  = None

client = OpenAI(
    api_key="api-key",
    base_url="https://api.deepseek.com"
)

# =============================================================================
# ASPECT-SPECİFİC ALT NEDEN SÖZLÜĞÜ
# =============================================================================

ALT_NEDEN_SOZLUGU = {
    1: {
        "name": "temizlik",
        "alt_nedenler": [
            "temizlik_cok_iyi", "temizlik_iyi", "temizlik_yeterli", "oda_temiz", 
            "oda_kokusuz", "oda_guzel_kokuyor", "hijyen_iyi", "temiz_titiz",
            "temizlik_yetersiz", "oda_genel_kirli", "oda_kirli", "toz_kir_birikimi", 
            "camasir_kirli", "koku_kotu", "oda_kokuyor", "bocek_hasere", 
            "pas_kirec", "leke_var", "oda_bakimsiz", "hijyen_kotu",
            "nevresim_kirli", "yatak_kirli", "yastik_kirli"
        ]
    },
    2: {
        "name": "konum",
        "alt_nedenler": [
            "merkeze_yakin", "ulasim_kolay", "konum_cok_iyi", "konum_iyi",
            "cevre_sakin", "cevre_guzel", "manzara_yakin_cevre_guzel",
            "havalimanina_yakin", "otogara_yakin", "metroya_yakin",
            "sahile_yakin", "denize_yakin", "plaja_yakin", "tarihi_yerler_yakin",
            "alisverise_yakin", "restoranlara_yakin", "yeri_guzel",
            "merkeze_uzak", "ulasim_zor", "cevre_gurultulu", "cevre_tehlikeli",
            "konum_kotu", "uzak", "yol_kotu", "trafik_sikisik"
        ]
    },
    3: {
        "name": "oda_kalitesi",
        "alt_nedenler": [
            "oda_genis", "oda_ferah", "oda_rahat", "oda_konforlu", "oda_guzel",
            "oda_duzeni_iyi", "oda_kalitesi_iyi", "oda_yeni", "oda_bakimli",
            "mobilya_yeni_duzgun", "mobilya_kaliteli", "oda_kullanisli",
            "oda_aydinlik", "oda_sicaklik_iyi", "oda_iyi", "oda_kusursuz",
            "oda_kucuk", "oda_dar", "oda_bunaltici", "oda_havasiz", "oda_kokuyor",
            "oda_bakimsiz", "oda_duzeni_kotu", "oda_kalitesi_kotu", "oda_eski",
            "mobilya_eski_yipranmis", "ekipman_eksik", "oda_karanlik",
            "oda_konforsuz", "oda_kotu", "rutubet_sorunu"
        ]
    },
    4: {
        "name": "uyku_yatak_kalitesi",
        "alt_nedenler": [
            "yatak_rahat", "yatak_kaliteli", "yatak_temiz", "yatak_genis",
            "yastik_rahat", "nevresim_kaliteli", "uyku_konforu_iyi",
            "yatak_yeni", "yorgan_rahat",
            "yatak_rahatsiz", "yatak_cokuk", "yatak_sert", "yatak_eski",
            "yatak_dar", "yatak_kucuk", "yatak_kirli",
            "yastik_rahatsiz", "yastik_kirli", "nevresim_kalitesiz",
            "uyku_konforu_kotu", "yorgan_ince"
        ]
    },
    5: {
        "name": "gurultu",
        "alt_nedenler": [
            "sessiz_sakin", "ses_yalitimi_iyi", "sessiz", "sakin_ortam",
            "dis_gurultu", "ic_gurultu", "gece_gurultu", "ses_yalitimi_zayif",
            "tamirat_gurultu", "trafik_gurultusu", "muzik_gurultusu",
            "komsu_oda_gurultu", "koridor_gurultu", "gurultulu",
            "ufak_gurultu", "cevre_gurultulu"
        ]
    },
    6: {
        "name": "personel",
        "alt_nedenler": [
            "guleryuzlu", "ilgili", "yardimsever", "profesyonel", "kibar",
            "nazik", "sicakkanli", "samimi", "saygili", "iletisim_iyi",
            "hizli_servis", "cozum_odakli", "misafirperver", "ozenli",
            "anlayisli", "caliskan", "yardimci_oldu", "musteri_iliskisi_iyi",
            "personel_cok_iyi", "personel_genel_iyi",
            "kaba", "ilgisiz", "profesyonel_degil", "yavas_servis",
            "iletisim_kotu", "sorun_cozmedi", "cozum_uretmedi", "umursamaz",
            "saygisiz", "soguk_davranis", "musteri_iliskisi_kotu",
            "personel_yetersiz", "personel_eksik", "yardimsever_degil"
        ]
    },
    7: {
        "name": "fiyat_performans",
        "alt_nedenler": [
            "fiyat_performans_iyi", "uygun", "ucuz", "hesapli", "degdi",
            "fiyat_uygun", "makul_fiyat", "ucretsiz",
            "pahali", "degmez", "cok_pahali", "fiyat_tutarsiz",
            "ekstra_ucret", "iade_yapilmadi", "kazik", "fiyat_yuksek",
            "ucretli", "fiyat_pahali"
        ]
    },
    8: {
        "name": "yemek_kalitesi",
        "alt_nedenler": [
            "lezzetli", "taze", "sicak", "hijyen_iyi", "sunum_iyi",
            "kaliteli", "doyurucu", "ev_yapimi", "organik", "tatli",
            "porsiyon_buyuk", "yemek_kalitesi_iyi",
            "lezzetsiz", "bayat", "sicak_degil", "soguk_geldi", "hijyen_kotu",
            "sunum_kotu", "mide_rahatsizlik", "tatsiz", "yagli", "tuzlu",
            "porsiyon_az", "porsiyon_kucuk", "kalite_kotu",
            "tatmin_edici_degil", "ortalama_lezzet"
        ]
    },
    9: {
        "name": "yemek_cesitliligi",
        "alt_nedenler": [
            "cesit_cok", "secenek_zengin", "menu_genis", "bufe_zengin",
            "her_sey_var", "cocuk_menusu_var", "vejetaryen_var",
            "cesit_az", "secenek_yetersiz", "menu_dar", "menu_kisitli",
            "vejetaryen_yok", "diyet_secenek_yok", "cocuk_icin_yetersiz",
            "tekrar_eden_menu", "bufe_yetersiz"
        ]
    },
    10: {
        "name": "havuz",
        "alt_nedenler": [
            "havuz_temiz", "havuz_buyuk", "havuz_guzel", "havuz_sicak",
            "havuz_sakin", "havuz_var", "havuz_genis", "havuz_iyi",
            "havuz_keyifli", "cocuk_havuzu_var", "kapali_havuz_var",
            "havuz_kirli", "havuz_soguk", "havuz_kucuk", "havuz_kalabalik",
            "havuz_bakimsiz", "havuz_yok", "havuz_kapali",
            "havuz_kullanilabilirlik_sorunu", "havuz_tehlikeli"
        ]
    },
    11: {
        "name": "spa_hamam",
        "alt_nedenler": [
            "spa_temiz", "spa_iyi", "spa_guzel", "hamam_iyi", "sauna_iyi",
            "termal_iyi", "spa_rahatlatici", "masaj_iyi", "spa_genis",
            "spa_hizmet_iyi", "spa_var",
            "spa_kirli", "spa_kapali", "spa_kalabalik", "spa_sicaklik_sorun",
            "spa_kucuk", "spa_bakimsiz", "spa_yok", "spa_kokuyor",
            "ekipman_bakimsiz", "hizmet_zayif", "sauna_yok", "hamam_kirli",
            "spa_kullanilabilirlik_sorun"
        ]
    },
    12: {
        "name": "plaj",
        "alt_nedenler": [
            "plaj_temiz", "plaj_guzel", "plaj_yakin", "denize_giris_kolay",
            "deniz_temiz", "deniz_sakin", "kum_guzel", "plaj_genis",
            "plaj_sakin", "plaj_var", "plaj_konforlu", "sezlong_var",
            "plaj_kirli", "plaj_uzak", "denize_giris_zor", "deniz_dalgali",
            "deniz_kirli", "cakil_rahatsiz", "plaj_kalabalik", "plaj_yok",
            "plaj_bakimsiz", "plaj_kucuk", "plaj_tehlikeli", "sezlong_yok"
        ]
    },
    13: {
        "name": "cocuk_dostu",
        "alt_nedenler": [
            "cocuk_havuzu_var", "mini_club_var", "cocuk_aktivite_var",
            "aile_icin_uygun", "cocuk_dostu", "cocuk_menusu_var",
            "oyun_alani_var", "bebek_yatagi_var", "cocuk_icin_uygun",
            "cocuk_havuzu_yok", "mini_club_yok", "cocuk_aktivite_yok",
            "cocuk_icin_tehlikeli", "cocuk_icin_yetersiz", "aile_icin_uygun_degil"
        ]
    },
    14: {
        "name": "wifi",
        "alt_nedenler": [
            "wifi_var_iyi", "wifi_hizli", "wifi_ucretsiz", "wifi_her_yerde",
            "wifi_iyi", "internet_hizli",
            "wifi_yok", "wifi_yavas", "wifi_kopuyor", "wifi_cekmez",
            "wifi_sadece_lobi", "wifi_ucretli", "wifi_calismiyor",
            "wifi_yetersiz", "internet_yok"
        ]
    },
    15: {
        "name": "banyo_tuvalet",
        "alt_nedenler": [
            "banyo_temiz", "banyo_genis", "banyo_guzel", "banyo_yeni",
            "banyo_konforlu", "dus_iyi", "su_sicaklik_iyi", "su_basinci_iyi",
            "hijyen_urun_var", "havlu_temiz",
            "banyo_kirli", "banyo_kucuk", "banyo_eski", "banyo_bakimsiz",
            "klozet_sorun", "dus_ariza", "ariza_tesisat", "su_sicaklik_sorunu",
            "su_basinci_sorunu", "hijyen_urun_yok", "havlu_yok", "havlu_kirli",
            "tuvalet_kirli", "tuvalet_sorun", "su_damlamasi", "tikanma_sorunu",
            "rutubet_sorunu"
        ]
    },
    16: {
        "name": "klima_isitma",
        "alt_nedenler": [
            "klima_var", "klima_calisiyor", "klima_iyi", "isitma_iyi",
            "oda_sicaklik_ideal", "sogutma_yeterli", "isitma_yeterli",
            "klima_yok", "klima_calismiyor", "klima_bozuk", "klima_gurultulu",
            "klima_eski", "klima_ucretli", "isitma_calismiyor",
            "oda_cok_soguk", "oda_cok_sicak", "isinma_yetersiz",
            "sogutma_yetersiz", "sicaklik_ayarlama_sorun"
        ]
    },
    17: {
        "name": "resepsiyon",
        "alt_nedenler": [
            "checkin_hizli", "iletisim_iyi", "yardimci_oldu", "cozum_odakli",
            "musteri_iliskisi_iyi", "karsilama_iyi", "checkout_hizli",
            "bilgilendirme_iyi", "sorun_cozdu",
            "checkin_yavas", "iletisim_kotu", "cozum_uretmedi", "yanlis_bilgi",
            "musteri_iliskisi_kotu", "ilgisiz", "sorun_cozmedi",
            "rezervasyon_sorunu", "bekleme_suresi_uzun"
        ]
    },
    18: {
        "name": "otopark",
        "alt_nedenler": [
            "otopark_var", "otopark_ucretsiz", "otopark_genis", "otopark_guvenli",
            "yer_bulmak_kolay", "otopark_buyuk", "vale_var",
            "otopark_yok", "otopark_dolu", "otopark_kucuk", "otopark_ucretli",
            "yer_bulmak_zor", "otopark_uzak", "otopark_dar", "otopark_guvensiz",
            "otopark_yetersiz", "otopark_sorunu", "park_sorunu"
        ]
    },
    19: {
        "name": "guvenlik",
        "alt_nedenler": [
            "guvenli", "guvenlik_iyi", "guvenlik_gorevlisi_var", "kamera_var",
            "guvende_hissettim", "guvenlik_onlemleri_iyi",
            "guvensiz", "guvenlik_yok", "guvenlik_gorevlisi_yok", "kamera_yok",
            "gece_tehlikeli", "esya_kaybi", "guvenlik_sorun", "cevre_tehlikeli",
            "hirsizlik"
        ]
    },
    20: {
        "name": "manzara",
        "alt_nedenler": [
            "manzara_guzel", "manzara_harika", "deniz_manzara", "dag_manzara",
            "sehir_manzara", "dogal_manzara", "manzara_var", "golet_manzara",
            "nehir_manzara", "orman_manzara", "havuz_manzara",
            "manzara_yok", "manzara_kotu", "manzara_kapali", "ic_cephe",
            "otopark_manzara", "duvar_manzara"
        ]
    },
    21: {
        "name": "oda_servisi",
        "alt_nedenler": [
            "oda_servisi_var", "oda_servisi_hizli", "sicak_geldi", "kalite_iyi",
            "servis_iyi", "24_saat_servis",
            "oda_servisi_yok", "gecikme", "soguk_geldi", "kalite_kotu",
            "oda_servisi_pahali", "oda_servisi_yavas", "servis_kotu"
        ]
    },
    22: {
        "name": "fitness_spor",
        "alt_nedenler": [
            "fitness_var", "ekipman_yeterli", "ekipman_cok", "ekipman_yeni",
            "spor_salonu_temiz", "spor_salonu_genis", "fitness_iyi",
            "fitness_yok", "ekipman_az", "ekipman_eski", "ekipman_bakimsiz",
            "spor_salonu_kirli", "spor_salonu_kucuk", "acik_saat_sorun",
            "kalabalik"
        ]
    },
    23: {
        "name": "mini_bar",
        "alt_nedenler": [
            "mini_bar_var", "mini_bar_dolu", "cesit_cok", "fiyat_uygun",
            "ucretsiz_minibar",
            "mini_bar_yok", "mini_bar_bos", "mini_bar_calismiyor",
            "cesit_az", "pahali", "son_kullanma_gecmis", "mini_bar_eksik"
        ]
    },
    24: {
        "name": "balkon_teras",
        "alt_nedenler": [
            "balkon_var", "balkon_genis", "teras_var", "balkon_guzel",
            "balkon_manzarali", "kullanisli", "oturma_alani_var",
            "balkon_yok", "balkon_kucuk", "balkon_dar", "kullanissiz",
            "balkon_bakimsiz", "guvenlik_sorun", "manzara_yok"
        ]
    },
    25: {
        "name": "aktivite_zenginligi",
        "alt_nedenler": [
            "aktivite_cok", "animasyon_var", "canli_muzik_var", "gece_eglence_var",
            "etkinlik_var", "dj_var", "gosteri_var", "eglence_programi_var",
            "etkinlik_kalitesi_iyi", "cocuk_aktivite_var",
            "aktivite_yok", "aktivite_az", "animasyon_yok", "canli_muzik_yok",
            "gece_eglence_yok", "etkinlik_kalitesi_kotu", "sikici",
            "cocuk_aktivite_yok", "eglence_yok"
        ]
    }
}

# Alt neden listesini string olarak oluştur
def generate_alt_neden_prompt():
    lines = []
    for asp_id, data in ALT_NEDEN_SOZLUGU.items():
        lines.append(f"\n{asp_id}) {data['name']}")
        for neden in data['alt_nedenler']:
            lines.append(f"- {neden}")
    return "\n".join(lines)

ALT_NEDEN_TEXT = generate_alt_neden_prompt()

SYSTEM_PROMPT = """
Sen bir otel yorumu etiketleme modelisin.

Görev:
- 25 aspect için SADECE yorumda bahsedilenleri etiketle.
- Duygu=0 olanları JSON'a YAZMA.
- Her etiket için {duygu, alt_neden} üret.
- alt_neden: AŞAĞIDAKİ SÖZLÜKTEN seçilen etiketlerin LİSTESİ olmalı.
- alt_neden serbest metin OLMAYACAK. Sadece listeden seç.
- Bir aspect için birden fazla alt_neden olabilir (1-3 arası).

⚠️ ÖNEMLİ KURAL: Her aspect SADECE KENDİ alt_neden listesinden seçim yapabilir!
Örneğin:
- "lezzetli" SADECE aspect 8 (yemek_kalitesi) için kullanılabilir
- "temizlik_cok_iyi" SADECE aspect 1 (temizlik) için kullanılabilir
- "guleryuzlu" SADECE aspect 6 (personel) için kullanılabilir

Duygu Kodları:
1 = negatif
2 = nötr (KULLANMA - sadece kesin pozitif/negatif etiketle)
3 = pozitif

ALT_NEDEN SÖZLÜĞÜ (SADECE BUNLARI KULLAN):
""" + ALT_NEDEN_TEXT + """

Aspectler (numara + kısa tanım):
1 – temizlik: sadece ODA temizliği (toz, çarşaf, oda kokusu). Banyo/tuvalet temizliği hariç (→ 15).
2 – konum: merkeze/toplu taşımaya/otogara/havalimanına yakınlık, çevre, ulaşılabilirlik.
3 – oda_kalitesi: oda büyüklüğü, ferahlık, koku, havalandırma, mobilya/oda durumu (yatak/banyo/gürültü hariç).
4 – uyku_yatak_kalitesi: yatak/yastık rahatı, uyku konforu (ses/gürültü hariç).
5 – gurultu: dışarıdan/koridordan/diğer odalardan gelen ses, sessizlik/gürültü durumu.
6 – personel: çalışanların ilgisi, güler yüzü, yardımseverliği, profesyonelliği.
7 – fiyat_performans: ödenen ücrete göre alınan hizmetin değeri.
8 – yemek_kalitesi: lezzet, tazelik, hijyen, sıcak/soğuk, pişirme kalitesi.
9 – yemek_çeşitliligi: menü/büfe çeşit sayısı, seçenek genişliği (az/kısıtlı/çok).
10 – havuz: havuzların temizlik, sıcaklık, boyut, derinlik, kalabalıklık, genel deneyimi.
11 – spa_hamam: spa, hamam, sauna, buhar odası, termal havuzlarla ilgili her yorum.
12 – plaj: plaj ve deniz kalitesi, kum/çakıl, temizlik, denize giriş/zorluk.
13 – cocuk_dostu: çocuk havuzu, kaydırak, mini club, çocuk aktiviteleri, çocuklar için uygunluk.
14 – wifi: wifi'nin hızı, çekimi, odada/ortak alanda çalışıp çalışmaması, var/yok durumu.
15 – banyo_tuvalet: banyo/tuvalet temizliği, genişliği, su basıncı/sıcaklığı, duş jeli/havlu/şampuan, klozet durumu.
16 – klima_isitma: oda sıcaklığı, klima/ısıtma çalışması, çok sıcak/soğuk şikayetleri.
17 – resepsiyon: karşılama, check-in/check-out süreci, telefonla ulaşılabilirlik, sorun çözme.
18 – otopark: park alanı var mı, kapasite, ücretsiz/ücretli olması, yer bulma kolaylığı.
19 – guvenlik: otel ve çevrenin güvenliği, güvenlik personeli, kamera, kendini güvende hissetme.
20 – manzara: oda/otel manzarası.
21 – oda_servisi: oda servisi var mı, hızı, gelen ürünlerin sıcaklığı/kalitesi.
22 – fitness_spor: spor salonu/fitness alanı.
23 – mini_bar: minibardaki ürün çeşitliliği, dolu/boş olması, fiyat algısı.
24 – balkon_teras: balkon/teras varlığı, genişliği, kullanışlılığı, balkondan görünen manzara.
25 – aktivite_zenginligi: aktiviteler, animasyonlar, canlı müzik, gece eğlenceleri.

ÇIKTI KURALI:
– Input bir JSON listesi olacak: [{"id": 0, "yorum": "..."}, ...]
– ÇIKTIN mutlaka bir JSON OBJE olacak;
   dış anahtarlar YORUM ID (string),
   iç anahtarlar ASPECT NUMARASI (string)
– İçte { "duygu": int, "alt_neden": [str, ...] }

EK KURALLAR:
- Bir aspect sadece açık KANIT varsa yazılır. Tahmin/varsayım yok.
- Duygu=1 ise pozitif alt_neden seçme. Duygu=3 ise negatif alt_neden seçme.
- Nötr (duygu=2) ASLA yazma.
- Her aspect SADECE kendi sözlüğündeki alt_nedenlerden seçebilir!

ÖRNEKLER:

ÖRNEK-1:
Yorum: "Oda pırıl pırıldı, personel çok ilgiliydi."
Çıktı:
{
  "1": {
    "1": {"duygu": 3, "alt_neden": ["temizlik_cok_iyi"]},
    "6": {"duygu": 3, "alt_neden": ["ilgili"]}
  }
}

ÖRNEK-2:
Yorum: "Konum merkeze çok yakın, ulaşım kolaydı."
Çıktı:
{
  "2": {
    "2": {"duygu": 3, "alt_neden": ["merkeze_yakin", "ulasim_kolay"]}
  }
}

ÖRNEK-3:
Yorum: "Yemekler lezzetliydi ama çeşit azdı."
Çıktı:
{
  "3": {
    "8": {"duygu": 3, "alt_neden": ["lezzetli"]},
    "9": {"duygu": 1, "alt_neden": ["cesit_az"]}
  }
}

ÖRNEK-4:
Yorum: "Havuz çok kalabalıktı ve soğuktu."
Çıktı:
{
  "4": {
    "10": {"duygu": 1, "alt_neden": ["havuz_kalabalik", "havuz_soguk"]}
  }
}

ÖRNEK-5:
Yorum: "Klima çalışmıyordu, oda çok sıcaktı."
Çıktı:
{
  "5": {
    "16": {"duygu": 1, "alt_neden": ["klima_calismiyor", "oda_cok_sicak"]}
  }
}
"""


def parse_model_output(raw_text):
    try:
        data = json.loads(raw_text)
    except Exception as e:
        return {}, f"json_load_error: {e}"

    if not isinstance(data, dict):
        return {}, "top_level_not_dict"

    clean = {}
    for y_id, aspect_dict in data.items():
        if not isinstance(aspect_dict, dict):
            continue

        if "duygu" in aspect_dict and "alt_neden" in aspect_dict and len(aspect_dict) <= 3:
            clean[str(y_id)] = "__INVALID_SINGLE__"
            continue

        inner = {}
        for asp_key, vals in aspect_dict.items():
            if not re.fullmatch(r"\d+", str(asp_key)):
                continue
            if not isinstance(vals, dict):
                continue
            if "duygu" not in vals:
                continue

            duygu = vals.get("duygu", None)
            if duygu not in (1, 3):
                continue

            alt = vals.get("alt_neden", [])
            if alt is None:
                alt = []
            if isinstance(alt, str):
                alt = [alt]
            if not isinstance(alt, list):
                alt = []
            alt = [str(x) for x in alt if isinstance(x, (str, int, float))]
            alt = alt[:3]
            
            # Aspect-specific validasyon
            asp_num = int(asp_key)
            if asp_num in ALT_NEDEN_SOZLUGU:
                valid_alts = set(ALT_NEDEN_SOZLUGU[asp_num]['alt_nedenler'])
                alt = [a for a in alt if a in valid_alts]

            if not alt:
                continue

            inner[str(asp_key)] = {
                "duygu": int(duygu),
                "alt_neden": alt
            }

        clean[str(y_id)] = inner

    return clean, None


def process_batch(batch_idx, input_list):
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(input_list, ensure_ascii=False)}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        raw_out = resp.choices[0].message.content
    except Exception as e:
        return batch_idx, {}, "", None, f"API_ERROR: {e}"

    parsed, perr = parse_model_output(raw_out)
    return batch_idx, parsed, raw_out, perr, None


# ---------------------- ANA AKIŞ ----------------------
if __name__ == "__main__":
    df = pd.read_excel(EXCEL_IN)

    needed_cols = ["yorum_id", "yorum"]
    for c in needed_cols:
        if c not in df.columns:
            raise ValueError(f"Excel içinde '{c}' sütunu yok. Mevcut sütunlar: {list(df.columns)}")

    if TOPLAM_YORUM is not None:
        df = df.iloc[:TOPLAM_YORUM]

    df = df.reset_index(drop=True)
    yorumlar = df["yorum"].astype(str)
    yorum_ids = df["yorum_id"].astype(int)

    n = len(yorumlar)
    toplam_batch = math.ceil(n / BATCH_SIZE)

    print(f"Toplam yorum: {n}, Batch sayısı: {toplam_batch}")

    batches = []
    for b in range(toplam_batch):
        start = b * BATCH_SIZE
        end = min((b+1) * BATCH_SIZE, n)

        batch_yorumlar = yorumlar.iloc[start:end]
        batch_ids = yorum_ids.iloc[start:end]

        input_list = [
            {"id": int(yid), "yorum": str(y)}
            for yid, y in zip(batch_ids.tolist(), batch_yorumlar.tolist())
        ]
        batches.append((b, input_list))

    print(f"{len(batches)} batch hazırlandı.\n")

    t0 = time()

    results_by_batch = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_batch = {}

        for (b_idx, inp) in batches:
            print(f"⏳ Batch {b_idx+1}/{toplam_batch} API'ye gönderildi")
            fut = executor.submit(process_batch, b_idx, inp)
            future_to_batch[fut] = b_idx

        for future in as_completed(future_to_batch):
            b_idx = future_to_batch[future]
            try:
                batch_idx, parsed, raw_out, perr, api_err = future.result()
            except Exception as e:
                results_by_batch[b_idx] = ({}, "", None, f"FUTURE_EXCEPTION: {e}")
                continue

            results_by_batch[batch_idx] = (parsed, raw_out, perr, api_err)

    with open(OUT_TXT, "w", encoding="utf-8") as f_txt, open(OUT_LOG, "w", encoding="utf-8") as f_log:
        for batch_idx in range(toplam_batch):
            parsed, raw_out, perr, api_err = results_by_batch.get(batch_idx, ({}, "", None, "MISSING_BATCH_RESULT"))

            if api_err is not None:
                f_log.write(f"\n--- {api_err} batch {batch_idx} ---\n")
                print(f"Batch {batch_idx+1}/{toplam_batch} FAIL (API/THREAD) → LOG'a yazıldı.")
                continue

            if perr is not None:
                f_log.write(f"\n--- PARSE ERROR batch {batch_idx} ---\n{perr}\n{raw_out}\n")

            for y_id_str, sonuc in parsed.items():
                if sonuc == "__INVALID_SINGLE__":
                    f_log.write(f"\n[INVALID_SINGLE] yorum_id={y_id_str} (batch={batch_idx})\n{raw_out}\n")
                    continue

                if not sonuc:
                    f_txt.write(f"[YORUM ID = {y_id_str}] {{}}\n")
                    continue

                line = f"[YORUM ID = {y_id_str}] " + json.dumps(sonuc, ensure_ascii=False)
                f_txt.write(line + "\n")

            print(f"Batch {batch_idx+1}/{toplam_batch} işlendi → TXT'ye yazıldı.")

    t1 = time()
    print(f"\nBİTTİ. Toplam süre: {t1 - t0:.1f} sn")
    print("Sonuç dosyası:", OUT_TXT)
    print("Hata/bozuk çıkışlar:", OUT_LOG)