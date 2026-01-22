
# 🏨 Multi-Stage Aspect-Based Hotel Review Summarization System

## Overview
This project is an **end-to-end Natural Language Processing (NLP) pipeline**
that analyzes hotel reviews using a **two-stage deep learning architecture**
to perform **aspect-based sentiment analysis** and generate
**human-like, qualitative hotel summaries**.

The system is designed with a strong focus on **research**, **academic validity**,
and **advanced NLP engineering practices**.

---

## Problem Statement
Hotel reviews on online platforms are:
- Large in volume
- Unstructured and noisy
- Often contradictory
- Mostly reduced to numerical ratings

These characteristics make it difficult for users to form a **clear and reliable
overall judgment** about a hotel.

This project addresses this problem by:
- Analyzing reviews at the **aspect level**
- Identifying strengths and weaknesses for each aspect
- Producing a **balanced, qualitative, and human-readable summary**

---

## Project Objectives
- High-accuracy **aspect extraction** for Turkish hotel reviews  
- Rich labeling with **sentiment + reason** information  
- **Abstractive summarization** without using numerical statistics  
- An architecture that is **academically defensible** and
  **industrially scalable**

---

## End-to-End System Architecture

```
User (Hotel Name)
        │
        ▼
Review Source (Experimental)
        │
        ▼
Text Cleaning & Normalization
        │
        ▼
Model-1: BERTurk
Aspect + Sentiment + Reason Extraction
        │
        ▼
Aspect Summary Construction
        │
        ▼
Model-2: LLaMA 3.1 8B
General Hotel Summary
        │
        ▼
Final JSON Output
```

---

## Data Collection Approach (Important Notice)

The web scraping components included in this repository are provided
**solely for experimental and demonstrational purposes**, in order to
illustrate the complete pipeline workflow.

### About Web Scraping
- Google Maps is used **only as an example data source**
- This project **does not encourage or endorse** scraping in production systems
- Automated data collection may be subject to third-party **Terms of Service**
  and **local regulations**
- The code demonstrates **pipeline integration**, not a production-ready scraper

**Responsibility Disclaimer:**  
Users are solely responsible for complying with all applicable third-party
terms and legal requirements. The authors assume no liability for misuse.

The pipeline can be adapted to **open datasets** or
**legally accessible data sources** without modification.

---

## Text Preprocessing
Raw reviews undergo the following preprocessing steps:
- Removal of HTML tags
- Cleaning of emojis, URLs, emails, and phone numbers
- Normalization of repeated characters
- Reduction of punctuation and symbol noise
- Case and whitespace normalization

These steps ensure **robust and generalizable model inputs**.

---

## Model-1: Aspect & Sentiment Extraction (BERTurk)

### Role of the Model
For each review, the model predicts for **25 predefined aspects**:
- Sentiment: Negative / Neutral / Positive
- Reason category: quality, price, accessibility, service, etc.

### Technical Details
- Base model: `dbmdz/bert-base-turkish-cased`
- Shared BERT encoder with independent classification heads
- Loss function: **Focal Loss**
- Output: 25-dimensional label vector per review

### Labeling Strategy
1. A subset of reviews was manually annotated
2. Rule-based guidance was derived from these annotations
3. **DeepSeek was used strictly via its official API**
4. API outputs were used **only to generate training data**
5. A **5-Fold Cross Validation** structure was applied

No third-party model weights are distributed in this repository.

---

## Aspect Summary Construction
Predictions from Model-1 are aggregated per hotel to construct an
**aspect_summary** structure containing:
- Aspect-level positive / negative / neutral tendencies
- Most frequently praised reasons
- Most frequently criticized reasons

This abstraction provides a **compact yet informative input**
for the summarization model.

---

## Model-2: General Hotel Summary (LLaMA 3.1 8B)

### Role of the Model
Generates a natural-language hotel summary that:
- Avoids numerical statistics
- Balances strengths and weaknesses
- Uses fluent and human-like Turkish

