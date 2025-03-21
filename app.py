# app.py - Arquivo principal da API
from flask import Flask, request, jsonify
import os
import base64
from io import BytesIO
import numpy as np
from PIL import Image
import tempfile
import subprocess

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

def convert_pdf_to_images(pdf_bytes, dpi=300):
    """Converte bytes de PDF em imagens usando poppler-utils (instalado nos requirements)."""
    images = []
    
    # Salva o PDF em um arquivo temporário
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
        temp_pdf.write(pdf_bytes)
        temp_pdf_path = temp_pdf.name
    
    try:
        # Cria um diretório temporário para as imagens
        with tempfile.TemporaryDirectory() as temp_dir:
            # Nome base para os arquivos de saída
            output_prefix = os.path.join(temp_dir, "page")
            
            # Executa pdftoppm para converter o PDF para imagens
            subprocess.run([
                'pdftoppm', 
                '-jpeg', 
                f'-r{dpi}', 
                temp_pdf_path, 
                output_prefix
            ], check=True)
            
            # Lê todas as imagens geradas
            for filename in sorted(os.listdir(temp_dir)):
                if filename.startswith(os.path.basename(output_prefix)) and filename.endswith('.jpg'):
                    file_path = os.path.join(temp_dir, filename)
                    with open(file_path, 'rb') as img_file:
                        img = Image.open(BytesIO(img_file.read()))
                        images.append(img)
    finally:
        # Limpa o arquivo temporário
        os.unlink(temp_pdf_path)
    
    return images

@app.route("/upload-pdf", methods=["POST"])
def upload_pdf():
    """Endpoint para receber um PDF e retornar suas páginas como imagens base64."""
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo foi enviado"}), 400
    
    file = request.files["file"]
    pdf_bytes = file.read()
    
    try:
        pages = convert_pdf_to_images(pdf_bytes, dpi=300)
        
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
        "message": "API de conversão PDF para Imagem está funcionando. Use /upload-pdf para enviar arquivos."
    })

if __name__ == "__main__":
    app.run(debug=True)