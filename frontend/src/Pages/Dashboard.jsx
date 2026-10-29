
import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  Clock,
  FileText,
  Upload,
  ArrowRight,
} from "lucide-react";

function Dashboard() {
  const stats = [
    {
      title: "Total Investigations",
      value: "0",
      icon: FileText,
    },
    {
      title: "Active Incidents",
      value: "0",
      icon: AlertTriangle,
    },
    {
      title: "Logs Analyzed",
      value: "0",
      icon: Activity,
    },
    {
      title: "Avg. Resolution Time",
      value: "--",
      icon: Clock,
    },
  ];

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

      <section className="welcome-card">
        <div className="welcome-icon">
          <Activity size={28} />
        </div>

        <h2>Start your first investigation</h2>

        <p>
          Upload logs from your application to build a chronological
          failure timeline, search request IDs, and identify related events.
        </p>

        <Link to="/upload" className="secondary-button">
          Start Investigation
          <ArrowRight size={18} />
        </Link>
      </section>

      <footer className="dashboard-footer">
        Software Failure Timeline Analyzer
      </footer>
    </main>
  );
}

export default Dashboard;
