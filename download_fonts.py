#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import urllib.request
import zipfile

FONTS_DIR = 'fonts'
DEJAVU_URL = 'https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.zip'

def download_fonts():
    os.makedirs(FONTS_DIR, exist_ok=True)
    
    print("Скачивание шрифтов DejaVu...")
    zip_path = os.path.join(FONTS_DIR, 'dejavu.zip')
    
    urllib.request.urlretrieve(DEJAVU_URL, zip_path)
    print("Шрифты скачаны!")
    
    print("Распаковка...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(FONTS_DIR)
    
    # Копируем нужные шрифты в корень
    ttf_dir = os.path.join(FONTS_DIR, 'dejavu-fonts-ttf-2.37', 'ttf')
    for font in ['DejaVuSans.ttf', 'DejaVuSans-Bold.ttf']:
        src = os.path.join(ttf_dir, font)
        dst = font
        if os.path.exists(src):
            with open(src, 'rb') as f_src:
                with open(dst, 'wb') as f_dst:
                    f_dst.write(f_src.read())
            print(f"✓ {font}")
    
    os.remove(zip_path)
    print("\n✅ Шрифты установлены!")

if __name__ == '__main__':
    download_fonts()
