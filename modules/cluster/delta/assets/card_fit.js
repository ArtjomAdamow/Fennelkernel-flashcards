(function () {
  "use strict";

  // Cluster module asset (new, 2026-10-27, roadmap step 31): fits a quiz card into the window.
  //
  // A quiz's question, its answer options and its feedback share one font size, the card font (style.css,
  // --card-font) times a scale (--card-scale, 1 by default). The card's frame must fit the browser window's
  // height, counted from the top of the card's window (window A: the progress slider above the frame counts),
  // less FIT_MARGIN. When it does not fit:
  //   1. the separating line rises: the panel's least height (--quiz-panel-min) shrinks toward the question's own
  //      height, never below it, so the question is never covered;
  //   2. then the question and the options scale down together (--card-scale), to the largest scale that fits,
  //      but never below a MIN_FONT_PX font; if even that does not fit, the frame grows and the page scrolls.
  // The back of a quiz (the feedback at the question's size) is fitted the same way. Anything else (a flashcard,
  // a deck, a topic, the dendrogram) is left as it is: both variables are removed.
  //
  // The fit measures the rendered frame, so it runs in the browser after every change of the frame's content
  // (a MutationObserver: before the browser paints), on a resize and once the web fonts are loaded. Its own
  // writes to the frame's style are not changes of the content and start no new fit.

  const FIT_MARGIN = 16;  // px left free below the frame
  const MIN_FONT_PX = 14;  // the scale never takes the card font below this size
  const MIN_SCALE = 0.3;  // the scale's floor when the font size cannot be read
  const SEARCH_STEPS = 10;  // binary search steps for the scale (about 1/1000 of the range)
  const FRAME = ".card-frame";
  const PANEL = ".quiz-panel";
  const SCALE = "--card-scale";
  const PANEL_MIN = "--quiz-panel-min";

  // The fit itself, independent of the DOM. measure(scale, minHeight) gives the frame's height (`total`) and the
  // quiz control's height (`control`) for a text scale and a panel least height in px (null: the CSS default,
  // 0: the panel's own height). Returns the scale and the least height to use (null: the CSS default).
  function fitCard(measure, limit, minScale, steps) {
    const floor = Math.min(1, Math.max(0, minScale));
    if (measure(1, null).total <= limit) {
      return { scale: 1, minHeight: null, fits: true };
    }
    // 1. The line rises: the panel as tall as the space the control leaves, at least the question's own height
    const natural = measure(1, 0);
    if (natural.total <= limit) {
      return { scale: 1, minHeight: Math.floor(limit - natural.control), fits: true };
    }
    // 2. The question and the options scale down together: the largest scale that fits
    const smallest = measure(floor, 0);
    if (smallest.total > limit) {
      return { scale: floor, minHeight: 0, fits: false };
    }
    let low = floor;
    let high = 1;
    for (let step = 0; step < steps; step += 1) {
      const middle = (low + high) / 2;
      if (measure(middle, 0).total <= limit) {
        low = middle;
      } else {
        high = middle;
      }
    }
    const scale = Math.max(floor, Math.floor(low * 1000 + 1e-9) / 1000);  // 3 decimals, never below the floor
    const fitted = measure(scale, 0);
    return { scale: scale, minHeight: Math.max(0, Math.floor(limit - fitted.control)), fits: true };
  }

  function setVariable(style, name, value) {
    if (value === null) {
      if (style.getPropertyValue(name) !== "") {
        style.removeProperty(name);
      }
    } else if (style.getPropertyValue(name) !== value) {
      style.setProperty(name, value);
    }
  }

  // The rendered height with its fraction (offsetHeight rounds, and rounded parts can add up to a pixel too much)
  function heightOf(element) {
    if (!element) {
      return 0;
    }
    return typeof element.getBoundingClientRect === "function" ? element.getBoundingClientRect().height : element.offsetHeight;
  }

  // The space the frame may take: the window's height, less the part of the card's window above the frame (the
  // progress slider) and the margin.
  function limitOf(frame, win) {
    const column = typeof frame.closest === "function" ? frame.closest(".window-a") : null;
    const above = column ? frame.getBoundingClientRect().top - column.getBoundingClientRect().top : 0;
    return win.innerHeight - Math.max(0, above) - FIT_MARGIN;
  }

  // Fit the frame's quiz, or clear the variables when it shows none. Returns the fit, or null.
  function fitFrame(frame, win) {
    const style = frame.style;
    setVariable(style, SCALE, null);
    setVariable(style, PANEL_MIN, null);
    const panel = frame.querySelector(PANEL);
    if (!panel) {
      return null;
    }
    const card = frame.querySelector("#selected-card") || panel;
    const control = frame.querySelector("#quiz-control");
    const text = panel.querySelector(".card-content, .quiz-feedback");
    const base = text ? parseFloat(win.getComputedStyle(text).fontSize) : NaN;
    // The floor, rounded up to 3 decimals: the font never goes below MIN_FONT_PX
    const minScale = Number.isFinite(base) && base > 0
      ? Math.min(1, Math.max(MIN_SCALE, Math.ceil((MIN_FONT_PX / base) * 1000 - 1e-9) / 1000))
      : MIN_SCALE;
    function measure(scale, minHeight) {
      setVariable(style, SCALE, scale === 1 ? null : String(scale));
      setVariable(style, PANEL_MIN, minHeight === null ? null : `${minHeight}px`);
      const controlHeight = heightOf(control);
      return { total: heightOf(card) + controlHeight, control: controlHeight };
    }
    const fit = fitCard(measure, limitOf(frame, win), minScale, SEARCH_STEPS);
    setVariable(style, SCALE, fit.scale === 1 ? null : String(fit.scale));
    setVariable(style, PANEL_MIN, fit.minHeight === null ? null : `${fit.minHeight}px`);
    return fit;
  }

  // Watch the card's frame (it is in the layout from the start; a replaced one is found again) and fit it after
  // every change of its content, on a resize and when the fonts are loaded.
  function install(doc, win, Observer) {
    let frame = null;
    let observer = null;
    let scheduled = false;

    function run() {
      scheduled = false;
      if (frame) {
        try {
          fitFrame(frame, win);
        } catch (error) {
          // a frame half-rendered or removed: the next change fits it again
        }
      }
    }

    function schedule() {
      if (!scheduled) {
        scheduled = true;
        win.requestAnimationFrame(run);
      }
    }

    // The frame's own style is the fit's output, not a change of the content
    function onMutations(records) {
      if (records.some(function (record) { return !(record.type === "attributes" && record.target === frame); })) {
        run();
      }
    }

    function attach() {
      const found = doc.querySelector(FRAME);
      if (!found || found === frame) {
        return Boolean(found);
      }
      frame = found;
      if (observer) {
        observer.disconnect();
      }
      observer = new Observer(onMutations);
      observer.observe(frame, {
        childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["style", "class"],
      });
      run();
      return true;
    }

    attach();
    win.setInterval(attach, 500);  // the frame appears with Dash's first render, and could be replaced
    win.addEventListener("resize", schedule);
    if (doc.fonts) {
      if (doc.fonts.ready && typeof doc.fonts.ready.then === "function") {
        doc.fonts.ready.then(schedule);
      }
      if (typeof doc.fonts.addEventListener === "function") {
        doc.fonts.addEventListener("loadingdone", schedule);
      }
    }
    return { run: run, attach: attach, frame: function () { return frame; } };
  }

  if (typeof document !== "undefined" && typeof window !== "undefined" && typeof MutationObserver !== "undefined") {
    install(document, window, MutationObserver);
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      FIT_MARGIN: FIT_MARGIN,
      MIN_FONT_PX: MIN_FONT_PX,
      fitCard: fitCard,
      fitFrame: fitFrame,
      install: install,
      limitOf: limitOf,
    };
  }
})();
