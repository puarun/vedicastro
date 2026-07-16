(function () {
  const KEY = "vedicastro.chartStyle";

  function applyStyle(style) {
    const root = document.documentElement;
    root.dataset.chartStyle = style;
    document.querySelectorAll(".toggle-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.style === style);
    });
    document.querySelectorAll(".chart-view.south-view").forEach((el) => {
      el.hidden = style !== "south";
    });
    document.querySelectorAll(".chart-view.north-view").forEach((el) => {
      el.hidden = style !== "north";
    });
  }

  function init() {
    const saved = localStorage.getItem(KEY) || "south";
    applyStyle(saved);
    document.querySelectorAll(".toggle-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const style = btn.dataset.style || "south";
        localStorage.setItem(KEY, style);
        applyStyle(style);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
