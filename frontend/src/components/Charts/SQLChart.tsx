import React from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar, Line, Pie } from "react-chartjs-2";
import { SQLChartData } from "../../types";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

interface SQLChartProps {
  chartData: SQLChartData;
}

export const SQLChart: React.FC<SQLChartProps> = ({ chartData }) => {
  if (!chartData || !chartData.labels || chartData.labels.length === 0) {
    return null;
  }

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: "top" as const,
        labels: {
          color: "#f8fafc",
        },
      },
    },
    scales:
      chartData.type !== "pie"
        ? {
            x: {
              ticks: { color: "#94a3b8" },
              grid: { color: "#334155" },
            },
            y: {
              ticks: { color: "#94a3b8" },
              grid: { color: "#334155" },
            },
          }
        : undefined,
  };

  return (
    <div style={{ marginTop: "16px", padding: "16px", background: "#0f172a", borderRadius: "12px" }}>
      {chartData.type === "line" && <Line data={chartData} options={options} />}
      {chartData.type === "pie" && <Pie data={chartData} options={options} />}
      {(chartData.type === "bar" || !["line", "pie"].includes(chartData.type)) && (
        <Bar data={chartData} options={options} />
      )}
    </div>
  );
};
