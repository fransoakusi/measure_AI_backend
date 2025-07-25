"""
Helper utility functions for the Flask application
General purpose utilities and common operations
"""

import os
import time
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import hashlib
import json

logger = logging.getLogger(__name__)

def generate_unique_filename(original_filename: str) -> str:
    """
    Generate unique filename with timestamp and UUID
    
    Args:
        original_filename (str): Original filename
        
    Returns:
        str: Unique filename
    """
    try:
        # Get file extension
        name, ext = os.path.splitext(original_filename)
        if not ext:
            ext = '.jpg'  # Default extension
        
        # Generate unique identifier
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        
        # Sanitize original name
        sanitized_name = ''.join(c for c in name if c.isalnum() or c in '-_')[:20]
        
        # Combine parts
        unique_filename = f"{sanitized_name}_{timestamp}_{unique_id}{ext}"
        
        return unique_filename
        
    except Exception as e:
        logger.error(f"Error generating unique filename: {str(e)}")
        return f"file_{int(time.time())}.jpg"

def cleanup_old_files(directory: str, max_age_hours: int = 24) -> int:
    """
    Clean up old files from a directory
    
    Args:
        directory (str): Directory path to clean
        max_age_hours (int): Maximum age of files in hours
        
    Returns:
        int: Number of files deleted
    """
    try:
        if not os.path.exists(directory):
            return 0
        
        cutoff_time = time.time() - (max_age_hours * 3600)
        deleted_count = 0
        
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            
            try:
                if os.path.isfile(filepath):
                    file_mtime = os.path.getmtime(filepath)
                    if file_mtime < cutoff_time:
                        os.remove(filepath)
                        deleted_count += 1
                        logger.debug(f"Deleted old file: {filename}")
                        
            except Exception as e:
                logger.warning(f"Could not delete file {filename}: {str(e)}")
                continue
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old files from {directory}")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error cleaning up directory {directory}: {str(e)}")
        return 0

