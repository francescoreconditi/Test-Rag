export interface DocumentAnalysis {
  analysis: string;
  confidence: number;
  sources: SourceReference[];
  metadata: AnalysisMetadata;
  processing_time?: number;
  file_info?: FileInfo;
}

export interface AnalysisResult {
  analysis: string;
  confidence: number;
  sources: SourceReference[];
  metadata: AnalysisMetadata;
}

export interface FileInfo {
  filename: string;
  size_bytes: number;
  pages: number;
  has_tables: boolean;
  has_ocr?: boolean;
}

export interface SourceReference {
  source: string;
  page?: number;
  confidence: number;
  metadata?: Record<string, any>;
  text?: string;
  score?: number;
}

export interface AnalysisMetadata {
  processing_time: number;
  document_pages: number;
  tables_found: number;
  charts_found?: number;
  document_type?: string;
  generated_at?: string;
}

export interface CSVAnalysis {
  summary: Record<string, number>;
  insights: string[];
  trends?: {
    yoy_growth: Array<{
      year: number;
      growth_percentage: number;
    }>;
  };
  recommendations?: string[];
  charts?: ChartData[];
}

export interface ChartData {
  type: 'bar' | 'line' | 'pie' | 'scatter';
  title: string;
  data: {
    labels: string[];
    datasets: Array<{
      label: string;
      data: number[];
      backgroundColor?: string | string[];
      borderColor?: string;
      borderWidth?: number;
    }>;
  };
}

export interface FAQItem {
  question: string;
  answer: string;
  confidence: number;
  sources?: SourceReference[];
  generated_at?: string;
}

export interface FAQResponse {
  success: boolean;
  faqs: FAQItem[];
  processing_time: number;
  metadata: {
    generated_at: string;
    document_types: string[];
    total_documents: number;
  };
  error?: string;
}

export interface IndexStats {
  total_vectors: number;
  total_documents: number;
  collection_name?: string;
  last_updated?: string;
}

export interface QueryRequest {
  query: string;
  output_format?: 'json' | 'text' | 'pdf';
  enterprise_mode?: boolean;
  max_results?: number;
}

export interface QueryResponse {
  response: string;
  sources: SourceReference[];
  confidence: number;
  processing_time: number;
  enterprise_stats?: EnterpriseStats;
}

export interface EnterpriseStats {
  hybrid_retrieval_enabled: boolean;
  ontology_mapping_applied: boolean;
  data_normalization_performed: boolean;
  financial_validation_passed: boolean;
  fact_table_entries_created: number;
}