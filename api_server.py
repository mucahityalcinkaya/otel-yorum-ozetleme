# -*- coding: utf-8 -*-
"""
BERT Aspect Extraction - FastAPI
Çıktı: Her yorum için 25 elemanlı dizi

Çalıştırma: python api_server.py
"""

import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import uvicorn
import os

# ============================================
# AYARLAR
# ============================================
CHECKPOINT_DIR = "checkpoint-6000"
MAX_LENGTH = 256
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ============================================
# MODEL
# ============================================
class BertMultiHeadFocal(nn.Module):
    def __init__(self, base_model_name, num_aspects=25, num_classes=22, dropout=0.1):
        super().__init__()
        self.bert = AutoModel.from_pretrained(base_model_name)
        hidden = self.bert.config.hidden_size
        self.dropout = nn.Dropout(dropout)
        self.heads = nn.ModuleList([
            nn.Linear(hidden, num_classes) for _ in range(num_aspects)
        ])
    
    def forward(self, input_ids=None, attention_mask=None):
        out = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0, :]
        cls = self.dropout(cls)
        logits = torch.stack([head(cls) for head in self.heads], dim=1)
        return {"logits": logits}

# ============================================
# MODEL YÜKLE
# ============================================
print(f"🖥️  Device: {DEVICE}")
print(f"📁 Checkpoint: {CHECKPOINT_DIR}")
print("\n🔄 Model yükleniyor...")

if not os.path.exists(CHECKPOINT_DIR):
    print(f"❌ HATA: {CHECKPOINT_DIR} bulunamadı!")
    exit(1)

tokenizer = AutoTokenizer.from_pretrained("dbmdz/bert-base-turkish-cased")

model = BertMultiHeadFocal(
    base_model_name="dbmdz/bert-base-turkish-cased",
    num_aspects=25,
    num_classes=22,
    dropout=0.1
)

model_path = os.path.join(CHECKPOINT_DIR, "model.safetensors")
from safetensors.torch import load_file
state_dict = load_file(model_path)
model.load_state_dict(state_dict)

model = model.to(DEVICE)
model.eval()
print("✅ Model yüklendi!")

# ============================================
# FASTAPI
# ============================================
app = FastAPI(title="Aspect API")

class SingleRequest(BaseModel):
    text: str

class BatchRequest(BaseModel):
    texts: List[str]

@app.get("/health")
def health():
    return {"status": "ok", "device": DEVICE}

@app.post("/predict")
def predict_single(req: SingleRequest) -> List[int]:
    """Tek yorum -> 25 elemanlı dizi"""
    inputs = tokenizer(
        req.text,
        return_tensors="pt",
        padding="max_length",
        max_length=MAX_LENGTH,
        truncation=True
    )
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model(inputs['input_ids'], inputs['attention_mask'])
        preds = torch.argmax(outputs['logits'], dim=-1).squeeze()
    
    return preds.cpu().tolist()

@app.post("/predict_batch")
def predict_batch(req: BatchRequest) -> List[List[int]]:
    """Çoklu yorum -> Her biri 25 elemanlı dizi listesi"""
    if not req.texts:
        return []
    
    inputs = tokenizer(
        req.texts,
        return_tensors="pt",
        padding="max_length",
        max_length=MAX_LENGTH,
        truncation=True
    )
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model(inputs['input_ids'], inputs['attention_mask'])
        preds = torch.argmax(outputs['logits'], dim=-1)
    
    return preds.cpu().tolist()

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 API: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("="*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
