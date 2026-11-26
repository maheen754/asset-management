// All communication with the Flask backend lives here.
// Same-origin by default (Flask serves the build, Vite proxies in dev).
// Set VITE_API_URL only if the API runs on a different host.
const BASE = import.meta.env.VITE_API_URL || "";

async function request(path, options) {
  let res;
  try {
    res = await fetch(BASE + path, options);
  } catch {
    throw new Error("Cannot reach the server. Check the network connection.");
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON response */
  }
  if (!res.ok) throw new Error(data?.error || `Request failed (${res.status})`);
  return data;
}

export const getCategories = () => request("/api/categories");

export const listAssets = ({ q = "", category = "", page = 1, perPage = 12 }) => {
  const params = new URLSearchParams({ page, per_page: perPage });
  if (q) params.set("q", q);
  if (category) params.set("category", category);
  return request(`/api/assets?${params}`);
};

export const getAsset = (assetId) => request(`/api/assets/${encodeURIComponent(assetId)}`);

export const createAsset = (formData) => request("/api/assets", { method: "POST", body: formData });

export const deleteAsset = (assetId) =>
  request(`/api/assets/${encodeURIComponent(assetId)}`, { method: "DELETE" });

export const photoSrc = (url) => (url ? BASE + url : null);