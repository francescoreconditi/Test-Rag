# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-08
# Scopo: Estrattore di raw blocks per pagina con preservazione completa
# ============================================

"""
Raw Blocks Extractor per documenti.

Estrae e salva "raw blocks" separati per ogni pagina/sezione di un documento,
preservando la struttura originale per riferimento e tracciabilità.

Supporta:
- PDF: blocchi di testo, tabelle, immagini per pagina
- Excel: blocchi per sheet/range
- HTML/XML: blocchi per sezione/tag
- Word: blocchi per paragrafo/sezione
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Optional, Union

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class BlockType(Enum):
    """Tipi di blocchi estratti."""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    FORMULA = "formula"
    CHART = "chart"
    HEADER = "header"
    FOOTER = "footer"
    FOOTNOTE = "footnote"
    METADATA = "metadata"
    CODE = "code"
    LIST = "list"
    QUOTE = "quote"


class DocumentType(Enum):
    """Tipi di documenti supportati."""
    PDF = "pdf"
    EXCEL = "excel"
    WORD = "word"
    HTML = "html"
    XML = "xml"
    CSV = "csv"
    TEXT = "text"
    IMAGE = "image"


@dataclass
class BoundingBox:
    """Coordinate del bounding box per il blocco."""
    x0: float
    y0: float
    x1: float
    y1: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RawBlock:
    """
    Rappresentazione di un blocco raw estratto.

    Un blocco è un'unità atomica di contenuto (testo, tabella, immagine, etc.)
    con la sua posizione esatta nel documento originale.
    """

    # Identificazione
    block_id: str  # ID univoco del blocco
    document_id: str  # Hash del documento
    document_path: str

    # Posizione
    page_number: Optional[int]  # Per PDF/Word
    sheet_name: Optional[str]  # Per Excel
    section: Optional[str]  # Sezione logica

    # Tipo e contenuto
    block_type: BlockType
    content: Any  # Contenuto raw del blocco
    text_content: Optional[str]  # Versione testuale se disponibile

    # Posizione fisica
    bounding_box: Optional[BoundingBox]  # Coordinate nel documento
    order_index: int  # Ordine di apparizione nella pagina/sezione

    # Metadati
    confidence: float = 1.0  # Confidenza nell'estrazione (0-1)
    extraction_method: str = ""  # Metodo usato per l'estrazione
    timestamp: datetime = None
    metadata: dict[str, Any] = None

    # Relazioni
    parent_block_id: Optional[str] = None  # Per blocchi annidati
    child_block_ids: list[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}
        if self.child_block_ids is None:
            self.child_block_ids = []

    def to_dict(self) -> dict:
        """Serializza il blocco in dizionario."""
        return {
            'block_id': self.block_id,
            'document_id': self.document_id,
            'document_path': self.document_path,
            'page_number': self.page_number,
            'sheet_name': self.sheet_name,
            'section': self.section,
            'block_type': self.block_type.value,
            'content': self.content if isinstance(self.content, (str, int, float, bool, list, dict)) else str(self.content),
            'text_content': self.text_content,
            'bounding_box': self.bounding_box.to_dict() if self.bounding_box else None,
            'order_index': self.order_index,
            'confidence': self.confidence,
            'extraction_method': self.extraction_method,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'parent_block_id': self.parent_block_id,
            'child_block_ids': self.child_block_ids
        }

    def to_source_ref(self) -> str:
        """Genera source reference per questo blocco."""
        if self.page_number is not None:
            return f"{self.document_path}|page:{self.page_number}|block:{self.block_id}"
        elif self.sheet_name:
            return f"{self.document_path}|sheet:{self.sheet_name}|block:{self.block_id}"
        else:
            return f"{self.document_path}|section:{self.section}|block:{self.block_id}"


@dataclass
class PageBlocks:
    """Blocchi estratti da una singola pagina/sezione."""

    page_number: Optional[int]
    sheet_name: Optional[str]
    section_name: Optional[str]
    blocks: list[RawBlock]
    page_metadata: dict[str, Any]

    def get_blocks_by_type(self, block_type: BlockType) -> list[RawBlock]:
        """Ottieni tutti i blocchi di un certo tipo."""
        return [b for b in self.blocks if b.block_type == block_type]

    def get_text_blocks(self) -> list[RawBlock]:
        """Ottieni tutti i blocchi di testo."""
        return self.get_blocks_by_type(BlockType.TEXT)

    def get_table_blocks(self) -> list[RawBlock]:
        """Ottieni tutti i blocchi tabella."""
        return self.get_blocks_by_type(BlockType.TABLE)

    def to_dict(self) -> dict:
        """Serializza in dizionario."""
        return {
            'page_number': self.page_number,
            'sheet_name': self.sheet_name,
            'section_name': self.section_name,
            'blocks': [b.to_dict() for b in self.blocks],
            'page_metadata': self.page_metadata
        }


@dataclass
class DocumentBlocks:
    """Collezione completa di blocchi estratti da un documento."""

    document_id: str
    document_path: str
    document_type: DocumentType
    extraction_timestamp: datetime
    pages: list[PageBlocks]
    document_metadata: dict[str, Any]

    def get_all_blocks(self) -> list[RawBlock]:
        """Ottieni tutti i blocchi del documento."""
        blocks = []
        for page in self.pages:
            blocks.extend(page.blocks)
        return blocks

    def get_blocks_by_page(self, page_number: int) -> Optional[PageBlocks]:
        """Ottieni blocchi di una specifica pagina."""
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None

    def get_blocks_by_type(self, block_type: BlockType) -> list[RawBlock]:
        """Ottieni tutti i blocchi di un certo tipo nel documento."""
        blocks = []
        for page in self.pages:
            blocks.extend(page.get_blocks_by_type(block_type))
        return blocks

    def to_dict(self) -> dict:
        """Serializza in dizionario."""
        return {
            'document_id': self.document_id,
            'document_path': self.document_path,
            'document_type': self.document_type.value,
            'extraction_timestamp': self.extraction_timestamp.isoformat(),
            'pages': [p.to_dict() for p in self.pages],
            'document_metadata': self.document_metadata
        }

    def save_to_json(self, output_path: Union[str, Path]):
        """Salva i blocchi in formato JSON."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_json(cls, json_path: Union[str, Path]) -> 'DocumentBlocks':
        """Carica blocchi da file JSON."""
        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)

        # Ricostruisci oggetti
        pages = []
        for page_data in data['pages']:
            blocks = []
            for block_data in page_data['blocks']:
                # Ricostruisci BoundingBox se presente
                bbox = None
                if block_data.get('bounding_box'):
                    bbox = BoundingBox(**block_data['bounding_box'])

                block = RawBlock(
                    block_id=block_data['block_id'],
                    document_id=block_data['document_id'],
                    document_path=block_data['document_path'],
                    page_number=block_data.get('page_number'),
                    sheet_name=block_data.get('sheet_name'),
                    section=block_data.get('section'),
                    block_type=BlockType(block_data['block_type']),
                    content=block_data['content'],
                    text_content=block_data.get('text_content'),
                    bounding_box=bbox,
                    order_index=block_data['order_index'],
                    confidence=block_data['confidence'],
                    extraction_method=block_data['extraction_method'],
                    timestamp=datetime.fromisoformat(block_data['timestamp']),
                    metadata=block_data.get('metadata', {}),
                    parent_block_id=block_data.get('parent_block_id'),
                    child_block_ids=block_data.get('child_block_ids', [])
                )
                blocks.append(block)

            page = PageBlocks(
                page_number=page_data.get('page_number'),
                sheet_name=page_data.get('sheet_name'),
                section_name=page_data.get('section_name'),
                blocks=blocks,
                page_metadata=page_data.get('page_metadata', {})
            )
            pages.append(page)

        return cls(
            document_id=data['document_id'],
            document_path=data['document_path'],
            document_type=DocumentType(data['document_type']),
            extraction_timestamp=datetime.fromisoformat(data['extraction_timestamp']),
            pages=pages,
            document_metadata=data.get('document_metadata', {})
        )


