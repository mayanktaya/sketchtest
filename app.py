from flask import Flask, render_template, request, redirect, url_for, jsonify
import numpy as np
import cv2
import os
import base64
import subprocess
from azure.storage.blob import BlobServiceClient, ContainerClient
from io import BytesIO

app = Flask(__name__)

connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
container_name = 'photos'

# Set your Azure Blob Storage connection string and container name
blob_service_client = BlobServiceClient.from_connection_string(conn_str=connect_str)
container_client = blob_service_client.get_container_client(container=container_name)

# Allowed file extensions
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def convert_to_sketch(image_bytes, output_path, colored=False, style='pencil', intensity=1):
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
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
    
    # Upload the processed image back to Azure Blob Storage
    container_client.upload_blob(name=output_path, data=BytesIO(buffer), overwrite=True)
    
    return buffer

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
            blob_name = file.filename
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(file, overwrite=True)
            return redirect(url_for('edit_file', filename=blob_name))
    return render_template('upload.html')

@app.route('/edit/<filename>', methods=['GET', 'POST'])
def edit_file(filename):
    blob_client = container_client.get_blob_client(filename)
    output_filename = 'output_' + filename
    
    if request.method == 'POST':
        sketch_option = request.form.get('sketch_options')
        colored = sketch_option == 'colored'
        style = 'charcoal' if sketch_option == 'charcoal' else 'pencil'
        intensity = float(request.form.get('intensity', 1))
        
        # Download the image from Azure Blob Storage
        image_bytes = blob_client.download_blob().readall()
        
        # Convert image to sketch
        sketch_image = convert_to_sketch(image_bytes, output_filename, colored, style, intensity)
        sketch_data = base64.b64encode(sketch_image).decode('utf-8')
        
        return render_template('edit.html', sketch_data=sketch_data, filename=filename, output_filename=output_filename)
    return render_template('edit.html', filename=filename)

@app.route('/export_to_paint/<output_filename>', methods=['POST'])
def export_to_paint(output_filename):
    # Download the image from Azure Blob Storage
    blob_client = container_client.get_blob_client(output_filename)
    image_path = os.path.join(os.getenv('UPLOAD_FOLDER', '.'), output_filename)
    
    with open(image_path, 'wb') as file:
        file.write(blob_client.download_blob().readall())
    
    subprocess.run(['mspaint', image_path])
    return redirect(url_for('edit_file', filename=output_filename))

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
