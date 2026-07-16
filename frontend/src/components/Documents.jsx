import { useState } from "react";

export function RequirementBadge({ required }) {
  return (
    <span
      className={`requirement-badge ${required ? "required" : "optional"}`}
    >
      {required ? "Required" : "Optional"}
    </span>
  );
}

export function FileChip({ label, onPreview, onClear, clearDisabled = false }) {
  return (
    <div className="file-chip">
      <span title={label}>{label}</span>
      <span className="file-actions">
        <button type="button" className="preview-file" onClick={onPreview}>
          Preview
        </button>
        <button type="button" onClick={onClear} disabled={clearDisabled}>
          Clear
        </button>
      </span>
    </div>
  );
}

export function DropZone({ multiple = false, onFiles, label, disabled = false }) {
  const [dragging, setDragging] = useState(false);

  function acceptFiles(fileList) {
    if (disabled) return;
    const pdfs = Array.from(fileList || []).filter(
      (item) =>
        item.type === "application/pdf" ||
        item.name.toLowerCase().endsWith(".pdf"),
    );
    if (pdfs.length) onFiles(multiple ? pdfs : [pdfs[0]]);
  }

  return (
    <label
      className={`drop-zone ${dragging ? "dragging" : ""} ${
        disabled ? "is-disabled" : ""
      }`}
      aria-disabled={disabled}
      onDragEnter={(event) => {
        event.preventDefault();
        if (disabled) return;
        setDragging(true);
      }}
      onDragOver={(event) => {
        event.preventDefault();
        if (disabled) return;
        setDragging(true);
      }}
      onDragLeave={(event) => {
        event.preventDefault();
        setDragging(false);
      }}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        if (disabled) return;
        acceptFiles(event.dataTransfer.files);
      }}
    >
      <strong>{label}</strong>
      <span>PDF only</span>
      <input
        type="file"
        accept="application/pdf,.pdf"
        multiple={multiple}
        disabled={disabled}
        onChange={(event) => {
          acceptFiles(event.target.files);
          event.target.value = "";
        }}
      />
    </label>
  );
}

export function PreviewModal({ preview, onClose }) {
  if (!preview) return null;

  return (
    <div
      className="preview-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="preview-dialog"
        role="dialog"
        aria-modal="true"
        aria-label={`Preview ${preview.label}`}
      >
        <div className="preview-heading">
          <div>
            <span className="eyebrow">Attached PDF</span>
            <h2>{preview.label}</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Close preview">
            Close
          </button>
        </div>
        <iframe src={preview.url} title={`Preview ${preview.label}`} />
        <p>
          If the PDF does not render in your browser,{" "}
          <a href={preview.url} target="_blank" rel="noreferrer">
            open it in a new tab
          </a>
          .
        </p>
      </section>
    </div>
  );
}

export function UploadCard({
  title,
  detail,
  defaultLabel,
  defaultKey,
  useDefault,
  setUseDefault,
  file,
  setFile,
  onPreview,
  multiple = false,
  required = false,
  step,
  mutationDisabled = false,
}) {
  const files = multiple ? file : file ? [file] : [];
  const hasDocument = useDefault || files.length > 0;

  function onFiles(selected) {
    if (mutationDisabled) return;
    if (!selected.length) return;
    if (multiple) {
      setFile((current) => [...current, ...selected]);
      return;
    }
    setFile(selected[0]);
    setUseDefault(false);
  }

  return (
    <div className="upload-card">
      <div
        className={`upload-number ${hasDocument ? "has-document" : "no-document"}`}
        aria-hidden="true"
      >
        {hasDocument ? "✓" : step}
      </div>
      <div className="upload-copy">
        <div className="upload-title-row">
          <h3>{title}</h3>
          <RequirementBadge required={required} />
        </div>
        <p>{detail}</p>
        {useDefault && (
          <FileChip
            label={defaultLabel}
            onPreview={() => onPreview(null, defaultKey, defaultLabel)}
            onClear={() => setUseDefault(false)}
            clearDisabled={mutationDisabled}
          />
        )}
        {files.map((selected, index) => (
          <FileChip
            key={`${selected.name}-${index}`}
            label={selected.name}
            onPreview={() => onPreview(selected, null, selected.name)}
            onClear={() =>
              setFile(
                multiple
                  ? files.filter((_, fileIndex) => fileIndex !== index)
                : null,
              )
            }
            clearDisabled={mutationDisabled}
          />
        ))}
        {(!hasDocument || multiple) && (
          <DropZone
            multiple={multiple}
            onFiles={onFiles}
            disabled={mutationDisabled}
            label={
              hasDocument
                ? "Drop more PDFs here or browse"
                : "Drop PDF here or browse"
            }
          />
        )}
      </div>
    </div>
  );
}
