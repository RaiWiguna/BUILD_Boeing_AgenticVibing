/**
 * DEMO track (ADR 0003): the port screens use to reach the local demo backend
 * (named workspaces, processing schedule, added recordings, saved playback).
 * Provided next to the ApiClient by ApiProvider; screens never import the adapter.
 */
import { create } from 'zustand';
import { isApiError } from './errors';

export type WorkspaceStatus = 'PROCESSING' | 'READY' | 'FAILED';

export interface ProcessingStep {
  key: string;
  label: string;
  status: 'PENDING' | 'RUNNING' | 'DONE';
  progress: number;
  planned_ms: number;
  detail: string[];
  /** Finished step: one line plus warnings. */
  summary?: string[];
}

export type FileRole = 'audio' | 'adsb';
/** Where a recording sits relative to the main one. */
export type FilePosition = 'before' | 'main' | 'after';

export interface WorkspaceFile {
  part: string;
  position: FilePosition;
  role: FileRole;
  name: string;
  size_bytes: number;
  sha256: string;
  detected: Record<string, unknown>;
}

export interface DemoWorkspace {
  id: string;
  name: string;
  scenario_id: string;
  status: WorkspaceStatus;
  duration_ms: number;
  created_at: string;
  ready_at: string | null;
  progress: number;
  eta_ms: number;
  steps: ProcessingStep[];
  files: WorkspaceFile[];
  labels: string[];
  recordings: { part: string; name: string; offset_ms: number; duration_ms: number; recorded_at: string }[];
  playback_cursor_ms: number;
}

/** A file picked for upload and the slot it was placed in. */
export interface PlacedFile {
  file: File;
  position: FilePosition;
}

export interface DemoHealth {
  status: string;
  profile: string;
  database: boolean;
  scenarios: number;
  version: string;
}

export interface DemoScenarios {
  expected_files: string[];
  files: { name: string; role: FileRole; position: FilePosition; part: string }[];
}

export interface DemoPort {
  health(): Promise<DemoHealth>;
  scenarios(): Promise<DemoScenarios>;
  listWorkspaces(): Promise<DemoWorkspace[]>;
  getWorkspace(id: string): Promise<DemoWorkspace>;
  /** Multipart upload of the session name and files (with their slots), with byte progress. */
  createWorkspace(name: string, files: PlacedFile[], onProgress: (loaded: number, total: number) => void, signal?: AbortSignal): Promise<DemoWorkspace>;
  /** Add recordings before or after an existing session; it is processed again. */
  savePlayback(id: string, cursorMs: number): Promise<{ cursor_ms: number }>;
  /** Make a READY workspace readable through the ApiClient (session screens). */
  registerWorkspace(id: string): Promise<void>;
  /** Remember the saved playback position for this browser session. */
  rememberPlayback(id: string, cursorMs: number): void;
}

export type DemoBackendStatus = 'UNKNOWN' | 'ONLINE' | 'OFFLINE';

/** Last known reachability of the demo backend, updated by the hybrid client. */
export const useDemoBackend = create<{ status: DemoBackendStatus; processing: DemoWorkspace[] }>(() => ({ status: 'UNKNOWN', processing: [] }));

/** Demo backend error code carried in `ApiError.details` (UNKNOWN_FILE, NAME_TAKEN, OFFLINE…). */
export function demoCode(error: unknown): string | null {
  if (!isApiError(error)) return null;
  return (error.details.code as string | undefined) ?? (error.details.demo_code as string | null | undefined) ?? null;
}
