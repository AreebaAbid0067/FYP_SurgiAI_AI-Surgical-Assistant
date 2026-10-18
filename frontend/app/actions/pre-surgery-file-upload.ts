export async function uploadPreSurgeryFiles(
  files: Record<string, File | null>,
  surgery: string,
  patientHistory: string
) {
  if (!files.prescription || !files.scan || !files.labReport) {
    return {
      status: "error" as const,
      message: "Upload all three records to continue.",
    };
  }

  const formData = new FormData();
  formData.append("prescription", files.prescription);
  formData.append("scan", files.scan);
  formData.append("lab_report", files.labReport);
  formData.append("operation", surgery);
  formData.append("patient_history", patientHistory);

  try {
    const response = await fetch("/api/pre-surgery/upload", {
      method: "POST",
      body: formData,
    });

    const responseData = await response.json();
    if (!response.ok) {
      return {
        status: "error" as const,
        message:
          typeof responseData.message === "string"
            ? responseData.message
            : `Report generation failed (HTTP ${response.status}).`,
      };
    }

    return { status: "success" as const, data: responseData };
  } catch (error) {
    return {
      status: "error" as const,
      message:
        error instanceof Error
          ? error.message
          : "Could not reach the backend. Check that it is running and try again.",
    };
  }
}
