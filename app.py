from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from flask import Flask, render_template, request, redirect, url_for, jsonify
import numpy as np
import cv2
import os
import base64
import subprocess

app = Flask(__name__)

# Azure Blob Storage configuration
connect_str = "YOUR_AZURE_STORAGE_CONNECTION_STRING"
container_name = "your-container-name"
blob_service_client = BlobServiceClient.from_connection_string(connect_str)
container_client = blob_service_client.get_container_client(container_name)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def upload_to_azure(file):
    blob_client = container_client.get_blob_client(file.filename)
    blob_client.upload_blob(file)
    return blob_client.url

def convert_to_sketch(image_data, colored=False, style='pencil', intensity=1):
    nparr = np.fromstring(image_data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    inverted_image = cv2.bitwise_not(gray_image)
    blur_image = cv2.GaussianBlur(inverted_image, (21, 21), sigmaX=0, sigmaY=0)
    inverted_blur = cv2.bitwise_not(blur_image)
    sketch_image = cv2.divide(gray_image, inverted_blur, scale=256.0)
    
    if style == 'charcoal':
        kernel = np.ones((5,5),np.uint8)
        sketch_image = cv2.dilate(sketch_image, kernel, iterations=1)
    
    if intensity != 1:
        sketch_image = cv2.multiply(sketch_image, np.array([intensity]))
    
    if colored:
        color_image = cv2.cvtColor(sketch_image, cv2.COLOR_GRAY2BGR)
        blended = cv2.addWeighted(image, 0.6, color_image, 0.4, 0)
        sketch_image = blended
    
    _, buffer = cv2.imencode('.png', sketch_image)
    return base64.b64encode(buffer).decode('utf-8')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            blob_url = upload_to_azure(file)
            return redirect(url_for('edit_file', filename=blob_url))
    return render_template('upload.html')

@app.route('/edit', methods=['GET', 'POST'])
def edit_file():
    image_url = request.args.get('filename')
    if request.method == 'POST':
        sketch_option = request.form.get('sketch_options')
        colored = sketch_option == 'colored'
        style = 'charcoal' if sketch_option == 'charcoal' else 'pencil'
        intensity = float(request.form.get('intensity', 1))
        blob_client = BlobClient.from_blob_url(image_url)
        image_data = blob_client.download_blob().readall()
        sketch_data = convert_to_sketch(image_data, colored, style, intensity)
        return render_template('edit.html', sketch_data=sketch_data, filename=image_url)
    return render_template('edit.html', filename=image_url)

@app.route('/voice-command', methods=['POST'])
def voice_command():
    command = request.json.get('command')
    if command == 'start':
        return jsonify({'action': 'start'})
    elif command == 'stop':
        return jsonify({'action': 'stop'})
    elif command == 'save':
        return jsonify({'action': 'save'})
    else:
        return jsonify({'action': 'invalid', 'message': 'Invalid voice command'})

if __name__ == '__main__':
    app.run(debug=True)
