import { useState } from "react";
import { getAuthHeaders } from "../services/auth";
import { updateUrlTags } from "../services/Tags";

export function useUrls({ onBanDetected, onError }) {
  const [urls, setUrls] = useState([]);
  const [tableLoading, setTableLoading] = useState(true);

  const fetchUrls = async () => {
    try {
      setTableLoading(true);

      const response = await fetch("http://localhost:8000/api/my-urls", {
        method: "GET",
        headers: getAuthHeaders(),
      });

      if (response.status === 403) {
        const data = await response.json().catch(() => ({}));
        onBanDetected(data.detail);
        return;
      }

      if (!response.ok) {
        throw new Error("Failed to fetch URLs");
      }

      const data = await response.json();
      setUrls(data);
    } catch (err) {
      console.error(err);
      onError("Failed to load your URLs.");
    } finally {
      setTableLoading(false);
    }
  };

  const deleteUrl = async (id) => {
    try {
      const response = await fetch(`http://localhost:8000/api/delete-url/${id}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });

      const data = await response.json();

      if (response.status === 403) {
        onBanDetected(data.detail);
        return false;
      }

      if (!response.ok) {
        throw new Error(data.detail || "Failed to delete URL");
      }

      setUrls((prev) => prev.filter((url) => url.id !== id));
      return true;
    } catch (err) {
      console.error(err);
      onError(err.message || "Something went wrong. Check backend or CORS settings.");
      return false;
    }
  };

  const validateUrl = async (id, currentStatus) => {
    try {
      const response = await fetch(`http://localhost:8000/api/validate-url/${id}`, {
        method: "PATCH",
        headers: getAuthHeaders(),
        body: JSON.stringify({ is_active: !currentStatus }),
      });

      const data = await response.json();

      if (response.status === 403) {
        onBanDetected(data.detail);
        return;
      }

      if (!response.ok) {
        throw new Error(data.detail || "Failed to update validation status");
      }

      setUrls((prevUrls) =>
        prevUrls.map((url) =>
          url.id === id ? { ...url, is_active: !currentStatus } : url
        )
      );
    } catch (err) {
      console.error(err);
      onError(err.message || "Failed to update validation status.");
    }
  };

  const toggleUrlTag = async (url, tagId) => {
    const currentTagIds = (url.tags || []).map((tag) => tag.id);
    const nextTagIds = currentTagIds.includes(tagId)
      ? currentTagIds.filter((id) => id !== tagId)
      : [...currentTagIds, tagId];

    try {
      const updated = await updateUrlTags(url.id, nextTagIds);
      setUrls((prev) =>
        prev.map((u) => (u.id === url.id ? { ...u, tags: updated.tags } : u))
      );
    } catch (err) {
      onError(err.message || "Failed to update tags.");
    }
  };

  // Called when a tag is deleted elsewhere (useTags) so the tag pills shown
  // on each row don't keep referencing a tag that no longer exists.
  const removeTagFromAllUrls = (tagId) => {
    setUrls((prev) =>
      prev.map((url) => ({
        ...url,
        tags: (url.tags || []).filter((tag) => tag.id !== tagId),
      }))
    );
  };

  return {
    urls,
    tableLoading,
    fetchUrls,
    deleteUrl,
    validateUrl,
    toggleUrlTag,
    removeTagFromAllUrls,
  };
}