### Training Process
- Reference summaries generated using the **DeepSeek API**
- Instruction-tuning paradigm
- Training conducted with **Unsloth**
- Converted to **GGUF** format for Ollama inference

---

## Pipeline & Deployment
1. User provides hotel name  
2. Reviews are collected from experimental sources  
3. Text preprocessing is applied  
4. Model-1 performs aspect analysis  
5. Model-2 generates the final summary  
6. A structured JSON output is returned  

---

## General Disclaimer
- This project is intended **for research and educational purposes only**
- Scraping components are **demonstrational**, not production-ready
- Users are responsible for compliance with third-party platforms
- The software is provided **"AS IS"**, without warranty of any kind

---

## License
This project is licensed under the **Apache License 2.0**.  
See the `LICENSE` file for the legally binding terms.

======================================================================

# 🏨 Çok Aşamalı Aspect Tabanlı Otel Yorum Özetleme Sistemi

## Genel Bakış
Bu proje, otel yorumlarını analiz ederek **aspect bazlı duygu analizi**
ve **insan benzeri, niteliksel otel özetleri** üreten,
iki aşamalı derin öğrenme mimarisi üzerine kurulu
**uçtan uca bir Doğal Dil İşleme (NLP) pipeline’ıdır**.

Sistem, **araştırma**, **akademik geçerlilik** ve
**ileri seviye NLP mühendisliği** odağıyla tasarlanmıştır.

---

## Problem Tanımı
Otel platformlarında yer alan kullanıcı yorumları:
- Çok sayıda
- Yapısız ve gürültülü
- Çoğu zaman çelişkili
- Genellikle sayısal puanlara indirgenmiş

Bu durum, kullanıcıların bir otel hakkında **net ve güvenilir
bir genel yargıya varmasını** zorlaştırmaktadır.

Bu proje problemi şu şekilde ele alır:
- Yorumları **aspect seviyesinde** analiz eder
- Her aspect için güçlü ve zayıf yönleri belirler
- **Dengeli, niteliksel ve okunabilir** bir genel özet sunar

---

## Projenin Amaçları
- Türkçe otel yorumları için **yüksek doğrulukta aspect çıkarımı**  
- **Duygu + neden** bilgisi içeren zengin etiketleme  
- Sayısal veri kullanmadan **soyutlayıcı özet üretimi**  
- Akademik olarak savunulabilir ve
  endüstriyel olarak ölçeklenebilir bir mimari

---

## Uçtan Uca Sistem Mimarisi

```
Kullanıcı (Otel Adı)
        │
        ▼
Yorum Kaynağı (Deneysel)
        │
        ▼
Metin Temizleme & Normalizasyon
        │
        ▼
Model-1: BERTurk
Aspect + Duygu + Neden Çıkartımı
        │
        ▼
Aspect Summary Oluşturma
        │
        ▼
Model-2: LLaMA 3.1 8B
Genel Otel Özeti
        │
        ▼
JSON Çıktı
```

---

## Veri Toplama Yaklaşımı (Önemli Açıklama)

Bu repoda yer alan web scraping bileşenleri,
uçtan uca pipeline işleyişini göstermek amacıyla
**yalnızca deneysel ve örnekleyici** olarak sunulmaktadır.

### Web Scraping Hakkında
- Google Maps **sadece örnek bir veri kaynağıdır**
- Bu proje, üretim ortamında scraping kullanımını **teşvik etmez**
- Otomatik veri toplama işlemleri, ilgili platformların
  **kullanım koşullarına** ve **yerel yasal düzenlemelere** tabi olabilir
- Kodlar, scraping çözümü sunmak için değil,
  **pipeline entegrasyonunu göstermek** için yer almaktadır

**Sorumluluk Reddi:**  
Bu kodları kullanan kişiler, üçüncü parti platformların kullanım
koşullarına uymaktan tamamen kendileri sorumludur.
Proje sahipleri, olası ihlallerden sorumlu tutulamaz.

