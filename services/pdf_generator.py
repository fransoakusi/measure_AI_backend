"""
PDF Generator Service
Creates professional measurement reports for clients
"""

import os
import logging
from datetime import datetime
from typing import Dict, Optional
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, grey
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import uuid

logger = logging.getLogger(__name__)

class PDFGenerator:
    """Generate professional PDF measurement reports"""
    
    def __init__(self):
        """Initialize PDF generator with styling"""
        self.page_size = letter
        self.margin = 0.75 * inch
        
        # Colors
        self.primary_color = HexColor('#2563eb')  # Indigo-600
        self.secondary_color = HexColor('#64748b')  # Slate-500
        self.accent_color = HexColor('#059669')  # Emerald-600
        
        # Company information
        self.company_name = "TailorMeasure AI"
        self.company_tagline = "Professional AI-Powered Body Measurements"
        self.company_address = "Professional Tailoring Solutions"
        
        logger.info("PDF Generator initialized")
    
    def generate_measurement_report(self, client_info: Dict, measurements: Dict, metadata: Dict = None) -> str:
        """
        Generate comprehensive measurement report PDF
        
        Args:
            client_info (Dict): Client information
            measurements (Dict): Body measurements
            metadata (Dict): Additional metadata
            
        Returns:
            str: Generated PDF filename
        """
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            client_name = client_info.get('name', 'client').replace(' ', '_')
            filename = f"measurement_report_{client_name}_{timestamp}.pdf"
            
            # Get export folder from environment or use default
            export_folder = os.environ.get('EXPORT_FOLDER', 'exports')
            os.makedirs(export_folder, exist_ok=True)
            
            filepath = os.path.join(export_folder, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(
                filepath,
                pagesize=self.page_size,
                rightMargin=self.margin,
                leftMargin=self.margin,
                topMargin=self.margin,
                bottomMargin=self.margin
            )
            
            # Build document content
            story = []
            story.extend(self._create_header())
            story.extend(self._create_client_section(client_info))
            story.extend(self._create_measurements_section(measurements))
            story.extend(self._create_guidelines_section())
            story.extend(self._create_footer(metadata))
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"Generated PDF report: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}")
            raise
    
    def _create_header(self) -> list:
        """Create PDF header with company branding"""
        styles = getSampleStyleSheet()
        story = []
        
        # Company name
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=6,
            alignment=TA_CENTER,
            textColor=self.primary_color,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=self.secondary_color,
            fontName='Helvetica'
        )
        
        story.append(Paragraph(self.company_name, title_style))
        story.append(Paragraph(self.company_tagline, subtitle_style))
        
        # Horizontal line
        story.append(HRFlowable(width="100%", thickness=2, color=self.primary_color))
        story.append(Spacer(1, 20))
        
        # Report title
        report_title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading2'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=black,
            fontName='Helvetica-Bold'
        )
        
        story.append(Paragraph("BODY MEASUREMENT REPORT", report_title_style))
        
        return story
    
    def _create_client_section(self, client_info: Dict) -> list:
        """Create client information section"""
        styles = getSampleStyleSheet()
        story = []
        
        # Section header
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=10,
            textColor=self.primary_color,
            fontName='Helvetica-Bold'
        )
        
        story.append(Paragraph("CLIENT INFORMATION", section_style))
        
        # Client details table
        client_data = [
            ['Name:', client_info.get('name', 'N/A')],
            ['Email:', client_info.get('email', 'N/A')],
            ['Phone:', client_info.get('phone', 'N/A')],
            ['Date:', datetime.now().strftime("%B %d, %Y")],
            ['Time:', datetime.now().strftime("%I:%M %p")]
        ]
        
        # Filter out empty fields
        client_data = [row for row in client_data if row[1] and row[1] != 'N/A']
        
        client_table = Table(client_data, colWidths=[1.5*inch, 4*inch])
        client_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), self.secondary_color),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        story.append(client_table)
        story.append(Spacer(1, 20))
        
        # Notes section if available
        if client_info.get('notes'):
            notes_style = ParagraphStyle(
                'Notes',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=20,
                textColor=self.secondary_color
            )
            story.append(Paragraph(f"<b>Notes:</b> {client_info['notes']}", notes_style))
        
        return story
    
    def _create_measurements_section(self, measurements: Dict) -> list:
        """Create measurements section with detailed table"""
        styles = getSampleStyleSheet()
        story = []
        
        # Section header
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=15,
            textColor=self.primary_color,
            fontName='Helvetica-Bold'
        )
        
        story.append(Paragraph("BODY MEASUREMENTS", section_style))
        
        # Measurement mapping for better display
        measurement_labels = {
            'chest': 'Chest',
            'waist': 'Waist',
            'hips': 'Hips',
            'shoulders': 'Shoulder Width',
            'armLength': 'Arm Length',
            'inseam': 'Inseam',
            'neck': 'Neck',
            'bicep': 'Bicep',
            'thigh': 'Thigh',
            'wrist': 'Wrist',
            'confidence': 'Measurement Confidence'
        }
        
        # Create measurements table
        measurement_data = [['MEASUREMENT', 'VALUE']]  # Header row
        
        for key, value in measurements.items():
            if key == 'confidence':
                continue  # Handle confidence separately
            
            label = measurement_labels.get(key, key.title())
            measurement_data.append([label, value])
        
        # Create table
        measurements_table = Table(measurement_data, colWidths=[3*inch, 2*inch])
        measurements_table.setStyle(TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), 'white'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), ['white', HexColor('#f8fafc')]),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#e2e8f0')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, self.primary_color),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        story.append(measurements_table)
        story.append(Spacer(1, 20))
        
        # Confidence score
        if 'confidence' in measurements:
            confidence_style = ParagraphStyle(
                'Confidence',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=20,
                alignment=TA_CENTER,
                textColor=self.accent_color,
                fontName='Helvetica-Bold'
            )
            
            confidence_text = f"Measurement Accuracy: {measurements['confidence']}"
            story.append(Paragraph(confidence_text, confidence_style))
        
        return story
    
    def _create_guidelines_section(self) -> list:
        """Create measurement guidelines section"""
        styles = getSampleStyleSheet()
        story = []
        
        # Section header
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=10,
            textColor=self.primary_color,
            fontName='Helvetica-Bold'
        )
        
        story.append(Paragraph("MEASUREMENT GUIDELINES", section_style))
        
        # Guidelines text
        guidelines_style = ParagraphStyle(
            'Guidelines',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=5,
            textColor=self.secondary_color,
            leftIndent=20
        )
        
        guidelines = [
            "• These measurements are AI-generated estimates based on body pose analysis",
            "• Measurements are calculated using advanced computer vision technology",
            "• For critical tailoring work, verify measurements with physical measuring tape",
            "• Accuracy may vary based on photo quality and body positioning",
            "• Best results achieved with full-body, front-facing photos in good lighting",
            "• Client should stand upright with arms slightly away from body"
        ]
        
        for guideline in guidelines:
            story.append(Paragraph(guideline, guidelines_style))
        
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_footer(self, metadata: Dict = None) -> list:
        """Create PDF footer with metadata"""
        styles = getSampleStyleSheet()
        story = []
        
        # Horizontal line
        story.append(HRFlowable(width="100%", thickness=1, color=self.secondary_color))
        story.append(Spacer(1, 10))
        
        # Footer information
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=self.secondary_color,
            alignment=TA_CENTER
        )
        
        footer_text = f"""
        <b>{self.company_name}</b> | {self.company_address}<br/>
        Report generated on {datetime.now().strftime("%B %d, %Y at %I:%M %p")}<br/>
        Powered by AI Computer Vision Technology
        """
        
        story.append(Paragraph(footer_text, footer_style))
        
        # Technical metadata if available
        if metadata:
            tech_info = []
            if metadata.get('processing_time'):
                tech_info.append(f"Processing Time: {metadata['processing_time']:.1f}s")
            if metadata.get('image_filename'):
                tech_info.append(f"Source Image: {metadata['image_filename']}")
            
            if tech_info:
                tech_style = ParagraphStyle(
                    'TechInfo',
                    parent=styles['Normal'],
                    fontSize=7,
                    textColor=grey,
                    alignment=TA_CENTER,
                    spaceAfter=0
                )
                
                story.append(Spacer(1, 5))
                story.append(Paragraph(" | ".join(tech_info), tech_style))
        
        return story
    
    def generate_comparison_report(self, client_info: Dict, measurements_history: list) -> str:
        """
        Generate comparison report showing measurement changes over time
        
        Args:
            client_info (Dict): Client information
            measurements_history (list): List of measurement records
            
        Returns:
            str: Generated PDF filename
        """
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            client_name = client_info.get('name', 'client').replace(' ', '_')
            filename = f"measurement_comparison_{client_name}_{timestamp}.pdf"
            
            export_folder = os.environ.get('EXPORT_FOLDER', 'exports')
            filepath = os.path.join(export_folder, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=self.page_size)
            story = []
            
            # Add header
            story.extend(self._create_header())
            
            # Add comparison content
            story.extend(self._create_comparison_content(client_info, measurements_history))
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"Generated comparison report: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error generating comparison report: {str(e)}")
            raise
    
    def _create_comparison_content(self, client_info: Dict, measurements_history: list) -> list:
        """Create comparison content for measurement history"""
        # This would be implemented for measurement comparison functionality
        # For now, return empty list
        return []