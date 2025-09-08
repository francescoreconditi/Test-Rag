# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-08
# Scopo: Test per raw blocks extractor
# ============================================

"""Test per RawBlocksExtractor."""

import json
import tempfile
from pathlib import Path
from datetime import datetime

import pytest
import fitz  # PyMuPDF
from openpyxl import Workbook

from src.application.services.raw_blocks_extractor import (
    RawBlocksExtractor,
    RawBlock,
    PageBlocks,
    DocumentBlocks,
    BlockType,
    DocumentType,
    BoundingBox
)


@pytest.fixture
def sample_pdf_file():
    """Crea un file PDF di esempio per i test."""
    # Crea file temporaneo senza context manager per evitare conflitti
    tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()  # Chiudi il file prima di usarlo con PyMuPDF
    
    # Crea PDF con PyMuPDF
    doc = fitz.open()
    
    # Pagina 1
    page1 = doc.new_page()
    page1.insert_text((50, 50), "Bilancio 2024", fontsize=16)
    page1.insert_text((50, 100), "Questo è il bilancio annuale dell'azienda XYZ.")
    page1.insert_text((50, 150), "Ricavi: € 1.000.000")
    page1.insert_text((50, 180), "Costi: € 800.000")
    page1.insert_text((50, 210), "EBITDA: € 200.000")
    
    # Pagina 2
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Dettaglio Costi", fontsize=14)
    page2.insert_text((50, 100), "Personale: € 400.000")
    page2.insert_text((50, 130), "Materiali: € 300.000")
    page2.insert_text((50, 160), "Altri: € 100.000")
    
    doc.save(str(tmp_path))
    doc.close()
    
    return tmp_path


@pytest.fixture
def sample_excel_file():
    """Crea un file Excel di esempio per i test."""
    wb = Workbook()
    
    # Sheet 1
    ws1 = wb.active
    ws1.title = "Dati"
    ws1['A1'] = 'Metrica'
    ws1['B1'] = 'Valore'
    ws1['A2'] = 'Ricavi'
    ws1['B2'] = 1000000
    ws1['A3'] = 'Costi'
    ws1['B3'] = 800000
    ws1['B4'] = '=B2-B3'
    
    # Sheet 2
    ws2 = wb.create_sheet("Grafici")
    ws2['A1'] = 'Grafico vendite'
    
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        wb.save(tmp.name)
        return Path(tmp.name)


@pytest.fixture
def sample_html_file():
    """Crea un file HTML di esempio per i test."""
    html_content = """
    <html>
    <head><title>Report</title></head>
    <body>
        <h1>Annual Report 2024</h1>
        <p>This is the annual report for XYZ Company.</p>
        
        <h2>Financial Highlights</h2>
        <p>Revenue increased by 20% this year.</p>
        
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Revenue</td><td>1,000,000</td></tr>
            <tr><td>Costs</td><td>800,000</td></tr>
        </table>
        
        <h3>Conclusion</h3>
        <p>The company is performing well.</p>
    </body>
    </html>
    """
    
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as tmp:
        tmp.write(html_content)
        return Path(tmp.name)


@pytest.fixture
def sample_text_file():
    """Crea un file di testo di esempio."""
    text_content = """Annual Report 2024

This is the first paragraph of the report.
It contains important financial information.

Revenue: 1,000,000
Costs: 800,000
Profit: 200,000

This is the conclusion paragraph.
The company is doing well."""
    
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w', encoding='utf-8') as tmp:
        tmp.write(text_content)
        return Path(tmp.name)


def test_extractor_initialization():
    """Test inizializzazione extractor."""
    extractor = RawBlocksExtractor()
    
    assert '.pdf' in extractor.supported_types
    assert '.xlsx' in extractor.supported_types
    assert '.html' in extractor.supported_types
    assert extractor.supported_types['.pdf'] == DocumentType.PDF


