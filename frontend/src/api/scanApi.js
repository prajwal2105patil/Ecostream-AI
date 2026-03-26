import axiosClient from "./axiosClient";

export async function uploadScan(file, latitude, longitude) {
  const form = new FormData();
  form.append("file", file);
  if (latitude != null) form.append("latitude", latitude);
  if (longitude != null) form.append("longitude", longitude);
  const res = await axiosClient.post("/api/scans/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function getScan(scanId) {
  const res = await axiosClient.get(`/api/scans/${scanId}`);
  return res.data;
}

export async function listScans(skip = 0, limit = 20) {
  const res = await axiosClient.get("/api/scans/", { params: { skip, limit } });
  return res.data;
}

export function scanImageUrl(scanId) {
  return `/api/scans/${scanId}/image`;
}
