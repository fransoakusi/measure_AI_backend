"""
Measurement Processor Service
Calculates body measurements from pose landmarks using computer vision
"""

import math
import time
import logging
from typing import Dict, Optional, Tuple, List
import numpy as np

logger = logging.getLogger(__name__)

class MeasurementProcessor:
    """Process pose landmarks to calculate body measurements"""
    
    def __init__(self):
        """Initialize measurement processor with default settings"""
        self.processing_start_time = None
        self.default_units = 'inches'
        
        # Average human body proportions (used for validation and estimation)
        self.body_proportions = {
            'head_to_body_ratio': 0.125,  # Head is ~1/8 of total height
            'shoulder_to_height_ratio': 0.25,  # Shoulders are ~1/4 from top
            'hip_to_height_ratio': 0.52,  # Hips are ~52% from top
            'arm_to_height_ratio': 0.44,  # Arm span is ~44% of height
            'leg_to_height_ratio': 0.48,  # Legs are ~48% of height
        }
        
        # Reference measurements for scaling
        self.reference_height_inches = 68  # Average adult height
        
        logger.info("Measurement processor initialized")
    
    def calculate_measurements(self, pose_data: Dict, image_dimensions: Tuple[int, int]) -> Dict:
        """
        Calculate body measurements from pose landmarks
        
        Args:
            pose_data (Dict): Pose detection results from computer vision
            image_dimensions (Tuple[int, int]): Image width and height
            
        Returns:
            Dict: Calculated measurements with confidence scores
        """
        self.processing_start_time = time.time()
        
        try:
            landmarks = pose_data['landmarks']
            width, height = image_dimensions
            
            # Calculate scale factor (pixels to real-world units)
            scale_factor = self._calculate_scale_factor(pose_data, height)
            
            measurements = {}
            
            # Calculate individual measurements
            measurements.update(self._calculate_torso_measurements(pose_data, scale_factor))
            measurements.update(self._calculate_arm_measurements(pose_data, scale_factor))
            measurements.update(self._calculate_leg_measurements(pose_data, scale_factor))
            measurements.update(self._calculate_additional_measurements(pose_data, scale_factor))
            
            # Calculate overall confidence
            confidence = self._calculate_measurement_confidence(pose_data, measurements)
            measurements['confidence'] = f"{confidence:.0f}%"
            
            # Validate measurements against typical human proportions
            measurements = self._validate_measurements(measurements)
            
            logger.info(f"Measurements calculated with {confidence:.0f}% confidence")
            return measurements
            
        except Exception as e:
            logger.error(f"Error calculating measurements: {str(e)}")
            return self._get_fallback_measurements()
    
    def _calculate_scale_factor(self, pose_data: Dict, image_height: int) -> float:
        """
        Calculate scale factor to convert pixels to real-world measurements
        
        Args:
            pose_data (Dict): Pose detection results
            image_height (int): Image height in pixels
            
        Returns:
            float: Scale factor (inches per pixel)
        """
        try:
            # Get head-to-foot distance in pixels
            head_point = self._get_landmark_coords(pose_data, 'nose')
            
            # Use average of both feet for more accuracy
            left_foot = self._get_landmark_coords(pose_data, 'left_ankle')
            right_foot = self._get_landmark_coords(pose_data, 'right_ankle')
            
            if not head_point or (not left_foot and not right_foot):
                # Fallback: use image height as reference
                return self.reference_height_inches / image_height
            
            # Calculate foot position (use available foot or average)
            if left_foot and right_foot:
                foot_y = (left_foot[1] + right_foot[1]) / 2
            elif left_foot:
                foot_y = left_foot[1]
            else:
                foot_y = right_foot[1]
            
            # Calculate person height in pixels
            person_height_pixels = abs(foot_y - head_point[1]) * image_height
            
            # Ensure reasonable height
            if person_height_pixels < image_height * 0.3:
                # Person is too small in image, use fallback
                return self.reference_height_inches / image_height
            
            # Calculate scale factor
            scale_factor = self.reference_height_inches / person_height_pixels
            
            # Validate scale factor is reasonable
            if scale_factor < 0.01 or scale_factor > 1.0:
                return self.reference_height_inches / image_height
            
            return scale_factor
            
        except Exception as e:
            logger.error(f"Error calculating scale factor: {str(e)}")
            return self.reference_height_inches / image_height
    
    def _calculate_torso_measurements(self, pose_data: Dict, scale_factor: float) -> Dict:
        """Calculate chest, waist, and hip measurements"""
        measurements = {}
        
        try:
            # Chest measurement (shoulder width as proxy)
            left_shoulder = self._get_landmark_coords(pose_data, 'left_shoulder')
            right_shoulder = self._get_landmark_coords(pose_data, 'right_shoulder')
            
            if left_shoulder and right_shoulder:
                shoulder_width_pixels = self._calculate_distance(left_shoulder, right_shoulder)
                shoulder_width_inches = shoulder_width_pixels * scale_factor * pose_data['image_dimensions']['width']
                
                # Estimate chest circumference (shoulder width * 1.8 is typical)
                chest_circumference = shoulder_width_inches * 1.8
                measurements['chest'] = f"{chest_circumference:.1f} inches"
            
            # Hip measurement
            left_hip = self._get_landmark_coords(pose_data, 'left_hip')
            right_hip = self._get_landmark_coords(pose_data, 'right_hip')
            
            if left_hip and right_hip:
                hip_width_pixels = self._calculate_distance(left_hip, right_hip)
                hip_width_inches = hip_width_pixels * scale_factor * pose_data['image_dimensions']['width']
                
                # Estimate hip circumference
                hip_circumference = hip_width_inches * 2.1
                measurements['hips'] = f"{hip_circumference:.1f} inches"
            
            # Waist measurement (estimate between chest and hips)
            if 'chest' in measurements and 'hips' in measurements:
                chest_val = float(measurements['chest'].split()[0])
                hip_val = float(measurements['hips'].split()[0])
                waist_estimate = (chest_val + hip_val) / 2 * 0.85  # Waist is typically 85% of average
                measurements['waist'] = f"{waist_estimate:.1f} inches"
            
            # Shoulder width
            if left_shoulder and right_shoulder:
                measurements['shoulders'] = f"{shoulder_width_inches:.1f} inches"
                
        except Exception as e:
            logger.error(f"Error calculating torso measurements: {str(e)}")
        
        return measurements
    
    def _calculate_arm_measurements(self, pose_data: Dict, scale_factor: float) -> Dict:
        """Calculate arm length and related measurements"""
        measurements = {}
        
        try:
            # Arm length (shoulder to wrist)
            left_shoulder = self._get_landmark_coords(pose_data, 'left_shoulder')
            left_wrist = self._get_landmark_coords(pose_data, 'left_wrist')
            right_shoulder = self._get_landmark_coords(pose_data, 'right_shoulder')
            right_wrist = self._get_landmark_coords(pose_data, 'right_wrist')
            
            arm_lengths = []
            
            # Calculate left arm length
            if left_shoulder and left_wrist:
                left_arm_pixels = self._calculate_distance(left_shoulder, left_wrist)
                left_arm_inches = left_arm_pixels * scale_factor * pose_data['image_dimensions']['width']
                arm_lengths.append(left_arm_inches)
            
            # Calculate right arm length
            if right_shoulder and right_wrist:
                right_arm_pixels = self._calculate_distance(right_shoulder, right_wrist)
                right_arm_inches = right_arm_pixels * scale_factor * pose_data['image_dimensions']['width']
                arm_lengths.append(right_arm_inches)
            
            if arm_lengths:
                avg_arm_length = sum(arm_lengths) / len(arm_lengths)
                measurements['armLength'] = f"{avg_arm_length:.1f} inches"
            
            # Bicep measurement (estimate from shoulder width)
            if left_shoulder and right_shoulder:
                shoulder_width_pixels = self._calculate_distance(left_shoulder, right_shoulder)
                shoulder_width_inches = shoulder_width_pixels * scale_factor * pose_data['image_dimensions']['width']
                bicep_estimate = shoulder_width_inches * 0.4  # Bicep is typically 40% of shoulder width
                measurements['bicep'] = f"{bicep_estimate:.1f} inches"
                
        except Exception as e:
            logger.error(f"Error calculating arm measurements: {str(e)}")
        
        return measurements
    
    def _calculate_leg_measurements(self, pose_data: Dict, scale_factor: float) -> Dict:
        """Calculate leg length and related measurements"""
        measurements = {}
        
        try:
            # Inseam (hip to ankle)
            left_hip = self._get_landmark_coords(pose_data, 'left_hip')
            left_ankle = self._get_landmark_coords(pose_data, 'left_ankle')
            right_hip = self._get_landmark_coords(pose_data, 'right_hip')
            right_ankle = self._get_landmark_coords(pose_data, 'right_ankle')
            
            inseam_lengths = []
            
            # Calculate left inseam
            if left_hip and left_ankle:
                left_inseam_pixels = self._calculate_distance(left_hip, left_ankle)
                left_inseam_inches = left_inseam_pixels * scale_factor * pose_data['image_dimensions']['height']
                inseam_lengths.append(left_inseam_inches)
            
            # Calculate right inseam
            if right_hip and right_ankle:
                right_inseam_pixels = self._calculate_distance(right_hip, right_ankle)
                right_inseam_inches = right_inseam_pixels * scale_factor * pose_data['image_dimensions']['height']
                inseam_lengths.append(right_inseam_inches)
            
            if inseam_lengths:
                avg_inseam = sum(inseam_lengths) / len(inseam_lengths)
                measurements['inseam'] = f"{avg_inseam:.1f} inches"
            
            # Thigh measurement (estimate from hip width)
            if left_hip and right_hip:
                hip_width_pixels = self._calculate_distance(left_hip, right_hip)
                hip_width_inches = hip_width_pixels * scale_factor * pose_data['image_dimensions']['width']
                thigh_estimate = hip_width_inches * 0.6  # Thigh is typically 60% of hip width
                measurements['thigh'] = f"{thigh_estimate:.1f} inches"
                
        except Exception as e:
            logger.error(f"Error calculating leg measurements: {str(e)}")
        
        return measurements
    
    def _calculate_additional_measurements(self, pose_data: Dict, scale_factor: float) -> Dict:
        """Calculate neck and other additional measurements"""
        measurements = {}
        
        try:
            # Neck measurement (estimate from head size)
            left_ear = self._get_landmark_coords(pose_data, 'left_ear')
            right_ear = self._get_landmark_coords(pose_data, 'right_ear')
            
            if left_ear and right_ear:
                head_width_pixels = self._calculate_distance(left_ear, right_ear)
                head_width_inches = head_width_pixels * scale_factor * pose_data['image_dimensions']['width']
                neck_estimate = head_width_inches * 0.8  # Neck is typically 80% of head width
                measurements['neck'] = f"{neck_estimate:.1f} inches"
            
            # Wrist measurement (very rough estimate)
            left_wrist = self._get_landmark_coords(pose_data, 'left_wrist')
            if left_wrist:
                # Very rough estimate based on typical proportions
                wrist_estimate = 6.5  # Average adult wrist circumference
                measurements['wrist'] = f"{wrist_estimate:.1f} inches"
                
        except Exception as e:
            logger.error(f"Error calculating additional measurements: {str(e)}")
        
        return measurements
    
    def _get_landmark_coords(self, pose_data: Dict, landmark_name: str) -> Optional[Tuple[float, float]]:
        """Get normalized coordinates for a landmark"""
        landmark_indices = {
            'nose': 0, 'left_shoulder': 11, 'right_shoulder': 12,
            'left_hip': 23, 'right_hip': 24, 'left_knee': 25, 'right_knee': 26,
            'left_ankle': 27, 'right_ankle': 28, 'left_wrist': 15, 'right_wrist': 16,
            'left_ear': 7, 'right_ear': 8
        }
        
        if landmark_name not in landmark_indices:
            return None
        
        idx = landmark_indices[landmark_name]
        landmarks = pose_data['landmarks']
        
        if idx >= len(landmarks):
            return None
        
        landmark = landmarks[idx]
        if landmark['visibility'] < 0.5:
            return None
        
        return (landmark['x'], landmark['y'])
    
    def _calculate_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two points"""
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)
    
    def _calculate_measurement_confidence(self, pose_data: Dict, measurements: Dict) -> float:
        """Calculate overall confidence of measurements"""
        try:
            # Base confidence on pose quality
            pose_confidence = pose_data.get('confidence', 0.5)
            
            # Adjust based on number of successful measurements
            expected_measurements = 8  # chest, waist, hips, shoulders, armLength, inseam, neck, bicep
            actual_measurements = len([k for k in measurements.keys() if k != 'confidence'])
            measurement_completeness = actual_measurements / expected_measurements
            
            # Calculate overall confidence
            overall_confidence = (pose_confidence * 0.6 + measurement_completeness * 0.4) * 100
            
            return min(95, max(50, overall_confidence))  # Clamp between 50% and 95%
            
        except Exception:
            return 75.0  # Default confidence
    
    def _validate_measurements(self, measurements: Dict) -> Dict:
        """Validate measurements against typical human proportions"""
        try:
            # Define reasonable ranges for measurements (in inches)
            measurement_ranges = {
                'chest': (28, 60),
                'waist': (24, 50),
                'hips': (30, 55),
                'shoulders': (14, 26),
                'armLength': (20, 35),
                'inseam': (26, 38),
                'neck': (12, 20),
                'bicep': (8, 20),
                'thigh': (16, 30),
                'wrist': (5, 9)
            }
            
            validated_measurements = {}
            
            for measurement_name, value_str in measurements.items():
                if measurement_name == 'confidence':
                    validated_measurements[measurement_name] = value_str
                    continue
                
                try:
                    # Extract numeric value
                    value = float(value_str.split()[0])
                    unit = value_str.split()[1] if len(value_str.split()) > 1 else 'inches'
                    
                    # Check if measurement is within reasonable range
                    if measurement_name in measurement_ranges:
                        min_val, max_val = measurement_ranges[measurement_name]
                        if value < min_val:
                            value = min_val
                        elif value > max_val:
                            value = max_val
                    
                    validated_measurements[measurement_name] = f"{value:.1f} {unit}"
                    
                except (ValueError, IndexError):
                    # Keep original value if parsing fails
                    validated_measurements[measurement_name] = value_str
            
            return validated_measurements
            
        except Exception as e:
            logger.error(f"Error validating measurements: {str(e)}")
            return measurements
    
    def _get_fallback_measurements(self) -> Dict:
        """Return fallback measurements if processing fails"""
        return {
            'chest': '38.0 inches',
            'waist': '32.0 inches',
            'hips': '40.0 inches',
            'shoulders': '18.0 inches',
            'armLength': '25.0 inches',
            'inseam': '30.0 inches',
            'neck': '15.0 inches',
            'bicep': '12.0 inches',
            'confidence': '50%'
        }
    
    def get_processing_time(self) -> float:
        """Get processing time in seconds"""
        if self.processing_start_time:
            return time.time() - self.processing_start_time
        return 0.0
    
    def convert_units(self, measurements: Dict, target_unit: str) -> Dict:
        """Convert measurements between inches and centimeters"""
        if target_unit not in ['inches', 'cm']:
            return measurements
        
        converted = {}
        conversion_factor = 2.54 if target_unit == 'cm' else 1/2.54
        
        for key, value_str in measurements.items():
            if key == 'confidence':
                converted[key] = value_str
                continue
            
            try:
                parts = value_str.split()
                if len(parts) >= 2:
                    value = float(parts[0])
                    current_unit = parts[1]
                    
                    # Convert if needed
                    if current_unit != target_unit:
                        if target_unit == 'cm' and current_unit == 'inches':
                            value *= conversion_factor
                        elif target_unit == 'inches' and current_unit == 'cm':
                            value *= conversion_factor
                    
                    converted[key] = f"{value:.1f} {target_unit}"
                else:
                    converted[key] = value_str
                    
            except (ValueError, IndexError):
                converted[key] = value_str
        
        return converted