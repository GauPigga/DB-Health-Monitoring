import React, { useState, useEffect } from "react";
import SectionHeader from "./SectionHeader";
import DataTable from "./DataTable";
import { exportToCSV } from "../utils/exportCsv";

const tablespaceColumns = [
  { header: "Name", accessor: "name" },
  { header: "Used (GB)", accessor: "used" },
  { header: "Total (GB)", accessor: "total" },
  { header: "Usage %", accessor: "usage" },
  { header: "Usage Bar", accessor: "bar" },
];

// Format GB sizes nicely, convert to MB if very small
const formatSize = (gb) => {
  if (gb > 0 && gb < 0.01) {
    return `${(gb * 1024).toFixed(2)} MB`;
  }
  return `${gb.toFixed(2)} GB`;
};

// Safe usage percentage calculation
const getUsagePercent = (used, total) =>
  total === 0 ? 0 : Math.round((used / total) * 100);

export default function TablespaceUsageTable() {
  const [tablespaceData, setTablespaceData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/tablespaces")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch tablespace data");
        return res.json();
      })
      .then((data) => {
        const mapped = data.map(
          ({
            tablespace_name,
            used_space_gb,
            total_space_gb,
            usage_percent,
          }) => {
            const used = used_space_gb || 0;
            const total = total_space_gb || 0;

            const usage = Number.isFinite(usage_percent)
              ? usage_percent
              : getUsagePercent(used, total);

            let barColor = "bg-green-400";
            if (usage > 80) barColor = "bg-red-500";
            else if (usage > 50) barColor = "bg-yellow-400";

            const bar = (
              <div className="w-full bg-gray-600 rounded h-3">
                <div
                  className={`${barColor} h-3 rounded`}
                  style={{ width: `${usage}%` }}
                />
              </div>
            );

            return {
              name: tablespace_name,
              used: formatSize(used),
              total: formatSize(total),
              usage: `${usage}%`,
              bar,
            };
          }
        );
        setTablespaceData(mapped);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <p>Loading tablespace data...</p>;
  if (error) return <p className="text-red-500">Error: {error}</p>;

  return (
    <section>
      <SectionHeader
        title="💾 Tablespace Usage"
        onExport={() => exportToCSV("tablespace_usage.csv", tablespaceData)}
      />
      <DataTable columns={tablespaceColumns} data={tablespaceData} />
    </section>
  );
}
