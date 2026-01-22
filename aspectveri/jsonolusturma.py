import os
import json
import random
import numpy as np
import pandas as pd

from iterstrat.ml_stratifiers import MultilabelStratifiedKFold, MultilabelStratifiedShuffleSplit

# =========================================================
# AYARLAR
# =========================================================
EXCEL_IN = r"C:\Users\Acer\Desktop\nlpdersiproje\veri2\tum_oteller_tagged_merged.xlsx"
OUT_DIR  = r"C:\Users\Acer\Desktop\nlpdersiproje\egitimverisihazirlama"

SEED = 42
INCLUDE_ASPECTS_FIELD = False   # True yaparsan jsonl'e "aspects" da yazar (debug)
DROP_ROWS_WITH_NO_ASPECT = False  # True -> labels tamamen 0 olan yorumları atar (genelde False bırak)

# 80/20 split
TEST_SIZE = 0.20

# 5-fold CV
N_SPLITS = 5

SHEET_NAME = None  # None -> ilk sheet

# =========================================================
# ASPECT MAP
# =========================================================
ASPECT_MAP = {
    1: "temizlik", 2: "konum", 3: "oda_kalitesi", 4: "uyku_yatak_kalitesi",
    5: "gurultu", 6: "personel", 7: "fiyat_performans", 8: "yemek_kalitesi",
    9: "yemek_çeşitliligi", 10: "havuz", 11: "spa_hamam", 12: "plaj",
    13: "cocuk_dostu", 14: "wifi", 15: "banyo_tuvalet", 16: "klima_isitma",
    17: "resepsiyon", 18: "otopark", 19: "guvenlik", 20: "manzara",
    21: "oda_servisi", 22: "fitness_spor", 23: "mini_bar",
    24: "balkon_teras", 25: "aktivite_zenginligi"
}

NEDEN_TEXT_TO_CODE = {
    "yokluk": 1,
    "kalite": 2,
    "erişim": 3,
    "erisim": 3,
    "servis": 4,
    "fiyat": 5,
    "olumlu_kalite": 6,
    "nötr_bilgi": 7,
    "notr_bilgi": 7,
    "nötr": 7,
    "notr": 7,
}

# =========================================================
# LABEL PACK (0..21)
# 0 = aspect yok
# 1..21 = (duygu 1..3) x (neden 1..7)
# =========================================================
def pack_label(duygu: int, neden: int) -> int:
    if duygu not in (1, 2, 3):
        return 0
    if neden not in (1, 2, 3, 4, 5, 6, 7):
        return 0
    return 1 + (duygu - 1) * 7 + (neden - 1)

def safe_int(x):
    if pd.isna(x):
        return None
    if isinstance(x, str) and x.strip() == "":
        return None
    try:
        return int(float(x))
    except:
        return None

def safe_neden_code(x):
    if pd.isna(x):
        return None
    if isinstance(x, (int, float)):
        v = safe_int(x)
        return v if v in (1,2,3,4,5,6,7) else None
    s = str(x).strip().lower()
    if s == "":
        return None
    return NEDEN_TEXT_TO_CODE.get(s, None)

# =========================================================
# Presence matrix: aspect var mı? (labels>0)
# =========================================================
def labels_to_presence(labels_25):
    return [1 if int(v) > 0 else 0 for v in labels_25]

