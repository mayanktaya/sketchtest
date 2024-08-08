from flask import Flask, render_template, request, redirect, url_for, jsonify
import numpy as np
import cv2
import os
import base64
from voice_commands import recognize_command
import subprocess

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = r'C:\Users\vybha\Desktop\TK\Capstone\PixieSketch\Local_Run\upload'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def convert_to_sketch(image_path, output_path, colored=False, style='pencil', intensity=1):
    image = cv2.imread(image_path)
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
    
    sketch_image_bgr = cv2.cvtColor(sketch_image, cv2.COLOR_GRAY2BGR) if len(sketch_image.shape) == 2 else sketch_image
    cv2.imwrite(output_path, sketch_image_bgr)
    
    return sketch_image_bgr

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
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            return redirect(url_for('edit_file', filename=filename))
    return render_template('upload.html')

@app.route('/edit/<filename>', methods=['GET', 'POST'])
def edit_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'output_' + filename)
    if request.method == 'POST':
        sketch_option = request.form.get('sketch_options')
        colored = sketch_option == 'colored'
        style = 'charcoal' if sketch_option == 'charcoal' else 'pencil'
        intensity = float(request.form.get('intensity', 1))
        sketch_image = convert_to_sketch(file_path, output_path, colored, style, intensity)
        _, buffer = cv2.imencode('.png', sketch_image)
        sketch_data = base64.b64encode(buffer).decode('utf-8')
        return render_template('edit.html', sketch_data=sketch_data, filename=filename, output_filename='output_' + filename)
    return render_template('edit.html', filename=filename)

@app.route('/export_to_paint/<output_filename>', methods=['POST'])
def export_to_paint(output_filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
    subprocess.run(['mspaint', file_path])
    return redirect(url_for('edit_file', filename=output_filename))

@app.route('/voice-command', methods=['POST'])
def voice_command():
    command = request.json.get('command')
    result = recognize_command(command)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
