import { useRef, useState } from "react";
import { getToken } from "../../services/auth";

// Extensions the bulk upload picker will accept. Kept in one place so the
// validation check and the <input accept=""> list can't drift apart.
const ALLOWED_BULK_EXTENSIONS = [".csv", ".xlsx", ".xls"];

function BulkUploadPanel({ onSuccess, onBanDetected }) {
  const [bulkUploading, setBulkUploading] = useState(false);
  const [bulkResults, setBulkResults] = useState(null);
  const [bulkError, setBulkError] = useState("");
  const bulkFileInputRef = useRef(null);

  // The visible button only opens the OS file picker; the real <input type="file">
  // stays hidden so it can be styled like the rest of the dashboard buttons.
  const handleBulkUploadClick = () => {
    setBulkError("");
    setBulkResults(null);
    bulkFileInputRef.current?.click();
  };

  const handleBulkFileChange = async (e) => {
    const file = e.target.files?.[0];

    // Reset the input value so picking the same file twice still fires onChange.
    e.target.value = "";

    if (!file) return;

    const lowerName = file.name.toLowerCase();
    const isAllowed = ALLOWED_BULK_EXTENSIONS.some((ext) => lowerName.endsWith(ext));

    if (!isAllowed) {
      setBulkError("Select a .csv, .xlsx, or .xls file.");
      return;
    }

    setBulkError("");
    setBulkResults(null);
    setBulkUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const token = getToken();

      const response = await fetch("http://localhost:8000/api/bulk-upload", {
        method: "POST",
        // No Content-Type header here on purpose — the browser has to set the
        // multipart boundary itself, and getAuthHeaders() would force JSON.
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      const data = await response.json();

      if (response.status === 403) {
        onBanDetected(data.detail);
        return;
      }

      if (!response.ok) {
        throw new Error(data.detail || "Bulk upload failed");
      }

      setBulkResults(data);
      await onSuccess();
    } catch (err) {
      console.error(err);
      setBulkError(
        err.message || "Bulk upload failed. Check the file format and try again."
      );
    } finally {
      setBulkUploading(false);
    }
  };

  const bulkSuccessCount = bulkResults
    ? bulkResults.filter((item) => item.status === "success").length
    : 0;
  const bulkFailedCount = bulkResults
    ? bulkResults.filter((item) => item.status !== "success").length
    : 0;

  return (
    <>
      <input
        type="file"
        ref={bulkFileInputRef}
        onChange={handleBulkFileChange}
        accept=".csv,.xlsx,.xls,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        className="bulk-file-input"
      />

      <button
        type="button"
        className="button bulk-upload-button"
        onClick={handleBulkUploadClick}
        disabled={bulkUploading}
      >
        {bulkUploading ? "Uploading..." : "Bulk Upload (CSV / Excel)"}
      </button>

      <p className="bulk-upload-hint">
        Accepts .csv, .xlsx, and .xls with a <code>URL</code> column.
      </p>

      {bulkError && <p className="error">{bulkError}</p>}

      {bulkResults && (
        <div className="bulk-results-box">
          <p className="result-label">
            {bulkSuccessCount} shortened, {bulkFailedCount} failed
          </p>

          {bulkResults.length === 0 ? (
            <p className="details-note">The file had no rows to process.</p>
          ) : (
            <div className="bulk-results-list">
              {bulkResults.map((item, index) => (
                <div
                  key={`${item.original_url}-${index}`}
                  className={`bulk-result-row ${item.status}`}
                >
                  <span className="bulk-result-url" title={item.original_url}>
                    {item.original_url || "(empty row)"}
                  </span>

                  {item.status === "success" ? (
                    <a
                      href={item.short_url}
                      target="_blank"
                      rel="noreferrer"
                      className="short-link"
                    >
                      {item.short_url}
                    </a>
                  ) : (
                    <span className="bulk-result-error" title={item.error}>
                      {item.error}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
}

export default BulkUploadPanel;
