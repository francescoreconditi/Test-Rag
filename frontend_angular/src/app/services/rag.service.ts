/**
 * RAG Service
 * Handles all RAG-related API calls and document processing
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { map } from 'rxjs/operators';

export interface RagQuery {
  query: string;
  enterprise_mode?: boolean;
  document_types?: string[];
  max_results?: number;
}

export interface RagResponse {
  answer: string;
  confidence_score: number;
  source_references: SourceReference[];
  processing_time_ms: number;
  validation_results?: ValidationResult[];
  warnings: string[];
  query_id: string;
}

export interface SourceReference {
  document_name: string;
  page_number?: number;
  confidence: number;
  text_snippet: string;
  source_type: string;
}

export interface ValidationResult {
  rule_name: string;
  passed: boolean;
  message: string;
  level: 'error' | 'warning' | 'info';
}

export interface DocumentUpload {
  file: File;
  enterprise_mode?: boolean;
  document_type?: string;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  document_id: string;
  processed_chunks: number;
  processing_time_ms: number;
}

export interface DashboardStats {
  total_documents: number;
  total_vectors: number;
  total_queries: number;
  system_health: 'healthy' | 'warning' | 'error' | 'unknown';
  enterprise_mode: boolean;
  processing_time_avg: number;
  success_rate: number;
}

export interface RecentActivity {
  id: string;
  type: 'query' | 'upload' | 'export';
  description: string;
  timestamp: Date;
  status: 'success' | 'error' | 'processing';
  user_email: string;
}

@Injectable({
  providedIn: 'root'
})
export class RagService {
  private readonly apiBaseUrl = 'http://localhost:8000';

  // Enterprise mode state
  private enterpriseModeSubject = new BehaviorSubject<boolean>(false);
  public enterpriseMode$ = this.enterpriseModeSubject.asObservable();

  constructor(private http: HttpClient) {
    this.loadEnterpriseMode();
  }

  /**
   * Load enterprise mode setting from localStorage
   */
  private loadEnterpriseMode(): void {
    const saved = localStorage.getItem('rag_enterprise_mode');
    if (saved) {
      this.enterpriseModeSubject.next(JSON.parse(saved));
    }
  }

  /**
   * Execute RAG query
   */
  query(ragQuery: RagQuery): Observable<RagResponse> {
    return this.http.post<any>(`${this.apiBaseUrl}/query`, ragQuery)
      .pipe(
        map(response => ({
          ...response,
          source_references: response.source_references?.map((ref: any) => ({
            ...ref,
            confidence: typeof ref.confidence === 'string' ?
              parseFloat(ref.confidence) : ref.confidence
          })) || []
        }))
      );
  }

  /**
   * Upload and process document
   */
  uploadDocument(upload: DocumentUpload): Observable<UploadResponse> {
    const formData = new FormData();
    formData.append('file', upload.file);

    let params = new HttpParams();
    if (upload.enterprise_mode !== undefined) {
      params = params.set('enterprise_mode', upload.enterprise_mode.toString());
    }
    if (upload.document_type) {
      params = params.set('document_type', upload.document_type);
    }

    return this.http.post<UploadResponse>(`${this.apiBaseUrl}/upload`, formData, { params });
  }

  /**
   * Get dashboard statistics
   */
  getDashboardStats(): Observable<DashboardStats> {
    return this.http.get<any>(`${this.apiBaseUrl}/stats/dashboard`)
      .pipe(
        map(response => ({
          total_documents: response.total_documents || 0,
          total_vectors: response.total_vectors || 0,
          total_queries: response.total_queries || 0,
          system_health: response.system_health || 'unknown',
          enterprise_mode: response.enterprise_mode || false,
          processing_time_avg: response.processing_time_avg || 0,
          success_rate: response.success_rate || 0
        }))
      );
  }

  /**
   * Get recent activities
   */
  getRecentActivities(limit: number = 10): Observable<RecentActivity[]> {
    const params = new HttpParams().set('limit', limit.toString());

    return this.http.get<any[]>(`${this.apiBaseUrl}/stats/activities`, { params })
      .pipe(
        map(activities => activities.map(activity => ({
          ...activity,
          timestamp: new Date(activity.timestamp)
        })))
      );
  }

  /**
   * Toggle enterprise mode
   */
  toggleEnterpriseMode(enabled: boolean): Observable<{ enterprise_mode: boolean }> {
    return this.http.post<any>(`${this.apiBaseUrl}/settings/enterprise-mode`, {
      enterprise_mode: enabled
    }).pipe(
      map(response => {
        this.enterpriseModeSubject.next(response.enterprise_mode);
        localStorage.setItem('rag_enterprise_mode', JSON.stringify(response.enterprise_mode));
        return response;
      })
    );
  }

  /**
   * Get list of uploaded documents
   */
  getDocuments(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiBaseUrl}/documents`);
  }

  /**
   * Delete document by ID
   */
  deleteDocument(documentId: string): Observable<{ success: boolean; message: string }> {
    return this.http.delete<any>(`${this.apiBaseUrl}/documents/${documentId}`);
  }

  /**
   * Get document analysis/preview
   */
  getDocumentPreview(documentId: string): Observable<any> {
    return this.http.get<any>(`${this.apiBaseUrl}/documents/${documentId}/preview`);
  }

  /**
   * Analyze CSV file
   */
  analyzeCsv(file: File, options?: any): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);

    let params = new HttpParams();
    if (options?.enterprise_mode !== undefined) {
      params = params.set('enterprise_mode', options.enterprise_mode.toString());
    }

    return this.http.post<any>(`${this.apiBaseUrl}/analyze/csv`, formData, { params });
  }

  /**
   * Analyze PDF file
   */
  analyzePdf(file: File, options?: any): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);

    let params = new HttpParams();
    if (options?.enterprise_mode !== undefined) {
      params = params.set('enterprise_mode', options.enterprise_mode.toString());
    }

    return this.http.post<any>(`${this.apiBaseUrl}/analyze/stored`, formData, { params });
  }

  /**
   * Export data in specified format
   */
  exportData(format: 'pdf' | 'excel' | 'json', data: any): Observable<Blob> {
    const options = {
      responseType: 'blob' as 'json'
    };

    return this.http.post<Blob>(`${this.apiBaseUrl}/export/${format}`, data, options);
  }

  /**
   * Get API health status
   */
  getApiHealth(): Observable<any> {
    return this.http.get<any>(`${this.apiBaseUrl}/health`);
  }

  /**
   * Run benchmark tests
   */
  runBenchmark(): Observable<any> {
    return this.http.post<any>(`${this.apiBaseUrl}/benchmark/run`, {});
  }

  /**
   * Get benchmark results
   */
  getBenchmarkResults(): Observable<any> {
    return this.http.get<any>(`${this.apiBaseUrl}/benchmark/results`);
  }

  /**
   * Get validation rules configuration
   */
  getValidationRules(): Observable<any> {
    return this.http.get<any>(`${this.apiBaseUrl}/validation/rules`);
  }

  /**
   * Update validation rules
   */
  updateValidationRules(rules: any): Observable<any> {
    return this.http.put<any>(`${this.apiBaseUrl}/validation/rules`, rules);
  }

  /**
   * Get current enterprise mode status
   */
  isEnterpriseMode(): boolean {
    return this.enterpriseModeSubject.value;
  }

  /**
   * Clear query cache
   */
  clearCache(): Observable<{ success: boolean; message: string }> {
    return this.http.post<any>(`${this.apiBaseUrl}/cache/clear`, {});
  }

  /**
   * Get system metrics
   */
  getSystemMetrics(): Observable<any> {
    return this.http.get<any>(`${this.apiBaseUrl}/metrics`);
  }
}