def test_extract_pdf_blocks(sample_pdf_file):
    """Test estrazione blocchi da PDF."""
    extractor = RawBlocksExtractor()
    document_blocks = extractor.extract(sample_pdf_file)
    
    # Verifica struttura documento
    assert isinstance(document_blocks, DocumentBlocks)
    assert document_blocks.document_type == DocumentType.PDF
    assert document_blocks.document_path == str(sample_pdf_file)
    assert len(document_blocks.pages) == 2  # Due pagine
    
    # Verifica prima pagina
    page1 = document_blocks.pages[0]
    assert page1.page_number == 1
    assert len(page1.blocks) > 0
    
    # Verifica blocchi di testo
    text_blocks = page1.get_text_blocks()
    assert len(text_blocks) > 0
    
    # Verifica contenuto blocchi
    all_text = ' '.join([b.text_content for b in text_blocks if b.text_content])
    assert 'Bilancio' in all_text or 'bilancio' in all_text.lower()
    
    # Verifica metadati blocco
    first_block = page1.blocks[0]
    assert first_block.page_number == 1
    assert first_block.block_type in [BlockType.TEXT, BlockType.IMAGE]
    assert first_block.document_id is not None
    assert first_block.block_id is not None
    assert first_block.confidence == 1.0
    assert first_block.extraction_method == "PyMuPDF"


def test_extract_excel_blocks(sample_excel_file):
    """Test estrazione blocchi da Excel."""
    extractor = RawBlocksExtractor()
    document_blocks = extractor.extract(sample_excel_file)
    
    # Verifica struttura documento
    assert document_blocks.document_type == DocumentType.EXCEL
    assert len(document_blocks.pages) == 2  # Due sheet
    
    # Verifica primo sheet
    sheet1 = document_blocks.pages[0]
    assert sheet1.sheet_name == "Dati"
    assert sheet1.page_number is None  # Excel non ha numeri di pagina
    
    # Verifica blocchi
    assert len(sheet1.blocks) > 0
    
    # Cerca blocchi tabella
    table_blocks = sheet1.get_table_blocks()
    if table_blocks:
        table_block = table_blocks[0]
        assert table_block.block_type == BlockType.TABLE
        assert 'headers' in table_block.content or 'range' in table_block.content
    
    # Cerca blocchi formula
    formula_blocks = [b for b in sheet1.blocks if b.block_type == BlockType.FORMULA]
    if formula_blocks:
        formula_block = formula_blocks[0]
        assert formula_block.content.startswith('=')


def test_extract_html_blocks(sample_html_file):
    """Test estrazione blocchi da HTML."""
    extractor = RawBlocksExtractor()
    document_blocks = extractor.extract(sample_html_file)
    
    # Verifica struttura documento
    assert document_blocks.document_type == DocumentType.HTML
    assert len(document_blocks.pages) == 1  # HTML è trattato come singola pagina
    
    page = document_blocks.pages[0]
    assert len(page.blocks) > 0
    
    # Verifica headers
    header_blocks = [b for b in page.blocks if b.block_type == BlockType.HEADER]
    assert len(header_blocks) > 0
    
    # Verifica contenuto headers
    h1_blocks = [b for b in header_blocks if b.metadata.get('tag') == 'h1']
    if h1_blocks:
        assert 'Annual Report' in h1_blocks[0].content
    
    # Verifica tabelle
    table_blocks = page.get_table_blocks()
    assert len(table_blocks) > 0
    assert 'Revenue' in table_blocks[0].text_content or 'table' in table_blocks[0].content


def test_extract_text_blocks(sample_text_file):
    """Test estrazione blocchi da file di testo."""
    extractor = RawBlocksExtractor()
    document_blocks = extractor.extract(sample_text_file)
    
    # Verifica struttura documento
    assert document_blocks.document_type == DocumentType.TEXT
    assert len(document_blocks.pages) == 1
    
    page = document_blocks.pages[0]
    assert len(page.blocks) > 0
    
    # Verifica che i paragrafi siano stati separati
    text_blocks = page.get_text_blocks()
    assert len(text_blocks) >= 2  # Almeno 2 paragrafi
    
    # Verifica contenuto
    all_text = ' '.join([b.text_content for b in text_blocks])
    assert 'Annual Report' in all_text
    assert 'Revenue' in all_text


