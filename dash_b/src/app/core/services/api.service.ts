import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';
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

  // Document Analysis
  analyzeDocument(file: File, analysisType: string = 'automatic'): Observable<DocumentAnalysis> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('analysis_type', analysisType);

    this.setLoading(true);
    return this.http.post<any>(`${this.baseUrl}/analyze/stored`, formData)
      .pipe(
        map(response => response.analysis || response),
        tap(() => this.setLoading(false)),
        catchError(error => {
          this.setLoading(false);
          return this.handleError('Document Analysis')(error);
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
    return this.http.post<FAQResponse>(`${this.baseUrl}/generate/faq`, {
      num_questions: numQuestions
    }, { headers: this.defaultHeaders })
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
    return this.http.post<QueryResponse>(`${this.baseUrl}/query`, request, {
      headers: this.defaultHeaders
    })
      .pipe(
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
            total_documents: response?.documents?.length || 0,
            total_vectors: response?.vectors || 0,
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

  // PDF Export
  exportToPDF(data: any, type: 'analysis' | 'faq' | 'report'): Observable<Blob> {
    return this.http.post(`${this.baseUrl}/export/pdf`, {
      data,
      type
    }, {
      headers: this.defaultHeaders,
      responseType: 'blob'
    })
      .pipe(
        catchError(this.handleError('PDF Export'))
      );
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