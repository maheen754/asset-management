import { useEffect, useState } from "react";
import { deleteAsset, getAsset, photoSrc } from "../api.js";

const fmt = (iso) => new Date(iso).toLocaleString();

export default function AssetDetail({ assetId, onDeleted }) {
  const [asset, setAsset] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setAsset(null);
    setError("");
    getAsset(assetId).then(setAsset).catch((e) => setError(e.message));
  }, [assetId]);

  async function handleDelete() {
    if (!window.confirm(`Delete asset ${asset.asset_id}? This cannot be undone.`)) return;
    try {
      await deleteAsset(asset.asset_id);
      onDeleted();
      window.location.hash = "#/";
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <section className="panel detail">
      <a className="back" href="#/">
        Back to all assets
      </a>

      {error && <p className="alert error">{error}</p>}
      {!asset && !error && <p className="empty">Loading…</p>}

      {asset && (
        <div className="detail-body">
          {asset.photo_url ? (
            <a href={photoSrc(asset.photo_url)} target="_blank" rel="noreferrer" title="Open full size">
              <img className="detail-photo" src={photoSrc(asset.photo_url)} alt={`Photo of ${asset.asset_id}`} />
            </a>
          ) : (
            <div className="no-photo big">No photo</div>
          )}

          <div className="detail-info">
            <h2>{asset.asset_id}</h2>
            <dl>
              <dt>Category</dt>
              <dd>{asset.category}</dd>
              <dt>Entered by</dt>
              <dd>{asset.source === "automated" ? "Automated system" : "Operator"}</dd>
              <dt>Registered</dt>
              <dd>{fmt(asset.created_at)}</dd>
              <dt>Last updated</dt>
              <dd>{fmt(asset.updated_at)}</dd>
            </dl>
            <button className="danger" onClick={handleDelete}>
              Delete asset
            </button>
          </div>
        </div>
      )}
    </section>
  );
}