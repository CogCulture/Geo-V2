export async function throwIfResNotOk(res: Response) {
    if (!res.ok) {
        const text = (await res.text()) || res.statusText;
        throw new Error(`${res.status}: ${text}`);
    }
}

export async function apiRequest(
    method: string,
    url: string,
    data?: unknown | undefined,
): Promise<Response> {
    const token = localStorage.getItem("token");
    const headers: Record<string, string> = {};

    if (data) {
        headers["Content-Type"] = "application/json";
    }

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    // Prepend API URL if it's a relative path starting with /api to avoid 404s
    let fullUrl = url;
    if (url.startsWith("/api") || url.startsWith("/")) {
        // Standardise to include /api in the base default
        const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
        const base = apiBase.endsWith("/") ? apiBase.slice(0, -1) : apiBase;
        
        // If url starts with /api, we strip it because it's already in the base
        let path = url;
        if (url.startsWith("/api")) {
            path = url.substring(4); // Remove "/api"
        }
        if (!path.startsWith("/")) {
            path = "/" + path;
        }
        fullUrl = `${base}${path}`;
    }

    // Handle case where url is already absolute (starts with http) - logic above handles relative only if we restricted validation, 
    // but "startsWith /" captures relative. If it starts with http, it won't be modified unless we check specifically.
    if (url.startsWith("http")) {
        fullUrl = url;
    }

    const res = await fetch(fullUrl, {
        method,
        headers,
        body: data ? JSON.stringify(data) : undefined,
        // credentials: "include", // CAUTION: credentials: include with CORS requires specific origin, not *. 
        // Backend is configured for localhost:3000 so this should be fine. 
    });

    await throwIfResNotOk(res);
    return res;
}
