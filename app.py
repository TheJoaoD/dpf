\# app.py - Versão robusta para PDFs de múltiplas páginas
from flask import Flask, request, jsonify
import os
import base64
from io import BytesIO
import numpy as np
from PIL import Image
import requests
import fitz  # PyMuPDF

app = Flask(__name__)

def image_to_data_uri(image, fmt="JPEG", quality=85):
    """Converte uma imagem PIL para data URI (base64)."""
    buffered = BytesIO()
    image.save(buffered, format=fmt, quality=quality, optimize=True)
    base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/{fmt.lower()};base64,{base64_data}"

def convert_pdf_to_images(pdf_bytes, dpi=200):
    """Converte bytes de PDF em múltiplas imagens usando PyMuPDF."""
    images = []
    
    # Carrega o PDF a partir dos bytes
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # Processa cada página
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # Renderiza a página como uma imagem
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
        
        # Converte para PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
        
    doc.close()
    return images

@app.route("/pdf-from-url", methods=["POST"])
def pdf_from_url():
    """Endpoint para processar PDFs de múltiplas páginas a partir de URLs."""
    if not request.is_json:
        return jsonify({"error": "Solicitação deve ser JSON"}), 400
    
    data = request.json
    if "url" not in data:
        return jsonify({"error": "URL do PDF não fornecida"}), 400
    
    try:
        url = data["url"]
        response = requests.get(url, timeout=30)  # Tempo maior para PDFs grandes
        
        if response.status_code != 200:
            return jsonify({"error": f"Erro ao baixar PDF. Status code: {response.status_code}"}), 400
        
        pdf_bytes = response.content
        images = convert_pdf_to_images(pdf_bytes, dpi=200)
        
        # Converter cada imagem para base64
        image_data_uris = []
        for img in images:
            data_uri = image_to_data_uri(img, quality=85)
            image_data_uris.append(data_uri)
        
        return jsonify({"cropped_images": image_data_uris})
    except Exception as e:
        return jsonify({"error": f"Erro ao processar o PDF: {str(e)}"}), 500

@app.route("/", methods=["GET"])
def index():
    """Rota padrão para verificar se a API está funcionando."""
    return jsonify({
        "status": "online",
        "message": "API de conversão PDF para Imagem está funcionando."
    })

if __name__ == "__main__":
    app.run(debug=True)
