import React, { useEffect, useState } from "react";
import "./Dashboard.css";
import { useNavigate } from "react-router-dom";
import { getAuthHeaders, logout, isTokenExpired } from "../services/auth";

import { useUrls } from "../hooks/useUrls";
import { useTags } from "../hooks/useTags";
import { useUrlStats } from "../hooks/useUrlStats";

import UrlCreateForm from "./dashboard/UrlCreateForm";
import BulkUploadPanel from "./dashboard/BulkUploadPanel";
import TagManager from "./dashboard/TagManager";
import UrlTable from "./dashboard/UrlTable";

function Dashboard() {
  const [error, setError] = useState("");
  const [sessionMessage, setSessionMessage] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);

  const navigate = useNavigate();

  // Central handler for "your account was banned mid-session" — any fetch
  // that comes back 403 from a now-inactive account routes through here so
  // the user gets logged out and bounced to /auth with a clear message,
  // instead of being left stuck on the dashboard staring at a generic error.
  const handleBanDetected = (message) => {
    logout();
    navigate("/auth", {
      replace: true,
      state: { message: message || "Your account has been banned." },
    });
  };

  const {
    urls,
    tableLoading,
    fetchUrls,
    deleteUrl,
    validateUrl,
    toggleUrlTag,
    removeTagFromAllUrls,
  } = useUrls({ onBanDetected: handleBanDetected, onError: setError });

  const { tags, tagActionLoading, fetchTags, createTag, deleteTag } = useTags({
    onError: setError,
    onTagDeleted: removeTagFromAllUrls,
  });

  const {
    expandedId,
    statsByUrl,
    statsLoadingId,
    toggleExpand,
    clearStatsFor,
  } = useUrlStats({ onBanDetected: handleBanDetected, onError: setError });

  const fetchCurrentUser = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/me", {
        method: "GET",
        headers: getAuthHeaders(),
      });

      const data = await response.json();

      if (response.status === 403) {
        handleBanDetected(data.detail);
        return;
      }

      if (!response.ok) {
        throw new Error(data.detail || "Failed to fetch current user");
      }

      setIsAdmin(Boolean(data.is_admin));
    } catch (err) {
      console.error(err);
      setError("Failed to load user information.");
    }
  };

  useEffect(() => {
    const handleSessionExpired = () => {
      logout();
      navigate("/auth", {
        replace: true,
        state: { message: "Session expired. Please enter your credentials again." },
      });
    };

    const initializeDashboard = async () => {
      if (isTokenExpired()) {
        handleSessionExpired();
        return;
      }

      await fetchCurrentUser();
      await fetchUrls();
      await fetchTags();
    };

    initializeDashboard();

    const interval = setInterval(() => {
      if (isTokenExpired()) {
        handleSessionExpired();
        return;
      }

      fetchUrls();
    }, 10000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate]);

  const handleGoToAdmin = () => {
    navigate("/admin");
  };

  const handleLogout = () => {
    try {
      logout();
      navigate("/auth");
    } catch (err) {
      console.error("Logout Failed:", err);
      setError("Logout Failed.");
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this URL?")) {
      return;
    }

    const success = await deleteUrl(id);
    if (success) {
      clearStatsFor(id);
    }
  };

  return (
    <div className="dashboard-page">
      {sessionMessage && <div className="session-toast">{sessionMessage}</div>}

      <div className="dashboard-layout">
        <div className="card left-panel">
          <h1 className="title">URL Shortener</h1>
          <p className="subtitle">Paste your long URL and get a shorter one.</p>

          <UrlCreateForm
            onCreated={fetchUrls}
            onBanDetected={handleBanDetected}
            tagManager={
              <TagManager
                tags={tags}
                loading={tagActionLoading}
                onCreate={createTag}
                onDelete={deleteTag}
              />
            }
          />

          <BulkUploadPanel onSuccess={fetchUrls} onBanDetected={handleBanDetected} />

          {error && <p className="error">{error}</p>}

          <div className="logout-row">
            {isAdmin && (
              <button
                onClick={handleGoToAdmin}
                className="logout-small-button"
                type="button"
              >
                Admin Panel
              </button>
            )}

            <button
              onClick={handleLogout}
              className="logout-small-button"
              type="button"
            >
              Logout
            </button>
          </div>
        </div>

        <div className="card right-panel">
          <h2 className="table-title">My URLs</h2>

          <UrlTable
            urls={urls}
            tableLoading={tableLoading}
            tags={tags}
            expandedId={expandedId}
            statsByUrl={statsByUrl}
            statsLoadingId={statsLoadingId}
            onToggleExpand={toggleExpand}
            onValidate={validateUrl}
            onDelete={handleDelete}
            onToggleUrlTag={toggleUrlTag}
          />
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
