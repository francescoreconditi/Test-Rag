"""Script per testare la funzionalità NotebookLM-like."""

from reportlab.lib.pagesizes import letter
from reportlab.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime

def create_sample_financial_report():
    """Crea un PDF di esempio per testare l'analisi automatica."""
    filename = "data/report_finanziario_2024.pdf"
    
    # Crea il documento
    doc = SimpleDocTemplate(filename, pagesize=A4,
                          rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=18)
    
    # Stili
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle',
                               parent=styles['Heading1'],
                               fontSize=24,
                               spaceAfter=30,
                               alignment=1)  # Center
    
    # Contenuto del report
    story = []
    
    # Titolo
    story.append(Paragraph("Report Finanziario Q3 2024", title_style))
    story.append(Spacer(1, 20))
    
    # Riepilogo Esecutivo
    story.append(Paragraph("Riepilogo Esecutivo", styles['Heading2']))
    executive_summary = """
    Il terzo trimestre 2024 ha mostrato una performance finanziaria solida con un fatturato di 2.8 milioni di euro, 
    rappresentando una crescita del 15% rispetto al Q3 2023. L'EBITDA ha raggiunto 850.000 euro (margine del 30.4%), 
    superando le aspettative del mercato. Le principali divisioni - Software (60% del fatturato) e Consulting (40%) - 
    hanno contribuito positivamente ai risultati.
    """
    story.append(Paragraph(executive_summary, styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Metriche Principali
    story.append(Paragraph("Metriche Finanziarie Principali", styles['Heading2']))
    
    # Tabella dati
    data = [
        ['Metrica', 'Q3 2024', 'Q3 2023', 'Variazione'],
        ['Fatturato', '€2.800.000', '€2.435.000', '+15%'],
        ['EBITDA', '€850.000', '€680.000', '+25%'],
        ['Utile Netto', '€620.000', '€485.000', '+28%'],
        ['Margine EBITDA', '30.4%', '27.9%', '+2.5pp'],
        ['Dipendenti', '125', '110', '+13.6%']
    ]
    
    table = Table(data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND',(0,1),(-1,-1), colors.beige),
        ('GRID',(0,0),(-1,-1),1,colors.black)
    ]))
    story.append(table)
    story.append(Spacer(1, 20))
    
    # Analisi per Divisione
    story.append(Paragraph("Analisi per Divisione", styles['Heading2']))
    division_analysis = """
    <b>Divisione Software:</b> Ha generato €1.680.000 (60% del fatturato totale) con una crescita del 22% YoY. 
    I nuovi prodotti SaaS hanno contribuito per €420.000, superando le proiezioni del 18%.
    
    <b>Divisione Consulting:</b> Ha registrato €1.120.000 (40% del fatturato) con una crescita del 8% YoY. 
    L'incremento è dovuto principalmente ai progetti di trasformazione digitale nel settore finanziario.
    """
    story.append(Paragraph(division_analysis, styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Outlook e Raccomandazioni
    story.append(Paragraph("Outlook Q4 2024", styles['Heading2']))
    outlook = """
    Per il quarto trimestre prevediamo un fatturato di €3.1 milioni, supportato dal lancio di due nuovi prodotti 
    e dalla pipeline di progetti consulting del valore di €1.5 milioni. Raccomandiamo di:
    
    • Investire €200.000 in R&D per accelerare lo sviluppo dei prodotti AI
    • Assumere 15 nuovi sviluppatori per supportare la crescita
    • Espandere la presenza geografica in Germania e Francia
    • Ottimizzare i processi operativi per mantenere i margini superiori al 30%
    """
    story.append(Paragraph(outlook, styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Rischi
    story.append(Paragraph("Principali Rischi", styles['Heading2']))
    risks = """
    <b>Rischi Operativi:</b> Difficoltà nel reclutamento di talenti tech qualificati potrebbero rallentare 
    la crescita. Il time-to-hire medio è aumentato a 45 giorni.
    
    <b>Rischi di Mercato:</b> La competizione nel settore SaaS si è intensificata del 25% con l'ingresso 
    di 3 nuovi competitor. Necessario investire in differenziazione del prodotto.
    
    <b>Rischi Finanziari:</b> L'aumento dei tassi di interesse potrebbe impattare i clienti enterprise 
    e ritardare le decisioni di investimento IT del 15-20%.
    """
    story.append(Paragraph(risks, styles['Normal']))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Generato il {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
    
    # Genera il PDF
    doc.build(story)
    print(f"✅ PDF creato: {filename}")
    return filename

if __name__ == "__main__":
    try:
        create_sample_financial_report()
        print("🚀 Ora puoi caricare il PDF nell'app per testare l'analisi automatica!")
        print("   1. Avvia l'app: streamlit run app.py")
        print("   2. Vai su 'RAG Documenti'") 
        print("   3. Carica il file data/report_finanziario_2024.pdf")
        print("   4. Vedrai l'analisi automatica come NotebookLM!")
    except ImportError:
        print("❌ Per creare il PDF installa reportlab: pip install reportlab")
    except Exception as e:
        print(f"❌ Errore: {e}")