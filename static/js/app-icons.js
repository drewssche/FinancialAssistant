(() => {
  window.App = window.App || {};
  const paths = {"plus": "M12 5v14M5 12h14", "edit": "m15 5 4 4M4 20l4-1L20 7a2 2 0 0 0-4-4L4 15v5Z", "trash": "M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7M14 10v7", "refresh": "M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-2l2 3M4 16l2 3a7 7 0 0 0 12-2", "chart": "M4 3v17h17M7 14l4-5 4 3 5-7", "receipt": "M6 3h12v18l-3-2-3 2-3-2-3 2V3ZM9 7h6M9 11h6M9 15h3", "unlink": "m8 8 8 8M7 3H5a3 3 0 0 0-3 3v2a3 3 0 0 0 3 3h3M17 21h2a3 3 0 0 0 3-3v-2a3 3 0 0 0-3-3h-3M3 17l4-4M17 7l4-4", "save": "m5 12 4 4L19 6", "filter": "M4 6h16M7 12h10M10 18h4", "expand": "m6 9 6-6 6 6M6 15l6 6 6-6", "collapse": "m6 3 6 6 6-6M6 21l6-6 6 6", "width": "M4 4v16M20 4v16M4 12h16m-4-4 4 4-4 4M8 8l-4 4 4 4", "close": "m6 6 12 12M18 6 6 18", "info": "M12 11v6M12 7h.01", "merge": "M4 4v3c0 5 8 3 8 8v6M20 4v3c0 5-8 3-8 8m-4 2 4 4 4-4", "history": "M3 5v5h5M3 10a9 9 0 1 1 1 8M12 7v5l3 2", "down": "M12 4v16m-6-6 6 6 6-6", "upload": "M12 16V4m-5 5 5-5 5 5M4 16v4h16v-4"};
  paths.skip = "M5 5l10 7-10 7V5ZM19 5v14";
  paths.repay = "M4 5h16v14H4V5Zm4 7h8m-3-3 3 3-3 3";
  paths.forgive = "M9 4H5v16h14V4h-4M9 4v4h6V4H9Zm-1 10 3 3 5-6";
  paths.calendar = "M5 5h14v16H5V5Zm3-2v4m8-4v4M5 10h14m-9 5h4";
  paths.link = "m9 15 6-6M7 14l-2 2a3 3 0 0 0 4 4l4-4M11 8l4-4a3 3 0 0 1 4 4l-2 2";
  paths.search = "M21 21l-6-6M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0";
  paths.forward = "M4 12h16m-6-6 6 6-6 6";
  paths.send = "m3 3 18 9-18 9 4-9-4-9Zm4 9h14";
  paths.eye = "M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12Zm7 0a3 3 0 1 0 6 0 3 3 0 0 0-6 0";
  paths.eyeOff = "m3 3 18 18M10 5h2c7 0 10 7 10 7a19 19 0 0 1-3 4M6 6a20 20 0 0 0-4 6s3 7 10 7c2 0 4-1 5-2";
  paths.folderPlus = "M3 7V4h6l2 3h10v13H3V7Zm9 3v7m-3-3h6";
  paths.back = "M20 12H4m6-6-6 6 6 6";
  const svg = name => `<svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="${paths[name] || paths.plus}"/></svg>`;
  function apply(button, name, label) {
    if (!button) return;
    button.classList.add("btn-icon");
    button.innerHTML = svg(name);
    button.setAttribute("aria-label", label);
    button.title = label;
  }
  window.App.icons = {svg, apply};
})();
