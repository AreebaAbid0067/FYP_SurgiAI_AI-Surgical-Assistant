"use server";

import axios from "axios";

export async function duringSurgery(
  surgeon_query: string,
  patient_history: string
) {
  try {
    const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    const response = await axios.post(`${backendUrl}/surgery`, {
      surgeon_query,
      patient_history,
    });

    console.log(response);
    if (response.status === 200) {
      return { status: 200, data: response.data };
    } else {
      return { status: 400, message: "Error" };
    }
  } catch (error) {
    console.log(error);
    return { status: 500, message: "Something went wrong" };
  }
}
