
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

function UploadLogs() {
  const [name, setName] = useState("");
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const MAX_FILE_SIZE = 1024 * 1024;

  function handleFileChange(event) {
    setError("");
    setMessage("");

    const selectedFiles = Array.from(event.target.files || []);

    if (selectedFiles.length === 0) {
      setFiles([]);
      return;
    }

    if (selectedFiles.length > 10) {
      setError("You can upload a maximum of 10 files.");
      event.target.value = "";
      setFiles([]);
      return;
    }

    for (const file of selectedFiles) {
      if (!file.name.toLowerCase().endsWith(".json")) {
        setError(`${file.name}: Only JSON files are allowed.`);
        event.target.value = "";
        setFiles([]);
        return;
      }

      if (file.size > MAX_FILE_SIZE) {
        setError(`${file.name}: File size must not exceed 1 MB.`);
        event.target.value = "";
        setFiles([]);
        return;
      }
    }

    setFiles(selectedFiles);
  }

  function removeFile(index) {
    setFiles((current) => current.filter((_, itemIndex) => itemIndex !== index));
  }

  async function handleUpload(event) {
    event.preventDefault();

    if (!name.trim()) {
      setError("Please provide an investigation name before uploading logs.");
      return;
    }

    if (files.length === 0) {
      setError("Please select at least one JSON file.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setMessage("");

      const investigationResponse = await api.post("/investigations/", {
        name: name.trim(),
        description: "Uploaded from the IncidentReplay UI.",
      });

      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));

      await api.post(
        `/investigations/${investigationResponse.data.id}/upload/`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      );

      setMessage("JSON logs uploaded and parsed successfully.");
      navigate(`/investigation/${investigationResponse.data.id}`);
    } catch (uploadError) {
      const details =
        uploadError.response?.data?.detail ||
        "There was an issue uploading the logs.";

      setError(details);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="upload-page">
      <div className="page-topbar">
        <button
          type="button"
          className="secondary-button small-button"
          onClick={() => navigate("/")}
        >
          Back to Dashboard
        </button>
      </div>

      <h1>Upload Logs</h1>
      <p className="page-summary">
        Upload JSON application logs to start an incident investigation.
      </p>

      <form className="upload-form" onSubmit={handleUpload}>
        <label htmlFor="investigation-name">Investigation Name</label>

        <input
          id="investigation-name"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Example: Checkout API outage"
        />

        <div className="upload-box">
          <label htmlFor="log-files">Select JSON log files</label>

          <input
            id="log-files"
            type="file"
            accept=".json,application/json"
            multiple
            onChange={handleFileChange}
          />

          <small>
            Supported format: JSON only. Maximum size per file: 1 MB.
            Maximum 10 files per upload.
          </small>
        </div>

        {files.length > 0 && (
          <section className="selected-files">
            <h3>Selected Files</h3>

            <ul>
              {files.map((file, index) => (
                <li key={`${file.name}-${index}`}>
                  <span>
                    {file.name} ({(file.size / 1024).toFixed(2)} KB)
                  </span>

                  <button
                    type="button"
                    className="remove-button"
                    onClick={() => removeFile(index)}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {message && <p className="success-box">{message}</p>}
        {error && <p className="error-box">{error}</p>}

        <div className="form-actions">
          <button type="submit" disabled={loading}>
            {loading ? "Uploading..." : "Upload Logs"}
          </button>
        </div>
      </form>
    </main>
  );
}

export default UploadLogs;
