(function () {
  "use strict";

  // Cluster module copy of assets/keyboard.js. Changes: Backspace sends the bare "back" command (Python decides:
  // unselect the dot, or leave the cards view; nothing while a dialog is open); the top bar buttons give up the
  // focus after a click, so a following Enter flips the card instead of clicking the button again; by card
  // order, Space stops the camera's motion (camera.js, constellationNav.stopMotion) and sends nothing; within
  // constellation, with no dot selected or one outside every constellation, Space stops the motion and the next
  // Space resumes it (constellationNav.toggleMotion), as in the main project; Enter is sent with nothing selected
  // too (it turns the card panel over where a module gives it a back). The quiz cards' answer options and the
  // image window (2026-10-27, roadmap step 31): a toggled quiz checkbox (a change inside .quiz-options) gives
  // up the focus 300 ms later (CHECKBOX_BLUR_MS), so the keys reach this handler again; within that time the
  // checkbox keeps its own keys (Space toggles it, Enter and the arrows are ignored as on any input). A clicked
  // Confirm (.quiz-confirm) gives up the focus at once, like the top bar buttons. While the image window covers
  // the map (#nav-config data-image), Space sends the bare "close-image" command instead of stopping the motion
  // or capturing the view, and within constellation the arrows send it too (their scroll needs the map).
  //
  // Browser key handling for constellation navigation.
  // By card order arrows remain bare directions. Within constellation, arrows send a generation;
  // Space always stops the camera's motion: with a constellation member selected it captures the settled
  // view; otherwise the next Space resumes the motion. Enter always flips the selected card.

  const KEY_WINDOW_MS = 200;
  const CHECKBOX_BLUR_MS = 300;  // a toggled quiz checkbox keeps the focus this long
  const CLOSE_IMAGE = "close-image";  // the bare command that closes the image window
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
      image: attribute("data-image") === "1",  // the image window covers the map
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
        env.sender.sendBare(direction);  // by card order the next card, whose image the window then shows
        return;
      }
      if (config.image) {
        // Within constellation the scroll needs the map (the ring's order on the screen, the white line): the
        // arrows close the image window first
        if (!event.repeat) {
          env.sender.sendBare(CLOSE_IMAGE);
        }
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

    // Enter goes to Python with or without a selected dot: with nothing selected it turns the card panel over
    // when a module gives it a back (the callback's overview_back); otherwise Python ignores it.
    function handleEnter(event) {
      if (isIgnoredTarget(event.target, ACTION_IGNORED)) {
        return;
      }
      event.preventDefault();
      if (!event.repeat) {
        env.sender.sendBare("enter");
      }
    }

    function handleBack(event) {
      // Backspace edits text and belongs to the controls the arrow keys leave alone
      if (isIgnoredTarget(event.target, ARROW_IGNORED)) {
        return;
      }
      event.preventDefault();  // never a browser "back" navigation
      if (!event.repeat) {
        env.sender.sendBare("back");
      }
    }

    // By card order: Space stops the camera's motion (the turn, the roll or the orbit), whatever is selected.
    // Nothing goes to Python; the motion starts again with the next selection or view change.
    function handleStop(event) {
      event.preventDefault();  // never a page scroll
      if (event.repeat) {
        return;
      }
      const nav = env.getNav();
      if (nav && typeof nav.stopMotion === "function") {
        nav.stopMotion();
      }
    }

    function handleSpace(event) {
      const config = env.readConfig();
      if (isIgnoredTarget(event.target, ACTION_IGNORED)) {
        return;
      }
      if (config.image) {
        // The image window covers the map: Space closes it and does nothing else, in both modes
        event.preventDefault();
        if (!event.repeat) {
          env.sender.sendBare(CLOSE_IMAGE);
        }
        return;
      }
      if (config.mode !== "constellation") {
        handleStop(event);
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
        // No dot selected, or one outside every constellation: no view capture. Space stops the motion,
        // the next Space resumes it; a selected dot still gets its message.
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
      } else if (event.key === "Backspace") {
        handleBack(event);
      } else if (event.key === " " || event.key === "Spacebar") {
        handleSpace(event);
      }
    };
  }

  // A toggled quiz checkbox (a change event inside .quiz-options) gives up the focus CHECKBOX_BLUR_MS later, if
  // it still has it: Enter, Space and the arrows then reach the key handler again, as after the click on
  // Random. A focus it lost in between (a click elsewhere) is left alone.
  function createChangeHandler(env) {
    return function onChange(event) {
      const target = event && event.target;
      if (!target || typeof target.closest !== "function" || !target.closest(".quiz-options")) {
        return;
      }
      env.setTimeout(function () {
        if (env.activeElement() === target && typeof target.blur === "function") {
          target.blur();
        }
      }, CHECKBOX_BLUR_MS);
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
    // A clicked top bar button (Random, Decks) or a quiz's Confirm keeps no focus: Enter then reaches the
    // handler above
    document.addEventListener("click", function (event) {
      const button = event.target && typeof event.target.closest === "function"
        ? event.target.closest(".random-button, .quiz-confirm") : null;
      if (button && typeof button.blur === "function") {
        button.blur();
      }
    });
    document.addEventListener("change", createChangeHandler({
      setTimeout: function (fn, ms) { return window.setTimeout(fn, ms); },
      activeElement: function () { return document.activeElement; },
    }));
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      ACTION_IGNORED: ACTION_IGNORED,
      ARROW_IGNORED: ARROW_IGNORED,
      CHECKBOX_BLUR_MS: CHECKBOX_BLUR_MS,
      CLOSE_IMAGE: CLOSE_IMAGE,
      KEY_WINDOW_MS: KEY_WINDOW_MS,
      createChangeHandler: createChangeHandler,
      createCommandSender: createCommandSender,
      createKeyDownHandler: createKeyDownHandler,
      isIgnoredTarget: isIgnoredTarget,
      readConfig: readConfig,
    };
  }
})();
