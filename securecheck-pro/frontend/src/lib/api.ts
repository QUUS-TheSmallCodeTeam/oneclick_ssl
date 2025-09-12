/**
 * API configuration and utilities for the frontend
 */

// API base URL configuration
const getApiBaseUrl = (): string => {
  // In development, use the backend server directly
  if (process.env.NODE_ENV === 'development') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }
  
  // In production, use relative URLs (assumes backend is served from same domain)
  return '/api/v1';
};

export const API_BASE_URL = getApiBaseUrl();

export const API_ENDPOINTS = {
  analyze: `${API_BASE_URL}/api/v1/analyze`,
  downloadReport: (reportId: string) => `${API_BASE_URL}/api/v1/reports/${reportId}/download`,
  generatePdf: `${API_BASE_URL}/api/v1/reports/generate-pdf`,
} as const;

// API utility functions
export const apiRequest = async <T>(
  url: string, 
  options: RequestInit = {}
): Promise<T> => {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error: ${response.status} ${response.statusText} - ${errorText}`);
  }

  return response.json();
};

export const downloadFile = async (url: string, filename: string): Promise<void> => {
  const response = await fetch(url);
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Download failed: ${response.status} ${response.statusText} - ${errorText}`);
  }

  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(downloadUrl);
  document.body.removeChild(a);
};