def write_jsonl(path, recs):
    with open(path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def aspect_stats_from_presence(Y):
    # Y: [N,25] 0/1
    Y = np.asarray(Y)
    counts = Y.sum(axis=0)  # [25]
    return counts

def save_report(path, title, n_total, n_train, n_val, presence_train, presence_val):
    train_counts = aspect_stats_from_presence(presence_train)
    val_counts   = aspect_stats_from_presence(presence_val)

    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{title}\n")
        f.write("=" * len(title) + "\n")
        f.write(f"Total: {n_total}\nTrain: {n_train}  Val: {n_val}\n\n")

        f.write("Aspect presence counts (Train vs Val)\n")
        f.write("-----------------------------------\n")
        for asp in range(1, 26):
            name = ASPECT_MAP[asp]
            tr = int(train_counts[asp-1])
            va = int(val_counts[asp-1])
            f.write(f"{asp:02d} {name:<22}  train={tr:<6}  val={va:<6}\n")
        f.write("\n\n")

# =========================================================
# MAIN
# =========================================================
def main():
    random.seed(SEED)
    np.random.seed(SEED)
    os.makedirs(OUT_DIR, exist_ok=True)

    # --- Excel oku ---
    if SHEET_NAME is None:
        df = pd.read_excel(EXCEL_IN)
    else:
        df = pd.read_excel(EXCEL_IN, sheet_name=SHEET_NAME)

    # --- Zorunlu kolon kontrolü ---
    for c in ["yorum_id", "yorum"]:
        if c not in df.columns:
            raise ValueError(f"Excel içinde '{c}' yok. Mevcut sütunlar: {list(df.columns)[:60]} ...")

    missing = []
    for asp_num, col in ASPECT_MAP.items():
        if col not in df.columns:
            missing.append(col)
        if f"{col}_neden" not in df.columns:
            missing.append(f"{col}_neden")
    if missing:
        raise ValueError(f"Excel içinde eksik sütun var: {missing[:30]} ... (toplam {len(missing)})")

    # --- Kayıt üret ---
    records = []
    presence = []
    skipped = 0
    dropped_no_aspect = 0

    for _, row in df.iterrows():
        yorum_id = safe_int(row["yorum_id"])
        text = "" if pd.isna(row["yorum"]) else str(row["yorum"]).strip()

        if yorum_id is None or text == "":
            skipped += 1
            continue

        labels_25 = []
        aspects_dict = {}

        for asp_num in range(1, 26):
            col = ASPECT_MAP[asp_num]
            col_neden = f"{col}_neden"

            d = safe_int(row[col])
            n = safe_neden_code(row[col_neden])

            if d not in (1, 2, 3) or n is None:
                labels_25.append(0)
                continue

            packed = pack_label(d, n)
            labels_25.append(packed)

            if INCLUDE_ASPECTS_FIELD:
                aspects_dict[str(asp_num)] = {"duygu": d, "neden": n}

        pres = labels_to_presence(labels_25)

        if DROP_ROWS_WITH_NO_ASPECT and sum(pres) == 0:
            dropped_no_aspect += 1
            continue

        rec = {
            "yorum_id": int(yorum_id),
            "yorum": text,
            "labels": labels_25,
        }
        if INCLUDE_ASPECTS_FIELD:
            rec["aspects"] = aspects_dict

        records.append(rec)
        presence.append(pres)

    if len(records) < 100:
        raise RuntimeError("Kayıt sayısı çok az çıktı. Excel kolonları/okuma hatalı olabilir.")

    print(f"OK. records={len(records)} skipped={skipped} dropped_no_aspect={dropped_no_aspect}")

    X = np.arange(len(records))
    Y = np.asarray(presence, dtype=int)

    # =========================================================
    # 1) 80/20 Multilabel Stratified Split
    # =========================================================
    splitter = MultilabelStratifiedShuffleSplit(
        n_splits=1, test_size=TEST_SIZE, random_state=SEED
    )
    train_idx, val_idx = next(splitter.split(X, Y))

    train_recs = [records[i] for i in train_idx]
    val_recs   = [records[i] for i in val_idx]

    train_path = os.path.join(OUT_DIR, "train_80.jsonl")
    val_path   = os.path.join(OUT_DIR, "val_20.jsonl")

    write_jsonl(train_path, train_recs)
    write_jsonl(val_path, val_recs)

    # report
    report1 = os.path.join(OUT_DIR, "split_report.txt")
    if os.path.exists(report1):
        os.remove(report1)

    save_report(
        report1,
        title="80/20 Multilabel Stratified Split",
        n_total=len(records),
        n_train=len(train_recs),
        n_val=len(val_recs),
        presence_train=Y[train_idx],
        presence_val=Y[val_idx]
    )

    print("Wrote:", train_path)
    print("Wrote:", val_path)
    print("Report:", report1)

    # =========================================================
    # 2) 5-Fold Multilabel Stratified CV
    # =========================================================
    mskf = MultilabelStratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)

    report2 = os.path.join(OUT_DIR, "folds_report.txt")
    if os.path.exists(report2):
        os.remove(report2)

    for fold, (tr, va) in enumerate(mskf.split(X, Y), start=1):
        tr_recs = [records[i] for i in tr]
        va_recs = [records[i] for i in va]

        tr_path = os.path.join(OUT_DIR, f"train_fold{fold}.jsonl")
        va_path = os.path.join(OUT_DIR, f"val_fold{fold}.jsonl")

        write_jsonl(tr_path, tr_recs)
        write_jsonl(va_path, va_recs)

        save_report(
            report2,
            title=f"Fold {fold} (MultilabelStratifiedKFold)",
            n_total=len(records),
            n_train=len(tr_recs),
            n_val=len(va_recs),
            presence_train=Y[tr],
            presence_val=Y[va],
        )

        print(f"Fold {fold} wrote: {tr_path} | {va_path}")

    print("CV report:", report2)
    print("\nDONE.")

if __name__ == "__main__":
    main()
