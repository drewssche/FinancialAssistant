(() => {
  const { el, core } = window.App;
  const sendButtons = [
    el.dashboardSendCurrencyDigestBtn,
    el.currencySendDigestBtn,
    el.analyticsSendCurrencyDigestBtn,
  ].filter(Boolean);
  let sendPromise = null;

  function setPendingState(isPending) {
    sendButtons.forEach((button) => {
      if (isPending) {
        button.dataset.currencyDigestIdleText = button.textContent || "Отправить дайджест";
        button.dataset.currencyDigestWasDisabled = button.disabled ? "1" : "0";
        button.textContent = "Отправляем...";
        button.disabled = true;
        button.classList.add("is-loading");
        button.setAttribute("aria-busy", "true");
        return;
      }

      button.textContent = button.dataset.currencyDigestIdleText || "Отправить дайджест";
      button.disabled = button.dataset.currencyDigestWasDisabled === "1";
      button.classList.remove("is-loading");
      button.removeAttribute("aria-busy");
      delete button.dataset.currencyDigestIdleText;
      delete button.dataset.currencyDigestWasDisabled;
    });
  }

  function sendCurrencyDigest() {
    if (sendPromise) {
      return sendPromise;
    }

    setPendingState(true);
    sendPromise = (async () => {
      try {
        const result = await core.requestJson("/api/v1/currency/telegram-digest/send", {
          method: "POST",
          headers: core.authHeaders(),
          timeoutMs: 120000,
        });
        core.setStatus(result?.message || "Валютный дайджест успешно отправлен в Telegram");
        return result;
      } catch (err) {
        if (!core.isAbortError?.(err)) {
          const message = core.errorMessage?.(err) || String(err || "Неизвестная ошибка");
          const deliveryIsUnconfirmed = /telegram не подтвердил отправку/i.test(message);
          core.setStatus(
            deliveryIsUnconfirmed
              ? message
              : `Не удалось отправить валютный дайджест: ${message}`,
          );
        }
        return null;
      } finally {
        setPendingState(false);
        sendPromise = null;
      }
    })();
    return sendPromise;
  }

  sendButtons.forEach((button) => {
    button.addEventListener("click", () => {
      sendCurrencyDigest();
    });
  });

  window.App.registerRuntimeModule?.("currency-digest-actions", {
    sendCurrencyDigest,
  });
})();
