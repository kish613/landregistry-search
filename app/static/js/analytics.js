document.addEventListener("DOMContentLoaded", () => {
  const sendEvent = (eventName, payload) => {
    if (typeof window.gtag !== "function") {
      return;
    }
    window.gtag("event", eventName, payload);
  };

  document.querySelectorAll("[data-track-event]").forEach((element) => {
    element.addEventListener("click", () => {
      sendEvent(element.dataset.trackEvent, {
        page_type: element.dataset.pageType || "unknown",
        slug: element.dataset.slug || "",
        cta_variant: element.dataset.ctaVariant || "",
        search_type: element.dataset.searchType || "",
      });
    });
  });

  window.landRegistryAnalytics = {
    sendEvent,
  };
});
