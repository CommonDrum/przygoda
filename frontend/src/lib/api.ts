import axios from "axios";
import type {
  Project,
  ProjectCreateInput,
  Page,
  AppSettings,
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
  data: Partial<ProjectCreateInput>
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

// --- Generation ---

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
  format: "zip" | "excel"
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
