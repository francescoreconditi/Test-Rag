export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000',
  appName: 'RAG Dashboard',
  version: '1.0.0',
  // OpenAI API Key for voice features - ADD YOUR KEY HERE
  openaiApiKey: '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', // Add your OpenAI API key here for voice functionality
  features: {
    enterprise: true,
    audioGeneration: true,
    pdfExport: true,
    multiTenant: true
  },
  limits: {
    maxFileSize: 50 * 1024 * 1024, // 50MB
    maxFiles: 10,
    allowedFileTypes: [
      'pdf', 'txt', 'docx', 'md', 'json',
      'csv', 'xls', 'xlsx', 'jpg', 'jpeg', 'png'
    ]
  },
  ui: {
    defaultTheme: 'indigo-pink',
    enableAnimations: true,
    autoSave: true,
    autoSaveInterval: 30000 // 30 seconds
  }
};