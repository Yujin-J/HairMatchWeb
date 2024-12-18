import base64
import os
from flask import Flask, request, jsonify, render_template, url_for, redirect
from PIL import Image
import requests
import time

app = Flask(__name__)

# Stability AI API 정보
API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-v1-6/image-to-image"
API_TOKEN = "sk-bgqBC63alGuFUXBSNOPVwyChagua4gY6NaWYhleCJxyAlQen"  # Stability AI에서 받은 API 토큰 입력

UPLOAD_FOLDER = 'static/uploads'
PROCESSED_FOLDER = 'static/processed'
GENERATED_FOLDER = 'static/generated'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['GENERATED_FOLDER'] = GENERATED_FOLDER


def resize_image(image_path, max_pixels=1048576):
    """이미지를 Stability AI 제한에 맞게 리사이즈"""
    with Image.open(image_path) as img:
        width, height = img.size
        if width * height <= max_pixels:
            return image_path  # 리사이즈 필요 없음

        # 비율 유지하며 리사이즈
        scale_factor = (max_pixels / (width * height)) ** 0.5
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)  # 변경된 부분
        resized_path = os.path.join(app.config['PROCESSED_FOLDER'], os.path.basename(image_path))
        resized_img.save(resized_path)
        return resized_path


@app.route('/')
def index():
    """홈페이지 엔드포인트"""
    return render_template('index.html')

@app.route('/index.html')
def index_html():
    """홈페이지 엔드포인트"""
    return render_template('index.html')

@app.route('/change-hairstyle.html', methods=['GET', 'POST'])
def change_hairstyle():
    if request.method == 'POST':
        hairstyle = request.form.get('hairstyle')
        shade = request.form.get('shade')
        color = request.form.get('color')
        uploaded_file = request.files.get('image')

        if not uploaded_file:
            return jsonify({"error": "Image is required"}), 400

        # 파일 저장
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
        uploaded_file.save(image_path)
        resized_image_path = resize_image(image_path)

        # Stability AI API 요청
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        payload = {
            "text_prompts[0][text]": f"{hairstyle}, {shade} shade, {color} color hairstyle",
            "text_prompts[0][weight]": 1.0,
            "cfg_scale": 7.0,
            "steps": 50,
        }
        files = {"init_image": open(resized_image_path, "rb")}

        response = requests.post(API_URL, headers=headers, files=files, data=payload)
        if response.status_code != 200:
            return jsonify({"error": f"API Error: {response.status_code}"}), 500

        result = response.json()

        if "artifacts" in result and result["artifacts"]:
            artifact = result["artifacts"][0]
            if "base64" in artifact and artifact["base64"]:
                # 타임스탬프 기반 파일명 생성
                timestamp = int(time.time())
                generated_filename = f"generated-{timestamp}-{uploaded_file.filename}"
                generated_image_path = os.path.join(app.config['GENERATED_FOLDER'], generated_filename)

                with open(generated_image_path, "wb") as f:
                    f.write(base64.b64decode(artifact["base64"]))

                return jsonify({
                    "original_image": url_for('static', filename=f'uploads/{uploaded_file.filename}'),
                    "generated_image": url_for('static', filename=f'generated/{generated_filename}')
                })

        return jsonify({"error": "No generated image received from API"}), 500

    return render_template('change-hairstyle.html')

@app.route('/hair-catalogue.html')
def hair_catalogue():
    """Hair Catalogue 엔드포인트"""
    return render_template('hair-catalogue.html')


if __name__ == "__main__":
    app.run(debug=True)
