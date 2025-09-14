/**
 * Simplified Analytics Dashboard Component
 * Advanced analytics without Chart.js dependency
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription, timer } from 'rxjs';
import { RagService } from '../../services/rag.service';
import { AuthService } from '../../services/auth.service';

interface AnalyticsData {
  queryMetrics: {
    totalQueries: number;
    successRate: number;
    avgResponseTime: number;
    queryTrends: { date: string; count: number; avgTime: number }[];
  };
  documentMetrics: {
    totalDocuments: number;
    totalVectors: number;
    documentTypes: { type: string; count: number }[];
    uploadTrends: { date: string; count: number }[];
  };
  systemMetrics: {
    cpuUsage: number;
    memoryUsage: number;
    diskUsage: number;
    systemHealth: 'healthy' | 'warning' | 'error';
  };
  enterpriseMetrics?: {
    validationResults: { rule: string; passed: number; failed: number }[];
    benchmarkScores: { metric: string; score: number; target: number }[];
    sourceAccuracy: { document: string; accuracy: number }[];
  };
}

interface BenchmarkResult {
  id: string;
  timestamp: Date;
  overallScore: number;
  categoryScores: { [key: string]: number };
  testResults: { name: string; passed: boolean; score: number }[];
  status: 'completed' | 'running' | 'failed';
}

@Component({
  selector: 'app-analytics',
  templateUrl: './analytics.component.html',
  styleUrls: ['./analytics.component.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule]
})
export class AnalyticsComponent implements OnInit, OnDestroy {

  analyticsData: AnalyticsData | null = null;
  benchmarkResults: BenchmarkResult[] = [];
  isLoading = false;
  isRunningBenchmark = false;
  error: string | null = null;

  // Time range selector
  selectedTimeRange = '7d';
  timeRanges = [
    { value: '24h', label: 'Last 24 Hours' },
    { value: '7d', label: 'Last 7 Days' },
    { value: '30d', label: 'Last 30 Days' },
    { value: '90d', label: 'Last 90 Days' }
  ];

  private subscriptions = new Subscription();

  constructor(
    private ragService: RagService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loadAnalyticsData();
    this.loadBenchmarkResults();
    this.startAutoRefresh();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  /**
   * Load analytics data
   */
  private loadAnalyticsData(): void {
    this.isLoading = true;
    this.error = null;

    // Mock analytics data - in real app would call API
    setTimeout(() => {
      this.analyticsData = {
        queryMetrics: {
          totalQueries: 15847,
          successRate: 94.2,
          avgResponseTime: 1250,
          queryTrends: this.generateQueryTrends()
        },
        documentMetrics: {
          totalDocuments: 342,
          totalVectors: 15847,
          documentTypes: [
            { type: 'PDF', count: 156 },
            { type: 'Excel', count: 89 },
            { type: 'CSV', count: 67 },
            { type: 'Word', count: 30 }
          ],
          uploadTrends: this.generateUploadTrends()
        },
        systemMetrics: {
          cpuUsage: 45.2,
          memoryUsage: 62.8,
          diskUsage: 73.1,
          systemHealth: 'healthy'
        },
        enterpriseMetrics: this.hasEnterpriseAccess() ? {
          validationResults: [
            { rule: 'Balance Sheet Coherence', passed: 89, failed: 11 },
            { rule: 'EBITDA Margin Validation', passed: 95, failed: 5 },
            { rule: 'Cash Flow Coherence', passed: 87, failed: 13 }
          ],
          benchmarkScores: [
            { metric: 'Numeric Accuracy', score: 92.3, target: 90 },
            { metric: 'Source Attribution', score: 88.7, target: 85 },
            { metric: 'Response Speed', score: 94.1, target: 90 }
          ],
          sourceAccuracy: [
            { document: 'Q3-2023-Report.pdf', accuracy: 96.2 },
            { document: 'Annual-Summary.xlsx', accuracy: 94.8 },
            { document: 'Market-Analysis.pdf', accuracy: 91.5 }
          ]
        } : undefined
      };

      this.isLoading = false;
    }, 1000);
  }

  /**
   * Load benchmark results
   */
  private loadBenchmarkResults(): void {
    // Mock benchmark results
    this.benchmarkResults = [
      {
        id: '1',
        timestamp: new Date(Date.now() - 86400000),
        overallScore: 92.3,
        categoryScores: {
          'Numeric Accuracy': 94.2,
          'Source Attribution': 88.7,
          'Response Speed': 94.1,
          'Validation': 91.8
        },
        testResults: [
          { name: 'Financial Metrics Extraction', passed: true, score: 95.2 },
          { name: 'Source Reference Accuracy', passed: true, score: 89.1 },
          { name: 'Response Time < 2s', passed: true, score: 94.7 }
        ],
        status: 'completed'
      }
    ];
  }

  /**
   * Generate mock query trends data
   */
  private generateQueryTrends(): { date: string; count: number; avgTime: number }[] {
    const trends = [];
    const days = this.getTimeRangeDays();

    for (let i = days - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);

      trends.push({
        date: date.toISOString().split('T')[0],
        count: Math.floor(Math.random() * 200) + 50,
        avgTime: Math.floor(Math.random() * 500) + 800
      });
    }

    return trends;
  }

  /**
   * Generate mock upload trends data
   */
  private generateUploadTrends(): { date: string; count: number }[] {
    const trends = [];
    const days = this.getTimeRangeDays();

    for (let i = days - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);

      trends.push({
        date: date.toISOString().split('T')[0],
        count: Math.floor(Math.random() * 20) + 1
      });
    }

    return trends;
  }

  /**
   * Get number of days for selected time range
   */
  private getTimeRangeDays(): number {
    switch (this.selectedTimeRange) {
      case '24h': return 1;
      case '7d': return 7;
      case '30d': return 30;
      case '90d': return 90;
      default: return 7;
    }
  }

  /**
   * Start auto-refresh timer
   */
  private startAutoRefresh(): void {
    this.subscriptions.add(
      timer(60000, 60000).subscribe(() => {
        this.refreshAnalytics();
      })
    );
  }

  /**
   * Refresh analytics data
   */
  refreshAnalytics(): void {
    this.loadAnalyticsData();
  }

  /**
   * Handle time range change
   */
  onTimeRangeChange(): void {
    this.refreshAnalytics();
  }

  /**
   * Run new benchmark
   */
  runBenchmark(): void {
    this.isRunningBenchmark = true;

    this.subscriptions.add(
      this.ragService.runBenchmark().subscribe({
        next: (result) => {
          const newResult: BenchmarkResult = {
            id: Date.now().toString(),
            timestamp: new Date(),
            overallScore: result.overallScore,
            categoryScores: result.categoryScores,
            testResults: result.testResults,
            status: 'completed'
          };

          this.benchmarkResults.unshift(newResult);
          this.isRunningBenchmark = false;
        },
        error: (error) => {
          this.error = 'Benchmark failed: ' + error.message;
          this.isRunningBenchmark = false;
        }
      })
    );
  }

  /**
   * Get system health icon
   */
  getSystemHealthIcon(): string {
    if (!this.analyticsData) return '❓';

    switch (this.analyticsData.systemMetrics.systemHealth) {
      case 'healthy': return '✅';
      case 'warning': return '⚠️';
      case 'error': return '❌';
      default: return '❓';
    }
  }

  /**
   * Get benchmark status icon
   */
  getBenchmarkStatusIcon(status: string): string {
    switch (status) {
      case 'completed': return '✅';
      case 'running': return '🔄';
      case 'failed': return '❌';
      default: return '❓';
    }
  }

  /**
   * Format percentage
   */
  formatPercentage(value: number): string {
    return value.toFixed(1) + '%';
  }

  /**
   * Format number with commas
   */
  formatNumber(num: number): string {
    return num.toLocaleString();
  }

  /**
   * Make Object available to template
   */
  Object = Object;

  /**
   * Check if user has enterprise access
   */
  hasEnterpriseAccess(): boolean {
    const tenant = this.authService.getCurrentTenant();
    return tenant?.tier === 'professional' || tenant?.tier === 'enterprise';
  }

  /**
   * Clear error message
   */
  clearError(): void {
    this.error = null;
  }
}