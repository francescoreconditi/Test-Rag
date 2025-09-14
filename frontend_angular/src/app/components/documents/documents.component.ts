/**
 * Documents Management Component
 * Upload, preview, and manage documents with enterprise features
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { RagService, DocumentUpload, UploadResponse } from '../../services/rag.service';
import { AuthService } from '../../services/auth.service';

interface DocumentInfo {
  id: string;
  name: string;
  type: string;
  size: number;
  upload_date: Date;
  status: 'processing' | 'completed' | 'error';
  chunks_count: number;
  enterprise_mode: boolean;
  validation_results?: any[];
}

@Component({
  selector: 'app-documents',
  templateUrl: './documents.component.html',
  styleUrls: ['./documents.component.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule]
})
export class DocumentsComponent implements OnInit, OnDestroy {
  documents: DocumentInfo[] = [];
  isLoading = false;
  error: string | null = null;
  selectedFiles: FileList | null = null;
  uploadProgress: { [key: string]: number } = {};
  isUploading = false;

  // Make Object available to template
  Object = Object;

  // Filters
  filterType = 'all';
  filterStatus = 'all';
  searchTerm = '';

  // Enterprise settings
  enterpriseMode = false;
  documentType = 'auto';

  private subscriptions = new Subscription();

  constructor(
    private ragService: RagService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loadDocuments();
    this.subscribeToEnterpriseMode();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  /**
   * Subscribe to enterprise mode changes
   */
  private subscribeToEnterpriseMode(): void {
    this.subscriptions.add(
      this.ragService.enterpriseMode$.subscribe(enabled => {
        this.enterpriseMode = enabled;
      })
    );
  }

  /**
   * Load documents list
   */
  loadDocuments(): void {
    this.isLoading = true;
    this.error = null;

    this.subscriptions.add(
      this.ragService.getDocuments().subscribe({
        next: (documents) => {
          this.documents = documents.map(doc => ({
            ...doc,
            upload_date: new Date(doc.upload_date)
          }));
          this.isLoading = false;
        },
        error: (error) => {
          this.error = 'Failed to load documents: ' + error.message;
          this.isLoading = false;
        }
      })
    );
  }

  /**
   * Handle file selection
   */
  onFileSelected(event: any): void {
    this.selectedFiles = event.target.files;
    this.error = null;
  }

  /**
   * Upload selected files
   */
  async uploadFiles(): Promise<void> {
    if (!this.selectedFiles || this.selectedFiles.length === 0) {
      this.error = 'Please select files to upload';
      return;
    }

    this.isUploading = true;
    this.error = null;

    const files = Array.from(this.selectedFiles);

    for (const file of files) {
      try {
        const upload: DocumentUpload = {
          file,
          enterprise_mode: this.enterpriseMode,
          document_type: this.documentType === 'auto' ? undefined : this.documentType
        };

        // Initialize progress tracking
        this.uploadProgress[file.name] = 0;

        const response = await this.uploadFile(upload);

        if (response.success) {
          this.uploadProgress[file.name] = 100;

          // Add to documents list
          const newDoc: DocumentInfo = {
            id: response.document_id,
            name: file.name,
            type: this.getFileType(file.name),
            size: file.size,
            upload_date: new Date(),
            status: 'completed',
            chunks_count: response.processed_chunks,
            enterprise_mode: this.enterpriseMode
          };

          this.documents.unshift(newDoc);
        }
      } catch (error: any) {
        this.uploadProgress[file.name] = -1; // Error state
        console.error('Upload failed for', file.name, error);
      }
    }

    this.isUploading = false;
    this.selectedFiles = null;

    // Clear file input
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    if (fileInput) {
      fileInput.value = '';
    }
  }

  /**
   * Upload single file
   */
  private uploadFile(upload: DocumentUpload): Promise<UploadResponse> {
    return new Promise((resolve, reject) => {
      this.ragService.uploadDocument(upload).subscribe({
        next: (response) => resolve(response),
        error: (error) => reject(error)
      });
    });
  }

  /**
   * Delete document
   */
  deleteDocument(document: DocumentInfo): void {
    if (!confirm(`Are you sure you want to delete "${document.name}"?`)) {
      return;
    }

    this.subscriptions.add(
      this.ragService.deleteDocument(document.id).subscribe({
        next: (response) => {
          if (response.success) {
            this.documents = this.documents.filter(doc => doc.id !== document.id);
          } else {
            this.error = 'Failed to delete document: ' + response.message;
          }
        },
        error: (error) => {
          this.error = 'Failed to delete document: ' + error.message;
        }
      })
    );
  }

  /**
   * Preview document
   */
  previewDocument(document: DocumentInfo): void {
    this.subscriptions.add(
      this.ragService.getDocumentPreview(document.id).subscribe({
        next: (preview) => {
          // Open preview in modal or new tab
          this.showDocumentPreview(document, preview);
        },
        error: (error) => {
          this.error = 'Failed to load preview: ' + error.message;
        }
      })
    );
  }

  /**
   * Show document preview modal
   */
  private showDocumentPreview(document: DocumentInfo, preview: any): void {
    // This would typically open a modal or navigate to preview page
    console.log('Document preview:', document, preview);
    alert(`Preview for ${document.name}\n\nChunks: ${preview.chunks?.length || 0}\nFirst chunk: ${preview.chunks?.[0]?.text?.substring(0, 100)}...`);
  }

  /**
   * Get filtered documents
   */
  getFilteredDocuments(): DocumentInfo[] {
    let filtered = this.documents;

    // Filter by type
    if (this.filterType !== 'all') {
      filtered = filtered.filter(doc => doc.type === this.filterType);
    }

    // Filter by status
    if (this.filterStatus !== 'all') {
      filtered = filtered.filter(doc => doc.status === this.filterStatus);
    }

    // Filter by search term
    if (this.searchTerm) {
      const term = this.searchTerm.toLowerCase();
      filtered = filtered.filter(doc =>
        doc.name.toLowerCase().includes(term)
      );
    }

    return filtered;
  }

  /**
   * Get unique document types
   */
  getDocumentTypes(): string[] {
    const types = [...new Set(this.documents.map(doc => doc.type))];
    return types.sort();
  }

  /**
   * Get file type from filename
   */
  private getFileType(filename: string): string {
    const extension = filename.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'pdf': return 'PDF';
      case 'csv': return 'CSV';
      case 'xlsx': case 'xls': return 'Excel';
      case 'docx': case 'doc': return 'Word';
      case 'txt': return 'Text';
      default: return 'Unknown';
    }
  }

  /**
   * Get status icon
   */
  getStatusIcon(status: string): string {
    switch (status) {
      case 'completed': return '✅';
      case 'processing': return '🔄';
      case 'error': return '❌';
      default: return '❓';
    }
  }

  /**
   * Get type icon
   */
  getTypeIcon(type: string): string {
    switch (type.toLowerCase()) {
      case 'pdf': return '📄';
      case 'csv': return '📊';
      case 'excel': return '📈';
      case 'word': return '📝';
      case 'text': return '📋';
      default: return '📁';
    }
  }

  /**
   * Format file size
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  /**
   * Get upload progress for file
   */
  getUploadProgress(filename: string): number {
    return this.uploadProgress[filename] || 0;
  }

  /**
   * Check if file has upload error
   */
  hasUploadError(filename: string): boolean {
    return this.uploadProgress[filename] === -1;
  }

  /**
   * Clear error message
   */
  clearError(): void {
    this.error = null;
  }

  /**
   * Refresh documents list
   */
  refresh(): void {
    this.loadDocuments();
  }

  /**
   * Check if user has enterprise access
   */
  hasEnterpriseAccess(): boolean {
    const tenant = this.authService.getCurrentTenant();
    return tenant?.tier === 'professional' || tenant?.tier === 'enterprise';
  }
}