def test_raw_block_structure():
    """Test struttura RawBlock."""
    block = RawBlock(
        block_id="test_001",
        document_id="doc_001",
        document_path="/path/to/doc.pdf",
        page_number=1,
        sheet_name=None,
        section="Introduction",
        block_type=BlockType.TEXT,
        content="Test content",
        text_content="Test content",
        bounding_box=BoundingBox(10, 20, 100, 50),
        order_index=0,
        confidence=0.95,
        extraction_method="Test method"
    )
    
    # Verifica attributi
    assert block.block_id == "test_001"
    assert block.page_number == 1
    assert block.block_type == BlockType.TEXT
    assert block.confidence == 0.95
    
    # Verifica serializzazione
    block_dict = block.to_dict()
    assert block_dict['block_id'] == "test_001"
    assert block_dict['block_type'] == "text"
    assert block_dict['bounding_box']['x0'] == 10
    
    # Verifica source reference
    source_ref = block.to_source_ref()
    assert "doc.pdf" in source_ref
    assert "page:1" in source_ref
    assert "block:test_001" in source_ref


def test_page_blocks_filtering():
    """Test filtraggio blocchi per tipo."""
    blocks = [
        RawBlock(
            block_id=f"b_{i}",
            document_id="doc_001",
            document_path="/test.pdf",
            page_number=1,
            sheet_name=None,
            section="Test",
            block_type=BlockType.TEXT if i % 2 == 0 else BlockType.TABLE,
            content=f"Content {i}",
            text_content=f"Content {i}",
            bounding_box=None,
            order_index=i,
            confidence=1.0,
            extraction_method="Test"
        )
        for i in range(5)
    ]
    
    page = PageBlocks(
        page_number=1,
        sheet_name=None,
        section_name="Test",
        blocks=blocks,
        page_metadata={}
    )
    
    # Test filtraggio per tipo
    text_blocks = page.get_text_blocks()
    assert len(text_blocks) == 3  # Blocchi con indice pari
    
    table_blocks = page.get_table_blocks()
    assert len(table_blocks) == 2  # Blocchi con indice dispari


def test_document_blocks_operations():
    """Test operazioni su DocumentBlocks."""
    # Crea documento di test
    pages = []
    for page_num in range(3):
        blocks = [
            RawBlock(
                block_id=f"p{page_num}_b{i}",
                document_id="doc_001",
                document_path="/test.pdf",
                page_number=page_num + 1,
                sheet_name=None,
                section=f"Page {page_num + 1}",
                block_type=BlockType.TEXT if i == 0 else BlockType.TABLE,
                content=f"Content p{page_num} b{i}",
                text_content=f"Content p{page_num} b{i}",
                bounding_box=None,
                order_index=i,
                confidence=1.0,
                extraction_method="Test"
            )
            for i in range(2)
        ]
        
        page = PageBlocks(
            page_number=page_num + 1,
            sheet_name=None,
            section_name=f"Page {page_num + 1}",
            blocks=blocks,
            page_metadata={}
        )
        pages.append(page)
    
    doc_blocks = DocumentBlocks(
        document_id="doc_001",
        document_path="/test.pdf",
        document_type=DocumentType.PDF,
        extraction_timestamp=datetime.now(),
        pages=pages,
        document_metadata={}
    )
    
    # Test get_all_blocks
    all_blocks = doc_blocks.get_all_blocks()
    assert len(all_blocks) == 6  # 3 pagine x 2 blocchi
    
    # Test get_blocks_by_page
    page2_blocks = doc_blocks.get_blocks_by_page(2)
    assert page2_blocks is not None
    assert page2_blocks.page_number == 2
    assert len(page2_blocks.blocks) == 2
    
    # Test get_blocks_by_type
    text_blocks = doc_blocks.get_blocks_by_type(BlockType.TEXT)
    assert len(text_blocks) == 3  # Un blocco TEXT per pagina
    
    table_blocks = doc_blocks.get_blocks_by_type(BlockType.TABLE)
    assert len(table_blocks) == 3  # Un blocco TABLE per pagina


