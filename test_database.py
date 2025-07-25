"""
Test script to check if your database is working
Run this in your backend directory
"""

import os
from datetime import datetime
from pymongo import MongoClient

def test_database():
    """Test database connection and operations"""
    
    try:
        # Connect to MongoDB
        mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/body_measurements')
        print(f"🔗 Connecting to: {mongo_uri}")
        
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ Database connection successful!")
        
        # Get database
        db_name = mongo_uri.split('/')[-1]
        db = client[db_name]
        print(f"📊 Using database: {db_name}")
        
        # Test insert
        test_doc = {
            'client_info': {
                'name': 'Test Client',
                'email': 'test@example.com'
            },
            'measurements': {
                'chest': '38.5 inches',
                'waist': '32.0 inches',
                'confidence': '85%'
            },
            'created_at': datetime.utcnow(),
            'test': True
        }
        
        result = db.measurements.insert_one(test_doc)
        print(f"✅ Test document inserted with ID: {result.inserted_id}")
        
        # Check how many documents exist
        count = db.measurements.count_documents({})
        print(f"📈 Total measurements in database: {count}")
        
        # Show recent measurements
        recent = list(db.measurements.find().sort('created_at', -1).limit(3))
        print(f"📝 Recent measurements:")
        for i, doc in enumerate(recent, 1):
            client_name = doc.get('client_info', {}).get('name', 'Unknown')
            created = doc.get('created_at', 'Unknown time')
            print(f"  {i}. {client_name} - {created}")
        
        # Clean up test document
        db.measurements.delete_one({'_id': result.inserted_id})
        print("🧹 Test document cleaned up")
        
        # Check collections
        collections = db.list_collection_names()
        print(f"📚 Collections in database: {collections}")
        
        client.close()
        print("\n🎉 Database test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("1. Make sure MongoDB is running: mongod")
        print("2. Check your MONGO_URI in .env file")
        print("3. Try connecting to MongoDB directly: mongosh")
        return False

if __name__ == "__main__":
    print("🧪 Testing Body Measurement AI Database")
    print("=" * 50)
    test_database()