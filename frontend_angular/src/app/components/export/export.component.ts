/**
 * Export Component
 * Generate and export reports in multiple formats (PDF, Excel, JSON)
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { RagService } from '../../services/rag.service';
import { AuthService } from '../../services/auth.service';
// Alternative to file-saver
const saveAs = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
};

interface ExportOptions {
  format: 'pdf' | 'excel' | 'json';
  includeMetadata: boolean;
  includeValidation: boolean;
  includeSourceRefs: boolean;
  dateRange?: {
    start: Date;
    end: Date;
  };
  documentTypes?: string[];
  queryHistory?: boolean;
}

interface ExportTemplate {
  id: string;
  name: string;
  description: string;
  format: 'pdf' | 'excel' | 'json';
  options: Partial<ExportOptions>;
  isDefault?: boolean;
}

interface ExportHistory {
  id: string;
  filename: string;
  format: string;
  createdAt: Date;
  size: number;
  status: 'completed' | 'processing' | 'failed';
  downloadCount: number;
}

@Component({
  selector: 'app-export',
  templateUrl: './export.component.html',
  styleUrls: ['./export.component.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule]
})
export class ExportComponent implements OnInit, OnDestroy {
  exportOptions: ExportOptions = {
    format: 'pdf',
    includeMetadata: true,
    includeValidation: true,
    includeSourceRefs: true,
    queryHistory: false,
    dateRange: {
      start: new Date(),
      end: new Date()
    }
  };

  availableTemplates: ExportTemplate[] = [
    {
      id: 'executive-summary',
      name: 'Executive Summary',
      description: 'High-level overview with key metrics and insights',
      format: 'pdf',
      options: {
        includeMetadata: true,
        includeValidation: false,
        includeSourceRefs: false
      },
      isDefault: true
    },
    {
      id: 'detailed-report',
      name: 'Detailed Technical Report',
      description: 'Complete analysis with all validation results',
      format: 'pdf',
      options: {
        includeMetadata: true,
        includeValidation: true,
        includeSourceRefs: true
      }
    },
    {
      id: 'data-export',
      name: 'Raw Data Export',
      description: 'Complete data export in Excel format',
      format: 'excel',
      options: {
        includeMetadata: true,
        includeValidation: true,
        includeSourceRefs: true,
        queryHistory: true
      }
    },
    {
      id: 'api-export',
      name: 'API Integration Export',
      description: 'JSON format for API integration',
      format: 'json',
      options: {
        includeMetadata: true,
        includeValidation: true,
        includeSourceRefs: true
      }
    }
  ];

  selectedTemplate: ExportTemplate | null = null;
  isExporting = false;
  exportProgress = 0;
  error: string | null = null;
  success: string | null = null;

  exportHistory: ExportHistory[] = [];
  showHistory = false;

  // Available document types for filtering
  availableDocumentTypes: string[] = ['PDF', 'CSV', 'Excel', 'Word'];

  private subscriptions = new Subscription();

  constructor(
    private ragService: RagService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loadExportHistory();
    this.setDefaultTemplate();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  /**
   * Set default template
   */
  private setDefaultTemplate(): void {
    const defaultTemplate = this.availableTemplates.find(t => t.isDefault);
    if (defaultTemplate) {
      this.selectTemplate(defaultTemplate);
    }
  }

  /**
   * Load export history
   */
  private loadExportHistory(): void {
    // Mock export history - in real app would call API
    this.exportHistory = [
      {
        id: '1',
        filename: 'executive-summary-2024-01.pdf',
        format: 'PDF',
        createdAt: new Date(Date.now() - 86400000), // 1 day ago
        size: 2.5 * 1024 * 1024, // 2.5MB
        status: 'completed',
        downloadCount: 3
      },
      {
        id: '2',
        filename: 'data-export-2024-01.xlsx',
        format: 'Excel',
        createdAt: new Date(Date.now() - 172800000), // 2 days ago
        size: 5.2 * 1024 * 1024, // 5.2MB
        status: 'completed',
        downloadCount: 1
      }
    ];
  }

  /**
   * Select export template
   */
  selectTemplate(template: ExportTemplate): void {
    this.selectedTemplate = template;
    this.exportOptions = {
      ...this.exportOptions,
      format: template.format,
      ...template.options
    };
    this.clearMessages();
  }

  /**
   * Generate and export report
   */
  async exportReport(): Promise<void> {
    if (!this.selectedTemplate) {
      this.error = 'Please select an export template';
      return;
    }

    this.isExporting = true;
    this.exportProgress = 0;
    this.clearMessages();

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        this.exportProgress = Math.min(this.exportProgress + 10, 90);
      }, 200);

      // Prepare export data
      const exportData = await this.prepareExportData();

      // Call export API
      const blob = await this.callExportApi(exportData);

      clearInterval(progressInterval);
      this.exportProgress = 100;

      // Generate filename
      const timestamp = new Date().toISOString().split('T')[0];
      const filename = `${this.selectedTemplate.id}-${timestamp}.${this.getFileExtension()}`;

      // Download file
      saveAs(blob, filename);

      // Add to history
      this.addToExportHistory(filename, blob.size);

      this.success = `Export completed successfully: ${filename}`;

    } catch (error: any) {
      this.error = 'Export failed: ' + (error.message || 'Unknown error');
    } finally {
      this.isExporting = false;
    }
  }

  /**
   * Prepare export data based on options
   */
  private async prepareExportData(): Promise<any> {
    const data: any = {
      template: this.selectedTemplate?.id,
      format: this.exportOptions.format,
      options: this.exportOptions,
      timestamp: new Date().toISOString(),
      user: this.authService.getCurrentUser(),
      tenant: this.authService.getCurrentTenant()
    };

    // Add dashboard stats if requested
    if (this.exportOptions.includeMetadata) {
      try {
        const stats = await this.ragService.getDashboardStats().toPromise();
        data.dashboardStats = stats;
      } catch (error) {
        console.warn('Failed to load dashboard stats for export:', error);
      }
    }

    // Add validation results if requested
    if (this.exportOptions.includeValidation) {
      try {
        const rules = await this.ragService.getValidationRules().toPromise();
        data.validationRules = rules;
      } catch (error) {
        console.warn('Failed to load validation rules for export:', error);
      }
    }

    // Add document list if requested
    if (this.exportOptions.includeSourceRefs) {
      try {
        const documents = await this.ragService.getDocuments().toPromise();
        data.documents = documents;
      } catch (error) {
        console.warn('Failed to load documents for export:', error);
      }
    }

    return data;
  }

  /**
   * Call export API
   */
  private callExportApi(data: any): Promise<Blob> {
    return new Promise((resolve, reject) => {
      this.ragService.exportData(this.exportOptions.format, data).subscribe({
        next: (blob) => resolve(blob),
        error: (error) => reject(error)
      });
    });
  }

  /**
   * Add export to history
   */
  private addToExportHistory(filename: string, size: number): void {
    const newExport: ExportHistory = {
      id: Date.now().toString(),
      filename,
      format: this.exportOptions.format.toUpperCase(),
      createdAt: new Date(),
      size,
      status: 'completed',
      downloadCount: 1
    };

    this.exportHistory.unshift(newExport);
  }

  /**
   * Get file extension for current format
   */
  private getFileExtension(): string {
    switch (this.exportOptions.format) {
      case 'pdf': return 'pdf';
      case 'excel': return 'xlsx';
      case 'json': return 'json';
      default: return 'txt';
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
   * Get format icon
   */
  getFormatIcon(format: string): string {
    switch (format.toLowerCase()) {
      case 'pdf': return '📄';
      case 'excel': case 'xlsx': return '📊';
      case 'json': return '🔗';
      default: return '📁';
    }
  }

  /**
   * Get status icon
   */
  getStatusIcon(status: string): string {
    switch (status) {
      case 'completed': return '✅';
      case 'processing': return '🔄';
      case 'failed': return '❌';
      default: return '❓';
    }
  }

  /**
   * Toggle export history visibility
   */
  toggleHistory(): void {
    this.showHistory = !this.showHistory;
  }

  /**
   * Download from history
   */
  downloadFromHistory(exportItem: ExportHistory): void {
    // In real app, would call API to re-download
    console.log('Re-downloading:', exportItem.filename);
    exportItem.downloadCount++;

    // Mock download
    const mockContent = JSON.stringify({
      message: 'This is a mock download',
      originalFile: exportItem.filename
    });
    const blob = new Blob([mockContent], { type: 'application/json' });
    saveAs(blob, exportItem.filename);
  }

  /**
   * Delete from history
   */
  deleteFromHistory(exportItem: ExportHistory): void {
    if (confirm(`Delete ${exportItem.filename}?`)) {
      this.exportHistory = this.exportHistory.filter(item => item.id !== exportItem.id);
    }
  }

  /**
   * Clear success and error messages
   */
  private clearMessages(): void {
    this.error = null;
    this.success = null;
  }

  /**
   * Clear error message
   */
  clearError(): void {
    this.error = null;
  }

  /**
   * Clear success message
   */
  clearSuccess(): void {
    this.success = null;
  }

  /**
   * Handle document type selection change
   */
  onDocumentTypeChange(event: any): void {
    const value = event.target.value;
    const checked = event.target.checked;

    if (!this.exportOptions.documentTypes) {
      this.exportOptions.documentTypes = [];
    }

    if (checked) {
      this.exportOptions.documentTypes.push(value);
    } else {
      const index = this.exportOptions.documentTypes.indexOf(value);
      if (index > -1) {
        this.exportOptions.documentTypes.splice(index, 1);
      }
    }
  }

  /**
   * Handle date changes
   */
  onStartDateChange(dateString: string): void {
    this.exportOptions.dateRange!.start = new Date(dateString);
  }

  onEndDateChange(dateString: string): void {
    this.exportOptions.dateRange!.end = new Date(dateString);
  }

  /**
   * Check if user has enterprise access
   */
  hasEnterpriseAccess(): boolean {
    const tenant = this.authService.getCurrentTenant();
    return tenant?.tier === 'professional' || tenant?.tier === 'enterprise';
  }
}