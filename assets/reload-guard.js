(function () {
  "use strict";

  const pollInterval = 3000;
  const bootId = window.__SERVER_BOOT_ID__;

  function checkBootId() {
    fetch("/boot-id", { cache: "no-store" })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        if (bootId && data.bootId && data.bootId !== bootId) {
          window.location.reload();
        }
      })
      .catch(function () {});
  }

  if (!bootId) {
    return;
  }

  window.setInterval(checkBootId, pollInterval);
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") {
      checkBootId();
    }
  });
})();
