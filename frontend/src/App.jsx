import { useCallback, useEffect, useState } from "react";
import AssetForm from "./components/AssetForm.jsx";
import AssetList from "./components/AssetList.jsx";
import AssetDetail from "./components/AssetDetail.jsx";
import { getCategories } from "./api.js";

// Tiny hash router: "#/asset/ABC-1" opens a record, anything else = dashboard.
// Hash links make the phone's Back button work without a router library.
function useHashRoute() {
  const read = () => window.location.hash.slice(1);
  const [hash, setHash] = useState(read);
  useEffect(() => {
    const onChange = () => setHash(read());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

export default function App() {
  const hash = useHashRoute();
  const [categories, setCategories] = useState([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    getCategories().then(setCategories).catch((e) => setLoadError(e.message));
  }, []);

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);
  const match = hash.match(/^\/asset\/(.+)$/);
  const openId = match ? decodeURIComponent(match[1]) : null;

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="#/">
          Warehouse Asset Register
        </a>
      </header>

      <main className="content">
        {loadError && <p className="alert error">{loadError}</p>}
        {openId ? (
          <AssetDetail assetId={openId} onDeleted={refresh} />
        ) : (
          <div className="dashboard">
            <AssetForm categories={categories} onCreated={refresh} />
            <AssetList categories={categories} refreshKey={refreshKey} />
          </div>
        )}
      </main>
    </div>
  );
}