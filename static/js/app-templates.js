(() => {
  const templates = window.App?.templates;
  if (!templates) {
    return;
  }

  const shellRoot = document.getElementById("appShellRoot");
  if (shellRoot && typeof templates.shell === "string") {
    shellRoot.innerHTML = templates.shell;
  }

  const modalRoot = document.getElementById("modalRoot");
  if (modalRoot && typeof templates.modals === "string") {
    modalRoot.innerHTML = templates.modals;
  }
})();
