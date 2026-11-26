import { useEffect, useRef, useState } from "react";
import { createAsset } from "../api.js";

export default function AssetForm({ categories, onCreated }) {
  const [assetId, setAssetId] = useState("");
  const [category, setCategory] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const fileInput = useRef(null);

  // Local preview of the chosen photo; release the object URL when it changes.
  useEffect(() => {
    if (!file) return setPreview(null);
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaved("");
    if (!assetId.trim()) return setError("Enter the asset ID.");
    if (!category) return setError("Choose a category.");
    if (!file) return setError("Add a photo of the asset.");

    const body = new FormData();
    body.append("asset_id", assetId.trim());
    body.append("category", category);
    body.append("photo", file);

    setBusy(true);
    try {
      const created = await createAsset(body);
      setSaved(`Saved ${created.asset_id}`);
      setAssetId("");
      setCategory("");
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel form-panel" aria-labelledby="form-title">
      <h2 id="form-title">Register an asset</h2>
      <form onSubmit={handleSubmit} noValidate>
        <label>
          Asset ID
          <input
            value={assetId}
            onChange={(e) => setAssetId(e.target.value)}
            placeholder="e.g. PLT-00123"
            autoComplete="off"
            maxLength={64}
          />
        </label>

        <label>
          Category
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">Choose a category</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        <label>
          Photo
          <input
            ref={fileInput}
            type="file"
            accept="image/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </label>

        {preview && <img className="preview" src={preview} alt="Selected asset" />}

        {error && <p className="alert error" role="alert">{error}</p>}
        {saved && <p className="alert ok" role="status">{saved}</p>}

        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Saving…" : "Save asset"}
        </button>
      </form>
    </section>
  );
}