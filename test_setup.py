"""
Test script to verify Flask backend setup
Tests all major components and dependencies
"""

import sys
import os
import requests
import json
import time
from datetime import datetime

def test_imports():
    """Test all required imports"""
    print("🔍 Testing imports...")
    
    try:
        import flask
        print(f"  ✅ Flask: {flask.__version__}")
    except ImportError as e:
        print(f"  ❌ Flask import failed: {e}")
        return False
    
    try:
        import cv2
        print(f"  ✅ OpenCV: {cv2.__version__}")
    except ImportError as e:
        print(f"  ❌ OpenCV import failed: {e}")
        return False
    
    try:
        import mediapipe as mp
        print(f"  ✅ MediaPipe: {mp.__version__}")
    except ImportError as e:
        print(f"  ❌ MediaPipe import failed: {e}")
        return False
    
    try:
        import pymongo
        print(f"  ✅ PyMongo: {pymongo.__version__}")
    except ImportError as e:
        print(f"  ❌ PyMongo import failed: {e}")
        return False
    
    try:
        from reportlab.lib.pagesizes import letter
        print("  ✅ ReportLab: Available")
    except ImportError as e:
        print(f"  ❌ ReportLab import failed: {e}")
        return False
    
    try:
        import numpy as np
        print(f"  ✅ NumPy: {np.__version__}")
    except ImportError as e:
        print(f"  ❌ NumPy import failed: {e}")
        return False
    
    return True

def test_directories():
    """Test required directories exist"""
    print("\n📁 Testing directories...")
    
    required_dirs = ['uploads', 'exports', 'models', 'services', 'utils']
    all_exist = True
    
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"  ✅ {dir_name}/ exists")
        else:
            print(f"  ❌ {dir_name}/ missing")
            all_exist = False
    
    return all_exist

def test_environment():
    """Test environment configuration"""
    print("\n🔧 Testing environment...")
    
    # Check for .env file
    if os.path.exists('.env'):
        print("  ✅ .env file exists")
    else:
        print("  ⚠️  .env file missing (optional)")
    
    # Check key environment variables
    env_vars = [
        'MONGO_URI',
        'SECRET_KEY',
        'FLASK_ENV'
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"  ✅ {var}: {'*' * min(len(value), 8)}")
        else:
            print(f"  ⚠️  {var}: Not set")
    
    return True

def test_database_connection():
    """Test MongoDB connection"""
    print("\n🗄️ Testing database connection...")
    
    try:
        from pymongo import MongoClient
        
        # Use default MongoDB URI if not specified
        mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/body_measurements_test')
        
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        
        # Get database info
        db_name = mongo_uri.split('/')[-1]
        db = client[db_name]
        
        print(f"  ✅ Connected to MongoDB")
        print(f"  ✅ Database: {db_name}")
        
        # Test basic operations
        test_collection = db.test_connection
        test_doc = {'test': True, 'timestamp': datetime.utcnow()}
        result = test_collection.insert_one(test_doc)
        
        # Clean up test document
        test_collection.delete_one({'_id': result.inserted_id})
        
        print("  ✅ Database operations working")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        print("  💡 Make sure MongoDB is running or check connection string")
        return False

def test_computer_vision():
    """Test computer vision components"""
    print("\n👁️ Testing computer vision...")
    
    try:
        # Test MediaPipe initialization
        import mediapipe as mp
        mp_pose = mp.solutions.pose
        
        pose = mp_pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5
        )
        
        print("  ✅ MediaPipe Pose initialized")
        
        # Test with a simple test image (create a dummy image)
        import numpy as np
        import cv2
        
        # Create test image (person-like shape)
        test_image = np.zeros((400, 300, 3), dtype=np.uint8)
        test_image[50:350, 100:200] = [128, 128, 128]  # Body
        
        # Process test image
        results = pose.process(cv2.cvtColor(test_image, cv2.COLOR_BGR2RGB))
        
        print("  ✅ Image processing working")
        
        pose.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Computer vision test failed: {e}")
        return False

