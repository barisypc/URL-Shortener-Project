import { useState } from "react";
import { getAuthHeaders } from "../../services/auth";

function UrlCreateForm({ onCreated, onBanDetected, tagManager }) {
  const [originalUrl, setOriginalUrl] = useState("");
  const [shortUrl, setShortUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [showAdvanced, setShowAdvanced] = useState(false);

  const [useExpiration, setUseExpiration] = useState(false);
  const [expirationMinutes, setExpirationMinutes] = useState("");

  const [useCustomCode, setUseCustomCode] = useState(false);
  const [customCode, setCustomCode] = useState("");

  const [useQrCode, setUseQrCode] = useState(false);
  const [showQrCode, setShowQrCode] = useState(false);

  const [useCountLimit, setUseCountLimit] = useState(false);
  const [countLimit, setCountLimit] = useState("");

  const [usePassword, setUsePassword] = useState(false);
  const [password, setPassword] = useState("");

  const [lastCreatedHasQr, setLastCreatedHasQr] = useState(false);
  const [lastCreatedQrImage, setLastCreatedQrImage] = useState("");

  const resetAdvancedInputs = () => {
    setUseExpiration(false);
    setExpirationMinutes("");
    setUseCustomCode(false);
    setCustomCode("");
    setUseQrCode(false);
    setUseCountLimit(false);
    setCountLimit("");
    setUsePassword(false);
    setPassword("");
    setShowAdvanced(false);
  };

  const handleShorten = async () => {
    setError("");
    setShortUrl("");
    setShowQrCode(false);
    setLastCreatedHasQr(false);
    setLastCreatedQrImage("");

    if (!originalUrl.trim()) {
      setError("Please enter a URL.");
      return;
    }

    if (useExpiration && !expirationMinutes.trim()) {
      setError("Please enter expiration time in minutes.");
      return;
    }

    if (useCustomCode && !customCode.trim()) {
      setError("Please enter a custom code.");
      return;
    }

    if (useCountLimit && !countLimit.trim()) {
      setError("Please enter a count limit.");
      return;
    }

    if (usePassword && !password.trim()) {
      setError("Please enter a password.");
      return;
    }

    setLoading(true);

    try {
      const qrRequested = useQrCode;

      const payload = {
        original_url: originalUrl,
        expiration_minutes: useExpiration ? parseInt(expirationMinutes, 10) : null,
        custom_code: useCustomCode ? customCode : null,
        qr_code: qrRequested,
        count_limit: useCountLimit ? parseInt(countLimit, 10) : null,
        password: usePassword ? password : null,
      };

      const response = await fetch("http://localhost:8000/shorten", {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (response.status === 403) {
        onBanDetected(data.detail);
        return;
      }

      if (!response.ok) {
        throw new Error(data.detail || "Failed to shorten URL");
      }

      setShortUrl(data.short_url || "");
      setLastCreatedHasQr(qrRequested);
      setShowQrCode(qrRequested);
      setLastCreatedQrImage(data.qr_code_image || "");

      setOriginalUrl("");
      resetAdvancedInputs();

      await onCreated();
    } catch (err) {
      console.error(err);
      setError(err.message || "Something went wrong. Check backend or CORS settings.");
    } finally {
      setLoading(false);
    }
  };

  const handleShowQr = () => setShowQrCode((prev) => !prev);

  return (
    <>
      <input
        type="text"
        placeholder="Enter your URL here..."
        value={originalUrl}
        onChange={(e) => setOriginalUrl(e.target.value)}
        className="input"
      />

      <button
        type="button"
        className="advanced-toggle-button"
        onClick={() => setShowAdvanced((prev) => !prev)}
      >
        {showAdvanced ? "Hide Advanced Features" : "Advanced Features"}
      </button>

      {showAdvanced && (
        <div className="advanced-box">
          <label className="feature-row">
            <input
              type="checkbox"
              checked={useExpiration}
              onChange={(e) => setUseExpiration(e.target.checked)}
            />
            <span>Custom expiration time</span>
          </label>
          {useExpiration && (
            <input
              type="number"
              min="1"
              placeholder="Expiration time (minutes)"
              value={expirationMinutes}
              onChange={(e) => setExpirationMinutes(e.target.value)}
              className="input small-input"
            />
          )}

          <label className="feature-row">
            <input
              type="checkbox"
              checked={useCustomCode}
              onChange={(e) => setUseCustomCode(e.target.checked)}
            />
            <span>Custom code</span>
          </label>
          {useCustomCode && (
            <input
              type="text"
              placeholder="Enter custom code"
              value={customCode}
              onChange={(e) => setCustomCode(e.target.value)}
              className="input small-input"
            />
          )}

          <label className="feature-row">
            <input
              type="checkbox"
              checked={useQrCode}
              onChange={(e) => setUseQrCode(e.target.checked)}
            />
            <span>QR code option</span>
          </label>

          <label className="feature-row">
            <input
              type="checkbox"
              checked={useCountLimit}
              onChange={(e) => setUseCountLimit(e.target.checked)}
            />
            <span>Count limit</span>
          </label>
          {useCountLimit && (
            <input
              type="number"
              min="1"
              placeholder="Enter click threshold"
              value={countLimit}
              onChange={(e) => setCountLimit(e.target.value)}
              className="input small-input"
            />
          )}

          <label className="feature-row">
            <input
              type="checkbox"
              checked={usePassword}
              onChange={(e) => setUsePassword(e.target.checked)}
            />
            <span>Password protect shortened URL</span>
          </label>
          {usePassword && (
            <input
              type="password"
              placeholder="Enter password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input small-input"
            />
          )}

          <div className="tag-manager-divider" />
          <h4 className="tag-manager-heading">Manage Tags</h4>
          {tagManager}
        </div>
      )}

      <button onClick={handleShorten} className="button" disabled={loading}>
        {loading ? "Shortening..." : "Shorten URL"}
      </button>

      {shortUrl && (
        <div className="result-box">
          <p className="result-label">Short URL:</p>

          <div className="result-link-row">
            <a href={shortUrl} target="_blank" rel="noreferrer" className="link">
              {shortUrl}
            </a>
          </div>

          {lastCreatedHasQr && (
            <button type="button" className="qr-toggle-button" onClick={handleShowQr}>
              {showQrCode ? "Hide QR Code" : "Show QR Code"}
            </button>
          )}

          {lastCreatedHasQr && showQrCode && (
            <div className="qr-placeholder">
              {lastCreatedQrImage ? (
                <img src={lastCreatedQrImage} alt="QR Code" className="qr-image" />
              ) : (
                <span>QR Code Preview Area</span>
              )}
            </div>
          )}
        </div>
      )}

      {error && <p className="error">{error}</p>}
    </>
  );
}

export default UrlCreateForm;
