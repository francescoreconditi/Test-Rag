import { Component, OnInit } from '@angular/core';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface ApiStatus {
  healthy: boolean;
  timestamp: string;
}

@Component({
  selector: 'app-root',
  templateUrl: './app.html',
  styleUrls: ['./app.scss'],
  standalone: true,
  imports: [CommonModule, HttpClientModule, FormsModule]
})
export class AppComponent implements OnInit {
  title = 'Business Intelligence RAG System';
  
  apiStatus: ApiStatus = {
    healthy: false,
    timestamp: new Date().toISOString()
  };
  
  selectedFile: File | null = null;
  isProcessing = false;
  analysisResult: any = null;
  errorMessage: string = '';
  
  private apiBaseUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.checkApiHealth();
  }

  checkApiHealth() {
    this.http.get<any>(`${this.apiBaseUrl}/health`).subscribe({
      next: (response) => {
        this.apiStatus = {
          healthy: response.status === 'healthy',
          timestamp: response.timestamp
        };
        this.errorMessage = '';
      },
      error: (error) => {
        this.apiStatus = {
          healthy: false,
          timestamp: new Date().toISOString()
        };
        this.errorMessage = 'Cannot connect to API server';
      }
    });
  }

  onFileSelected(event: any, type: string) {
    const file = event.target.files[0];
    if (file) {
      this.selectedFile = file;
      this.analysisResult = null;
      this.errorMessage = '';
    }
  }

  analyzeDocument(type: 'pdf' | 'csv') {
    if (!this.selectedFile) {
      this.errorMessage = 'Please select a file first';
      return;
    }

    this.isProcessing = true;
    this.errorMessage = '';
    this.analysisResult = null;

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    const endpoint = type === 'pdf' ? '/analyze/pdf' : '/analyze/csv';
    const url = `${this.apiBaseUrl}${endpoint}?output_format=json&enterprise_mode=false`;

    this.http.post(url, formData).subscribe({
      next: (response) => {
        this.analysisResult = response;
        this.isProcessing = false;
      },
      error: (error) => {
        this.errorMessage = `Analysis failed: ${error.error?.error || error.message || 'Unknown error'}`;
        this.isProcessing = false;
      }
    });
  }

  clearError() {
    this.errorMessage = '';
  }
}