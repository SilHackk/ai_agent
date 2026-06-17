FROM python:3.11-slim

# Sisteminės priklausomybės
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-lit \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data uploads/email_attachments uploads/manual uploads/temp \
    uploads/pdf_pages uploads/pdf_previews uploads/overlays config

RUN python -c "import json,os; p='config/vision_rules.json'; r={'min_object_area_ratio':0.00008,'min_object_area_px':80,'ocr_enabled':False,'known_colors':{'blue_zone':{'meaning':'speciali melyna zona','hsv_ranges':[[[85,35,35],[140,255,255]]]},'red_opening_mark':{'meaning':'varstymo zymejimas','hsv_ranges':[[[0,45,45],[14,255,255]],[[164,45,45],[180,255,255]]]}},'manufacturing_rules':{'roof_window_keywords':['stoglang','roof window','velux'],'door_keywords':['dur','door'],'window_keywords':['lang','window']}}; open(p,'w').write(json.dumps(r,indent=2)) if not os.path.exists(p) else None"

EXPOSE 8000 8501