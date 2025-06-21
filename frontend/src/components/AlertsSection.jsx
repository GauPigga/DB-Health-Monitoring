import React, { useEffect, useState } from "react";
import SectionHeader from "./SectionHeader";
import DataTable from "./DataTable";
import { FaExclamationTriangle } from "react-icons/fa";

const alertColumns = [
  { header: "Time", accessor: "time" },
  { header: "Message", accessor: "message" },
];

export default function AlertsSection() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/alerts")
      .then((res) => res.json())
      .then((data) => {
        setAlerts(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch alerts:", err);
        setLoading(false);
      });
  }, []);

  return (
    <section>
      <SectionHeader
        title={
          <span className="flex items-center gap-2">
            <FaExclamationTriangle className="text-red-500" />
            Recent Alerts
          </span>
        }
      />

      {loading ? (
        <div>Loading alerts...</div>
      ) : alerts.length === 0 ? (
        <div>No recent alerts to display.</div>
      ) : (
        <DataTable columns={alertColumns} data={alerts} />
      )}
    </section>
  );
}
