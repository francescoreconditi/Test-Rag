"""Professional PDF exporter with ZCS-inspired design."""

import io
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
    Flowable,
)
from reportlab.graphics.shapes import Drawing, Line, Rect
from reportlab.graphics import renderPDF


# ZCS Company inspired color palette
class ZCSColors:
    """ZCS Company brand colors."""
    PRIMARY_BLUE = HexColor('#003366')      # Deep navy blue
    SECONDARY_GREEN = HexColor('#00A86B')   # Emerald green
    ACCENT_LIGHT_BLUE = HexColor('#4A90E2') # Light blue
    TEXT_DARK = HexColor('#2C3E50')         # Dark gray for text
    TEXT_LIGHT = HexColor('#7F8C8D')        # Light gray for secondary text
    BACKGROUND_LIGHT = HexColor('#F8F9FA')  # Light gray background
    BACKGROUND_WHITE = HexColor('#FFFFFF')  # Pure white
    BORDER_LIGHT = HexColor('#E0E0E0')      # Light border
    SUCCESS_GREEN = HexColor('#27AE60')     # Success green
    WARNING_ORANGE = HexColor('#F39C12')    # Warning orange


class HeaderFooterCanvas(canvas.Canvas):
    """Custom canvas for professional header and footer."""
    
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []
        self.width, self.height = A4
    
    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()
    
    def save(self):
        page_count = len(self.pages)
        for page_num, page in enumerate(self.pages, start=1):
            self.__dict__.update(page)
            self.draw_header_footer(page_num, page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
    
    def draw_header_footer(self, page_num, page_count):
        """Draw professional header and footer."""
        # Header
        self.setFillColor(ZCSColors.PRIMARY_BLUE)
        self.rect(0, self.height - 60, self.width, 60, fill=1, stroke=0)
        
        # Header text
        self.setFillColor(colors.white)
        self.setFont("Helvetica-Bold", 14)
        self.drawString(30, self.height - 35, "Business Intelligence RAG System")
        
        # Header line accent
        self.setStrokeColor(ZCSColors.SECONDARY_GREEN)
        self.setLineWidth(3)
        self.line(30, self.height - 55, 150, self.height - 55)
        
        # Footer
        self.setFillColor(ZCSColors.BACKGROUND_LIGHT)
        self.rect(0, 0, self.width, 40, fill=1, stroke=0)
        
        # Footer content
        self.setFillColor(ZCSColors.TEXT_DARK)
        self.setFont("Helvetica", 9)
        self.drawString(30, 20, f"Pagina {page_num} di {page_count}")
        
        # Timestamp
        self.drawRightString(self.width - 30, 20, 
                            f"Generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        # Footer accent line
        self.setStrokeColor(ZCSColors.SECONDARY_GREEN)
        self.setLineWidth(1)
        self.line(30, 35, self.width - 30, 35)


class SectionHeader(Flowable):
    """Custom flowable for section headers with colored background."""
    
    def __init__(self, text, color=None):
        Flowable.__init__(self)
        self.text = text
        self.color = color or ZCSColors.PRIMARY_BLUE
        self.height = 40
        self.width = 500
    
    def draw(self):
        # Draw background
        self.canv.setFillColor(self.color)
        self.canv.roundRect(0, 0, self.width, self.height, 5, fill=1, stroke=0)
        
        # Draw text
        self.canv.setFillColor(colors.white)
        self.canv.setFont("Helvetica-Bold", 14)
        self.canv.drawString(15, 12, self.text)


class GradientBackground(Flowable):
    """Gradient background for title sections."""
    
    def __init__(self, width, height, start_color, end_color):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.start_color = start_color
        self.end_color = end_color
    
    def draw(self):
        # Simple gradient effect using multiple rectangles
        steps = 20
        for i in range(steps):
            ratio = i / float(steps)
            r = self.start_color.red * (1 - ratio) + self.end_color.red * ratio
            g = self.start_color.green * (1 - ratio) + self.end_color.green * ratio
            b = self.start_color.blue * (1 - ratio) + self.end_color.blue * ratio
            
            self.canv.setFillColor(HexColor(f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'))
            y = self.height * i / steps
            h = self.height / steps
            self.canv.rect(0, y, self.width, h, fill=1, stroke=0)


class PDFExporter:
    """Professional PDF exporter with ZCS-inspired design."""
    
    def __init__(self):
        """Initialize PDF exporter with professional styling."""
        self.styles = getSampleStyleSheet()
        self._setup_professional_styles()
    
    def _setup_professional_styles(self):
        """Setup professional paragraph styles with ZCS branding."""
        
        # Main title style
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=ZCSColors.PRIMARY_BLUE,
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=30
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=ZCSColors.TEXT_LIGHT,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=ZCSColors.PRIMARY_BLUE,
            fontName='Helvetica-Bold',
            spaceBefore=20,
            spaceAfter=15,
            borderColor=ZCSColors.SECONDARY_GREEN,
            borderWidth=0,
            borderPadding=5,
            leftIndent=0
        ))
        
        # Question style - elegant
        self.styles.add(ParagraphStyle(
            name='QuestionStyle',
            parent=self.styles['Normal'],
            fontSize=13,
            textColor=ZCSColors.PRIMARY_BLUE,
            fontName='Helvetica-Bold',
            spaceBefore=15,
            spaceAfter=10,
            leftIndent=10,
            borderColor=ZCSColors.ACCENT_LIGHT_BLUE,
            borderWidth=0,
            borderPadding=3
        ))
        
        # Answer style - professional
        self.styles.add(ParagraphStyle(
            name='AnswerStyle',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=ZCSColors.TEXT_DARK,
            alignment=TA_JUSTIFY,
            spaceAfter=15,
            leftIndent=10,
            rightIndent=10,
            fontName='Helvetica',
            leading=14
        ))
        
        # Source style - refined
        self.styles.add(ParagraphStyle(
            name='SourceStyle',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=ZCSColors.TEXT_LIGHT,
            spaceAfter=8,
            leftIndent=20,
            rightIndent=20,
            fontName='Helvetica-Oblique',
            backColor=ZCSColors.BACKGROUND_LIGHT,
            borderColor=ZCSColors.BORDER_LIGHT,
            borderWidth=0.5,
            borderPadding=5
        ))
        
        # Metadata style - subtle
        self.styles.add(ParagraphStyle(
            name='MetadataStyle',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=ZCSColors.TEXT_LIGHT,
            spaceAfter=10,
            alignment=TA_RIGHT,
            fontName='Helvetica'
        ))
        
        # Executive summary style
        self.styles.add(ParagraphStyle(
            name='ExecutiveSummary',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=ZCSColors.TEXT_DARK,
            alignment=TA_JUSTIFY,
            spaceAfter=20,
            leftIndent=30,
            rightIndent=30,
            fontName='Helvetica',
            leading=16,
            backColor=HexColor('#F0F8FF'),
            borderColor=ZCSColors.ACCENT_LIGHT_BLUE,
            borderWidth=1,
            borderPadding=10
        ))
    
    def _create_professional_table(self, data, col_widths=None, style_name='professional'):
        """Create a professionally styled table."""
        
        table = Table(data, colWidths=col_widths)
        
        if style_name == 'professional':
            table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), ZCSColors.PRIMARY_BLUE),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                
                # Body styling
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, ZCSColors.BACKGROUND_LIGHT]),
                
                # Borders
                ('GRID', (0, 0), (-1, -1), 0.5, ZCSColors.BORDER_LIGHT),
                ('LINEBELOW', (0, 0), (-1, 0), 2, ZCSColors.SECONDARY_GREEN),
            ]))
        
        elif style_name == 'compact':
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (0, -1), ZCSColors.PRIMARY_BLUE),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
        
        return table
    
    def _create_divider(self, width=450, color=None):
        """Create a styled divider line."""
        color = color or ZCSColors.BORDER_LIGHT
        drawing = Drawing(width, 10)
        line = Line(0, 5, width, 5)
        line.strokeColor = color
        line.strokeWidth = 1
        drawing.add(line)
        return drawing
    
    def export_qa_session(
        self,
        question: str,
        answer: str,
        sources: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        filename: Optional[str] = None
    ) -> io.BytesIO:
        """Export a single Q&A session with professional styling."""
        
        buffer = io.BytesIO()
        doc = BaseDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=80,
            bottomMargin=60
        )
        
        # Create page template with custom canvas
        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id='normal'
        )
        
        template = PageTemplate(
            id='professional',
            frames=frame,
            onPage=self._add_page_decoration
        )
        doc.addPageTemplates([template])
        
        story = []
        
        # Title section with gradient effect
        story.append(Paragraph("Analisi Q&A Intelligence", self.styles['MainTitle']))
        story.append(Paragraph("Business Intelligence RAG System", self.styles['Subtitle']))
        story.append(self._create_divider(width=450, color=ZCSColors.SECONDARY_GREEN))
        story.append(Spacer(1, 30))
        
        # Metadata section if available
        if metadata:
            story.append(SectionHeader("Informazioni Sessione", ZCSColors.ACCENT_LIGHT_BLUE))
            story.append(Spacer(1, 10))
            
            metadata_data = []
            for key, value in metadata.items():
                formatted_key = key.replace('_', ' ').title()
                metadata_data.append([formatted_key, str(value)])
            
            if metadata_data:
                metadata_table = self._create_professional_table(
                    metadata_data, 
                    col_widths=[2.5*inch, 3.5*inch],
                    style_name='compact'
                )
                story.append(metadata_table)
                story.append(Spacer(1, 20))
        
        # Question section
        story.append(SectionHeader("Domanda", ZCSColors.PRIMARY_BLUE))
        story.append(Spacer(1, 10))
        story.append(Paragraph(self._clean_text(question), self.styles['QuestionStyle']))
        story.append(Spacer(1, 20))
        
        # Answer section
        story.append(SectionHeader("Risposta", ZCSColors.SECONDARY_GREEN))
        story.append(Spacer(1, 10))
        story.append(Paragraph(self._clean_text(answer), self.styles['AnswerStyle']))
        story.append(Spacer(1, 25))
        
        # Sources section
        if sources:
            story.append(SectionHeader(f"Fonti Utilizzate ({len(sources)})", ZCSColors.ACCENT_LIGHT_BLUE))
            story.append(Spacer(1, 15))
            
            for i, source in enumerate(sources, 1):
                # Create a keep-together block for each source
                source_elements = []
                
                # Source header with relevance score
                score = source.get('score', 0)
                source_header = f"<b>Fonte {i}</b> - Rilevanza: {score:.1%}"
                source_elements.append(Paragraph(source_header, self.styles['QuestionStyle']))
                
                # Source content in a styled box
                source_text = source.get('text', 'N/A')
                if len(source_text) > 400:
                    source_text = source_text[:400] + "..."
                source_elements.append(Paragraph(self._clean_text(source_text), self.styles['SourceStyle']))
                
                # Source metadata
                if source.get('metadata'):
                    metadata_items = []
                    for key in ['source', 'page', 'file_type']:
                        if key in source['metadata']:
                            value = source['metadata'][key]
                            metadata_items.append(f"<i>{key.title()}: {value}</i>")
                    
                    if metadata_items:
                        metadata_text = " | ".join(metadata_items)
                        source_elements.append(Paragraph(metadata_text, self.styles['MetadataStyle']))
                
                source_elements.append(Spacer(1, 10))
                
                # Keep source elements together
                story.append(KeepTogether(source_elements))
        
        # Footer disclaimer
        story.append(Spacer(1, 30))
        story.append(self._create_divider(width=450))
        story.append(Spacer(1, 10))
        disclaimer = (
            "<i>Questo documento è stato generato automaticamente dal Sistema RAG di Business Intelligence. "
            "Le informazioni sono basate su analisi AI dei documenti aziendali indicizzati.</i>"
        )
        story.append(Paragraph(disclaimer, self.styles['MetadataStyle']))
        
        # Build PDF
        doc.build(story, canvasmaker=HeaderFooterCanvas)
        buffer.seek(0)
        return buffer
    
    def export_document_analysis(
        self,
        document_analyses: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None,
        filename: Optional[str] = None
    ) -> io.BytesIO:
        """Export document analysis with professional styling."""
        
        buffer = io.BytesIO()
        doc = BaseDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=80,
            bottomMargin=60
        )
        
        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id='normal'
        )
        
        template = PageTemplate(
            id='professional',
            frames=frame,
            onPage=self._add_page_decoration
        )
        doc.addPageTemplates([template])
        
        story = []
        
        # Title section
        story.append(Paragraph("Analisi Documenti Aziendali", self.styles['MainTitle']))
        story.append(Paragraph("Powered by AI Intelligence", self.styles['Subtitle']))
        story.append(self._create_divider(width=450, color=ZCSColors.SECONDARY_GREEN))
        story.append(Spacer(1, 30))
        
        # Executive summary if multiple documents
        if len(document_analyses) > 1:
            story.append(SectionHeader("Executive Summary", ZCSColors.PRIMARY_BLUE))
            story.append(Spacer(1, 10))
            
            summary_text = f"Sono stati analizzati <b>{len(document_analyses)}</b> documenti aziendali. "
            summary_text += "Ogni documento è stato processato con algoritmi di intelligenza artificiale "
            summary_text += "per estrarre informazioni chiave, metriche e insights strategici."
            
            story.append(Paragraph(summary_text, self.styles['ExecutiveSummary']))
            story.append(Spacer(1, 20))
            
            # Document overview table
            overview_data = [["Documento", "Tipo Analisi", "Lunghezza"]]
            for doc_name, analysis in document_analyses.items():
                doc_type = "Finanziaria" if "bilancio" in doc_name.lower() else "Generale"
                word_count = len(analysis.split())
                overview_data.append([doc_name[:40], doc_type, f"{word_count} parole"])
            
            overview_table = self._create_professional_table(
                overview_data,
                col_widths=[3*inch, 1.5*inch, 1.5*inch]
            )
            story.append(overview_table)
            story.append(PageBreak())
        
        # Individual document analyses
        for i, (file_name, analysis) in enumerate(document_analyses.items(), 1):
            # Document header
            story.append(SectionHeader(f"Documento {i}: {file_name}", ZCSColors.ACCENT_LIGHT_BLUE))
            story.append(Spacer(1, 15))
            
            # Analysis content with formatting
            formatted_analysis = self._format_analysis_content(analysis)
            story.append(Paragraph(formatted_analysis, self.styles['AnswerStyle']))
            story.append(Spacer(1, 20))
            
            if i < len(document_analyses):
                story.append(PageBreak())
        
        # Build PDF
        doc.build(story, canvasmaker=HeaderFooterCanvas)
        buffer.seek(0)
        return buffer
    
    def export_faq(
        self,
        faqs: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        filename: Optional[str] = None
    ) -> io.BytesIO:
        """Export FAQ with professional styling."""
        
        buffer = io.BytesIO()
        doc = BaseDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=80,
            bottomMargin=60
        )
        
        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id='normal'
        )
        
        template = PageTemplate(
            id='professional',
            frames=frame,
            onPage=self._add_page_decoration
        )
        doc.addPageTemplates([template])
        
        story = []
        
        # Title section
        story.append(Paragraph("Frequently Asked Questions", self.styles['MainTitle']))
        story.append(Paragraph("Knowledge Base Intelligence", self.styles['Subtitle']))
        story.append(self._create_divider(width=450, color=ZCSColors.SECONDARY_GREEN))
        story.append(Spacer(1, 30))
        
        # Metadata section
        if metadata:
            story.append(SectionHeader("Informazioni FAQ", ZCSColors.ACCENT_LIGHT_BLUE))
            story.append(Spacer(1, 10))
            
            info_text = f"Generate automaticamente da <b>{metadata.get('total_documents', 'N/A')}</b> vettori di documenti. "
            if metadata.get('document_types'):
                types = ', '.join(metadata['document_types'])
                info_text += f"Tipologie documenti: <i>{types}</i>."
            
            story.append(Paragraph(info_text, self.styles['ExecutiveSummary']))
            story.append(Spacer(1, 20))
        
        # FAQ Index (if more than 5 questions)
        if len(faqs) > 5:
            story.append(SectionHeader("Indice Domande", ZCSColors.PRIMARY_BLUE))
            story.append(Spacer(1, 10))
            
            for i, faq in enumerate(faqs, 1):
                question_preview = faq.get('question', '')[:80]
                if len(faq.get('question', '')) > 80:
                    question_preview += "..."
                index_text = f"<b>{i}.</b> {question_preview}"
                story.append(Paragraph(index_text, self.styles['SourceStyle']))
            
            story.append(PageBreak())
        
        # FAQ Content
        for i, faq in enumerate(faqs, 1):
            # Keep Q&A together if possible
            qa_elements = []
            
            # Question with number badge
            question_header = f"<b>Domanda {i}</b>"
            qa_elements.append(Paragraph(question_header, self.styles['SectionHeader']))
            qa_elements.append(Paragraph(self._clean_text(faq.get('question', 'N/A')), 
                                        self.styles['QuestionStyle']))
            qa_elements.append(Spacer(1, 10))
            
            # Answer
            qa_elements.append(Paragraph("<b>Risposta:</b>", self.styles['SectionHeader']))
            qa_elements.append(Paragraph(self._clean_text(faq.get('answer', 'N/A')), 
                                        self.styles['AnswerStyle']))
            
            # Sources summary (compact)
            sources = faq.get('sources', [])
            if sources:
                qa_elements.append(Spacer(1, 10))
                sources_text = f"<i>Basato su {len(sources)} fonti documentali</i>"
                qa_elements.append(Paragraph(sources_text, self.styles['MetadataStyle']))
            
            qa_elements.append(Spacer(1, 15))
            
            # Divider between questions
            if i < len(faqs):
                qa_elements.append(self._create_divider(width=400, color=ZCSColors.BORDER_LIGHT))
                qa_elements.append(Spacer(1, 15))
            
            story.extend(qa_elements)
        
        # Build PDF
        doc.build(story, canvasmaker=HeaderFooterCanvas)
        buffer.seek(0)
        return buffer
    
    def _add_page_decoration(self, canvas, doc):
        """Add page decorations (called by ReportLab)."""
        # This is handled by HeaderFooterCanvas
        pass
    
    def _format_analysis_content(self, text: str) -> str:
        """Format analysis content with proper structure."""
        # Add formatting for better readability
        text = self._clean_text(text)
        
        # Highlight key sections
        text = text.replace("## ", "<b>")
        text = text.replace("\n\n", "</b><br/><br/>")
        
        return text
    
    def _clean_text(self, text: str) -> str:
        """Clean and format text for PDF generation."""
        if not text:
            return ""
        
        import re
        
        # Remove any existing HTML/XML tags
        text = re.sub(r'<[^>]*>', '', text)
        
        # Clean formatting artifacts
        text = re.sub(r'\n\d+\n', '\n', text)
        text = re.sub(r'\n\d+$', '', text, flags=re.MULTILINE)
        
        # Convert markdown headers to bold
        text = re.sub(r'#{3,}\s*(.*?)(?=\n|$)', r'<b>\1</b>', text, flags=re.MULTILINE)
        text = re.sub(r'#{2}\s*(.*?)(?=\n|$)', r'<b>\1</b>', text, flags=re.MULTILINE)
        text = re.sub(r'#{1}\s*(.*?)(?=\n|$)', r'<b>\1</b>', text, flags=re.MULTILINE)
        
        # Escape HTML entities
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        # Restore our formatting tags
        text = text.replace('&lt;b&gt;', '<b>')
        text = text.replace('&lt;/b&gt;', '</b>')
        text = text.replace('&lt;i&gt;', '<i>')
        text = text.replace('&lt;/i&gt;', '</i>')
        
        # Convert markdown bold/italic
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        
        # Handle newlines
        text = text.replace('\n\n', '<br/><br/>')
        text = text.replace('\n', '<br/>')
        
        # Clean up multiple breaks
        text = re.sub(r'(<br/>){3,}', '<br/><br/>', text)
        
        return text.strip()