"""
Database connection and models for MongoDB
Handles client data and measurement storage
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pymongo import MongoClient, IndexModel
from pymongo.errors import ConnectionFailure, OperationFailure
import gridfs

logger = logging.getLogger(__name__)

# Global database connection
_db = None
_client = None
_gridfs = None

def init_db(app=None):
    """Initialize database connection"""
    global _db, _client, _gridfs
    
    try:
        # Get MongoDB URI from environment or config
        if app:
            mongo_uri = app.config.get('MONGO_URI', 'mongodb://localhost:27017/body_measurements')
            db_name = app.config.get('MONGO_DBNAME', 'body_measurements')
        else:
            mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/body_measurements')
            db_name = os.environ.get('MONGO_DBNAME', 'body_measurements')
        
        # Create MongoDB client
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Test connection
        _client.admin.command('ping')
        
        # Get database
        _db = _client[db_name]
        
        # Initialize GridFS for large file storage
        _gridfs = gridfs.GridFS(_db)
        
        # Create indexes for better performance
        create_indexes()
        
        logger.info(f"Connected to MongoDB database: {db_name}")
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def get_db():
    """Get database instance"""
    global _db
    if _db is None:
        init_db()
    return _db

def get_gridfs():
    """Get GridFS instance for file storage"""
    global _gridfs
    if _gridfs is None:
        init_db()
    return _gridfs

def create_indexes():
    """Create database indexes for optimal performance"""
    try:
        db = get_db()
        
        # Measurements collection indexes
        measurements_indexes = [
            IndexModel([("client_info.email", 1)]),
            IndexModel([("client_info.name", 1)]),
            IndexModel([("created_at", -1)]),
            IndexModel([("client_info.email", 1), ("created_at", -1)]),
        ]
        db.measurements.create_indexes(measurements_indexes)
        
        # Clients collection indexes (if using separate collection)
        clients_indexes = [
            IndexModel([("email", 1)], unique=True),
            IndexModel([("name", 1)]),
            IndexModel([("created_at", -1)]),
        ]
        db.clients.create_indexes(clients_indexes)
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")

class MeasurementModel:
    """Model for measurement data operations"""
    
    @staticmethod
    def create_measurement(client_info: Dict, measurements: Dict, metadata: Dict = None) -> str:
        """
        Create a new measurement record
        
        Args:
            client_info (Dict): Client information
            measurements (Dict): Body measurements
            metadata (Dict): Additional metadata
            
        Returns:
            str: Inserted document ID
        """
        try:
            db = get_db()
            
            document = {
                'client_info': {
                    'name': client_info.get('name'),
                    'email': client_info.get('email'),
                    'phone': client_info.get('phone'),
                    'notes': client_info.get('notes', '')
                },
                'measurements': measurements,
                'metadata': metadata or {},
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            result = db.measurements.insert_one(document)
            logger.info(f"Created measurement record for {client_info.get('name')}")
            
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error creating measurement: {str(e)}")
            raise

    @staticmethod
    def get_measurement_by_id(measurement_id: str) -> Optional[Dict]:
        """
        Get measurement by ID
        
        Args:
            measurement_id (str): Measurement document ID
            
        Returns:
            Dict: Measurement document or None
        """
        try:
            from bson import ObjectId
            db = get_db()
            
            measurement = db.measurements.find_one({'_id': ObjectId(measurement_id)})
            
            if measurement:
                measurement['_id'] = str(measurement['_id'])
                return measurement
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting measurement by ID: {str(e)}")
            return None

    @staticmethod
    def get_measurements_by_client_email(email: str, limit: int = 50) -> List[Dict]:
        """
        Get measurements for a specific client
        
        Args:
            email (str): Client email address
            limit (int): Maximum number of records to return
            
        Returns:
            List[Dict]: List of measurement documents
        """
        try:
            db = get_db()
            
            measurements = list(db.measurements.find(
                {'client_info.email': email}
            ).sort('created_at', -1).limit(limit))
            
            # Convert ObjectId to string
            for measurement in measurements:
                measurement['_id'] = str(measurement['_id'])
            
            return measurements
            
        except Exception as e:
            logger.error(f"Error getting measurements by client email: {str(e)}")
            return []

    @staticmethod
    def update_measurement(measurement_id: str, updates: Dict) -> bool:
        """
        Update measurement record
        
        Args:
            measurement_id (str): Measurement document ID
            updates (Dict): Fields to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from bson import ObjectId
            db = get_db()
            
            updates['updated_at'] = datetime.utcnow()
            
            result = db.measurements.update_one(
                {'_id': ObjectId(measurement_id)},
                {'$set': updates}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating measurement: {str(e)}")
            return False

    @staticmethod
    def delete_measurement(measurement_id: str) -> bool:
        """
        Delete measurement record
        
        Args:
            measurement_id (str): Measurement document ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from bson import ObjectId
            db = get_db()
            
            result = db.measurements.delete_one({'_id': ObjectId(measurement_id)})
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting measurement: {str(e)}")
            return False

    @staticmethod
    def search_measurements(query: str, limit: int = 50) -> List[Dict]:
        """
        Search measurements by client name or email
        
        Args:
            query (str): Search query
            limit (int): Maximum number of records to return
            
        Returns:
            List[Dict]: List of matching measurement documents
        """
        try:
            db = get_db()
            
            search_filter = {
                '$or': [
                    {'client_info.name': {'$regex': query, '$options': 'i'}},
                    {'client_info.email': {'$regex': query, '$options': 'i'}}
                ]
            }
            
            measurements = list(db.measurements.find(search_filter)
                              .sort('created_at', -1).limit(limit))
            
            # Convert ObjectId to string
            for measurement in measurements:
                measurement['_id'] = str(measurement['_id'])
            
            return measurements
            
        except Exception as e:
            logger.error(f"Error searching measurements: {str(e)}")
            return []

class ClientModel:
    """Model for client data operations"""
    
    @staticmethod
    def get_unique_clients(limit: int = 100) -> List[Dict]:
        """
        Get list of unique clients from measurements
        
        Args:
            limit (int): Maximum number of clients to return
            
        Returns:
            List[Dict]: List of unique clients with their stats
        """
        try:
            db = get_db()
            
            pipeline = [
                {
                    '$group': {
                        '_id': '$client_info.email',
                        'name': {'$first': '$client_info.name'},
                        'email': {'$first': '$client_info.email'},
                        'phone': {'$first': '$client_info.phone'},
                        'last_measurement': {'$max': '$created_at'},
                        'first_measurement': {'$min': '$created_at'},
                        'measurement_count': {'$sum': 1},
                        'latest_measurements': {'$first': '$measurements'}
                    }
                },
                {
                    '$sort': {'last_measurement': -1}
                },
                {
                    '$limit': limit
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
                    'last_measurement': client['last_measurement'],
                    'first_measurement': client['first_measurement'],
                    'measurement_count': client['measurement_count'],
                    'latest_measurements': client.get('latest_measurements', {})
                })
            
            return formatted_clients
            
        except Exception as e:
            logger.error(f"Error getting unique clients: {str(e)}")
            return []

    @staticmethod
    def get_client_statistics() -> Dict:
        """
        Get overall client statistics
        
        Returns:
            Dict: Statistics about clients and measurements
        """
        try:
            db = get_db()
            
            # Total measurements
            total_measurements = db.measurements.count_documents({})
            
            # Unique clients
            unique_clients = len(db.measurements.distinct('client_info.email'))
            
            # Recent activity (last 30 days)
            from datetime import timedelta
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_measurements = db.measurements.count_documents({
                'created_at': {'$gte': thirty_days_ago}
            })
            
            # Average measurements per client
            avg_measurements = total_measurements / max(unique_clients, 1)
            
            return {
                'total_measurements': total_measurements,
                'unique_clients': unique_clients,
                'recent_measurements': recent_measurements,
                'average_measurements_per_client': round(avg_measurements, 2),
                'last_updated': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error getting client statistics: {str(e)}")
            return {}

class ImageModel:
    """Model for image storage using GridFS"""
    
    @staticmethod
    def store_image(image_data: bytes, filename: str, metadata: Dict = None) -> str:
        """
        Store image in GridFS
        
        Args:
            image_data (bytes): Image binary data
            filename (str): Original filename
            metadata (Dict): Additional metadata
            
        Returns:
            str: GridFS file ID
        """
        try:
            gridfs_instance = get_gridfs()
            
            file_metadata = {
                'filename': filename,
                'upload_date': datetime.utcnow(),
                'content_type': 'image/jpeg',  # Default content type
                **(metadata or {})
            }
            
            file_id = gridfs_instance.put(
                image_data,
                filename=filename,
                metadata=file_metadata
            )
            
            logger.info(f"Stored image in GridFS: {filename}")
            return str(file_id)
            
        except Exception as e:
            logger.error(f"Error storing image: {str(e)}")
            raise

    @staticmethod
    def get_image(file_id: str) -> Optional[bytes]:
        """
        Retrieve image from GridFS
        
        Args:
            file_id (str): GridFS file ID
            
        Returns:
            bytes: Image binary data or None
        """
        try:
            from bson import ObjectId
            gridfs_instance = get_gridfs()
            
            grid_out = gridfs_instance.get(ObjectId(file_id))
            return grid_out.read()
            
        except Exception as e:
            logger.error(f"Error retrieving image: {str(e)}")
            return None

    @staticmethod
    def delete_image(file_id: str) -> bool:
        """
        Delete image from GridFS
        
        Args:
            file_id (str): GridFS file ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from bson import ObjectId
            gridfs_instance = get_gridfs()
            
            gridfs_instance.delete(ObjectId(file_id))
            return True
            
        except Exception as e:
            logger.error(f"Error deleting image: {str(e)}")
            return False

def close_db_connection():
    """Close database connection"""
    global _client
    if _client:
        _client.close()
        logger.info("Closed database connection")