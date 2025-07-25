"""
Body Measurement AI - Flask Backend
Main application file with routes and configuration
"""

import os
import json
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import logging

# Import our custom modules
from config import Config
from models.database import init_db, get_db
from services.computer_vision import BodyMeasurementCV
from services.measurement_processor import MeasurementProcessor
from services.pdf_generator import PDFGenerator
from utils.validators import validate_image, validate_client_data
from utils.helpers import cleanup_old_files, generate_unique_filename

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for React frontend
CORS(app, origins=['http://localhost:3000', 'http://localhost:5173'])

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
init_db(app)

# Initialize services
cv_service = BodyMeasurementCV()
measurement_processor = MeasurementProcessor()
pdf_generator = PDFGenerator()

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 413

@app.errorhandler(500)
def internal_error(e):
    logger.error(f'Internal error: {str(e)}')
    return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db = get_db()
        db.command('ping')
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'services': {
                'database': 'connected',
                'computer_vision': 'ready',
                'pdf_generation': 'ready'
            }
        })
    except Exception as e:
        logger.error(f'Health check failed: {str(e)}')
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/api/process-measurements', methods=['POST'])
def process_measurements():
    """Process uploaded image and extract body measurements"""
    try:
        # Validate request
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        image_file = request.files['image']
        client_info_str = request.form.get('clientInfo', '{}')
        
        if image_file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400
        
        # Parse client info
        try:
            client_info = json.loads(client_info_str)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid client information format'}), 400
        
        # Validate client data
        validation_error = validate_client_data(client_info)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        # Validate image file
        validation_error = validate_image(image_file)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        # Save uploaded file temporarily
        filename = generate_unique_filename(image_file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(filepath)
        
        try:
            # Process image with computer vision
            logger.info(f'Processing image: {filename}')
            pose_landmarks = cv_service.detect_pose(filepath)
            
            if not pose_landmarks:
                return jsonify({
                    'error': 'Could not detect human pose in image. Please ensure the person is fully visible and standing upright.'
                }), 400
            
            # Calculate measurements
            measurements = measurement_processor.calculate_measurements(
                pose_landmarks, 
                cv_service.get_image_dimensions(filepath)
            )
            
            # Add metadata
            result = {
                'measurements': measurements,
                'metadata': {
                    'processed_at': datetime.utcnow().isoformat(),
                    'image_filename': filename,
                    'client_name': client_info.get('name', 'Unknown'),
                    'processing_time': measurement_processor.get_processing_time()
                }
            }
            
            logger.info(f'Successfully processed measurements for {client_info.get("name", "Unknown")}')
            return jsonify(result)
            
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
                
    except Exception as e:
        logger.error(f'Error processing measurements: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Failed to process measurements. Please try again.',
            'details': str(e) if app.debug else None
        }), 500

@app.route('/api/save-measurements', methods=['POST'])
def save_measurements():
    """Save measurements to database"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['clientInfo', 'measurements']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate client data
        validation_error = validate_client_data(data['clientInfo'])
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        # Prepare document for database
        document = {
            'client_info': data['clientInfo'],
            'measurements': data['measurements'],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'metadata': data.get('metadata', {})
        }
        
        # Save to database
        db = get_db()
        result = db.measurements.insert_one(document)
        
        logger.info(f'Saved measurements for client: {data["clientInfo"].get("name", "Unknown")}')
        
        return jsonify({
            'success': True,
            'measurement_id': str(result.inserted_id),
            'message': 'Measurements saved successfully'
        })
        
    except Exception as e:
        logger.error(f'Error saving measurements: {str(e)}')
        return jsonify({
            'error': 'Failed to save measurements',
            'details': str(e) if app.debug else None
        }), 500

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get list of all clients"""
    try:
        db = get_db()
        
        # Get unique clients from measurements
        pipeline = [
            {
                '$group': {
                    '_id': '$client_info.email',
                    'name': {'$first': '$client_info.name'},
                    'email': {'$first': '$client_info.email'},
                    'phone': {'$first': '$client_info.phone'},
                    'last_measurement': {'$max': '$created_at'},
                    'measurement_count': {'$sum': 1}
                }
            },
            {
                '$sort': {'last_measurement': -1}
            }
        ]
        
        clients = list(db.measurements.aggregate(pipeline))
        
        # Format response
        formatted_clients = []
        for client in clients:
            formatted_clients.append({
                'name': client['name'],
                'email': client['email'],
                'phone': client.get('phone'),
                'last_measurement': client['last_measurement'].isoformat(),
                'measurement_count': client['measurement_count']
            })
        
        return jsonify({'clients': formatted_clients})
        
    except Exception as e:
        logger.error(f'Error fetching clients: {str(e)}')
        return jsonify({
            'error': 'Failed to fetch clients',
            'details': str(e) if app.debug else None
        }), 500

@app.route('/api/clients/<client_email>/measurements', methods=['GET'])
def get_client_measurements(client_email):
    """Get measurement history for a specific client"""
    try:
        db = get_db()
        
        measurements = list(db.measurements.find(
            {'client_info.email': client_email}
        ).sort('created_at', -1))
        
        # Format response
        formatted_measurements = []
        for measurement in measurements:
            formatted_measurements.append({
                'id': str(measurement['_id']),
                'measurements': measurement['measurements'],
                'created_at': measurement['created_at'].isoformat(),
                'metadata': measurement.get('metadata', {})
            })
        
        return jsonify({
            'client_email': client_email,
            'measurements': formatted_measurements
        })
        
    except Exception as e:
        logger.error(f'Error fetching client measurements: {str(e)}')
        return jsonify({
            'error': 'Failed to fetch client measurements',
            'details': str(e) if app.debug else None
        }), 500

