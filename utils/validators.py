"""
Input validation utilities for the Flask application
"""

import re
import os
import logging
from typing import Optional, Dict, Any
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)

# Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def validate_image(image_file) -> Optional[str]:
    """
    Validate uploaded image file
    
    Args:
        image_file: Uploaded file object
        
    Returns:
        str: Error message if validation fails, None if valid
    """
    try:
        # Check if file exists
        if not image_file or not image_file.filename:
            return "No image file provided"
        
        # Check file extension
        if not _allowed_file_extension(image_file.filename):
            return f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        
        return None  # No errors found
        
    except Exception as e:
        logger.error(f"Error validating image: {str(e)}")
        return "Error validating image file"

def validate_client_data(client_info: Dict[str, Any]) -> Optional[str]:
    """
    Validate client information data
    
    Args:
        client_info (Dict): Client information dictionary
        
    Returns:
        str: Error message if validation fails, None if valid
    """
    try:
        # Check required fields
        if not client_info:
            return "Client information is required"
        
        # Validate name (required)
        name = client_info.get('name', '').strip()
        if not name:
            return "Client name is required"
        
        if len(name) < 2:
            return "Client name must be at least 2 characters"
        
        if len(name) > 100:
            return "Client name must be less than 100 characters"
        
        # Validate email (optional but must be valid if provided)
        email = client_info.get('email', '').strip()
        if email:
            if not _validate_email(email):
                return "Invalid email address format"
        
        # Validate phone (optional but must be valid if provided)
        phone = client_info.get('phone', '').strip()
        if phone:
            if not _validate_phone(phone):
                return "Invalid phone number format"
        
        return None  # No errors found
        
    except Exception as e:
        logger.error(f"Error validating client data: {str(e)}")
        return "Error validating client information"

def _allowed_file_extension(filename: str) -> bool:
    """Check if file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _validate_email(email: str) -> bool:
    """Validate email address format"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def _validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    # Remove common formatting characters
    cleaned_phone = re.sub(r'[\s\-\(\)\+\.]', '', phone)
    
    # Check if it contains only digits and is reasonable length
    if not cleaned_phone.isdigit():
        return False
    
    # Check length (7-15 digits is reasonable for most phone numbers)
    if len(cleaned_phone) < 7 or len(cleaned_phone) > 15:
        return False
    
    return True