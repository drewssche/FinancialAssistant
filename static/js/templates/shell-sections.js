(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.shellSections = `
${window.App.templates.shellSectionsPrimary || ""}
${window.App.templates.shellSectionsSecondary || ""}
`;
})();
