# upscale.py vai tieši app.py
import cv2
import requests
import numpy as np
from io import BytesIO
from PIL import Image

def improve_image_quality(image_url, sharpen_strength=1.5):
    """
    Uzlabo attēla kvalitāti (asumu, detaļas), nepalielinot izmēru.
    sharpen_strength: 1.0 = viegli, 1.5 = vidēji, 2.0 = stipri
    """
    try:
        # 1. Lejupielādē oriģinālo bildi
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        img_array = np.frombuffer(response.content, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return None
        
        original_height, original_width = img.shape[:2]
        
        # 2. Nedaudz upscale (piem. 1.5x) ar Lanczos – pievieno detaļas
        temp_scale = 1.5  # var būt 1.3–2.0
        upscaled = cv2.resize(img, None, fx=temp_scale, fy=temp_scale, 
                              interpolation=cv2.INTER_LANCZOS4)
        
        # 3. Stiprs sharpening – atgriež asumu
        kernel = np.array([[-1, -1, -1],
                           [-1,  9, -1],
                           [-1, -1, -1]])
        sharpened = cv2.filter2D(upscaled, -1, kernel * sharpen_strength)
        
        # 4. Atgriež atpakaļ uz oriģinālo izmēru (bet tagad ar labākām detaļām!)
        final = cv2.resize(sharpened, (original_width, original_height), 
                           interpolation=cv2.INTER_LANCZOS4)
        
        # Pārvērš par PIL Image priekš Streamlit
        final = cv2.cvtColor(final, cv2.COLOR_BGR2RGB)
        return Image.fromarray(final)
    
    except Exception as e:
        print(f"Kļūda uzlabošanā: {e}")
        return None