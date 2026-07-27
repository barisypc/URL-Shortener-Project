import { useState } from "react";
import {
  listTags,
  createTag as createTagRequest,
  deleteTag as deleteTagRequest,
} from "../services/Tags";

export function useTags({ onError, onTagDeleted }) {
  const [tags, setTags] = useState([]);
  const [tagActionLoading, setTagActionLoading] = useState(false);

  const fetchTags = async () => {
    try {
      const data = await listTags();
      setTags(data);
    } catch (err) {
      console.error(err);
    }
  };

  const createTag = async (name) => {
    if (!name.trim()) {
      onError("Please enter a tag name.");
      return false;
    }

    try {
      setTagActionLoading(true);
      const tag = await createTagRequest(name.trim());
      setTags((prev) => [...prev, tag].sort((a, b) => a.name.localeCompare(b.name)));
      return true;
    } catch (err) {
      onError(err.message || "Failed to create tag.");
      return false;
    } finally {
      setTagActionLoading(false);
    }
  };

  const deleteTag = async (tagId) => {
    if (!window.confirm("Delete this tag? It will be removed from all URLs that use it.")) {
      return;
    }

    try {
      await deleteTagRequest(tagId);
      setTags((prev) => prev.filter((tag) => tag.id !== tagId));
      onTagDeleted?.(tagId);
    } catch (err) {
      onError(err.message || "Failed to delete tag.");
    }
  };

  return { tags, tagActionLoading, fetchTags, createTag, deleteTag };
}
