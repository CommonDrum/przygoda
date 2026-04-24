import axios from "axios";
import type {
  Project,
  ProjectCreateInput,
  ProjectUpdateInput,
  Page,
  AppSettings,
  Prompt,
  PromptInput,
  PromptKind,
  ImageVersion,
  ExportFormat,
  ModelCatalog,
} from "./types";
import { getToken, clearToken } from "./auth";

const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearToken();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// --- Auth ---

export async function loginApi(
  username: string,
  password: string
): Promise<{ access_token: string; token_type: string }> {
  const { data } = await api.post("/auth/login", { username, password });
  return data;
}

// --- Projects ---

export async function getProjects(): Promise<Project[]> {
  const { data } = await api.get("/projects");
  return data;
}

export async function getProject(id: number): Promise<Project> {
  const { data } = await api.get(`/projects/${id}`);
  return data;
}

export async function createProject(
  input: ProjectCreateInput
): Promise<Project> {
  const { data } = await api.post("/projects", input);
  return data;
}

export async function updateProject(
  id: number,
  data: ProjectUpdateInput
): Promise<Project> {
  const { data: result } = await api.put(`/projects/${id}`, data);
  return result;
}

export async function deleteProject(id: number): Promise<void> {
  await api.delete(`/projects/${id}`);
}

// --- Pages ---

export async function getPages(projectId: number): Promise<Page[]> {
  const { data } = await api.get(`/projects/${projectId}/pages`);
  return data;
}

export async function getPageVersions(pageId: number): Promise<ImageVersion[]> {
  const { data } = await api.get(`/pages/${pageId}/versions`);
  return data;
}

export async function restorePageVersion(
  pageId: number,
  versionId: number
): Promise<Page> {
  const { data } = await api.post(`/pages/${pageId}/restore-version`, {
    version_id: versionId,
  });
  return data;
}

export async function getReferenceVersions(
  projectId: number
): Promise<ImageVersion[]> {
  const { data } = await api.get(`/projects/${projectId}/reference-versions`);
  return data;
}

export async function restoreReference(
  projectId: number,
  versionId: number
): Promise<Project> {
  const { data } = await api.post(`/projects/${projectId}/restore-reference`, {
    version_id: versionId,
  });
  return data;
}

// --- Generation ---

export async function generateReference(projectId: number): Promise<Project> {
  const { data } = await api.post(`/projects/${projectId}/generate-reference`);
  return data;
}

export async function regenerateReference(
  projectId: number,
  prompt?: string
): Promise<Project> {
  const body = prompt !== undefined ? { prompt } : undefined;
  const { data } = await api.post(
    `/projects/${projectId}/regenerate-reference`,
    body
  );
  return data;
}

export async function uploadReferenceImage(
  projectId: number,
  file: File
): Promise<Project> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post(
    `/projects/${projectId}/upload-reference`,
    form
  );
  return data;
}

export async function uploadStyleGuide(
  projectId: number,
  file: File
): Promise<Project> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post(
    `/projects/${projectId}/upload-style-guide`,
    form
  );
  return data;
}

export async function deleteStyleGuide(projectId: number): Promise<Project> {
  const { data } = await api.delete(`/projects/${projectId}/style-guide`);
  return data;
}

export async function updatePage(
  pageId: number,
  data: { text?: string | null; image_prompt?: string | null }
): Promise<Page> {
  const { data: result } = await api.put(`/pages/${pageId}`, data);
  return result;
}

export async function approveReference(projectId: number): Promise<Project> {
  const { data } = await api.post(`/projects/${projectId}/approve-reference`);
  return data;
}

export async function generateStory(projectId: number): Promise<Project> {
  const { data } = await api.post(`/projects/${projectId}/generate-story`);
  return data;
}

export async function generatePrompts(projectId: number): Promise<Project> {
  const { data } = await api.post(`/projects/${projectId}/generate-prompts`);
  return data;
}

export async function generateImages(projectId: number): Promise<void> {
  await api.post(`/projects/${projectId}/generate-images`);
}

export async function regenerateImage(
  pageId: number,
  prompt?: string
): Promise<Page> {
  const body = prompt !== undefined ? { prompt } : undefined;
  const { data } = await api.post(`/pages/${pageId}/regenerate-image`, body);
  return data;
}

// --- Export ---

export async function exportProject(
  projectId: number,
  format: ExportFormat
): Promise<string> {
  const { data } = await api.post(`/projects/${projectId}/export`, { format });
  return data.file_path;
}

// --- Settings ---

export async function getSettings(): Promise<AppSettings> {
  const { data } = await api.get("/settings");
  return data;
}

export async function updateSettings(
  settings: Partial<AppSettings>
): Promise<AppSettings> {
  const { data } = await api.put("/settings", settings);
  return data;
}

export async function validateApiKey(
  provider: string
): Promise<{ valid: boolean; error?: string }> {
  const { data } = await api.post("/settings/validate-key", { provider });
  return data;
}

// --- Prompts library ---

export async function listPrompts(kind?: PromptKind): Promise<Prompt[]> {
  const { data } = await api.get("/prompts", {
    params: kind ? { kind } : undefined,
  });
  return data;
}

export async function createPrompt(input: PromptInput): Promise<Prompt> {
  const { data } = await api.post("/prompts", input);
  return data;
}

export async function updatePrompt(
  id: number,
  input: Partial<Pick<PromptInput, "title" | "content">>
): Promise<Prompt> {
  const { data } = await api.put(`/prompts/${id}`, input);
  return data;
}

export async function deletePrompt(id: number): Promise<void> {
  await api.delete(`/prompts/${id}`);
}

// --- Provider model catalog ---

export async function getModelCatalog(): Promise<ModelCatalog> {
  const { data } = await api.get("/providers/models");
  return data;
}
