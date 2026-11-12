/* The Settings tab: read-only facts about the dashboard host, from `state`
   (`host_*`, `osc_contract_version`, `storage_schema`). */
(function () {
  const $id = (id) => document.getElementById(id);
  const set = (id, value, fallback = "—") => {
    const target = $id(id);
    if (target) target.textContent = value === null || value === undefined || value === "" ? fallback : String(value);
  };
  const BUILD_NOTES = {
    release: "this checkout is the tagged release",
    dev: "a development checkout, past the release tag",
    export: "a copy of the files without a git checkout",
    unknown: "no valid VERSION file",
  };

  function render(state) {
    if (!state) return;
    const release = state.host_release;
    const hasCount = Number.isInteger(state.host_ahead);
    set("settings-release", release);
    set("settings-release-note", release ? "from the VERSION file" : "no valid VERSION file");
    set("settings-state", state.host_state || "unknown");
    set("settings-state-note", BUILD_NOTES[state.host_state] || BUILD_NOTES.unknown);
    set("settings-ahead", hasCount ? state.host_ahead : null);
    set("settings-ahead-note", hasCount
      ? (state.host_ahead === 0 ? `at the release tag v${release}` : `since the release tag v${release}`)
      : "not counted: no git checkout or no release tag reachable");
    set("settings-hash", state.host_git_rev);
    set("settings-hash-note", state.host_git_rev ? "the commit this dashboard runs from" : "no git checkout");
    set("settings-contract", state.osc_contract_version);
    set("settings-schema", state.storage_schema);
  }

  ws.on("state", render);
})();
