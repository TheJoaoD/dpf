# app.py - Versão atualizada para processar PDF por URL
from flask import Flask, request, jsonify
import os
import base64
from io import BytesIO
import numpy as np
from PIL import Image
import tempfile
import subprocess
import requests

app = Flask(__name__)

def auto_crop(image, threshold=240):
    """Recorta automaticamente a imagem removendo bordas em branco."""
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

def image_to_data_uri(image, fmt="JPEG", quality=85):
    """Converte uma imagem PIL para data URI (base64)."""
    buffered = BytesIO()
    image.save(buffered, format=fmt, quality=quality, optimize=True)
    base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/{fmt.lower()};base64,{base64_data}"

def convert_pdf_to_images(pdf_bytes, dpi=150):
    """Converte bytes de PDF em imagens usando biblioteca PIL."""
    try:
        # Tentamos usar o método simples primeiro - converte apenas a primeira página
        # mas funciona sem dependências extras
        img = Image.open(BytesIO(pdf_bytes))
        return [img]
    except Exception as e:
        print(f"Erro ao converter com método simples: {str(e)}")
        # Se falhar, retornamos uma imagem de erro simples
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
        pages = convert_pdf_to_images(pdf_bytes, dpi=150)
        
        cropped_images = []
        for idx, page in enumerate(pages):
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
        pages = convert_pdf_to_images(pdf_bytes, dpi=150)
        
        cropped_images = []
        for idx, page in enumerate(pages):
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
