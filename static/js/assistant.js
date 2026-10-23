(function () {
  "use strict";

  var root = document.querySelector("[data-assistant]");
  if (!root) {
    return;
  }

  var chatUrl = root.getAttribute("data-chat-url");
  var toggle = root.querySelector("[data-assistant-toggle]");
  var panel = root.querySelector("[data-assistant-panel]");
  var closeButton = root.querySelector("[data-assistant-close]");
  var messages = root.querySelector("[data-assistant-messages]");
  var suggestions = root.querySelector("[data-assistant-suggestions]");
  var form = root.querySelector("[data-assistant-form]");
  var input = root.querySelector("[data-assistant-input]");
  var sendButton = root.querySelector("[data-assistant-send]");
  var csrfInput = form ? form.querySelector("input[name='csrfmiddlewaretoken']") : null;

  if (!chatUrl || !toggle || !panel || !messages || !form || !input || !sendButton) {
    return;
  }

  var history = [];
  var isSending = false;
  var isNavigating = false;

  function setOpen(isOpen) {
    panel.hidden = !isOpen;
    root.classList.toggle("is-open", isOpen);
    toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    if (isOpen) {
      window.setTimeout(function () {
        input.focus();
      }, 40);
    }
  }

  function scrollToLatest() {
    messages.scrollTop = messages.scrollHeight;
  }

  function escapeHtml(value) {
    return value.replace(/[&<>"']/g, function (character) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[character];
    });
  }

  function formatReply(value) {
    var safe = escapeHtml(value);
    safe = safe.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    );
    safe = safe.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
    return safe;
  }

  function addMessage(role, text) {
    var bubble = document.createElement("div");
    bubble.className = "assistant-message assistant-message-" + role;
    if (role === "bot") {
      bubble.innerHTML = formatReply(text);
    } else {
      bubble.textContent = text;
    }
    messages.appendChild(bubble);
    scrollToLatest();
    return bubble;
  }

  function addError(text) {
    var bubble = document.createElement("div");
    bubble.className = "assistant-message assistant-message-bot assistant-message-error";
    bubble.textContent = text;
    messages.appendChild(bubble);
    scrollToLatest();
  }

  function addTyping() {
    var bubble = document.createElement("div");
    bubble.className = "assistant-message assistant-message-bot";
    bubble.setAttribute("data-assistant-typing", "");
    bubble.innerHTML =
      '<span class="assistant-typing" aria-label="Assistant is typing"><span></span><span></span><span></span></span>';
    messages.appendChild(bubble);
    scrollToLatest();
    return bubble;
  }

  function removeTyping(bubble) {
    if (bubble && bubble.parentNode) {
      bubble.parentNode.removeChild(bubble);
    }
  }

  function addSources(sources) {
    if (!Array.isArray(sources) || !sources.length) {
      return;
    }

    var valid = sources.filter(function (source) {
      return (
        source &&
        typeof source.url === "string" &&
        /^https?:\/\//i.test(source.url) &&
        typeof source.title === "string"
      );
    });
    if (!valid.length) {
      return;
    }

    var block = document.createElement("div");
    block.className = "assistant-sources";

    var title = document.createElement("p");
    title.className = "assistant-sources-title";
    title.textContent = "Sources";
    block.appendChild(title);

    valid.forEach(function (source) {
      var link = document.createElement("a");
      link.href = source.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = source.title;
      block.appendChild(link);
    });

    messages.appendChild(block);
    scrollToLatest();
  }

  function addAction(action) {
    if (!action || typeof action.url !== "string" || !action.url) {
      return;
    }

    var link = document.createElement("a");
    link.className = "assistant-action";
    link.href = action.url;
    link.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/><path d="M13 6l6 6-6 6"/></svg>';
    link.appendChild(document.createTextNode(action.label || "Open in SmartMeds"));
    messages.appendChild(link);
    scrollToLatest();

    if (!isNavigating) {
      isNavigating = true;
      window.setTimeout(function () {
        window.location.assign(action.url);
      }, 750);
    }
  }

  function updateSendState() {
    sendButton.disabled = isSending || !input.value.trim();
  }

  function resizeInput() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  }

  function pushHistory(role, content) {
    history.push({ role: role, content: content });
    if (history.length > 10) {
      history = history.slice(history.length - 10);
    }
  }

  async function sendMessage(text) {
    var message = (text || "").trim();
    if (!message || isSending) {
      return;
    }

    setOpen(true);
    isSending = true;
    updateSendState();
    addMessage("user", message);
    input.value = "";
    resizeInput();
    if (suggestions) {
      suggestions.hidden = true;
    }

    var typing = addTyping();

    try {
      var response = await fetch(chatUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrfInput ? csrfInput.value : "",
        },
        body: JSON.stringify({
          message: message,
          history: history.slice(-8),
        }),
      });

      var payload = null;
      try {
        payload = await response.json();
      } catch (error) {
        payload = null;
      }

      removeTyping(typing);

      if (!response.ok) {
        addError(
          (payload && payload.error) ||
            "The assistant could not respond right now. Please try again."
        );
        return;
      }

      if (!payload || typeof payload.reply !== "string") {
        addError("The assistant returned an empty response. Please try again.");
        return;
      }

      pushHistory("user", message);
      pushHistory("assistant", payload.reply);
      addMessage("bot", payload.reply);
      addSources(payload.sources);

      if (Array.isArray(payload.actions) && payload.actions.length) {
        addAction(payload.actions[0]);
      }
    } catch (error) {
      removeTyping(typing);
      addError("Could not reach the assistant. Check your connection and try again.");
    } finally {
      isSending = false;
      updateSendState();
    }
  }

  toggle.addEventListener("click", function () {
    setOpen(panel.hidden);
  });

  if (closeButton) {
    closeButton.addEventListener("click", function () {
      setOpen(false);
      toggle.focus();
    });
  }

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !panel.hidden) {
      setOpen(false);
      toggle.focus();
    }
  });

  if (suggestions) {
    suggestions.addEventListener("click", function (event) {
      var chip = event.target.closest("[data-assistant-prompt]");
      if (!chip) {
        return;
      }
      sendMessage(chip.getAttribute("data-assistant-prompt") || "");
    });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    sendMessage(input.value);
  });

  input.addEventListener("input", function () {
    updateSendState();
    resizeInput();
  });

  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage(input.value);
    }
  });

  updateSendState();
})();
