(function () {
  "use strict";

  // Cluster module asset (new, 2026-10-27, roadmap step 26, the known issue "the rail's length"): lines the
  // cut-off slider's rail up with the dendrogram's height axis.
  //
  // The dendrogram's figure (layout/dendrogram.py) carries in its meta `rail`: the heights of the cut-off line at
  // 0 % and at 100 %. The slider's thumb should stand beside the dashed line: at 100 % level with the line's
  // highest place, at 0 % with its lowest. The plot area is the figure less its margins, which Plotly widens for
  // long leaf labels, and it sits lower when the panel shows a description, so the fit measures the rendered
  // figure. It sets three variables on the card's window (`.window-a-card`, marked `data-rail`), which style.css
  // applies: --rail-height (the slider's height), --rail-offset (the slider moves down, or up) and --rail-lift
  // (the column's top padding, given up first when the slider must move up, so the gap under the value box
  // stays; the thumb never covers the box).
  //
  // The fit runs after every change in the card's window (a MutationObserver: before the browser paints) and on
  // a resize. Its own writes to the window's style and attributes start no new fit. With no rail to line up (a
  // dot selected, no connections) the variables are removed and the slider keeps its height from panels.py.

  const LIFT_ROOM = 12;  // px: the column's top padding (style.css, .cutoff-control), given up first
  const OFFSET_FLOOR = -10;  // px: the slider moves up at most this far (the gap under the value box less 2 px)
  const THUMB_HALF = 9;  // px: half the thumb (style.css: 18 px); its centre stops this far inside the slider
  const WINDOW = ".window-a-card";
  const GRAPH = ".dendrogram-graph .js-plotly-plot";
  const ROOT = ".cutoff-slider .dash-slider-root";
  const THUMB = ".cutoff-slider .dash-slider-thumb";
  const HEIGHT = "--rail-height";
  const OFFSET = "--rail-offset";
  const LIFT = "--rail-lift";
  const MARK = "data-rail";

  function round(value) {
    return Math.round(value * 100) / 100;
  }

  // The fit itself, independent of the DOM. `plot` is the plot area in page px ({ top, height }), `range` its
  // height axis ([bottom value, top value]), `ends` the line's heights at 0 % and 100 %, `natural` the slider's
  // top without the fit and `thumbHalf` half the thumb. Returns the slider's height, its offset and the lift, in
  // px, or null when nothing fits.
  function railFit(plot, range, ends, natural, thumbHalf) {
    const span = range[1] - range[0];
    if (!(span > 0) || !(plot.height > 0)) {
      return null;
    }
    function pixel(value) {
      return plot.top + plot.height * (1 - (value - range[0]) / span);
    }
    const high = pixel(ends[1]);
    const low = pixel(ends[0]);
    if (!(low > high)) {
      return null;
    }
    const shift = high - thumbHalf - natural;
    const lift = Math.min(LIFT_ROOM, Math.max(0, -shift));
    return {
      height: round(low - high + 2 * thumbHalf),
      offset: round(Math.max(OFFSET_FLOOR, shift + lift)),
      lift: round(lift),
    };
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

  function applied(style, name) {
    const value = parseFloat(style.getPropertyValue(name));
    return Number.isFinite(value) ? value : 0;
  }

  function clear(container) {
    [HEIGHT, OFFSET, LIFT].forEach(function (name) { setVariable(container.style, name, null); });
    if (container.hasAttribute(MARK)) {
      container.removeAttribute(MARK);
    }
  }

  // Line the rail up in the card's window, or clear the variables when there is no rail to line up. Returns the
  // fit, or null.
  function fitRail(container) {
    const graph = container.querySelector(GRAPH);
    const root = container.querySelector(ROOT);
    const layout = graph && graph._fullLayout;
    const ends = layout && layout.meta && layout.meta.rail;
    const size = layout && layout._size;
    const range = layout && layout.yaxis && layout.yaxis.range;
    const rootRect = root ? root.getBoundingClientRect() : null;
    if (!rootRect || rootRect.height <= 0 || !Array.isArray(ends) || ends.length !== 2 || !size || !Array.isArray(range)) {
      clear(container);  // no dendrogram with a cut-off line, or the slider hidden
      return null;
    }
    const thumb = container.querySelector(THUMB);
    const thumbHeight = thumb ? thumb.getBoundingClientRect().height : 0;
    const thumbHalf = thumbHeight > 0 ? thumbHeight / 2 : THUMB_HALF;
    const style = container.style;
    // Where the slider would start without the fit: the offset moved it down, the lift up
    const natural = rootRect.top - applied(style, OFFSET) + applied(style, LIFT);
    const plot = { top: graph.getBoundingClientRect().top + size.t, height: size.h };
    const fit = railFit(plot, range, ends, natural, thumbHalf);
    if (!fit) {
      clear(container);
      return null;
    }
    setVariable(style, HEIGHT, `${fit.height}px`);
    setVariable(style, OFFSET, `${fit.offset}px`);
    setVariable(style, LIFT, `${fit.lift}px`);
    if (!container.hasAttribute(MARK)) {
      container.setAttribute(MARK, "");
    }
    return fit;
  }

  // Watch the card's window (it is in the layout from the start; a replaced one is found again) and fit the rail
  // after every change in it (the panel's text, the dendrogram's drawing, the slider) and on a resize.
  function install(doc, win, Observer) {
    let container = null;
    let observer = null;
    let scheduled = false;

    function run() {
      scheduled = false;
      if (container) {
        try {
          fitRail(container);
        } catch (error) {
          // a window half-rendered or removed: the next change fits it again
        }
      }
    }

    function schedule() {
      if (!scheduled) {
        scheduled = true;
        win.requestAnimationFrame(run);
      }
    }

    // The window's own style and mark are the fit's output, not a change of its content
    function onMutations(records) {
      if (records.some(function (record) { return !(record.type === "attributes" && record.target === container); })) {
        run();
      }
    }

    function attach() {
      const found = doc.querySelector(WINDOW);
      if (!found || found === container) {
        return Boolean(found);
      }
      container = found;
      if (observer) {
        observer.disconnect();
      }
      observer = new Observer(onMutations);
      observer.observe(container, {
        childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["style", "class"],
      });
      run();
      return true;
    }

    attach();
    win.setInterval(attach, 500);  // the window appears with Dash's first render, and could be replaced
    win.addEventListener("resize", schedule);
    if (doc.fonts && doc.fonts.ready && typeof doc.fonts.ready.then === "function") {
      doc.fonts.ready.then(schedule);
    }
    return { run: run, attach: attach, container: function () { return container; } };
  }

  if (typeof document !== "undefined" && typeof window !== "undefined" && typeof MutationObserver !== "undefined") {
    install(document, window, MutationObserver);
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      LIFT_ROOM: LIFT_ROOM,
      OFFSET_FLOOR: OFFSET_FLOOR,
      fitRail: fitRail,
      install: install,
      railFit: railFit,
    };
  }
})();