def test_document_blocks_serialization():
    """Test serializzazione/deserializzazione DocumentBlocks."""
    # Crea documento di test
    block = RawBlock(
        block_id="test_001",
        document_id="doc_001",
        document_path="/test.pdf",
        page_number=1,
        sheet_name=None,
        section="Test",
        block_type=BlockType.TEXT,
        content="Test content",
        text_content="Test content",
        bounding_box=BoundingBox(10, 20, 100, 50),
        order_index=0,
        confidence=0.95,
        extraction_method="Test",
        metadata={'key': 'value'},
        parent_block_id="parent_001",
        child_block_ids=["child_001", "child_002"]
    )
    
    page = PageBlocks(
        page_number=1,
        sheet_name=None,
        section_name="Test",
        blocks=[block],
        page_metadata={'page_key': 'page_value'}
    )
    
    doc_blocks = DocumentBlocks(
        document_id="doc_001",
        document_path="/test.pdf",
        document_type=DocumentType.PDF,
        extraction_timestamp=datetime.now(),
        pages=[page],
        document_metadata={'doc_key': 'doc_value'}
    )
    
    # Salva in JSON
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    doc_blocks.save_to_json(tmp_path)
    
    # Verifica che il file sia stato creato
    assert tmp_path.exists()
    
    # Carica da JSON
    loaded_doc = DocumentBlocks.load_from_json(tmp_path)
    
    # Verifica che i dati siano stati preservati
    assert loaded_doc.document_id == doc_blocks.document_id
    assert loaded_doc.document_type == doc_blocks.document_type
    assert len(loaded_doc.pages) == 1
    
    loaded_page = loaded_doc.pages[0]
    assert loaded_page.page_number == 1
    assert len(loaded_page.blocks) == 1
    
    loaded_block = loaded_page.blocks[0]
    assert loaded_block.block_id == "test_001"
    assert loaded_block.block_type == BlockType.TEXT
    assert loaded_block.confidence == 0.95
    assert loaded_block.bounding_box.x0 == 10
    assert loaded_block.metadata['key'] == 'value'
    assert loaded_block.parent_block_id == "parent_001"
    assert len(loaded_block.child_block_ids) == 2
    
    # Clean up
    tmp_path.unlink()


def test_document_hash_calculation(sample_pdf_file):
    """Test calcolo hash documento."""
    extractor = RawBlocksExtractor()
    document_blocks = extractor.extract(sample_pdf_file)
    
    # L'hash dovrebbe essere consistente
    assert document_blocks.document_id is not None
    assert len(document_blocks.document_id) == 16  # Primi 16 caratteri SHA256
    
    # Estrai di nuovo e verifica che l'hash sia lo stesso
    document_blocks2 = extractor.extract(sample_pdf_file)
    assert document_blocks2.document_id == document_blocks.document_id


def test_error_handling_nonexistent_file():
    """Test gestione errore file non esistente."""
    extractor = RawBlocksExtractor()
    
    with pytest.raises(FileNotFoundError):
        extractor.extract("nonexistent_file.pdf")


def test_bounding_box():
    """Test BoundingBox."""
    bbox = BoundingBox(10.5, 20.3, 100.7, 50.9)
    
    assert bbox.x0 == 10.5
    assert bbox.y0 == 20.3
    assert bbox.x1 == 100.7
    assert bbox.y1 == 50.9
    
    # Test serializzazione
    bbox_dict = bbox.to_dict()
    assert bbox_dict['x0'] == 10.5
    assert bbox_dict['y0'] == 20.3
    assert bbox_dict['x1'] == 100.7
    assert bbox_dict['y1'] == 50.9


def test_block_relationships():
    """Test relazioni tra blocchi (parent/child)."""
    parent_block = RawBlock(
        block_id="parent_001",
        document_id="doc_001",
        document_path="/test.pdf",
        page_number=1,
        sheet_name=None,
        section="Test",
        block_type=BlockType.TEXT,
        content="Parent content",
        text_content="Parent content",
        bounding_box=None,
        order_index=0,
        child_block_ids=["child_001", "child_002"]
    )
    
    child_block1 = RawBlock(
        block_id="child_001",
        document_id="doc_001",
        document_path="/test.pdf",
        page_number=1,
        sheet_name=None,
        section="Test",
        block_type=BlockType.TEXT,
        content="Child 1 content",
        text_content="Child 1 content",
        bounding_box=None,
        order_index=1,
        parent_block_id="parent_001"
    )
    
    child_block2 = RawBlock(
        block_id="child_002",
        document_id="doc_001",
        document_path="/test.pdf",
        page_number=1,
        sheet_name=None,
        section="Test",
        block_type=BlockType.TEXT,
        content="Child 2 content",
        text_content="Child 2 content",
        bounding_box=None,
        order_index=2,
        parent_block_id="parent_001"
    )
    
    # Verifica relazioni
    assert len(parent_block.child_block_ids) == 2
    assert "child_001" in parent_block.child_block_ids
    assert "child_002" in parent_block.child_block_ids
    
    assert child_block1.parent_block_id == "parent_001"
    assert child_block2.parent_block_id == "parent_001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])