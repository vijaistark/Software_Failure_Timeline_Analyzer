import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  Clock3,
  FileText,
  Upload,
  ArrowRight,
  ArrowUpRight,
} from "lucide-react";
import api from "../services/api";

function Dashboard() {
  const [investigations, setInvestigations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchInvestigations() {
      try {
        setLoading(true);
        const response = await api.get("/investigations/");
        setInvestigations(response.data || []);
      } catch (fetchError) {
        setError(fetchError.response?.data?.detail || "Unable to load investigations.");
      } finally {
        setLoading(false);
      }
    }

    fetchInvestigations();
  }, []);

  const stats = useMemo(() => {
    const totalInvestigations = investigations.length;
    const totalEvents = investigations.reduce((total, item) => total + Number(item.event_count || 0), 0);
    const errorAndCritical = investigations.reduce(
      (total, item) => total + Number(item.error_count || 0) + Number(item.critical_count || 0),
      0,
    );

    return [
      { title: "Total Investigations", value: totalInvestigations, icon: FileText },
      { title: "Total Log Events", value: totalEvents, icon: Activity },
      { title: "Error & Critical", value: errorAndCritical, icon: AlertTriangle },
      { title: "Status", value: investigations.length ? "Ready" : "Waiting", icon: Clock3 },
    ];
  }, [investigations]);

  return (
    <main className="dashboard">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">INCIDENT MANAGEMENT</p>
          <h1>IncidentReplay</h1>
          <p className="subtitle">
            Analyze application failures and investigate log timelines.
          </p>
        </div>

        <Link to="/upload" className="primary-button">
          <Upload size={18} />
          Upload Logs
        </Link>
      </header>

      <section className="stats-grid">
        {stats.map((stat) => {
          const Icon = stat.icon;

          return (
            <article className="stat-card" key={stat.title}>
              <div className="stat-icon">
                <Icon size={21} />
              </div>
              <p>{stat.title}</p>
              <h2>{stat.value}</h2>
            </article>
          );
        })}
      </section>

      <section className="dashboard-panel">
        <div className="panel-header">
          <h2>Recent Investigations</h2>
          <Link to="/upload" className="secondary-button small-button">
            Start Investigation
            <ArrowRight size={16} />
          </Link>
        </div>

        {loading ? (
          <p className="empty-state">Loading investigations...</p>
        ) : error ? (
          <p className="error-box">{error}</p>
        ) : investigations.length === 0 ? (
          <div className="empty-state">
            <p>No investigations yet.</p>
            <Link to="/upload" className="secondary-button">
              Create your first timeline
            </Link>
          </div>
        ) : (
          <div className="recent-list">
            {investigations.map((investigation) => (
              <Link
                key={investigation.id}
                to={`/investigation/${investigation.id}`}
                className="recent-item"
              >
                <div>
                  <h3>{investigation.name}</h3>
                  <p>{investigation.description || "No description provided."}</p>
                  <span>
                    {new Date(investigation.created_at).toLocaleString()} • {investigation.event_count || 0} events
                  </span>
                </div>
                <ArrowUpRight size={18} />
              </Link>
            ))}
          </div>
        )}
      </section>

      <section className="welcome-card">
        <div className="welcome-icon">
          <Activity size={28} />
        </div>
        <h2>Start your first investigation</h2>
        <p>
          Upload logs from your application to build a chronological failure timeline, search request IDs,
          and identify related events.
        </p>
        <Link to="/upload" className="secondary-button">
          Start Investigation
          <ArrowRight size={18} />
        </Link>
      </section>

      <footer className="dashboard-footer">Software Failure Timeline Analyzer</footer>
    </main>
  );
}

export default Dashboard;
