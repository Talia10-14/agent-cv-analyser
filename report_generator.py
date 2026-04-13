"""
PDF Report Generator for CV Analysis Results
Uses reportlab to generate professional PDF reports
"""

import os
import io
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, Color
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.pdfgen import canvas
from datetime import datetime
from html import unescape


class CVReportGenerator:
    """Generate professional PDF reports from CV analysis results"""
    
    def __init__(self, result: Dict[str, Any]):
        """
        Initialize report generator with analysis result
        
        Args:
            result: Dictionary containing CV analysis data
        """
        self.result = result
        self.primary_color = HexColor("#7C3AED")  # Violet
        self.secondary_color = HexColor("#1E1B4B")  # Dark slate
        self.success_color = HexColor("#10B981")   # Green
        self.warning_color = HexColor("#EF4444")   # Red
        self.light_bg = HexColor("#F5F3FF")        # Light violet
        
    def _sanitize_text(self, text: Optional[str]) -> str:
        """Sanitize and clean text for PDF display"""
        if not text:
            return ""
        # Unescape HTML entities
        text = unescape(text)
        # Remove HTML tags if any
        text = text.replace("<", "&lt;").replace(">", "&gt;")
        return str(text).strip()
    
    def _get_text(self, key: str, fallback: str = "") -> str:
        """Get and sanitize text from result dictionary"""
        value = self.result.get(key, fallback)
        return self._sanitize_text(value)
    
    def _get_list(self, key: str, fallback: list = None) -> list:
        """Get list from result dictionary with fallback"""
        if fallback is None:
            fallback = []
        value = self.result.get(key, fallback)
        if isinstance(value, list):
            return [self._sanitize_text(item) for item in value]
        return fallback
    
    def _build_elements(self, styles):
        """
        Build PDF elements list. Extracted to avoid duplication between 
        generate_pdf() and get_pdf_bytes().
        
        Args:
            styles: ReportLab style sheet
            
        Returns:
            list: Elements ready to be added to PDF document
        """
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=self.secondary_color,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=self.primary_color,
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        subheading_style = ParagraphStyle(
            'SubHeading',
            parent=styles['Normal'],
            fontSize=10,
            textColor=HexColor("#666666"),
            spaceAfter=8,
            fontName='Helvetica'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=HexColor("#333333"),
            leading=14,
            spaceAfter=8
        )
        
        elements = []
        
        # ==================== HEADER ====================
        nom = self._get_text('nom', 'Candidate')
        poste_actuel = self._get_text('poste_actuel', 'Position not specified')
        
        elements.append(Paragraph(nom, title_style))
        elements.append(Paragraph(poste_actuel, subheading_style))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", subheading_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        # ==================== SCORES SECTION ====================
        elements.append(Paragraph("Analysis Scores", heading_style))
        
        score_global = int(self.result.get('score_global', 0))
        score_tech = int(self.result.get('score_technique', 0))
        score_exp = int(self.result.get('score_experience', 0))
        
        # Score table
        score_data = [
            [
                Paragraph("<b>Global Score</b>", normal_style),
                Paragraph(f"{score_global}%", normal_style)
            ],
            [
                Paragraph("<b>Technical Score</b>", normal_style),
                Paragraph(f"{score_tech}%", normal_style)
            ],
            [
                Paragraph("<b>Experience Score</b>", normal_style),
                Paragraph(f"{score_exp}%", normal_style)
            ]
        ]
        
        score_table = Table(score_data, colWidths=[2.5 * inch, 1.5 * inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), self.light_bg),
            ('BACKGROUND', (0, 1), (1, 1), HexColor("#FFFFFF")),
            ('BACKGROUND', (0, 2), (1, 2), HexColor("#FFFFFF")),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.secondary_color),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, HexColor("#E5E7EB")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor("#FFFFFF"), HexColor("#F9FAFB")])
        ]))
        
        elements.append(score_table)
        elements.append(Spacer(1, 0.2 * inch))
        
        # ==================== SKILLS SECTION ====================
        competences = self._get_list('competences') or self._get_list('points_forts')
        if competences:
            elements.append(Paragraph("Key Skills & Competencies", heading_style))
            
            # Create skills text
            skills_text = ", ".join(competences[:20])
            elements.append(Paragraph(skills_text, normal_style))
            elements.append(Spacer(1, 0.15 * inch))
        
        # ==================== STRENGTHS SECTION ====================
        strengths = self._get_list('forces') or self._get_list('points_forts')
        if strengths:
            elements.append(Paragraph("Strengths", heading_style))
            
            for strength in strengths[:6]:
                bullet = Paragraph(f"• {strength}", normal_style)
                elements.append(bullet)
            
            elements.append(Spacer(1, 0.15 * inch))
        
        # ==================== WEAKNESSES SECTION ====================
        weaknesses = self._get_list('faiblesses') or self._get_list('points_faibles')
        if weaknesses:
            elements.append(Paragraph("Areas for Improvement", heading_style))
            
            for weakness in weaknesses[:6]:
                bullet = Paragraph(f"• {weakness}", normal_style)
                elements.append(bullet)
            
            elements.append(Spacer(1, 0.15 * inch))
        
        # ==================== HR ASSESSMENT SECTION ====================
        hr_assessment = self._get_text('avis_rh') or self._get_text('resume_rh', '')
        if hr_assessment:
            elements.append(Paragraph("HR Assessment", heading_style))
            elements.append(Paragraph(hr_assessment, normal_style))
            elements.append(Spacer(1, 0.15 * inch))
        
        # ==================== RECOMMENDATION SECTION ====================
        recommendation = self._get_text('recommendation') or self._get_text('recommandation', '')
        
        rec_map = {
            "KEPT": "✓ RETAINED",
            "CONSIDER": "◐ CONSIDER",
            "REJECTED": "✕ NOT RECOMMENDED",
            "RETENU": "✓ RETAINED",
            "À CONSIDÉRER": "◐ CONSIDER",
        }
        
        rec_text = rec_map.get(recommendation, "- NO RECOMMENDATION")
        
        elements.append(Paragraph("Final Recommendation", heading_style))
        elements.append(Paragraph(f"<b>{rec_text}</b>", normal_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        # ==================== FOOTER ====================
        footer_text = "This report was generated by CV Analyzer. For questions or concerns, please contact HR."
        elements.append(Paragraph(footer_text, 
                                ParagraphStyle(
                                    name='Footer',
                                    fontSize=8,
                                    textColor=HexColor("#999999"),
                                    alignment=1
                                )))
        
        return elements
    
    def generate_pdf(self, output_path: str) -> bool:
        """
        Generate PDF report and save to file.
        
        Args:
            output_path: Path where PDF should be saved
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=0.5 * inch,
                leftMargin=0.5 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch
            )
            
            styles = getSampleStyleSheet()
            elements = self._build_elements(styles)
            
            doc.build(elements)
            return True
            
        except Exception as e:
            print(f"Error generating PDF: {str(e)}")
            return False
    
    def get_pdf_bytes(self) -> Optional[bytes]:
        """
        Generate PDF and return as bytes for Streamlit download.
        
        Returns:
            bytes: PDF content or None if generation failed
        """
        try:
            pdf_buffer = io.BytesIO()
            
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=letter,
                rightMargin=0.5 * inch,
                leftMargin=0.5 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch
            )
            
            styles = getSampleStyleSheet()
            elements = self._build_elements(styles)
            
            doc.build(elements)
            pdf_buffer.seek(0)
            return pdf_buffer.getvalue()
            
        except Exception as e:
            print(f"Error generating PDF bytes: {str(e)}")
            return None
