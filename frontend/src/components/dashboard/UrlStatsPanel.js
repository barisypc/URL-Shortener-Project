import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts";

const PIE_COLORS = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2"];

const formatPieData = (items = []) =>
  items.map((item) => ({
    name: item.label,
    value: item.count,
  }));

const formatRecentClicksData = (items = []) =>
  items.map((item, index) => ({
    name: item.timestamp
      ? new Date(item.timestamp).toLocaleString([], {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })
      : `Click ${index + 1}`,
    clicks: item.count ?? 1,
  }));

function UrlStatsPanel({ stats, isLoading }) {
  if (isLoading) {
    return <div className="details-note">Loading statistics...</div>;
  }

  if (!stats) {
    return (
      <div className="details-note">
        No statistics available for this URL yet.
      </div>
    );
  }

  const browserPieData = formatPieData(stats.by_browser || []);
  const platformPieData = formatPieData(stats.by_platform || []);
  const recentClicksData = formatRecentClicksData(stats.recent_clicks || []);

  return (
    <div className="statistics-section">
      <h3>Statistics</h3>

      <div className="charts-grid">
        <div className="chart-card">
          <h4>Browser Distribution</h4>
          {browserPieData.length > 0 ? (
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={browserPieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    label
                  >
                    {browserPieData.map((entry, index) => (
                      <Cell
                        key={`browser-cell-${index}`}
                        fill={PIE_COLORS[index % PIE_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p>No browser data available.</p>
          )}
        </div>

        <div className="chart-card">
          <h4>Platform Distribution</h4>
          {platformPieData.length > 0 ? (
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={platformPieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    label
                  >
                    {platformPieData.map((entry, index) => (
                      <Cell
                        key={`platform-cell-${index}`}
                        fill={PIE_COLORS[index % PIE_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p>No platform data available.</p>
          )}
        </div>
      </div>

      <div className="chart-card click-history-card">
        <h4>Recent Click Activity</h4>
        <div className="click-total">
          Total Clicks: <strong>{stats.total_clicks ?? 0}</strong>
        </div>

        {recentClicksData.length > 0 ? (
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={recentClicksData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="clicks"
                  stroke="#2563eb"
                  strokeWidth={3}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p>No recent click history available.</p>
        )}
      </div>

      <div className="stats-group">
        <h4>By Country</h4>
        {stats.by_country && stats.by_country.length > 0 ? (
          <ul>
            {stats.by_country.map((item, index) => (
              <li key={index}>
                {item.label}: {item.count}
              </li>
            ))}
          </ul>
        ) : (
          <p>No country data available.</p>
        )}
      </div>
    </div>
  );
}

export default UrlStatsPanel;
