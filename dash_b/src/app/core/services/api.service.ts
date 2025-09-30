import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, throwError } from 'rxjs';
import { catchError, map, switchMap, tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import {
    CSVAnalysis,
    DocumentAnalysis,
    FAQResponse,
    QueryRequest,
    QueryResponse
} from '../models/analysis.model';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly baseUrl = environment.apiUrl || 'http://localhost:8000';
  private loadingSubject = new BehaviorSubject<boolean>(false);
  public loading$ = this.loadingSubject.asObservable();

  private readonly defaultHeaders = new HttpHeaders({
    'Content-Type': 'application/json'
  });

  constructor(private http: HttpClient) {}

  // Health Check
  getHealthCheck(): Observable<any> {
    return this.http.get(`${this.baseUrl.replace('/api/v1', '')}/health`)
      .pipe(
        catchError(this.handleError('Health Check'))
      );
  }

  // Upload file to vector DB first
  uploadFileToVectorDB(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('files', file);

    return this.http.post<any>(`${this.baseUrl.replace('/api/v1', '')}/upload/file`, formData)
      .pipe(
        catchError(this.handleError('File Upload to Vector DB'))
      );
  }

  // Document Analysis - now analyzes documents already in vector DB
  analyzeStoredDocuments(): Observable<DocumentAnalysis> {
    this.setLoading(true);

    // Get auth token for the request
    const token = localStorage.getItem('authToken');
    const headers = token
      ? new HttpHeaders({ 'Authorization': `Bearer ${token}` })
      : new HttpHeaders();

    return this.http.post<any>(`${this.baseUrl.replace('/api/v1', '')}/analyze/stored`, {}, { headers })
      .pipe(
        map(response => response.analysis || response),
        tap(() => this.setLoading(false)),
        catchError(error => {
          this.setLoading(false);
          return this.handleError('Document Analysis')(error);
        })
      );
  }

  // Combined upload and analyze workflow
  analyzeDocument(file: File, analysisType: string = 'automatic'): Observable<DocumentAnalysis> {
    this.setLoading(true);

    // First upload the file to vector DB
    return this.uploadFileToVectorDB(file).pipe(
      switchMap(() => {
        // Then analyze the stored documents
        return this.analyzeStoredDocuments();
      }),
      catchError(error => {
        this.setLoading(false);
        return this.handleError('Document Upload and Analysis')(error);
      })
    );
  }

  // CSV Analysis
  analyzeCSV(file: File, question?: string): Observable<CSVAnalysis> {
    const formData = new FormData();
    formData.append('file', file);
    if (question) {
      formData.append('question', question);
    }

    this.setLoading(true);
    return this.http.post<CSVAnalysis>(`${this.baseUrl}/analyze/csv`, formData)
      .pipe(
        tap(() => this.setLoading(false)),
        catchError(error => {
          this.setLoading(false);
          return this.handleError('CSV Analysis')(error);
        })
      );
  }

  // FAQ Generation
  generateFAQ(numQuestions: number = 10): Observable<FAQResponse> {
    this.setLoading(true);
    return this.http.post<FAQResponse>(`${this.baseUrl}/analyze/faqs?num_questions=${numQuestions}`, {},
      { headers: this.defaultHeaders })
      .pipe(
        tap(() => this.setLoading(false)),
        catchError(error => {
          this.setLoading(false);
          return this.handleError('FAQ Generation')(error);
        })
      );
  }

  // RAG Query
  queryRAG(request: QueryRequest): Observable<QueryResponse> {
    this.setLoading(true);
    // Transform request to match API format
    const apiRequest = {
      question: request.query,
      enterprise_mode: request.enterprise_mode || false
    };
    return this.http.post<any>(`${this.baseUrl}/query`, apiRequest, {
      headers: this.defaultHeaders
    })
      .pipe(
        map(apiResponse => ({
          response: apiResponse.answer,
          confidence: apiResponse.confidence,
          sources: apiResponse.sources || [],
          processing_time: apiResponse.processing_time || 0,
          enterprise_stats: apiResponse.enterprise_stats
        })),
        tap(() => this.setLoading(false)),
        catchError(error => {
          this.setLoading(false);
          return this.handleError('RAG Query')(error);
        })
      );
  }

  // Document Management
  uploadDocument(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);

    this.setLoading(true);
    return this.http.post<any>(`${this.baseUrl}/documents/upload`, formData)
      .pipe(
        tap(() => this.setLoading(false)),
        catchError(error => {
          this.setLoading(false);
          return this.handleError('Document Upload')(error);
        })
      );
  }

  uploadMultipleDocuments(files: File[]): Observable<any> {
    const formData = new FormData();
    files.forEach((file, index) => {
      formData.append(`files`, file);
    });

    this.setLoading(true);
    return this.http.post<any>(`${this.baseUrl}/documents/upload/multiple`, formData)
      .pipe(
        tap(() => this.setLoading(false)),
        catchError(error => {
          this.setLoading(false);
          return this.handleError('Multiple Document Upload')(error);
        })
      );
  }

  getIndexStats(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl.replace('/api/v1', '')}/documents`)
      .pipe(
        map(response => {
          // Transform documents list into stats format
          return {
            total_documents: response?.total_documents || 0,
            total_vectors: response?.indexed_vectors || 0,
            collection_status: response?.status || 'unknown',
            last_updated: new Date().toISOString()
          };
        }),
        catchError(this.handleError('Index Stats'))
      );
  }

  clearIndex(): Observable<any> {
    return this.http.delete(`${this.baseUrl}/documents/clear`)
      .pipe(
        catchError(this.handleError('Clear Index'))
      );
  }

  // Enterprise Features
  enableEnterpriseMode(): Observable<any> {
    return this.http.post(`${this.baseUrl}/enterprise/enable`, {}, {
      headers: this.defaultHeaders
    })
      .pipe(
        catchError(this.handleError('Enable Enterprise Mode'))
      );
  }

  getEnterpriseStats(): Observable<any> {
    return this.http.get(`${this.baseUrl}/enterprise/stats`)
      .pipe(
        catchError(this.handleError('Enterprise Stats'))
      );
  }

  // PDF Export - Using FastAPI backend endpoint for professional PDF generation
  exportToPDF(data: any, type: 'analysis' | 'faq' | 'report'): Observable<Blob> {
    // Use the new FastAPI endpoint for FAQ PDF generation
    if (type === 'faq' && data.faqs) {
      return this.exportFAQToPDF(data.faqs, data.metadata);
    }

    // Fallback to client-side generation for other types (for now)
    return new Observable(observer => {
      try {
        // Create HTML content for the PDF
        const htmlContent = this.generatePDFHTML(data, type);

        // Convert HTML to blob
        const blob = new Blob([htmlContent], { type: 'text/html' });

        observer.next(blob);
        observer.complete();
      } catch (error) {
        observer.error(error);
      }
    });
  }

  // New method to export Analysis to PDF using FastAPI endpoint
  exportAnalysisToPDF(analysis: string, metadata?: any): Observable<Blob> {
    const requestBody = {
      analysis: analysis,
      metadata: {
        ...metadata,
        timestamp: new Date().toLocaleString('it-IT')
      },
      filename: `analisi_${new Date().toISOString().split('T')[0].replace(/-/g, '')}`
    };

    return this.http.post<any>(`${this.baseUrl}/export/pdf/analysis`, requestBody, {
      headers: this.defaultHeaders
    }).pipe(
      map(response => {
        // Decode base64 PDF
        const binaryString = atob(response.pdf_b64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        return new Blob([bytes], { type: 'application/pdf' });
      }),
      catchError(error => {
        console.error('Error generating Analysis PDF:', error);
        // Fallback to HTML generation if API fails
        const htmlContent = this.generatePDFHTML({ analysis }, 'analysis');
        return of(new Blob([htmlContent], { type: 'text/html' }));
      })
    );
  }

  // New method to export Q&A Session to PDF using FastAPI endpoint
  exportQASessionToPDF(question: string, answer: string, sources: any[], metadata?: any): Observable<Blob> {
    const requestBody = {
      question: question,
      answer: answer,
      sources: sources,
      metadata: {
        ...metadata,
        timestamp: new Date().toLocaleString('it-IT'),
        query_type: metadata?.query_type || 'RAG Query'
      },
      filename: `qa_session_${new Date().toISOString().split('T')[0].replace(/-/g, '')}`
    };

    return this.http.post<any>(`${this.baseUrl}/export/pdf/qa-session`, requestBody, {
      headers: this.defaultHeaders
    }).pipe(
      map(response => {
        // Decode base64 PDF
        const binaryString = atob(response.pdf_b64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        return new Blob([bytes], { type: 'application/pdf' });
      }),
      catchError(error => {
        console.error('Error generating Q&A Session PDF:', error);
        // Fallback to HTML generation if API fails
        const htmlContent = this.generatePDFHTML({
          question,
          answer,
          sources,
          metadata
        }, 'report');
        return of(new Blob([htmlContent], { type: 'text/html' }));
      })
    );
  }

  // New method to export FAQ to PDF using FastAPI endpoint
  private exportFAQToPDF(faqs: any[], metadata?: any): Observable<Blob> {
    // Format FAQs as a string for the API
    const faqString = faqs.map(faq =>
      `Q: ${faq.question}\nA: ${faq.answer}`
    ).join('\n\n');

    const requestBody = {
      faqs: faqString,
      metadata: {
        numero_faq: faqs.length,
        timestamp: new Date().toLocaleString('it-IT'),
        categoria: 'FAQ Intelligenti',
        ...metadata
      },
      filename: `faq_${new Date().toISOString().split('T')[0].replace(/-/g, '')}`
    };

    return this.http.post<any>(`${this.baseUrl}/export/pdf/faq`, requestBody, {
      headers: this.defaultHeaders
    }).pipe(
      map(response => {
        // Decode base64 PDF
        const binaryString = atob(response.pdf_b64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        return new Blob([bytes], { type: 'application/pdf' });
      }),
      catchError(error => {
        console.error('Error generating PDF:', error);
        // Fallback to HTML generation if API fails
        const htmlContent = this.generatePDFHTML({ faqs }, 'faq');
        return of(new Blob([htmlContent], { type: 'text/html' }));
      })
    );
  }

  private generatePDFHTML(data: any, type: string): string {
    const timestamp = new Date().toLocaleString('it-IT');
    let content = '';

    if (type === 'report' && data.result) {
      content = `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <title>Query Report - RAG Dashboard</title>
          <style>
            body { font-family: Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }
            h1 { color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
            h2 { color: #333; margin-top: 30px; }
            .header { margin-bottom: 30px; }
            .query-box { background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }
            .response-box { background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0; }
            .source { background: #f9f9f9; padding: 10px; margin: 10px 0; border-left: 3px solid #667eea; }
            .confidence { color: #2e7d32; font-weight: bold; }
            .metadata { color: #666; font-size: 0.9em; margin-top: 10px; }
            .footer { margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 0.9em; }
          </style>
        </head>
        <body>
          <div class="header">
            <h1>🚀 RAG Dashboard - Query Report</h1>
            <div class="metadata">Generated: ${timestamp}</div>
          </div>

          <div class="query-box">
            <h2>Query</h2>
            <p>${data.query || 'N/A'}</p>
          </div>

          <div class="response-box">
            <h2>Response</h2>
            <p>${data.result?.response || 'N/A'}</p>
            <div class="metadata">
              Confidence: <span class="confidence">${((data.result?.confidence || 0) * 100).toFixed(1)}%</span> |
              Processing Time: ${(data.result?.processing_time || 0).toFixed(2)}s
            </div>
          </div>

          <h2>Sources</h2>
          ${(data.result?.sources || []).map((source: any, index: number) => `
            <div class="source">
              <strong>Source ${index + 1}:</strong> ${source.source || 'N/A'}
              <div class="metadata">
                Confidence: <span class="confidence">${((source.confidence || 0) * 100).toFixed(0)}%</span>
                ${source.page ? ` | Page: ${source.page}` : ''}
              </div>
              <p>${source.text || ''}</p>
            </div>
          `).join('')}

          <div class="footer">
            <p>© ${new Date().getFullYear()} ZCS Company - RAG Dashboard</p>
            <p>This report was automatically generated and is confidential.</p>
          </div>
        </body>
        </html>
      `;
    } else {
      // Generic fallback
      content = `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <title>Export - RAG Dashboard</title>
          <style>
            body { font-family: Arial, sans-serif; padding: 40px; }
            h1 { color: #667eea; }
            pre { background: #f5f5f5; padding: 15px; border-radius: 5px; }
          </style>
        </head>
        <body>
          <h1>RAG Dashboard Export</h1>
          <p>Type: ${type}</p>
          <p>Generated: ${timestamp}</p>
          <pre>${JSON.stringify(data, null, 2)}</pre>
        </body>
        </html>
      `;
    }

    return content;
  }

  // Audio Features
  generateAudioSummary(text: string): Observable<Blob> {
    return this.http.post(`${this.baseUrl}/audio/generate`, {
      text
    }, {
      headers: this.defaultHeaders,
      responseType: 'blob'
    })
      .pipe(
        catchError(this.handleError('Audio Generation'))
      );
  }

  // Utility Methods
  private setLoading(loading: boolean): void {
    this.loadingSubject.next(loading);
  }

  private handleError(operation: string) {
    return (error: HttpErrorResponse): Observable<never> => {
      console.error(`${operation} failed:`, error);

      let errorMessage = 'Si è verificato un errore sconosciuto.';

      if (error.error instanceof ErrorEvent) {
        // Client-side error
        errorMessage = `Errore: ${error.error.message}`;
      } else {
        // Server-side error
        switch (error.status) {
          case 400:
            errorMessage = 'Richiesta non valida. Controlla i dati inseriti.';
            break;
          case 401:
            errorMessage = 'Accesso non autorizzato.';
            break;
          case 403:
            errorMessage = 'Accesso negato.';
            break;
          case 404:
            errorMessage = 'Servizio non trovato.';
            break;
          case 500:
            errorMessage = 'Errore interno del server.';
            break;
          case 503:
            errorMessage = 'Servizio temporaneamente non disponibile.';
            break;
          default:
            errorMessage = `Errore ${error.status}: ${error.message}`;
        }
      }

      return throwError(() => new Error(errorMessage));
    };
  }
}