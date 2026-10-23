(function () {
  "use strict";

  // Browser key handling for constellation navigation.
  // By card order arrows remain bare directions. Within constellation, arrows send a generation;
  // Space always stops the camera's motion: with a constellation member selected it captures the settled
  // view; otherwise the next Space resumes the motion. Enter always flips the selected card.

  const KEY_WINDOW_MS = 200;
  const ARROWS = { ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down" };

  // Controls that own their arrow keys (dropdowns, sliders, text entry).
  const ARROW_IGNORED = [
    "input", "textarea", "select", "[contenteditable]",
    "[role=slider]", "[role=combobox]", "[role=listbox]",
    ".Select", ".dash-dropdown", ".dash-slider",
  ].join(", ");
  // Space and Enter also belong to buttons (native activation), so buttons are added here.
  // Arrow keys are NOT ignored on buttons: a Confirm button keeps focus after it is clicked and
  // By card order never ignored buttons.
  const ACTION_IGNORED = ARROW_IGNORED + ", button";

  function isIgnoredTarget(target, selector) {
    if (!target) {
      return false;
    }
    if (target.isContentEditable === true) {
      return true;
    }
    if (typeof target.closest === "function") {
      try {
        return Boolean(target.closest(selector));
      } catch (error) {
        return false;
      }
    }
    const tag = String(target.tagName || "").toUpperCase();
    return ["INPUT", "TEXTAREA", "SELECT"].indexOf(tag) !== -1
      || (selector === ACTION_IGNORED && tag === "BUTTON");
  }

  // #nav-config is re-rendered by every callback; it is the only Python-to-JS channel.
  function readConfig(doc) {
    const element = doc && typeof doc.getElementById === "function" ? doc.getElementById("nav-config") : null;
    function attribute(name) {
      return element && typeof element.getAttribute === "function" ? element.getAttribute(name) : null;
    }
    return {
      mode: attribute("data-mode") === "constellation" ? "constellation" : "card_order",
      preview: attribute("data-preview") === "1",
      selected: attribute("data-selected") === "1",
      member: attribute("data-member") === "1",
    };
  }

  function defaultSetProps(value) {
    const dash = typeof window !== "undefined" ? window.dash_clientside : undefined;
    if (dash && typeof dash.set_props === "function") {
      dash.set_props("keyboard-nav", { value: value });
      return;
    }
    // Fallback when set_props is missing (gate 1): the legacy native-setter transport.
    const input = document.querySelector("input#keyboard-nav, #keyboard-nav input");
    if (!input) {
      return;
    }
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }

  // One shared sender, so keyboard.js and camera.js (invalidate) draw from the same seq.
  // seq only makes every written value unique; no ordering logic depends on it.
  function createCommandSender(setProps) {
    let seq = 0;
    return {
      sendBare: function (value) {
        setProps(value);
      },
      sendCommand: function (command) {
        seq += 1;
        setProps(JSON.stringify(Object.assign({ cmd: command.cmd, seq: seq }, command)));
        return seq;
      },
    };
  }

  function createKeyDownHandler(env) {
    let lastArrowAt = null;
    let arrowPending = false;
    let lastSpaceAt = null;
    let spacePending = false;

    function handleArrow(event, direction) {
      if (isIgnoredTarget(event.target, ARROW_IGNORED)) {
        return;
      }
      const config = env.readConfig();
      event.preventDefault();
      if (config.mode !== "constellation") {
        env.sender.sendBare(direction);
        return;
      }
      const nav = env.getNav();
      if (!nav || typeof nav.getGeneration !== "function") {
        return;
      }
      const now = env.now();
      if (arrowPending || (lastArrowAt !== null && now - lastArrowAt < KEY_WINDOW_MS)) {
        return;
      }
      lastArrowAt = now;
      arrowPending = true;
      try {
        env.sender.sendCommand({ cmd: direction, generation: nav.getGeneration() });
      } finally {
        arrowPending = false;
      }
    }

    function handleEnter(event) {
      if (!env.readConfig().selected || isIgnoredTarget(event.target, ACTION_IGNORED)) {
        return;
      }
      event.preventDefault();
      if (!event.repeat) {
        env.sender.sendBare("enter");
      }
    }

    function handleSpace(event) {
      const config = env.readConfig();
      if (config.mode !== "constellation" || isIgnoredTarget(event.target, ACTION_IGNORED)) {
        return;
      }
      event.preventDefault();
      if (event.repeat) {
        return;
      }
      const now = env.now();
      if (spacePending || (lastSpaceAt !== null && now - lastSpaceAt < KEY_WINDOW_MS)) {
        return;
      }
      const nav = env.getNav();
      if (!config.selected || !config.member) {
        // No card selected, or one outside every constellation: no view capture. Space stops the motion,
        // the next Space resumes it; a selected card still gets its message.
        lastSpaceAt = now;
        if (nav && typeof nav.toggleMotion === "function") {
          nav.toggleMotion();
        }
        if (config.selected) {
          env.sender.sendCommand({ cmd: "space" });
        }
        return;
      }
      if (!nav || typeof nav.captureView !== "function") {
        return;
      }
      lastSpaceAt = now;
      spacePending = true;
      let outcome;
      try {
        // Capture synchronously stops any centering/orbit before Plotly handles the key event.
        outcome = nav.captureView();
      } catch (error) {
        spacePending = false;
        return;
      }
      Promise.resolve(outcome).then(function (result) {
        if (result && result.view) {
          env.sender.sendCommand({ cmd: "space", view: result.view });
        }
      }).catch(function () {}).then(function () {
        spacePending = false;
      });
    }

    return function onKeyDown(event) {
      if (event.ctrlKey || event.altKey || event.metaKey) {
        return;
      }
      const direction = ARROWS[event.key];
      if (direction) {
        handleArrow(event, direction);
      } else if (event.key === "Enter") {
        handleEnter(event);
      } else if (event.key === " " || event.key === "Spacebar") {
        handleSpace(event);
      }
    };
  }

  if (typeof document !== "undefined" && typeof document.addEventListener === "function") {
    const sender = createCommandSender(defaultSetProps);
    window.constellationKeys = sender;
    document.addEventListener("keydown", createKeyDownHandler({
      readConfig: function () { return readConfig(document); },
      getNav: function () { return window.constellationNav; },
      sender: sender,
      now: function () { return window.performance.now(); },
    }), true);
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      ACTION_IGNORED: ACTION_IGNORED,
      ARROW_IGNORED: ARROW_IGNORED,
      KEY_WINDOW_MS: KEY_WINDOW_MS,
      createCommandSender: createCommandSender,
      createKeyDownHandler: createKeyDownHandler,
      isIgnoredTarget: isIgnoredTarget,
      readConfig: readConfig,
    };
  }
})();
