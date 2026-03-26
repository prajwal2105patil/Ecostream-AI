import axiosClient from "./axiosClient";

export async function getHeatmapData(city, days = 7, ward = null) {
  const params = { city, days };
  if (ward) params.ward = ward;
  const res = await axiosClient.get("/api/heatmap/data", { params });
  return res.data;
}

export async function getHeatmapSummary(city, days = 7) {
  const res = await axiosClient.get("/api/heatmap/summary", { params: { city, days } });
  return res.data;
}
