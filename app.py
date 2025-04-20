# app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import base64
import time
import uuid
import logging
from datetime import datetime
from dotenv import load_dotenv
import requests
import json

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_FOLDER = 'temp_images'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Create static folder if it doesn't exist
if not os.path.exists('static'):
    os.makedirs('static')

# Telegram API Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Route to serve the index.html file
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/send-image', methods=['POST'])
def send_image():
    """
    Endpoint to receive image data and send it via Telegram.
    Expected JSON payload:
    {
        "image_data": "base64_encoded_image",
        "chat_id": "telegram_chat_id"
    }
    """
    try:
        # Get request data
        data = request.json
        
        # Get image data and chat ID
        image_data = data.get('image_data')
        chat_id = data.get('chat_id')
        
        if not image_data or not chat_id:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Remove data:image/jpeg;base64, prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Save image temporarily
        img_filename = f"{uuid.uuid4()}.jpg"
        img_path = os.path.join(UPLOAD_FOLDER, img_filename)
        
        with open(img_path, 'wb') as f:
            f.write(base64.b64decode(image_data))
        
        # Send image via Telegram
        result = send_telegram_photo(img_path, chat_id)
        
        # Clean up - delete the temporary file
        try:
            os.remove(img_path)
        except Exception as e:
            logger.warning(f"Failed to delete temp file {img_path}: {e}")
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def send_telegram_photo(image_path, chat_id):
    """
    Send a photo to a Telegram chat using the Telegram Bot API.
    
    Args:
        image_path (str): Path to the image file
        chat_id (str): Telegram chat ID
        
    Returns:
        dict: API response data
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        url = f"{TELEGRAM_API_URL}/sendPhoto"
        
        with open(image_path, 'rb') as photo:
            files = {'photo': photo}
            data = {
                'chat_id': chat_id,
                'caption': f"Surveillance image captured at {timestamp}"
            }
            
            response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            logger.info(f"Image sent successfully to chat {chat_id}")
            return {
                'success': True, 
                'message': 'Image sent successfully',
                'telegram_response': response.json()
            }
        else:
            logger.error(f"Failed to send image: {response.text}")
            return {
                'success': False, 
                'error': f"Failed to send image: {response.text}"
            }
            
    except Exception as e:
        logger.error(f"Error sending Telegram image: {str(e)}")
        return {'success': False, 'error': str(e)}

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)