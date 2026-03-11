import { NextRequest, NextResponse } from "next/server";
import axios from "axios";

const FASTAPI_BASE_URL = process.env.FASTAPI_BASE_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Get token from request headers
    const authHeader = request.headers.get("authorization");

    // Fallback: attempt to read token from cookies (set by client on login)
    let cookieToken: string | null = null;
    try {
      cookieToken = request.cookies.get("token")?.value || null;
    } catch (e) {
      cookieToken = null;
    }

    const headerToUse = authHeader ?? (cookieToken ? `Bearer ${cookieToken}` : undefined);

    // Debug: log presence of auth information (do not log actual token)
    console.log("Auth header present:", !!authHeader, "Cookie token present:", !!cookieToken);

    // Forward the authorization header (if any) to backend
    const response = await axios.post(`${FASTAPI_BASE_URL}/api/analysis/run`, body, {
      headers: {
        "Content-Type": "application/json",
        ...(headerToUse && { "Authorization": headerToUse }),
      },
    });
    return NextResponse.json(response.data);
  } catch (error) {
    console.error("Error starting analysis:", error);
    if (axios.isAxiosError(error)) {
      return NextResponse.json(
        {
          error: error.response?.data?.detail || "Failed to start analysis",
        },
        { status: error.response?.status || 500 }
      );
    } else {
      return NextResponse.json(
        { error: "Internal server error" },
        { status: 500 }
      );
    }
  }
}
