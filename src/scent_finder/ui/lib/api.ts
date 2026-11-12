import { useQuery, useSuspenseQuery, useMutation } from "@tanstack/react-query";
import type { UseQueryOptions, UseSuspenseQueryOptions, UseMutationOptions } from "@tanstack/react-query";
export class ApiError extends Error {
    status: number;
    statusText: string;
    body: unknown;
    constructor(status: number, statusText: string, body: unknown){
        super(`HTTP ${status}: ${statusText}`);
        this.name = "ApiError";
        this.status = status;
        this.statusText = statusText;
        this.body = body;
    }
}
export interface ChatIn {
    messages: ChatMessage[];
}
export interface ChatMessage {
    content: string;
    role: string;
}
export interface ChatOut {
    pending_import?: ImportPreviewOut | null;
    remaining_today?: number | null;
    reply: string;
    tool_calls: ToolCall[];
    usage: Record<string, number>;
}
export interface CollectionOut {
    count: number;
    items: Fragrance[];
}
export interface Fragrance {
    accords?: string[];
    description?: string | null;
    family?: string | null;
    house: string;
    id?: number | null;
    last_worn?: string | null;
    low_confidence?: boolean;
    my_rating?: number | null;
    my_status?: string | null;
    name: string;
    notes?: string[];
    price_band?: string | null;
    season?: string[];
    source?: string | null;
    times_worn?: number | null;
    year?: number | null;
}
export interface HTTPValidationError {
    detail?: ValidationError[];
}
export interface ImportIn {
    status?: string;
    text: string;
}
export interface ImportMatch {
    already?: string | null;
    id: number;
    input: string;
    match: string;
    score: number;
}
export interface ImportMiss {
    did_you_mean?: string[];
    input: string;
}
export interface ImportPreviewOut {
    preview: ImportMatch[];
    status?: string;
    unmatched: ImportMiss[];
}
export interface ItemUpdateIn {
    rating?: number | null;
    status?: string | null;
}
export interface MeOut {
    by_status: Record<string, number>;
    daily_limit: number;
    display_name?: string | null;
    shelf_count: number;
}
export interface SaveIn {
    fragrance_ids: number[];
    rating?: number | null;
    status?: string;
}
export interface SaveOut {
    count: number;
    saved: boolean;
}
export interface ScentDnaOut {
    based_on: string;
    family_gaps: string[];
    favourites: string[];
    profile: Record<string, number>;
    you_tend_to_like: string[];
}
export interface ToolCall {
    args: Record<string, unknown>;
    name: string;
}
export interface ValidationError {
    ctx?: Record<string, unknown>;
    input?: unknown;
    loc: (string | number)[];
    msg: string;
    type: string;
}
export interface VersionOut {
    version: string;
}
export const chat = async (data: ChatIn, options?: RequestInit): Promise<{
    data: ChatOut;
}> =>{
    const res = await fetch("/api/chat", {
        ...options,
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...options?.headers
        },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export function useChat(options?: {
    mutation?: UseMutationOptions<{
        data: ChatOut;
    }, ApiError, ChatIn>;
}) {
    return useMutation({
        mutationFn: (data)=>chat(data),
        ...options?.mutation
    });
}
export interface GetCollectionParams {
    status?: string | null;
}
export const getCollection = async (params?: GetCollectionParams, options?: RequestInit): Promise<{
    data: CollectionOut;
}> =>{
    const searchParams = new URLSearchParams();
    if (params?.status != null) searchParams.set("status", String(params?.status));
    const queryString = searchParams.toString();
    const url = queryString ? `/api/collection?${queryString}` : "/api/collection";
    const res = await fetch(url, {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const getCollectionKey = (params?: GetCollectionParams)=>{
    return [
        "/api/collection",
        params
    ] as const;
};
export function useGetCollection<TData = {
    data: CollectionOut;
}>(options?: {
    params?: GetCollectionParams;
    query?: Omit<UseQueryOptions<{
        data: CollectionOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: getCollectionKey(options?.params),
        queryFn: ()=>getCollection(options?.params),
        ...options?.query
    });
}
export function useGetCollectionSuspense<TData = {
    data: CollectionOut;
}>(options?: {
    params?: GetCollectionParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: CollectionOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: getCollectionKey(options?.params),
        queryFn: ()=>getCollection(options?.params),
        ...options?.query
    });
}
export const previewImport = async (data: ImportIn, options?: RequestInit): Promise<{
    data: ImportPreviewOut;
}> =>{
    const res = await fetch("/api/collection/preview", {
        ...options,
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...options?.headers
        },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export function usePreviewImport(options?: {
    mutation?: UseMutationOptions<{
        data: ImportPreviewOut;
    }, ApiError, ImportIn>;
}) {
    return useMutation({
        mutationFn: (data)=>previewImport(data),
        ...options?.mutation
    });
}
export const saveToCollection = async (data: SaveIn, options?: RequestInit): Promise<{
    data: SaveOut;
}> =>{
    const res = await fetch("/api/collection/save", {
        ...options,
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...options?.headers
        },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export function useSaveToCollection(options?: {
    mutation?: UseMutationOptions<{
        data: SaveOut;
    }, ApiError, SaveIn>;
}) {
    return useMutation({
        mutationFn: (data)=>saveToCollection(data),
        ...options?.mutation
    });
}
export interface UpdateCollectionItemParams {
    fragrance_id: number;
}
export const updateCollectionItem = async (params: UpdateCollectionItemParams, data: ItemUpdateIn, options?: RequestInit): Promise<{
    data: Record<string, unknown>;
}> =>{
    const res = await fetch(`/api/collection/${params.fragrance_id}`, {
        ...options,
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            ...options?.headers
        },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export function useUpdateCollectionItem(options?: {
    mutation?: UseMutationOptions<{
        data: Record<string, unknown>;
    }, ApiError, {
        params: UpdateCollectionItemParams;
        data: ItemUpdateIn;
    }>;
}) {
    return useMutation({
        mutationFn: (vars)=>updateCollectionItem(vars.params, vars.data),
        ...options?.mutation
    });
}
export interface RemoveFromCollectionParams {
    fragrance_id: number;
}
export const removeFromCollection = async (params: RemoveFromCollectionParams, options?: RequestInit): Promise<{
    data: Record<string, unknown>;
}> =>{
    const res = await fetch(`/api/collection/${params.fragrance_id}`, {
        ...options,
        method: "DELETE"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export function useRemoveFromCollection(options?: {
    mutation?: UseMutationOptions<{
        data: Record<string, unknown>;
    }, ApiError, {
        params: RemoveFromCollectionParams;
    }>;
}) {
    return useMutation({
        mutationFn: (vars)=>removeFromCollection(vars.params),
        ...options?.mutation
    });
}
export const getScentDna = async (options?: RequestInit): Promise<{
    data: ScentDnaOut | null;
}> =>{
    const res = await fetch("/api/dna", {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const getScentDnaKey = ()=>{
    return [
        "/api/dna"
    ] as const;
};
export function useGetScentDna<TData = {
    data: ScentDnaOut | null;
}>(options?: {
    query?: Omit<UseQueryOptions<{
        data: ScentDnaOut | null;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: getScentDnaKey(),
        queryFn: ()=>getScentDna(),
        ...options?.query
    });
}
export function useGetScentDnaSuspense<TData = {
    data: ScentDnaOut | null;
}>(options?: {
    query?: Omit<UseSuspenseQueryOptions<{
        data: ScentDnaOut | null;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: getScentDnaKey(),
        queryFn: ()=>getScentDna(),
        ...options?.query
    });
}
export interface LookupFragrancesParams {
    q: string;
}
export const lookupFragrances = async (params: LookupFragrancesParams, options?: RequestInit): Promise<{
    data: Fragrance[];
}> =>{
    const searchParams = new URLSearchParams();
    if (params.q != null) searchParams.set("q", String(params.q));
    const queryString = searchParams.toString();
    const url = queryString ? `/api/fragrances/lookup?${queryString}` : "/api/fragrances/lookup";
    const res = await fetch(url, {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const lookupFragrancesKey = (params?: LookupFragrancesParams)=>{
    return [
        "/api/fragrances/lookup",
        params
    ] as const;
};
export function useLookupFragrances<TData = {
    data: Fragrance[];
}>(options: {
    params: LookupFragrancesParams;
    query?: Omit<UseQueryOptions<{
        data: Fragrance[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: lookupFragrancesKey(options.params),
        queryFn: ()=>lookupFragrances(options.params),
        ...options?.query
    });
}
export function useLookupFragrancesSuspense<TData = {
    data: Fragrance[];
}>(options: {
    params: LookupFragrancesParams;
    query?: Omit<UseSuspenseQueryOptions<{
        data: Fragrance[];
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: lookupFragrancesKey(options.params),
        queryFn: ()=>lookupFragrances(options.params),
        ...options?.query
    });
}
export const getMe = async (options?: RequestInit): Promise<{
    data: MeOut;
}> =>{
    const res = await fetch("/api/me", {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const getMeKey = ()=>{
    return [
        "/api/me"
    ] as const;
};
export function useGetMe<TData = {
    data: MeOut;
}>(options?: {
    query?: Omit<UseQueryOptions<{
        data: MeOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: getMeKey(),
        queryFn: ()=>getMe(),
        ...options?.query
    });
}
export function useGetMeSuspense<TData = {
    data: MeOut;
}>(options?: {
    query?: Omit<UseSuspenseQueryOptions<{
        data: MeOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: getMeKey(),
        queryFn: ()=>getMe(),
        ...options?.query
    });
}
export const version = async (options?: RequestInit): Promise<{
    data: VersionOut;
}> =>{
    const res = await fetch("/api/version", {
        ...options,
        method: "GET"
    });
    if (!res.ok) {
        const body = await res.text();
        let parsed: unknown;
        try {
            parsed = JSON.parse(body);
        } catch  {
            parsed = body;
        }
        throw new ApiError(res.status, res.statusText, parsed);
    }
    return {
        data: await res.json()
    };
};
export const versionKey = ()=>{
    return [
        "/api/version"
    ] as const;
};
export function useVersion<TData = {
    data: VersionOut;
}>(options?: {
    query?: Omit<UseQueryOptions<{
        data: VersionOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useQuery({
        queryKey: versionKey(),
        queryFn: ()=>version(),
        ...options?.query
    });
}
export function useVersionSuspense<TData = {
    data: VersionOut;
}>(options?: {
    query?: Omit<UseSuspenseQueryOptions<{
        data: VersionOut;
    }, ApiError, TData>, "queryKey" | "queryFn">;
}) {
    return useSuspenseQuery({
        queryKey: versionKey(),
        queryFn: ()=>version(),
        ...options?.query
    });
}