class RawBlocksExtractor:
    """Estrattore principale per raw blocks da documenti."""

    def __init__(self):
        self.supported_types = {
            '.pdf': DocumentType.PDF,
            '.xlsx': DocumentType.EXCEL,
            '.xls': DocumentType.EXCEL,
            '.docx': DocumentType.WORD,
            '.doc': DocumentType.WORD,
            '.html': DocumentType.HTML,
            '.htm': DocumentType.HTML,
            '.xml': DocumentType.XML,
            '.csv': DocumentType.CSV,
            '.txt': DocumentType.TEXT
        }

    def extract(self, file_path: Union[str, Path]) -> DocumentBlocks:
        """
        Estrae raw blocks dal documento.

        Args:
            file_path: Percorso del documento

        Returns:
            DocumentBlocks con tutti i blocchi estratti
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File non trovato: {file_path}")

        # Determina tipo documento
        doc_type = self._detect_document_type(file_path)

        # Calcola hash documento
        doc_id = self._calculate_document_hash(file_path)

        logger.info(f"Extracting raw blocks from {doc_type.value} document: {file_path}")

        # Estrai blocchi basandosi sul tipo
        if doc_type == DocumentType.PDF:
            pages = self._extract_pdf_blocks(file_path, doc_id)
        elif doc_type == DocumentType.EXCEL:
            pages = self._extract_excel_blocks(file_path, doc_id)
        elif doc_type in [DocumentType.HTML, DocumentType.XML]:
            pages = self._extract_markup_blocks(file_path, doc_id, doc_type)
        else:
            # Fallback per documenti testuali semplici
            pages = self._extract_text_blocks(file_path, doc_id)

        # Crea documento blocks
        return DocumentBlocks(
            document_id=doc_id,
            document_path=str(file_path),
            document_type=doc_type,
            extraction_timestamp=datetime.now(),
            pages=pages,
            document_metadata={
                'file_size': file_path.stat().st_size,
                'file_modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                'extraction_version': '1.0'
            }
        )

    def _detect_document_type(self, file_path: Path) -> DocumentType:
        """Rileva il tipo di documento dall'estensione."""
        suffix = file_path.suffix.lower()
        return self.supported_types.get(suffix, DocumentType.TEXT)

    def _calculate_document_hash(self, file_path: Path) -> str:
        """Calcola hash SHA256 del documento."""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]  # Primi 16 caratteri

    def _extract_pdf_blocks(self, file_path: Path, doc_id: str) -> list[PageBlocks]:
        """Estrae blocchi da PDF usando PyMuPDF."""
        pages = []

        try:
            pdf = fitz.open(str(file_path))

            for page_num, page in enumerate(pdf):
                blocks = []
                order_index = 0

                # Estrai blocchi di testo
                text_blocks = page.get_text("blocks")
                for _idx, block in enumerate(text_blocks):
                    x0, y0, x1, y1, text, block_no, block_type = block

                    # Skip blocchi vuoti
                    if not text or not text.strip():
                        continue

                    raw_block = RawBlock(
                        block_id=f"{doc_id}_p{page_num}_b{order_index}",
                        document_id=doc_id,
                        document_path=str(file_path),
                        page_number=page_num + 1,
                        sheet_name=None,
                        section=f"Page {page_num + 1}",
                        block_type=BlockType.TEXT if block_type == 0 else BlockType.IMAGE,
                        content=text,
                        text_content=text.strip(),
                        bounding_box=BoundingBox(x0, y0, x1, y1),
                        order_index=order_index,
                        confidence=1.0,
                        extraction_method="PyMuPDF",
                        metadata={
                            'font_size': None,  # PyMuPDF non fornisce direttamente
                            'block_number': block_no
                        }
                    )
                    blocks.append(raw_block)
                    order_index += 1

                # Estrai tabelle (se presenti)
                tables = self._extract_pdf_tables(page, page_num, doc_id, order_index)
                blocks.extend(tables)
                order_index += len(tables)

                # Estrai immagini
                images = self._extract_pdf_images(page, page_num, doc_id, order_index)
                blocks.extend(images)

                # Crea PageBlocks
                page_blocks = PageBlocks(
                    page_number=page_num + 1,
                    sheet_name=None,
                    section_name=f"Page {page_num + 1}",
                    blocks=blocks,
                    page_metadata={
                        'width': page.rect.width,
                        'height': page.rect.height,
                        'rotation': page.rotation
                    }
                )
                pages.append(page_blocks)

            pdf.close()

        except Exception as e:
            logger.error(f"Error extracting PDF blocks: {e}")
            raise

        return pages

    def _extract_pdf_tables(self, page, page_num: int, doc_id: str, start_index: int) -> list[RawBlock]:
        """Estrae tabelle da una pagina PDF."""
        tables = []

        try:
            # Usa il metodo di PyMuPDF per trovare tabelle
            # Nota: questo è un approccio semplificato
            # Per tabelle complesse, usare camelot-py o tabula-py

            # Cerca pattern che sembrano tabelle (righe con | o colonne allineate)
            text = page.get_text()
            lines = text.split('\n')

            table_lines = []
            in_table = False

            for line in lines:
                # Semplice euristica: linee con multiple "|" potrebbero essere tabelle
                if line.count('|') >= 2 or line.count('\t') >= 2:
                    if not in_table:
                        in_table = True
                        table_lines = []
                    table_lines.append(line)
                elif in_table and table_lines:
                    # Fine della tabella
                    table_content = '\n'.join(table_lines)

                    table_block = RawBlock(
                        block_id=f"{doc_id}_p{page_num}_t{start_index + len(tables)}",
                        document_id=doc_id,
                        document_path="",  # Sarà impostato dal chiamante
                        page_number=page_num + 1,
                        sheet_name=None,
                        section=f"Page {page_num + 1}",
                        block_type=BlockType.TABLE,
                        content=table_content,
                        text_content=table_content,
                        bounding_box=None,  # Difficile da determinare senza parsing avanzato
                        order_index=start_index + len(tables),
                        confidence=0.7,  # Confidenza più bassa per tabelle euristiche
                        extraction_method="Pattern matching",
                        metadata={'rows': len(table_lines)}
                    )
                    tables.append(table_block)

                    in_table = False
                    table_lines = []

        except Exception as e:
            logger.warning(f"Error extracting tables from page {page_num}: {e}")

        return tables

    def _extract_pdf_images(self, page, page_num: int, doc_id: str, start_index: int) -> list[RawBlock]:
        """Estrae immagini da una pagina PDF."""
        images = []

        try:
            image_list = page.get_images()

            for idx, img in enumerate(image_list):
                xref = img[0]

                # Ottieni metadati immagine
                img_dict = page.parent.extract_image(xref)

                if img_dict:
                    image_block = RawBlock(
                        block_id=f"{doc_id}_p{page_num}_i{start_index + idx}",
                        document_id=doc_id,
                        document_path="",
                        page_number=page_num + 1,
                        sheet_name=None,
                        section=f"Page {page_num + 1}",
                        block_type=BlockType.IMAGE,
                        content=f"Image_{xref}",  # Riferimento all'immagine
                        text_content=None,
                        bounding_box=None,
                        order_index=start_index + idx,
                        confidence=1.0,
                        extraction_method="PyMuPDF",
                        metadata={
                            'width': img_dict.get('width'),
                            'height': img_dict.get('height'),
                            'colorspace': img_dict.get('colorspace'),
                            'bpc': img_dict.get('bpc'),  # Bits per component
                            'xref': xref
                        }
                    )
                    images.append(image_block)

        except Exception as e:
            logger.warning(f"Error extracting images from page {page_num}: {e}")

        return images

    def _extract_excel_blocks(self, file_path: Path, doc_id: str) -> list[PageBlocks]:
        """Estrae blocchi da file Excel."""
        from src.application.parsers.excel_parser import ExcelParser

        pages = []
        parser = ExcelParser()

        try:
            extracted_data = parser.parse(file_path)

            for sheet_idx, sheet_name in enumerate(extracted_data.data_frames.keys()):
                blocks = []
                order_index = 0

                # Estrai blocchi dalle tabelle rilevate
                sheet_tables = [t for t in extracted_data.tables if t.sheet_name == sheet_name]

                for table in sheet_tables:
                    # Crea blocco per la tabella
                    table_block = RawBlock(
                        block_id=f"{doc_id}_s{sheet_idx}_t{order_index}",
                        document_id=doc_id,
                        document_path=str(file_path),
                        page_number=None,
                        sheet_name=sheet_name,
                        section=sheet_name,
                        block_type=BlockType.TABLE,
                        content={
                            'headers': table.headers,
                            'range': f"{table.start_cell}:{table.end_cell}",
                            'rows': table.total_rows,
                            'columns': table.total_columns
                        },
                        text_content=f"Table with {len(table.headers)} columns",
                        bounding_box=None,
                        order_index=order_index,
                        confidence=1.0,
                        extraction_method="ExcelParser",
                        metadata={
                            'has_totals': table.has_totals,
                            'table_name': table.table_name
                        }
                    )
                    blocks.append(table_block)
                    order_index += 1

                # Estrai blocchi per formule
                if sheet_name in extracted_data.formulas:
                    for cell_ref, formula in extracted_data.formulas[sheet_name]:
                        formula_block = RawBlock(
                            block_id=f"{doc_id}_s{sheet_idx}_f{order_index}",
                            document_id=doc_id,
                            document_path=str(file_path),
                            page_number=None,
                            sheet_name=sheet_name,
                            section=sheet_name,
                            block_type=BlockType.FORMULA,
                            content=formula,
                            text_content=formula,
                            bounding_box=None,
                            order_index=order_index,
                            confidence=1.0,
                            extraction_method="ExcelParser",
                            metadata={'cell_reference': cell_ref}
                        )
                        blocks.append(formula_block)
                        order_index += 1

                # Crea PageBlocks per lo sheet
                page_blocks = PageBlocks(
                    page_number=None,
                    sheet_name=sheet_name,
                    section_name=sheet_name,
                    blocks=blocks,
                    page_metadata={
                        'sheet_index': sheet_idx,
                        'max_row': extracted_data.workbook_metadata.sheets[sheet_idx].max_row,
                        'max_column': extracted_data.workbook_metadata.sheets[sheet_idx].max_column
                    }
                )
                pages.append(page_blocks)

        except Exception as e:
            logger.error(f"Error extracting Excel blocks: {e}")
            raise

        return pages

    def _extract_markup_blocks(self, file_path: Path, doc_id: str, doc_type: DocumentType) -> list[PageBlocks]:
        """Estrae blocchi da HTML/XML."""
        from bs4 import BeautifulSoup

        pages = []

        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            soup = BeautifulSoup(content, 'html.parser' if doc_type == DocumentType.HTML else 'xml')

            # Estrai blocchi per sezione/tag principale
            blocks = []
            order_index = 0

            # Headers
            for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                header_block = RawBlock(
                    block_id=f"{doc_id}_h{order_index}",
                    document_id=doc_id,
                    document_path=str(file_path),
                    page_number=None,
                    sheet_name=None,
                    section=header.name,
                    block_type=BlockType.HEADER,
                    content=header.get_text(strip=True),
                    text_content=header.get_text(strip=True),
                    bounding_box=None,
                    order_index=order_index,
                    confidence=1.0,
                    extraction_method="BeautifulSoup",
                    metadata={'tag': header.name}
                )
                blocks.append(header_block)
                order_index += 1

            # Paragraphs
            for p in soup.find_all('p'):
                if p.get_text(strip=True):
                    p_block = RawBlock(
                        block_id=f"{doc_id}_p{order_index}",
                        document_id=doc_id,
                        document_path=str(file_path),
                        page_number=None,
                        sheet_name=None,
                        section="paragraph",
                        block_type=BlockType.TEXT,
                        content=p.get_text(strip=True),
                        text_content=p.get_text(strip=True),
                        bounding_box=None,
                        order_index=order_index,
                        confidence=1.0,
                        extraction_method="BeautifulSoup",
                        metadata={}
                    )
                    blocks.append(p_block)
                    order_index += 1

            # Tables
            for table in soup.find_all('table'):
                table_block = RawBlock(
                    block_id=f"{doc_id}_t{order_index}",
                    document_id=doc_id,
                    document_path=str(file_path),
                    page_number=None,
                    sheet_name=None,
                    section="table",
                    block_type=BlockType.TABLE,
                    content=str(table),
                    text_content=table.get_text(strip=True),
                    bounding_box=None,
                    order_index=order_index,
                    confidence=1.0,
                    extraction_method="BeautifulSoup",
                    metadata={'rows': len(table.find_all('tr'))}
                )
                blocks.append(table_block)
                order_index += 1

            # Crea una singola "pagina" per il documento markup
            page_blocks = PageBlocks(
                page_number=None,
                sheet_name=None,
                section_name="Document",
                blocks=blocks,
                page_metadata={'total_blocks': len(blocks)}
            )
            pages.append(page_blocks)

        except Exception as e:
            logger.error(f"Error extracting markup blocks: {e}")
            raise

        return pages

    def _extract_text_blocks(self, file_path: Path, doc_id: str) -> list[PageBlocks]:
        """Estrae blocchi da file di testo semplice."""
        pages = []

        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            # Dividi in paragrafi
            paragraphs = content.split('\n\n')

            blocks = []
            for idx, para in enumerate(paragraphs):
                if para.strip():
                    text_block = RawBlock(
                        block_id=f"{doc_id}_p{idx}",
                        document_id=doc_id,
                        document_path=str(file_path),
                        page_number=None,
                        sheet_name=None,
                        section="paragraph",
                        block_type=BlockType.TEXT,
                        content=para,
                        text_content=para.strip(),
                        bounding_box=None,
                        order_index=idx,
                        confidence=1.0,
                        extraction_method="Text split",
                        metadata={'paragraph_index': idx}
                    )
                    blocks.append(text_block)

            # Crea una singola "pagina"
            page_blocks = PageBlocks(
                page_number=None,
                sheet_name=None,
                section_name="Document",
                blocks=blocks,
                page_metadata={'total_paragraphs': len(blocks)}
            )
            pages.append(page_blocks)

        except Exception as e:
            logger.error(f"Error extracting text blocks: {e}")
            raise

        return pages