@app.route('/api/export-pdf', methods=['POST'])
def export_pdf():
    """Generate and download PDF report"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['clientInfo', 'measurements']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Generate PDF
        pdf_filename = pdf_generator.generate_measurement_report(
            data['clientInfo'],
            data['measurements'],
            data.get('metadata', {})
        )
        
        pdf_path = os.path.join(app.config['EXPORT_FOLDER'], pdf_filename)
        
        if not os.path.exists(pdf_path):
            return jsonify({'error': 'Failed to generate PDF report'}), 500
        
        # Schedule cleanup of old PDF files
        cleanup_old_files(app.config['EXPORT_FOLDER'], max_age_hours=24)
        
        logger.info(f'Generated PDF report: {pdf_filename}')
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f'measurements_{data["clientInfo"].get("name", "client")}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f'Error generating PDF: {str(e)}')
        return jsonify({
            'error': 'Failed to generate PDF report',
            'details': str(e) if app.debug else None
        }), 500

@app.route('/api/clients/search', methods=['GET'])
def search_clients():
    """Search clients by name or email"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({'clients': []})
        
        db = get_db()
        
        # Search in client info
        search_filter = {
            '$or': [
                {'client_info.name': {'$regex': query, '$options': 'i'}},
                {'client_info.email': {'$regex': query, '$options': 'i'}}
            ]
        }
        
        measurements = list(db.measurements.find(search_filter).sort('created_at', -1))
        
        # Get unique clients
        unique_clients = {}
        for measurement in measurements:
            client_email = measurement['client_info']['email']
            if client_email not in unique_clients:
                unique_clients[client_email] = {
                    'name': measurement['client_info']['name'],
                    'email': measurement['client_info']['email'],
                    'phone': measurement['client_info'].get('phone'),
                    'last_measurement': measurement['created_at'].isoformat(),
                    'measurement_count': 1
                }
            else:
                unique_clients[client_email]['measurement_count'] += 1
        
        return jsonify({'clients': list(unique_clients.values())})
        
    except Exception as e:
        logger.error(f'Error searching clients: {str(e)}')
        return jsonify({
            'error': 'Failed to search clients',
            'details': str(e) if app.debug else None
        }), 500

# Add this route to your app.py (after the other routes)

@app.route('/', methods=['GET'])
def homepage():
    """Homepage with API information"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Body Measurement AI - Backend</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2563eb; }
            .endpoint { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #2563eb; }
            .status { color: #059669; font-weight: bold; }
            code { background: #e5e7eb; padding: 2px 6px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Body Measurement AI Backend</h1>
            <p class="status">✅ Server is running successfully!</p>
            
            <h2>📡 Available API Endpoints</h2>
            
            <div class="endpoint">
                <strong>Health Check:</strong><br>
                <code>GET /api/health</code><br>
                <a href="/api/health" target="_blank">Test Health Check</a>
            </div>
            
            <div class="endpoint">
                <strong>Process Measurements:</strong><br>
                <code>POST /api/process-measurements</code><br>
                Upload image + client info → Get AI measurements
            </div>
            
            <div class="endpoint">
                <strong>Save Measurements:</strong><br>
                <code>POST /api/save-measurements</code><br>
                Save measurements to database
            </div>
            
            <div class="endpoint">
                <strong>Get Clients:</strong><br>
                <code>GET /api/clients</code><br>
                <a href="/api/clients" target="_blank">View All Clients</a>
            </div>
            
            <div class="endpoint">
                <strong>Export PDF:</strong><br>
                <code>POST /api/export-pdf</code><br>
                Generate measurement report PDF
            </div>
            
            <h2>🚀 Usage</h2>
            <p>This backend is designed to work with the React frontend. Start your React app and upload images to see the AI in action!</p>
            
            <h2>🔧 React Frontend Setup</h2>
            <p>Make sure your React app's <code>.env</code> file contains:</p>
            <code>REACT_APP_API_URL=http://localhost:5000</code>
            
            <hr style="margin: 30px 0;">
            <p style="text-align: center; color: #6b7280;">
                <strong>Body Measurement AI</strong> - Powered by MediaPipe & Flask
            </p>
        </div>
    </body>
    </html>
    """

@app.before_request
def log_request_info():
    """Log incoming requests"""
    if app.debug:
        logger.debug(f'{request.method} {request.url}')

@app.after_request
def cleanup_temp_files(response):
    """Clean up temporary files after request"""
    # Clean up old upload files periodically
    if hasattr(app, '_cleanup_counter'):
        app._cleanup_counter += 1
    else:
        app._cleanup_counter = 1
    
    # Run cleanup every 100 requests
    if app._cleanup_counter % 100 == 0:
        cleanup_old_files(app.config['UPLOAD_FOLDER'], max_age_hours=1)
    
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f'Starting Body Measurement AI server on port {port}')
    logger.info(f'Debug mode: {debug}')
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    )