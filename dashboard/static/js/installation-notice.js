// Shared persistent notice, outside the dashboard tabs and Remote cards.
(function () {
  const region = document.querySelector("#installation-notice");
  ws.on("state", state => {
    const notices = state.notices || [];
    const text = notices.join("\n");
    if (region.textContent !== text) region.textContent = text;
    region.hidden = notices.length === 0;
  });
  // Keep Control's viewport-height columns above the Monitor even when a long
  // filename makes the notice wrap. Remote's cards use normal document flow.
  new ResizeObserver(() => {
    document.documentElement.style.setProperty(
      "--installation-notice-height", `${region.getBoundingClientRect().height}px`,
    );
  }).observe(region);
})();
