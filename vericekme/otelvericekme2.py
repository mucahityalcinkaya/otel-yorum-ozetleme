import pandas as pd  # Gerekirse kalsın, kullanmasan da sorun olmaz

# Dosya yolları
input_path_all = r"C:\Users\Acer\Desktop\nlpdersiproje\otelk.txt"
input_path_filtered = r"C:\Users\Acer\Desktop\nlpdersiproje\otelk_filtered.txt"
output_path_new = r"C:\Users\Acer\Desktop\nlpdersiproje\otelk2.txt"

# --- 1. Tüm otelleri oku ---
with open(input_path_all, "r", encoding="utf-8") as f:
    all_lines = [line.strip() for line in f.readlines() if line.strip()]

# --- 2. Daha önce seçilenleri (otelk_filtered.txt) oku ---
with open(input_path_filtered, "r", encoding="utf-8") as f:
    filtered_lines = {line.strip() for line in f.readlines() if line.strip()}  # set olarak

# --- 3. Adana'yı ve filtered'dakileri çıkar, (hotel, city, line) formatla ---
data_remaining = []
for line in all_lines:
    if line in filtered_lines:
        continue  # daha önce seçilmiş, atla

    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 2:
        continue

    hotel = parts[0]
    city = parts[-1]

    if city == "Adana":
        continue  # Adana tamamen dışarıda

    data_remaining.append((hotel, city, line))

# --- 4. Kalanlardan (şehir sınırı olmadan) en fazla 200 otel seç ---
city_count = {}
selected_new = []

for hotel, city, original_line in data_remaining:
    # Toplam 200 otele ulaştıysan dur
    if len(selected_new) >= 200:
        break

    selected_new.append(original_line)
    city_count[city] = city_count.get(city, 0) + 1

# --- 5. Yeni listeyi yaz (otelk2.txt) ---
with open(output_path_new, "w", encoding="utf-8") as f:
    for s in selected_new:
        f.write(s + "\n")

print("Tamamlandı →", output_path_new)
print("Şehir başına seçilen otel sayıları:", city_count)
