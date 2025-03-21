# app.py - Versão atualizada para processar múltiplas páginas de PDF
from flask import Flask, request, jsonify
import os
import base64
from io import BytesIO
import numpy as np
from PIL import Image
import tempfile
import subprocess
import requests
import fitz  # PyMuPDF

app = Flask(__name__)

def auto_crop(image, threshold=240):
    """Recorta automaticamente a imagem removendo bordas em branco."""
    try:
        gray = image.convert("L")
        np_gray = np.array(gray)
        mask = np_gray < threshold
        if not mask.any():
            return image
        coords = np.argwhere(mask)
        y0, x0 = coords.min(axis=0)
        y1, x1 = coords.max(axis=0)
        cropped = image.crop((x0, y0, x1+1, y1+1))
        return cropped
    except Exception as e:
        print(f"Erro no auto crop: {str(e)}")
        return image

def image_to_data_uri(image, fmt="JPEG", quality=85):
    """Converte uma imagem PIL para data URI (base64)."""
    buffered = BytesIO()
    image.save(buffered, format=fmt, quality=quality, optimize=True)
    base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/{fmt.lower()};base64,{base64_data}"

def convert_pdf_to_images(pdf_bytes, dpi=200):
    """Converte bytes de PDF em múltiplas imagens usando PyMuPDF."""
    images = []
    try:
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
    except Exception as e:
        print(f"Erro ao converter PDF para imagens: {str(e)}")
        # Em caso de erro, retornamos uma imagem de erro simples
        error_img = Image.new('RGB', (800, 600), color='white')
        return [error_img]

@app.route("/upload-pdf", methods=["POST"])
def upload_pdf():
    """Endpoint para receber um PDF e retornar suas páginas como imagens base64."""
    if "file" in request.files:
        # Método original: upload de arquivo
        file = request.files["file"]
        pdf_bytes = file.read()
    elif "url" in request.json:
        # Novo método: fornecer URL do PDF
        try:
            url = request.json["url"]
            response = requests.get(url, timeout=10)
            pdf_bytes = response.content
        except Exception as e:
            return jsonify({"error": f"Erro ao baixar PDF da URL: {str(e)}"}), 400
    else:
        return jsonify({"error": "Nenhum arquivo ou URL foi enviado. Envie um arquivo com o campo 'file' ou uma URL com o campo 'url'"}), 400
    
    try:
        pages = convert_pdf_to_images(pdf_bytes, dpi=200)
        
        cropped_images = []
        for idx, page in enumerate(pages):
            print(f"Processando página {idx+1}...")
            cropped_page = auto_crop(page, threshold=240)
            data_uri = image_to_data_uri(cropped_page, quality=85)
            cropped_images.append(data_uri)
        
        return jsonify({"cropped_images": cropped_images})
    except Exception as e:
        return jsonify({"error": f"Erro ao processar o PDF: {str(e)}"}), 500

@app.route("/pdf-from-url", methods=["POST"])
def pdf_from_url():
    """Endpoint específico para processar PDFs a partir de URLs."""
    if not request.is_json:
        return jsonify({"error": "Solicitação deve ser JSON"}), 400
    
    data = request.json
    if "url" not in data:
        return jsonify({"error": "URL do PDF não fornecida"}), 400
    
    try:
        url = data["url"]
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return jsonify({"error": f"Erro ao baixar PDF. Status code: {response.status_code}"}), 400
        
        pdf_bytes = response.content
        pages = convert_pdf_to_images(pdf_bytes, dpi=200)
        
        cropped_images = []
        for idx, page in enumerate(pages):
            print(f"Processando página {idx+1}...")
            cropped_page = auto_crop(page, threshold=240)
            data_uri = image_to_data_uri(cropped_page, quality=85)
            cropped_images.append(data_uri)
        
        return jsonify({"cropped_images": cropped_images})
    except Exception as e:
        return jsonify({"error": f"Erro ao processar o PDF: {str(e)}"}), 500

@app.route("/", methods=["GET"])
def index():
    """Rota padrão para verificar se a API está funcionando."""
    return jsonify({
        "status": "online",
        "message": "API de conversão PDF para Imagem está funcionando. Use /upload-pdf para enviar arquivos ou /pdf-from-url para processar de uma URL."
    })

if __name__ == "__main__":
    app.run(debug=True)