def test_api_server():
    """Test if Flask server is running"""
    print("\n🌐 Testing API server...")
    
    api_url = "http://localhost:5000"
    
    try:
        # Test health endpoint
        response = requests.get(f"{api_url}/api/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("  ✅ Server is running")
            print(f"  ✅ Health check: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"  ❌ Server returned status {response.status_code}")
            return False
            
    except requests.ConnectionError:
        print("  ❌ Cannot connect to server")
        print("  💡 Make sure to run 'python app.py' in another terminal")
        return False
    except Exception as e:
        print(f"  ❌ Server test failed: {e}")
        return False

def create_test_image():
    """Create a test image for API testing"""
    try:
        import cv2
        import numpy as np
        
        # Create a simple test image with a person-like figure
        img = np.zeros((600, 400, 3), dtype=np.uint8)
        img.fill(255)  # White background
        
        # Draw a simple stick figure
        # Head
        cv2.circle(img, (200, 100), 30, (0, 0, 0), 2)
        
        # Body
        cv2.line(img, (200, 130), (200, 300), (0, 0, 0), 3)
        
        # Arms
        cv2.line(img, (200, 180), (150, 220), (0, 0, 0), 2)
        cv2.line(img, (200, 180), (250, 220), (0, 0, 0), 2)
        
        # Legs
        cv2.line(img, (200, 300), (170, 400), (0, 0, 0), 3)
        cv2.line(img, (200, 300), (230, 400), (0, 0, 0), 3)
        
        # Save test image
        test_image_path = "test_image.jpg"
        cv2.imwrite(test_image_path, img)
        
        print(f"  ✅ Created test image: {test_image_path}")
        return test_image_path
        
    except Exception as e:
        print(f"  ❌ Failed to create test image: {e}")
        return None

def test_full_api():
    """Test complete API workflow"""
    print("\n🚀 Testing complete API workflow...")
    
    # Create test image
    test_image_path = create_test_image()
    if not test_image_path:
        return False
    
    try:
        # Test measurement processing
        api_url = "http://localhost:5000"
        
        with open(test_image_path, 'rb') as f:
            files = {'image': f}
            data = {
                'clientInfo': json.dumps({
                    'name': 'Test Client',
                    'email': 'test@example.com',
                    'phone': '555-0123'
                })
            }
            
            response = requests.post(
                f"{api_url}/api/process-measurements",
                files=files,
                data=data,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            print("  ✅ Measurement processing successful")
            
            if 'measurements' in result:
                measurements = result['measurements']
                print(f"  ✅ Got {len(measurements)} measurements")
                
                # Test save measurements
                save_data = {
                    'clientInfo': {
                        'name': 'Test Client',
                        'email': 'test@example.com'
                    },
                    'measurements': measurements
                }
                
                save_response = requests.post(
                    f"{api_url}/api/save-measurements",
                    json=save_data,
                    timeout=10
                )
                
                if save_response.status_code == 200:
                    print("  ✅ Save measurements successful")
                else:
                    print(f"  ⚠️  Save measurements failed: {save_response.status_code}")
                
            return True
        else:
            print(f"  ❌ API request failed: {response.status_code}")
            if response.text:
                print(f"  📝 Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"  ❌ Full API test failed: {e}")
        return False
    finally:
        # Clean up test image
        if test_image_path and os.path.exists(test_image_path):
            os.remove(test_image_path)

def main():
    """Run all tests"""
    print("🧪 Body Measurement AI - Backend Setup Test")
    print("=" * 50)
    
    tests = [
        ("Package Imports", test_imports),
        ("Directory Structure", test_directories),
        ("Environment Configuration", test_environment),
        ("Database Connection", test_database_connection),
        ("Computer Vision", test_computer_vision),
    ]
    
    # Run basic tests
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary of basic tests
    print("\n📊 Basic Test Results:")
    print("-" * 30)
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nBasic Tests: {passed}/{len(tests)} passed")
    
    # Test server if basic tests pass
    if passed >= 4:  # Most basic tests should pass
        print("\n🔄 Testing live server...")
        server_running = test_api_server()
        
        if server_running:
            # Full API test
            api_success = test_full_api()
            
            if api_success:
                print("\n🎉 ALL TESTS PASSED!")
                print("Your backend is ready to use! 🚀")
            else:
                print("\n⚠️  Server is running but API tests failed")
                print("Check the server logs for more details")
        else:
            print("\n💡 To test the complete API:")
            print("1. Run 'python app.py' in another terminal")
            print("2. Run this test script again")
    else:
        print("\n❌ Basic setup issues found. Please fix the failed tests first.")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()