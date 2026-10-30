import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";

const initialFilters = {
  severity: "ALL",
  service: "",
  request_id: "",
  search: "",
  start: "",
  end: "",
};

function Investigation() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [investigation, setInvestigation] = useState(null);
  const [events, setEvents] = useState([]);
  const [correlations, setCorrelations] = useState([]);
  const [filters, setFilters] = useState(initialFilters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [pageInfo, setPageInfo] = useState({ count: 0, page_size: 20, page: 1 });

  useEffect(() => {
    async function loadInvestigation() {
      try {
        const response = await api.get(`/investigations/${id}/`);
        setInvestigation(response.data);
      } catch (loadError) {
        setError(loadError.response?.data?.detail || "Unable to load this investigation.");
      }
    }

    if (id) {
      loadInvestigation();
    }
  }, [id]);

  useEffect(() => {
    async function loadEvents() {
      if (!id) {
        return;
      }

      try {
        setLoading(true);
        setError("");

        const params = new URLSearchParams();
        if (filters.severity !== "ALL") params.set("severity", filters.severity);
        if (filters.service) params.set("service", filters.service);
        if (filters.request_id) params.set("request_id", filters.request_id);
        if (filters.search) params.set("search", filters.search);
        if (filters.start) params.set("start", filters.start);
        if (filters.end) params.set("end", filters.end);
        params.set("page", String(page));
        params.set("page_size", "20");

        const response = await api.get(`/investigations/${id}/events/`, { params });
        setEvents(response.data.results || []);
        setPageInfo({
          count: response.data.count || 0,
          page_size: response.data.page_size || 20,
          page: response.data.page || 1,
        });
      } catch (loadError) {
        setError(loadError.response?.data?.detail || "Unable to fetch events for this investigation.");
      } finally {
        setLoading(false);
      }
    }

    loadEvents();
  }, [id, page, filters]);

  useEffect(() => {
    async function loadCorrelations() {
      if (!id) {
        return;
      }

      try {
        const response = await api.get(`/investigations/${id}/correlations/`);
        setCorrelations(response.data.results || []);
      } catch (correlationError) {
        setCorrelations([]);
      }
    }

    loadCorrelations();
  }, [id]);

  const serviceOptions = useMemo(
    () => [...new Set(events.map((event) => event.service_name).filter(Boolean))].sort(),
    [events],
  );

  function handleFilterChange(event) {
    const { name, value } = event.target;
    setFilters((current) => ({ ...current, [name]: value }));
    setPage(1);
  }

  function handleResetFilters() {
    setFilters(initialFilters);
    setPage(1);
  }

  function buildExportUrl(format) {
    return `${import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api"}/investigations/${id}/export/?format=${format}`;
  }

  if (!investigation && !error) {
    return <main className="investigation-page"><p className="empty-state">Loading investigation...</p></main>;
  }

  return (
    <main className="investigation-page">
      <div className="page-topbar">
        <button type="button" className="secondary-button small-button" onClick={() => navigate("/")}>
          Back to Dashboard
        </button>
        <div className="export-actions">
          <button type="button" className="secondary-button small-button" onClick={() => window.open(buildExportUrl("csv"), "_blank")}>
            Export CSV
          </button>
          <button type="button" className="secondary-button small-button" onClick={() => window.open(buildExportUrl("json"), "_blank")}>
            Export JSON
          </button>
        </div>
      </div>

      {error ? (
        <p className="error-box">{error}</p>
      ) : (
        <>
          <header className="investigation-header">
            <div>
              <p className="eyebrow">INVESTIGATION</p>
              <h1>{investigation?.name || "Incident Investigation"}</h1>
            </div>
            <span className="status-badge">{investigation?.status || "draft"}</span>
          </header>

          <section className="summary-row">
            <article className="summary-card">
              <label>Total Events</label>
              <strong>{investigation?.event_count || 0}</strong>
            </article>
            <article className="summary-card">
              <label>Errors</label>
              <strong>{investigation?.error_count || 0}</strong>
            </article>
            <article className="summary-card">
              <label>Critical</label>
              <strong>{investigation?.critical_count || 0}</strong>
            </article>
          </section>

          <section className="filter-panel">
            <div className="panel-header">
              <h2>Event Filters</h2>
              <button type="button" className="link-button" onClick={handleResetFilters}>
                Reset filters
              </button>
            </div>

            <div className="filter-grid">
              <label>
                Severity
                <select name="severity" value={filters.severity} onChange={handleFilterChange}>
                  <option value="ALL">All severities</option>
                  <option value="DEBUG">DEBUG</option>
                  <option value="INFO">INFO</option>
                  <option value="WARNING">WARNING</option>
                  <option value="ERROR">ERROR</option>
                  <option value="CRITICAL">CRITICAL</option>
                </select>
              </label>

              <label>
                Service
                <select name="service" value={filters.service} onChange={handleFilterChange}>
                  <option value="">All services</option>
                  {serviceOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Request ID
                <input
                  type="text"
                  name="request_id"
                  value={filters.request_id}
                  onChange={handleFilterChange}
                  placeholder="Search request ID"
                />
              </label>

              <label>
                Search text
                <input
                  type="text"
                  name="search"
                  value={filters.search}
                  onChange={handleFilterChange}
                  placeholder="Message or service"
                />
              </label>

              <label>
                Start time
                <input type="datetime-local" name="start" value={filters.start} onChange={handleFilterChange} />
              </label>

              <label>
                End time
                <input type="datetime-local" name="end" value={filters.end} onChange={handleFilterChange} />
              </label>
            </div>
          </section>

          <section className="timeline-panel">
            <div className="panel-header">
              <h2>Failure Timeline</h2>
            </div>

            {loading ? (
              <p className="empty-state">Loading events...</p>
            ) : events.length === 0 ? (
              <p className="empty-state">No log events match the current filters.</p>
            ) : (
              <div className="timeline-list">
                {events.map((event) => (
                  <article key={event.id} className="timeline-item">
                    <div className={`severity-pill ${event.severity.toLowerCase()}`}>
                      {event.severity}
                    </div>
                    <div className="timeline-body">
                      <div className="timeline-head">
                        <span className="timestamp">{new Date(event.timestamp).toLocaleString()}</span>
                        <span className="service">{event.service_name || "Unknown service"}</span>
                      </div>
                      <p className="message">{event.message}</p>
                      <div className="meta-row">
                        <span>Request ID: {event.request_id || "Not available"}</span>
                        <span>Source: {event.source_file || "Uploaded log"}</span>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}

            {pageInfo.count > 20 && (
              <div className="pagination">
                <button type="button" disabled={page === 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>
                  Previous
                </button>
                <span>
                  Page {pageInfo.page} of {Math.max(1, Math.ceil(pageInfo.count / pageInfo.page_size))}
                </span>
                <button
                  type="button"
                  disabled={page >= Math.ceil(pageInfo.count / pageInfo.page_size)}
                  onClick={() => setPage((current) => current + 1)}
                >
                  Next
                </button>
              </div>
            )}
          </section>

          <section className="correlation-panel">
            <h2>Related Events</h2>
            {correlations.length === 0 ? (
              <p className="empty-state">No request ID correlations were found in this investigation.</p>
            ) : (
              <div className="correlation-list">
                {correlations.map((group) => (
                  <div key={group.request_id} className="correlation-item">
                    <h3>Request ID: {group.request_id}</h3>
                    <p>{group.event_count} related events across {group.services.join(", ") || "multiple services"}</p>
                    <ul>
                      {group.events.map((event) => (
                        <li key={event.id}>
                          <strong>{event.severity}</strong> • {new Date(event.timestamp).toLocaleString()} • {event.service_name || "Unknown service"} • {event.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}

export default Investigation;
