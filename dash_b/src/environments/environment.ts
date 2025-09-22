export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1',
  appName: 'RAG Dashboard',
  version: '1.0.0',
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