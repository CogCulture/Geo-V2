import { NextRequest, NextResponse } from "next/server";
import axios from "axios";

const FASTAPI_BASE_URL = process.env.FASTAPI_BASE_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const { sessionId } = await params;
    const authHeader = request.headers.get("authorization");
    
    const response = await axios.get(`${FASTAPI_BASE_URL}/api/analysis/status/${sessionId}`, {
      headers: {
        ...(authHeader && { "Authorization": authHeader }),
      },
    });
    return NextResponse.json(response.data);
  } catch (error) {
    console.error("Error fetching status:", error);
    if (axios.isAxiosError(error)) {
      return NextResponse.json(
        {
          error: error.response?.data?.detail || "Failed to fetch analysis status",
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
