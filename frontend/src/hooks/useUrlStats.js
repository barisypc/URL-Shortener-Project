import { useState } from "react";
import { getAuthHeaders } from "../services/auth";

export function useUrlStats({ onBanDetected, onError }) {
  const [expandedId, setExpandedId] = useState(null);
  const [statsByUrl, setStatsByUrl] = useState({});
  const [statsLoadingId, setStatsLoadingId] = useState(null);

  const fetchStatsForUrl = async (id) => {
    try {
      setStatsLoadingId(id);

      const response = await fetch(`http://localhost:8000/api/show-statistics/${id}`, {
        method: "GET",
        headers: getAuthHeaders(),
      });

      const data = await response.json();

      if (response.status === 403) {
        onBanDetected(data.detail);
        return;
      }

      if (!response.ok) {
        throw new Error(data.detail || "Failed to show statistics.");
      }

      setStatsByUrl((prev) => ({
        ...prev,
        [id]: data,
      }));
    } catch (err) {
      console.error(err);
      onError(err.message || "Failed to show the statistics.");
    } finally {
      setStatsLoadingId(null);
    }
  };

  const toggleExpand = async (id) => {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }

    setExpandedId(id);
    await fetchStatsForUrl(id);
  };

  // Called after a URL is deleted so its cached stats don't linger and its
  // row (if open) collapses instead of showing stats for a deleted URL.
  const clearStatsFor = (id) => {
    setStatsByUrl((prev) => {
      const updated = { ...prev };
      delete updated[id];
      return updated;
    });

    setExpandedId((current) => (current === id ? null : current));
  };

  return { expandedId, statsByUrl, statsLoadingId, toggleExpand, clearStatsFor };
}