def calculate_file_hash(filepath: str) -> Optional[str]:
    """
    Calculate MD5 hash of a file
    
    Args:
        filepath (str): Path to file
        
    Returns:
        str: MD5 hash string or None if error
    """
    try:
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
        
    except Exception as e:
        logger.error(f"Error calculating file hash: {str(e)}")
        return None

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes (int): File size in bytes
        
    Returns:
        str: Formatted file size
    """
    try:
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
        
    except Exception:
        return "Unknown size"

def extract_measurement_stats(measurements_list: List[Dict]) -> Dict:
    """
    Extract statistics from a list of measurements
    
    Args:
        measurements_list (List[Dict]): List of measurement records
        
    Returns:
        Dict: Statistical analysis of measurements
    """
    try:
        if not measurements_list:
            return {}
        
        stats = {
            'total_count': len(measurements_list),
            'date_range': {},
            'common_measurements': {},
            'average_confidence': 0
        }
        
        # Date range analysis
        dates = [m.get('created_at') for m in measurements_list if m.get('created_at')]
        if dates:
            stats['date_range'] = {
                'earliest': min(dates).isoformat() if hasattr(min(dates), 'isoformat') else str(min(dates)),
                'latest': max(dates).isoformat() if hasattr(max(dates), 'isoformat') else str(max(dates))
            }
        
        # Measurement type analysis
        measurement_counts = {}
        confidence_values = []
        
        for record in measurements_list:
            measurements = record.get('measurements', {})
            
            # Count measurement types
            for key in measurements.keys():
                if key != 'confidence':
                    measurement_counts[key] = measurement_counts.get(key, 0) + 1
            
            # Collect confidence values
            confidence = measurements.get('confidence', '0%')
            try:
                conf_value = float(confidence.rstrip('%'))
                confidence_values.append(conf_value)
            except (ValueError, AttributeError):
                pass
        
        stats['common_measurements'] = measurement_counts
        
        # Average confidence
        if confidence_values:
            stats['average_confidence'] = sum(confidence_values) / len(confidence_values)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error extracting measurement stats: {str(e)}")
        return {}

def validate_image_dimensions(filepath: str) -> Tuple[bool, Optional[Tuple[int, int]]]:
    """
    Validate image dimensions for pose detection
    
    Args:
        filepath (str): Path to image file
        
    Returns:
        Tuple[bool, Optional[Tuple[int, int]]]: (is_valid, dimensions)
    """
    try:
        from PIL import Image
        
        with Image.open(filepath) as img:
            width, height = img.size
            
            # Minimum dimensions for reliable pose detection
            min_width, min_height = 200, 200
            
            # Maximum dimensions to prevent memory issues
            max_width, max_height = 4000, 4000
            
            is_valid = (
                width >= min_width and height >= min_height and
                width <= max_width and height <= max_height
            )
            
            return is_valid, (width, height)
            
    except Exception as e:
        logger.error(f"Error validating image dimensions: {str(e)}")
        return False, None

def create_response_dict(success: bool, message: str, data: Dict = None, error_code: str = None) -> Dict:
    """
    Create standardized API response dictionary
    
    Args:
        success (bool): Whether operation was successful
        message (str): Response message
        data (Dict): Response data
        error_code (str): Error code if applicable
        
    Returns:
        Dict: Standardized response dictionary
    """
    response = {
        'success': success,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response['data'] = data
    
    if error_code:
        response['error_code'] = error_code
    
    return response

def log_api_call(endpoint: str, method: str, client_ip: str, processing_time: float, status_code: int):
    """
    Log API call details for monitoring
    
    Args:
        endpoint (str): API endpoint
        method (str): HTTP method
        client_ip (str): Client IP address
        processing_time (float): Processing time in seconds
        status_code (int): HTTP status code
    """
    try:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'endpoint': endpoint,
            'method': method,
            'client_ip': client_ip,
            'processing_time': round(processing_time, 3),
            'status_code': status_code
        }
        
        logger.info(f"API Call: {json.dumps(log_data)}")
        
    except Exception as e:
        logger.error(f"Error logging API call: {str(e)}")

def convert_measurements_units(measurements: Dict, target_unit: str) -> Dict:
    """
    Convert measurements between units (inches/cm)
    
    Args:
        measurements (Dict): Measurements dictionary
        target_unit (str): Target unit ('inches' or 'cm')
        
    Returns:
        Dict: Converted measurements
    """
    try:
        if target_unit not in ['inches', 'cm']:
            return measurements
        
        converted = {}
        
        for key, value in measurements.items():
            if key == 'confidence':
                converted[key] = value
                continue
            
            try:
                # Parse value and unit
                parts = str(value).split()
                if len(parts) >= 2:
                    numeric_value = float(parts[0])
                    current_unit = parts[1].lower()
                    
                    # Convert if needed
                    if current_unit != target_unit:
                        if target_unit == 'cm' and current_unit in ['inches', 'in']:
                            numeric_value *= 2.54
                        elif target_unit == 'inches' and current_unit == 'cm':
                            numeric_value /= 2.54
                    
                    converted[key] = f"{numeric_value:.1f} {target_unit}"
                else:
                    converted[key] = value
                    
            except (ValueError, IndexError):
                converted[key] = value
        
        return converted
        
    except Exception as e:
        logger.error(f"Error converting measurement units: {str(e)}")
        return measurements

def get_system_info() -> Dict:
    """
    Get system information for health checks
    
    Returns:
        Dict: System information
    """
    try:
        import psutil
        import platform
        
        return {
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except ImportError:
        # psutil not available, return basic info
        import platform
        return {
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        return {'error': 'Could not retrieve system information'}

def validate_pose_quality(pose_data: Dict) -> Tuple[bool, str]:
    """
    Validate pose quality for measurement accuracy
    
    Args:
        pose_data (Dict): Pose detection results
        
    Returns:
        Tuple[bool, str]: (is_good_quality, reason)
    """
    try:
        if not pose_data or 'landmarks' not in pose_data:
            return False, "No pose landmarks detected"
        
        landmarks = pose_data['landmarks']
        
        # Check minimum number of visible landmarks
        visible_landmarks = sum(1 for lm in landmarks if lm.get('visibility', 0) > 0.5)
        if visible_landmarks < 20:  # Need at least 20 visible landmarks
            return False, f"Too few visible landmarks: {visible_landmarks}/33"
        
        # Check quality score if available
        quality_score = pose_data.get('quality_score', 0)
        if quality_score < 0.6:
            return False, f"Low pose quality score: {quality_score:.2f}"
        
        # Check confidence
        confidence = pose_data.get('confidence', 0)
        if confidence < 0.5:
            return False, f"Low pose detection confidence: {confidence:.2f}"
        
        return True, "Good pose quality"
        
    except Exception as e:
        logger.error(f"Error validating pose quality: {str(e)}")
        return False, "Error validating pose"

def create_measurement_summary(measurements: Dict) -> Dict:
    """
    Create summary of measurements for quick overview
    
    Args:
        measurements (Dict): Full measurements dictionary
        
    Returns:
        Dict: Measurement summary
    """
    try:
        summary = {
            'total_measurements': 0,
            'key_measurements': {},
            'confidence': measurements.get('confidence', 'N/A'),
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Key measurements for summary
        key_types = ['chest', 'waist', 'hips', 'shoulders', 'armLength', 'inseam']
        
        for key, value in measurements.items():
            if key == 'confidence':
                continue
                
            summary['total_measurements'] += 1
            
            if key in key_types:
                summary['key_measurements'][key] = value
        
        return summary
        
    except Exception as e:
        logger.error(f"Error creating measurement summary: {str(e)}")
        return {}

def schedule_cleanup_task(app):
    """
    Schedule periodic cleanup tasks
    
    Args:
        app: Flask application instance
    """
    try:
        # This would be implemented with a task scheduler like Celery
        # For now, we'll do basic cleanup on app startup
        
        upload_folder = app.config.get('UPLOAD_FOLDER')
        export_folder = app.config.get('EXPORT_FOLDER')
        
        if upload_folder:
            cleanup_old_files(upload_folder, max_age_hours=1)
        
        if export_folder:
            cleanup_old_files(export_folder, max_age_hours=24)
        
        logger.info("Cleanup tasks completed")
        
    except Exception as e:
        logger.error(f"Error in cleanup task: {str(e)}")

def safe_json_loads(json_string: str, default: Dict = None) -> Dict:
    """
    Safely parse JSON string with fallback
    
    Args:
        json_string (str): JSON string to parse
        default (Dict): Default value if parsing fails
        
    Returns:
        Dict: Parsed JSON or default value
    """
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError, ValueError):
        return default or {}

def format_processing_time(start_time: float) -> str:
    """
    Format processing time from start timestamp
    
    Args:
        start_time (float): Start time timestamp
        
    Returns:
        str: Formatted processing time
    """
    try:
        processing_time = time.time() - start_time
        
        if processing_time < 1:
            return f"{processing_time*1000:.0f}ms"
        else:
            return f"{processing_time:.2f}s"
            
    except Exception:
        return "Unknown"