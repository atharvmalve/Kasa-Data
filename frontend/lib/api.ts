import {
  DataPack,
  Document,
  DocumentContent,
  DocumentChunk,
  ChunkVectorResponse,
  DocumentSummary,
  ExtractedFact,
  ProcessingEvent,
  PaginatedResponse,
  TransformationLedger,
  ChunkingComparisonResponse,
  EvaluationResponse,
  StorageFootprintResponse,
} from "@/types";

const BASE_URL = ""; // Relative path, resolved by Next.js rewrites to backend

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    let errorDetail = "An unexpected error occurred.";
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      errorDetail = `Request failed with status ${res.status}`;
    }
    throw new ApiError(errorDetail, res.status);
  }

  if (res.status === 204) {
    return {} as T;
  }

  return res.json();
}

export const api = {
  // Health
  getHealth: () =>
    request<{ status: string; database: { status: string; engine: string }; version: string }>("/api/health"),

  // DataPacks
  listDataPacks: () => request<DataPack[]>("/api/datapacks"),
  getDataPack: (id: string) => request<DataPack>(`/api/datapacks/${id}`),
  createDataPack: (data: { name: string; description?: string }) =>
    request<DataPack>("/api/datapacks", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateDataPack: (id: string, data: { name?: string; description?: string }) =>
    request<DataPack>(`/api/datapacks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteDataPack: (id: string) =>
    request<void>(`/api/datapacks/${id}`, {
      method: "DELETE",
    }),

  // Documents
  listDocuments: (datapackId: string) =>
    request<Document[]>(`/api/datapacks/${datapackId}/documents`),
  getDocument: (id: string) => request<Document>(`/api/documents/${id}`),
  getDocumentContent: (id: string) => request<DocumentContent>(`/api/documents/${id}/content`),
  getDocumentChunks: (id: string, page = 1, pageSize = 20) =>
    request<PaginatedResponse<DocumentChunk>>(`/api/documents/${id}/chunks?page=${page}&page_size=${pageSize}`),
  getChunkVector: (documentId: string, chunkId: string) =>
    request<ChunkVectorResponse>(`/api/documents/${documentId}/chunks/${chunkId}/vector`),
  getDocumentFacts: (id: string) => request<ExtractedFact[]>(`/api/documents/${id}/facts`),
  getDocumentSummaries: (id: string) => request<DocumentSummary[]>(`/api/documents/${id}/summaries`),
  getDocumentEvents: (id: string, page = 1, pageSize = 50) =>
    request<PaginatedResponse<ProcessingEvent>>(`/api/documents/${id}/events?page=${page}&page_size=${pageSize}`),

  // Phase 1.1 Context Quality & Compression Audit
  getDocumentAudit: (id: string) => request<TransformationLedger>(`/api/documents/${id}/audit`),
  compareChunkingTargets: (id: string) =>
    request<ChunkingComparisonResponse>(`/api/documents/${id}/chunking-comparison`, {
      method: "POST",
    }),
  getDocumentEvaluation: (id: string) => request<EvaluationResponse>(`/api/documents/${id}/evaluation`),
  getDocumentStorageFootprint: (id: string) =>
    request<StorageFootprintResponse>(`/api/documents/${id}/storage-footprint`),

  uploadDocument: async (datapackId: string, file: File): Promise<Document> => {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`/api/datapacks/${datapackId}/documents`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      let errorDetail = "Failed to upload file.";
      try {
        const errJson = await res.json();
        errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
      } catch {
        errorDetail = `Upload failed with status ${res.status}`;
      }
      throw new ApiError(errorDetail, res.status);
    }

    return res.json();
  },

  retryProcessing: (documentId: string) =>
    request<Document>(`/api/documents/${documentId}/retry`, {
      method: "POST",
    }),

  deleteDocument: (documentId: string) =>
    request<void>(`/api/documents/${documentId}`, {
      method: "DELETE",
    }),
};
