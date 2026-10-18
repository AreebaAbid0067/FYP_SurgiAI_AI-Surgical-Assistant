import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest): Promise<Response> {
  let formData: FormData;

  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json(
      { message: "The upload request must use multipart form data." },
      { status: 400 }
    );
  }

  const requiredFields = [
    "prescription",
    "scan",
    "lab_report",
    "operation",
    "patient_history",
  ];
  for (const field of requiredFields) {
    if (!formData.has(field)) {
      return NextResponse.json(
        { message: `Missing required upload field: ${field}.` },
        { status: 400 }
      );
    }
  }

  try {
    const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    const backendResponse = await fetch(`${backendUrl}/pre-surgery/upload`, {
      method: "POST",
      body: formData,
    });
    const responseBody = await backendResponse.text();

    return new Response(responseBody, {
      status: backendResponse.status,
      headers: {
        "Content-Type":
          backendResponse.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (error) {
    console.error("Pre-surgery backend request failed:", error);
    return NextResponse.json(
      { message: "Could not reach the backend. Check that it is running and try again." },
      { status: 502 }
    );
  }
}
