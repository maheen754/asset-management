import { useEffect, useState } from "react";
import { listAssets, photoSrc } from "../api.js";
import { useDebounce } from "../hooks.js";

const PER_PAGE = 12;

export default function AssetList({ categories, refreshKey }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const q = useDebounce(query.trim());

  // Any new search or filter starts again from page 1.
  useEffect(() => setPage(1), [q, category]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listAssets({ q, category, page, perPage: PER_PAGE })
      .then((res) => !cancelled && (setData(res), setError("")))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true; // ignore stale responses from earlier keystrokes
    };
  }, [q, category, page, refreshKey]);

  const pages = Math.max(1, Math.ceil(data.total / PER_PAGE));

  return (
    <section className="panel list-panel" aria-labelledby="list-title">
      <div className="list-head">
        <h2 id="list-title">
          Assets <span className="count">{data.total}</span>
        </h2>
        <div className="filters">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by Asset ID"
            aria-label="Search by Asset ID"
          />
          <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Filter by category">
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <p className="alert error">{error}</p>}

      {!loading && !error && data.items.length === 0 && (
        <p className="empty">
          {q || category ? "No assets match this search." : "No assets yet. Register the first one using the form."}
        </p>
      )}

      <ul className="grid">
        {data.items.map((a) => (
          <li key={a.id}>
            <a className="card" href={`#/asset/${encodeURIComponent(a.asset_id)}`}>
              {a.photo_url ? (
                <img src={photoSrc(a.photo_url)} alt={`Photo of ${a.asset_id}`} loading="lazy" />
              ) : (
                <div className="no-photo">No photo</div>
              )}
              <div className="card-body">
                <strong>{a.asset_id}</strong>
                <span>{a.category}</span>
              </div>
            </a>
          </li>
        ))}
      </ul>

      {pages > 1 && (
        <nav className="pager" aria-label="Pages">
          <button onClick={() => setPage((p) => p - 1)} disabled={page <= 1}>
            Previous
          </button>
          <span>
            Page {page} of {pages}
          </span>
          <button onClick={() => setPage((p) => p + 1)} disabled={page >= pages}>
            Next
          </button>
        </nav>
      )}
    </section>
  );
}
