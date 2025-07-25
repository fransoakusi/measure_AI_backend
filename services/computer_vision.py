"""
Computer Vision Service using MediaPipe for body pose detection
Extracts key body landmarks for measurement calculation
"""

import cv2
import mediapipe as mp
import numpy as np
import logging
from typing import Optional, Dict, List, Tuple
import os

logger = logging.getLogger(__name__)

class BodyMeasurementCV:
    """Computer vision service for body measurement extraction"""
    
    def __init__(self):
        """Initialize MediaPipe pose detection"""
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Initialize pose detection with optimized parameters
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=2,  # Higher accuracy model
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Key landmark indices for measurements
        self.landmark_indices = {
            'nose': 0,
            'left_eye_inner': 1,
            'left_eye': 2,
            'left_eye_outer': 3,
            'right_eye_inner': 4,
            'right_eye': 5,
            'right_eye_outer': 6,
            'left_ear': 7,
            'right_ear': 8,
            'mouth_left': 9,
            'mouth_right': 10,
            'left_shoulder': 11,
            'right_shoulder': 12,
            'left_elbow': 13,
            'right_elbow': 14,
            'left_wrist': 15,
            'right_wrist': 16,
            'left_pinky': 17,
            'right_pinky': 18,
            'left_index': 19,
            'right_index': 20,
            'left_thumb': 21,
            'right_thumb': 22,
            'left_hip': 23,
            'right_hip': 24,
            'left_knee': 25,
            'right_knee': 26,
            'left_ankle': 27,
            'right_ankle': 28,
            'left_heel': 29,
            'right_heel': 30,
            'left_foot_index': 31,
            'right_foot_index': 32
        }
        
        logger.info("Computer Vision service initialized with MediaPipe")
    
    def detect_pose(self, image_path: str) -> Optional[Dict]:
        """
        Detect pose landmarks in an image
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            Dict: Pose landmarks and metadata, None if detection fails
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not read image: {image_path}")
                return None
            
            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            height, width = image.shape[:2]
            
            # Process image
            results = self.pose.process(image_rgb)
            
            if not results.pose_landmarks:
                logger.warning("No pose landmarks detected in image")
                return None
            
            # Extract landmark coordinates
            landmarks = []
            for landmark in results.pose_landmarks.landmark:
                landmarks.append({
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z,
                    'visibility': landmark.visibility
                })
            
            # Calculate pose quality score
            quality_score = self._calculate_pose_quality(landmarks)
            
            # Check if pose is suitable for measurements
            if quality_score < 0.6:
                logger.warning(f"Low pose quality score: {quality_score}")
                return None
            
            pose_data = {
                'landmarks': landmarks,
                'image_dimensions': {
                    'width': width,
                    'height': height
                },
                'quality_score': quality_score,
                'confidence': self._calculate_overall_confidence(landmarks)
            }
            
            logger.info(f"Pose detected successfully with quality score: {quality_score:.2f}")
            return pose_data
            
        except Exception as e:
            logger.error(f"Error in pose detection: {str(e)}")
            return None
    
    def _calculate_pose_quality(self, landmarks: List[Dict]) -> float:
        """
        Calculate pose quality based on landmark visibility and positioning
        
        Args:
            landmarks (List[Dict]): List of landmark dictionaries
            
        Returns:
            float: Quality score between 0 and 1
        """
        try:
            # Key landmarks for measurement quality assessment
            key_landmarks = [
                'left_shoulder', 'right_shoulder',
                'left_hip', 'right_hip',
                'left_knee', 'right_knee',
                'left_ankle', 'right_ankle'
            ]
            
            total_visibility = 0
            valid_landmarks = 0
            
            for landmark_name in key_landmarks:
                idx = self.landmark_indices[landmark_name]
                if idx < len(landmarks):
                    visibility = landmarks[idx]['visibility']
                    if visibility > 0.5:  # Minimum visibility threshold
                        total_visibility += visibility
                        valid_landmarks += 1
            
            if valid_landmarks == 0:
                return 0.0
            
            # Calculate average visibility
            avg_visibility = total_visibility / valid_landmarks
            
            # Check pose symmetry (both sides visible)
            symmetry_score = self._calculate_symmetry_score(landmarks)
            
            # Check if person is standing upright
            posture_score = self._calculate_posture_score(landmarks)
            
            # Combined quality score
            quality_score = (avg_visibility * 0.4 + symmetry_score * 0.3 + posture_score * 0.3)
            
            return min(1.0, quality_score)
            
        except Exception as e:
            logger.error(f"Error calculating pose quality: {str(e)}")
            return 0.0
    
    def _calculate_symmetry_score(self, landmarks: List[Dict]) -> float:
        """Calculate how symmetric the pose is (both sides visible)"""
        try:
            left_landmarks = ['left_shoulder', 'left_hip', 'left_knee', 'left_ankle']
            right_landmarks = ['right_shoulder', 'right_hip', 'right_knee', 'right_ankle']
            
            left_visible = sum(1 for name in left_landmarks 
                             if landmarks[self.landmark_indices[name]]['visibility'] > 0.5)
            right_visible = sum(1 for name in right_landmarks 
                              if landmarks[self.landmark_indices[name]]['visibility'] > 0.5)
            
            total_pairs = len(left_landmarks)
            symmetry = min(left_visible, right_visible) / total_pairs
            
            return symmetry
            
        except Exception:
            return 0.0
    
    def _calculate_posture_score(self, landmarks: List[Dict]) -> float:
        """Calculate if person is standing upright"""
        try:
            # Get key points for posture analysis
            left_shoulder = landmarks[self.landmark_indices['left_shoulder']]
            right_shoulder = landmarks[self.landmark_indices['right_shoulder']]
            left_hip = landmarks[self.landmark_indices['left_hip']]
            right_hip = landmarks[self.landmark_indices['right_hip']]
            
            # Calculate shoulder and hip alignment
            shoulder_angle = abs(left_shoulder['y'] - right_shoulder['y'])
            hip_angle = abs(left_hip['y'] - right_hip['y'])
            
            # Check vertical alignment (shoulders above hips)
            shoulder_center_y = (left_shoulder['y'] + right_shoulder['y']) / 2
            hip_center_y = (left_hip['y'] + right_hip['y']) / 2
            
            if shoulder_center_y >= hip_center_y:
                return 0.0  # Person is upside down or lying down
            
            # Calculate posture score based on alignment
            max_angle_threshold = 0.1  # Maximum acceptable angle difference
            shoulder_score = max(0, 1 - (shoulder_angle / max_angle_threshold))
            hip_score = max(0, 1 - (hip_angle / max_angle_threshold))
            
            return (shoulder_score + hip_score) / 2
            
        except Exception:
            return 0.0
    
    def _calculate_overall_confidence(self, landmarks: List[Dict]) -> float:
        """Calculate overall confidence of the pose detection"""
        try:
            total_visibility = sum(landmark['visibility'] for landmark in landmarks)
            avg_visibility = total_visibility / len(landmarks)
            return min(1.0, avg_visibility)
        except Exception:
            return 0.0
    
    def get_landmark_coordinates(self, pose_data: Dict, landmark_name: str) -> Optional[Tuple[float, float]]:
        """
        Get normalized coordinates for a specific landmark
        
        Args:
            pose_data (Dict): Pose detection results
            landmark_name (str): Name of the landmark
            
        Returns:
            Tuple[float, float]: (x, y) coordinates or None if not found
        """
        try:
            if landmark_name not in self.landmark_indices:
                return None
            
            idx = self.landmark_indices[landmark_name]
            landmarks = pose_data['landmarks']
            
            if idx >= len(landmarks):
                return None
            
            landmark = landmarks[idx]
            if landmark['visibility'] < 0.5:
                return None
            
            return (landmark['x'], landmark['y'])
            
        except Exception as e:
            logger.error(f"Error getting landmark coordinates: {str(e)}")
            return None
    
    def get_pixel_coordinates(self, pose_data: Dict, landmark_name: str) -> Optional[Tuple[int, int]]:
        """
        Get pixel coordinates for a specific landmark
        
        Args:
            pose_data (Dict): Pose detection results
            landmark_name (str): Name of the landmark
            
        Returns:
            Tuple[int, int]: (x, y) pixel coordinates or None if not found
        """
        try:
            normalized_coords = self.get_landmark_coordinates(pose_data, landmark_name)
            if not normalized_coords:
                return None
            
            width = pose_data['image_dimensions']['width']
            height = pose_data['image_dimensions']['height']
            
            x_pixel = int(normalized_coords[0] * width)
            y_pixel = int(normalized_coords[1] * height)
            
            return (x_pixel, y_pixel)
            
        except Exception as e:
            logger.error(f"Error getting pixel coordinates: {str(e)}")
            return None
    
    def calculate_distance_pixels(self, pose_data: Dict, point1: str, point2: str) -> Optional[float]:
        """
        Calculate pixel distance between two landmarks
        
        Args:
            pose_data (Dict): Pose detection results
            point1 (str): First landmark name
            point2 (str): Second landmark name
            
        Returns:
            float: Distance in pixels or None if calculation fails
        """
        try:
            coords1 = self.get_pixel_coordinates(pose_data, point1)
            coords2 = self.get_pixel_coordinates(pose_data, point2)
            
            if not coords1 or not coords2:
                return None
            
            # Calculate Euclidean distance
            distance = np.sqrt((coords1[0] - coords2[0])**2 + (coords1[1] - coords2[1])**2)
            return float(distance)
            
        except Exception as e:
            logger.error(f"Error calculating distance: {str(e)}")
            return None
    
    def get_image_dimensions(self, image_path: str) -> Optional[Tuple[int, int]]:
        """
        Get image dimensions
        
        Args:
            image_path (str): Path to image file
            
        Returns:
            Tuple[int, int]: (width, height) or None if error
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                return None
            
            height, width = image.shape[:2]
            return (width, height)
            
        except Exception as e:
            logger.error(f"Error getting image dimensions: {str(e)}")
            return None
    
    def draw_pose_landmarks(self, image_path: str, output_path: str, pose_data: Dict) -> bool:
        """
        Draw pose landmarks on image for debugging
        
        Args:
            image_path (str): Input image path
            output_path (str): Output image path
            pose_data (Dict): Pose detection results
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                return False
            
            # Convert landmarks back to MediaPipe format for drawing
            mp_landmarks = []
            for landmark_data in pose_data['landmarks']:
                mp_landmark = self.mp_pose.PoseLandmark()
                mp_landmark.x = landmark_data['x']
                mp_landmark.y = landmark_data['y']
                mp_landmark.z = landmark_data['z']
                mp_landmark.visibility = landmark_data['visibility']
                mp_landmarks.append(mp_landmark)
            
            # Create MediaPipe landmarks object
            pose_landmarks = self.mp_pose.PoseLandmarks()
            pose_landmarks.landmark.extend(mp_landmarks)
            
            # Draw landmarks
            self.mp_drawing.draw_landmarks(
                image, 
                pose_landmarks, 
                self.mp_pose.POSE_CONNECTIONS
            )
            
            # Save annotated image
            cv2.imwrite(output_path, image)
            return True
            
        except Exception as e:
            logger.error(f"Error drawing pose landmarks: {str(e)}")
            return False
    
    def __del__(self):
        """Clean up resources"""
        if hasattr(self, 'pose'):
            self.pose.close()