import { useState } from "react";
import UrlStatsPanel from "./UrlStatsPanel";

function UrlTable({
  urls,
  tableLoading,
  tags,
  expandedId,
  statsByUrl,
  statsLoadingId,
  onToggleExpand,
  onValidate,
  onDelete,
  onToggleUrlTag,
}) {
  const [copiedId, setCopiedId] = useState(null);

  const handleCopy = async (id, text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);

      setTimeout(() => {
        setCopiedId(null);
      }, 1500);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  if (tableLoading) {
    return <p>Loading your URLs...</p>;
  }

  if (urls.length === 0) {
    return <p>No URLs found yet.</p>;
  }

  return (
    <div className="table-wrapper">
      <div className="list-header">
        <div>ID</div>
        <div>Original URL</div>
        <div>Short URL</div>
        <div>Actions</div>
        <div></div>
      </div>

      {urls.map((url) => {
        const isOpen = expandedId === url.id;
        const isValidated = Boolean(url.is_active);
        const stats = statsByUrl[url.id];
        const isStatsLoading = statsLoadingId === url.id;

        return (
          <div key={url.id} className={`url-entry ${isOpen ? "open" : ""}`}>
            <div className="url-entry-header" onClick={() => onToggleExpand(url.id)}>
              <div className="url-entry-col">
                <div className="url-entry-label">ID</div>
                {url.id}
              </div>

              <div className="url-entry-col truncate">
                <div className="url-entry-label">Original URL</div>
                {url.original_url}
                {url.tags && url.tags.length > 0 && (
                  <div className="url-tag-pills">
                    {url.tags.map((tag) => (
                      <span key={tag.id} className="url-tag-pill">
                        {tag.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="url-entry-col">
                <div className="url-entry-label">Short URL</div>
                <a
                  href={url.short_url}
                  target="_blank"
                  rel="noreferrer"
                  className="short-link"
                  onClick={(e) => e.stopPropagation()}
                >
                  {url.short_url}
                </a>
              </div>

              <div
                className="url-entry-col"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="action-buttons">
                  <button
                    onClick={() => handleCopy(url.id, url.short_url)}
                    className={`copy-button ${
                      copiedId === url.id ? "copied" : ""
                    }`}
                    type="button"
                  >
                    <span className="copy-icon">
                      {copiedId === url.id ? "✓" : "⧉"}
                    </span>
                    <span>
                      {copiedId === url.id ? "Copied!" : "Copy"}
                    </span>
                  </button>

                  <button
                    onClick={() => onValidate(url.id, isValidated)}
                    className={`validate-button ${
                      isValidated ? "validated" : "invalidated"
                    }`}
                    type="button"
                  >
                    {isValidated ? "Deactivate" : "Activate"}
                  </button>

                  <button
                    onClick={() => onDelete(url.id)}
                    className="delete-button"
                    type="button"
                  >
                    Delete
                  </button>
                </div>
              </div>

              <div className="chevron">⌄</div>
            </div>

            <div className="url-entry-details">
              <div className="url-entry-details-inner">
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-label">Total Clicks</div>
                    <div className="stat-value">
                      {stats ? stats.total_clicks : url.clicks}
                    </div>
                  </div>

                  <div className="stat-card">
                    <div className="stat-label">Status</div>
                    <div className="stat-value">
                      {url.is_active ? "Active" : "Inactive"}
                    </div>
                  </div>

                  <div className="stat-card">
                    <div className="stat-label">Click Limit</div>
                    <div className="stat-value">
                      {url.click_limit ?? "None"}
                    </div>
                  </div>

                  <div className="stat-card">
                    <div className="stat-label">Expires At</div>
                    <div className="stat-value">
                      {url.expires_at
                        ? new Date(url.expires_at).toLocaleString()
                        : "Never"}
                    </div>
                  </div>
                </div>

                <div className="tags-assign-section">
                  <h4>Tags</h4>
                  {tags.length === 0 ? (
                    <p className="details-note">
                      No tags created yet. Use "Manage Tags" above to create some.
                    </p>
                  ) : (
                    <div
                      className="tag-checkbox-list"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {tags.map((tag) => {
                        const isChecked = (url.tags || []).some(
                          (t) => t.id === tag.id
                        );
                        return (
                          <label key={tag.id} className="tag-checkbox-row">
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => onToggleUrlTag(url, tag.id)}
                            />
                            <span>{tag.name}</span>
                          </label>
                        );
                      })}
                    </div>
                  )}
                </div>

                <UrlStatsPanel stats={stats} isLoading={isStatsLoading} />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default UrlTable;