Pipeline, açık veri setleri veya yasal olarak erişime izin verilen
veri kaynaklarıyla herhangi bir değişiklik yapılmadan çalıştırılabilir.

---

## Metin Ön İşleme
Ham yorumlar aşağıdaki ön işleme adımlarından geçirilir:
- HTML etiketlerinin kaldırılması
- Emoji, URL, e-posta ve telefon numaralarının temizlenmesi
- Tekrarlı karakterlerin normalize edilmesi
- Noktalama ve sembol gürültüsünün azaltılması
- Harf ve boşluk normalizasyonu

Bu adımlar, **daha kararlı ve genellenebilir** model girdileri sağlar.

---

## Model-1: Aspect & Duygu Çıkartımı (BERTurk)

### Modelin Rolü
Her bir yorum için **25 önceden tanımlanmış aspect** özelinde:
- Duygu: Olumsuz / Nötr / Olumlu
- Neden kategorisi: kalite, fiyat, erişim, servis vb.

tahmin edilir.

### Teknik Detaylar
- Taban model: `dbmdz/bert-base-turkish-cased`
- Ortak BERT encoder ve aspect başına bağımsız sınıflandırma kafaları
- Kayıp fonksiyonu: **Focal Loss**
- Çıkış: Yorum başına 25 boyutlu etiket vektörü

### Etiketleme Stratejisi
1. Yorumların bir bölümü manuel olarak etiketlenmiştir
2. Bu etiketlerden kural tabanlı yönlendirme üretilmiştir
3. **DeepSeek modeli yalnızca resmi API üzerinden** kullanılmıştır
4. API çıktıları **eğitim verisi üretimi amacıyla** kullanılmıştır
5. **5-Fold Cross Validation** yapısı uygulanmıştır

Bu repoda hiçbir üçüncü parti modele ait ağırlık paylaşılmamaktadır.

---

## Aspect Summary Oluşturma
Model-1 çıktıları otel bazında birleştirilerek:
- Aspect bazlı pozitif / negatif / nötr eğilimler
- En sık övülen nedenler
- En sık şikayet edilen nedenler

içeren bir **aspect_summary** yapısı oluşturulur.

Bu yapı, özetleme modeli için
**yoğunlaştırılmış ve bilgilendirici** bir girdi sağlar.

---

## Model-2: Genel Otel Özeti (LLaMA 3.1 8B)

### Modelin Rolü
Aspect summary verilerinden:
- Sayısal ifade kullanmadan
- Güçlü ve zayıf yönleri dengeli biçimde ele alan
- Akıcı ve doğal Türkçe ile

genel bir otel değerlendirmesi üretir.

### Eğitim Süreci
- Referans özetler **DeepSeek API** kullanılarak oluşturulmuştur
- Instruction-tuning yaklaşımı benimsenmiştir
- Eğitim **Unsloth** framework ile gerçekleştirilmiştir
- Model **GGUF** formatına dönüştürülerek Ollama ile çalıştırılmıştır

---

## Pipeline ve Dağıtım
1. Kullanıcı otel adını girer  
2. Yorumlar deneysel kaynaklardan toplanır  
3. Metin ön işleme uygulanır  
4. Model-1 aspect analizi yapar  
5. Model-2 genel özet üretir  
6. Yapılandırılmış JSON çıktısı oluşturulur  

---

## Genel Sorumluluk Reddi
- Bu proje **yalnızca araştırma ve eğitim amaçlıdır**
- Scraping bileşenleri **örnekleyici niteliktedir**
- Kullanıcılar, üçüncü parti platformların koşullarına uymakla yükümlüdür
- Yazılım **"OLDUĞU GİBİ"** sunulmaktadır

---

## Lisans
Bu proje **Apache License 2.0** kapsamında lisanslanmıştır.  
Hukuken bağlayıcı metin için `LICENSE` dosyasına bakınız.
