import axiosClient from "./axiosClient";

export async function getTrends(city, days = 30) {
  const res = await axiosClient.get("/api/analytics/trends", { params: { city, days } });
  return res.data;
}

export async function getCategories(days = 30) {
  const res = await axiosClient.get("/api/analytics/categories", { params: { days } });
  return res.data;
}

export async function getHotspots(city) {
  const res = await axiosClient.get("/api/analytics/hotspots", { params: { city } });
  return res.data;
}

export async function generateRoute(city, routeDate, wardNumber = null) {
  const res = await axiosClient.post("/api/routes/generate", {
    city,
    route_date: routeDate,
    ward_number: wardNumber,
  });
  return res.data;
}
