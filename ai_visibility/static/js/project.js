/* Project specific Javascript goes here. */

/* ai-visibility: render metric sparkline charts from data-points attributes. */
window.addEventListener("DOMContentLoaded", function () {
  if (typeof Chart === "undefined") return;
  document.querySelectorAll("canvas.av-chart").forEach(function (canvas) {
    var points;
    try {
      points = JSON.parse(canvas.dataset.points || "[]");
    } catch (e) {
      return;
    }
    if (!points.length) return;
    new Chart(canvas, {
      type: "line",
      data: {
        labels: points.map(function (p) { return p.x; }),
        datasets: [{
          label: canvas.dataset.label || "",
          data: points.map(function (p) { return p.y; }),
          borderColor: "#0d6efd",
          tension: 0.3,
          pointRadius: 2,
        }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { x: { display: false } },
      },
    });
  });
});
