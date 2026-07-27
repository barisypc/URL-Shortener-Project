import { useState } from "react";

function TagManager({ tags, loading, onCreate, onDelete }) {
  const [newTagName, setNewTagName] = useState("");

  const handleCreate = async () => {
    const success = await onCreate(newTagName);
    if (success) {
      setNewTagName("");
    }
  };

  return (
    <>
      <div className="tag-create-row">
        <input
          type="text"
          placeholder="New tag name"
          value={newTagName}
          onChange={(e) => setNewTagName(e.target.value)}
          className="input small-input"
        />
        <button
          type="button"
          className="button tag-create-button"
          onClick={handleCreate}
          disabled={loading}
        >
          Add Tag
        </button>
      </div>

      {tags.length === 0 ? (
        <p className="details-note">No tags yet. Create one above.</p>
      ) : (
        <div className="tag-chip-list">
          {tags.map((tag) => (
            <span key={tag.id} className="tag-chip">
              {tag.name}
              <button
                type="button"
                className="tag-chip-remove"
                onClick={() => onDelete(tag.id)}
                aria-label={`Delete tag ${tag.name}`}
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      )}
    </>
  );
}

export default TagManager;
