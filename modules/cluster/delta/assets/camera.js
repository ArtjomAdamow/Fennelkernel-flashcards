(function () {
  "use strict";

  // Cluster module copy of assets/camera.js. Changes: the figure's meta carries the view ("space" or
  // "deck"). A view change stops any centering/orbit. In the deck view the camera is never centred on a
  // card: it orbits around the sun (the origin) on entering and whenever no card is selected, and holds
  // still while a card is selected. A sun with several group colours cycles through them.

  const graphId = "sphere";
  const centeringDuration = 1800;
  const rotationDuration = 90000;
  const zoomFactor = 0.5;
  let attachedGraph = null;
  let motionActive = false;
  let animationFrame = null;
  let lastSelectedId = null;
  let cameraWriteInFlight = false;
  let pendingCameraWrite = null;
  let cameraWritePromise = Promise.resolve();
  let motionGeneration = 0;
  let lastView = null;
  let deckSelection;  // deck view: undefined before its first figure, then null or the selected card
  const sunColorMs = 1800;
  let sunTimer = null;
  let sunKey = null;

  // Constellation navigation (additive, transient, never persisted).
  const gestureQuietMs = 200;
  const stopTimeoutMs = 1000;
  let viewGeneration = 0;
  let pointerIsDown = false;
  let lastGestureAt = -Infinity;
  let navSent = false;
  let invalidateTimer = null;
  let cameraSource = "layout";

  function defaultCamera() {
    return {
      eye: { x: 1.25, y: 1.25, z: 1.25 },
      up: { x: 0, y: 0, z: 1 },
      center: { x: 0, y: 0, z: 0 },
    };
  }

  function selectedId(graph) {
    const trace = (graph.data || []).find(function (item) {
      return item.name === "Selected";
    });
    return trace && trace.customdata && trace.customdata[0];
  }

  function cancelMotion(graph) {
    motionGeneration += 1;
    pendingCameraWrite = null;
    if (!motionActive) {
      return;
    }
    if (animationFrame !== null) {
      window.cancelAnimationFrame(animationFrame);
    }
    animationFrame = null;
    motionActive = false;
  }

  function writeCamera(graph, camera) {
    pendingCameraWrite = { graph: graph, camera: camera };
    return flushCameraWrites();
  }

  function flushCameraWrites() {
    if (cameraWriteInFlight) {
      return cameraWritePromise;
    }

    if (!pendingCameraWrite) {
      return Promise.resolve();
    }

    const write = pendingCameraWrite;
    pendingCameraWrite = null;
    cameraWriteInFlight = true;
    cameraWritePromise = Promise.resolve()
      .then(function () {
        return window.Plotly.relayout(write.graph, { "scene.camera": write.camera });
      })
      .catch(function () {})
      .then(function () {
        cameraWriteInFlight = false;
        return flushCameraWrites();
      });
    return cameraWritePromise;
  }

  function eased(progress) {
    return progress < 0.5
      ? 4 * progress * progress * progress
      : 1 - Math.pow(-2 * progress + 2, 3) / 2;
  }

  function interpolateCamera(start, target, progress) {
    const eye = start.eye || {};
    const targetEye = target.eye || {};
    const center = start.center || { x: 0, y: 0, z: 0 };
    const targetCenter = target.center || center;
    return Object.assign({}, start, {
      eye: Object.assign({}, eye, {
        x: eye.x + (targetEye.x - eye.x) * progress,
        y: eye.y + (targetEye.y - eye.y) * progress,
        z: eye.z + (targetEye.z - eye.z) * progress,
      }),
      center: {
        x: center.x + (targetCenter.x - center.x) * progress,
        y: center.y + (targetCenter.y - center.y) * progress,
        z: center.z + (targetCenter.z - center.z) * progress,
      },
    });
  }

  function cameraTargetedAt(point, dataScale, distanceFactor) {
    const camera = defaultCamera();
    const eye = camera.eye;
    const scale = dataScale || [1, 1, 1];
    // camera.center/eye are both in gl3d's internal data-scaled space; an invisible
    // anchor trace (map.py) pins dataScale to a fixed, uniform constant, so this stays
    // correct regardless of how many cards are currently visible.
    const scaledPoint = {
      x: point.x * scale[0],
      y: point.y * scale[1],
      z: point.z * scale[2],
    };
    return Object.assign({}, camera, {
      eye: {
        x: scaledPoint.x + eye.x * distanceFactor,
        y: scaledPoint.y + eye.y * distanceFactor,
        z: scaledPoint.z + eye.z * distanceFactor,
      },
      center: scaledPoint,
    });
  }

  function clone(value) {
    return value == null ? value : JSON.parse(JSON.stringify(value));
  }

  function rectangleOf(element) {
    return element && element.getBoundingClientRect
      ? element.getBoundingClientRect().toJSON()
      : null;
  }

  function collectSelectionSnapshot(graph, point) {
    const scene = graph._fullLayout && graph._fullLayout.scene;
    const internalScene = scene && scene._scene;
    return {
      point: clone(point),
      axisRanges: {
        x: clone(scene && scene.xaxis && scene.xaxis.range),
        y: clone(scene && scene.yaxis && scene.yaxis.range),
        z: clone(scene && scene.zaxis && scene.zaxis.range),
      },
      dataScale: clone(internalScene && internalScene.dataScale),
      sceneDomain: clone(scene && scene.domain),
      camera: clone(scene && scene.camera),
      cameraMatrix: clone(internalScene && internalScene.camera && internalScene.camera.matrix),
      graphRect: rectangleOf(graph),
      sceneRect: rectangleOf(internalScene && internalScene.container),
    };
  }

  function orbitCamera(camera, point, elapsed) {
    const eye = camera.eye || { x: 1.25, y: 1.25, z: 1.25 };
    const center = camera.center || point;
    const relative = {
      x: eye.x - center.x,
      y: eye.y - center.y,
      z: eye.z - center.z,
    };
    const angle = (elapsed / rotationDuration) * Math.PI * 2;
    const cosine = Math.cos(angle);
    const sine = Math.sin(angle);
    return Object.assign({}, camera, {
      eye: {
        x: point.x + relative.x * cosine - relative.y * sine,
        y: point.y + relative.x * sine + relative.y * cosine,
        z: point.z + relative.z,
      },
      center: point,
    });
  }

  function moveCamera(graph, selection) {
    noteViewChange();
    const camera = selection.camera && selection.camera.eye && selection.camera.center
      && ["x", "y", "z"].every(function (axis) {
        return Number.isFinite(selection.camera.eye[axis]) && Number.isFinite(selection.camera.center[axis]);
      })
      ? clone(selection.camera)
      : defaultCamera();
    cancelMotion(graph);
    const generation = motionGeneration;
    const selectedTarget = cameraTargetedAt(selection.point, selection.dataScale, zoomFactor);
    motionActive = true;

    if (!window.Plotly || typeof window.Plotly.relayout !== "function") {
      motionActive = false;
      return;
    }

    let startedAt;

    function step(now) {
      if (!motionActive) {
        return;
      }
      const elapsed = now - startedAt;
      const centeringProgress = Math.min(elapsed / centeringDuration, 1);
      const nextCamera = interpolateCamera(camera, selectedTarget, eased(centeringProgress));
      writeCamera(graph, nextCamera);
      if (centeringProgress < 1) {
        animationFrame = window.requestAnimationFrame(step);
      } else {
        rotateCamera(graph, selectedTarget);
      }
    }

    writeCamera(graph, camera).then(function () {
      if (!motionActive || generation !== motionGeneration) {
        return;
      }
      startedAt = performance.now();
      animationFrame = window.requestAnimationFrame(step);
    });
  }

  function rotateCamera(graph, centered) {
    const startedAt = performance.now();

    function step(now) {
      if (!motionActive) {
        return;
      }
      const nextCamera = orbitCamera(centered, centered.center, now - startedAt);
      writeCamera(graph, nextCamera);
      animationFrame = window.requestAnimationFrame(step);
    }

    animationFrame = window.requestAnimationFrame(step);
  }

  function figureView(graph) {
    const meta = graph.layout && graph.layout.meta;
    return meta && meta.view ? meta.view : null;
  }

  // Deck view: orbit around the sun, starting from the current camera with the centre at the origin.
  function orbitSun(graph) {
    noteViewChange();
    cancelMotion(graph);
    if (!window.Plotly || typeof window.Plotly.relayout !== "function") {
      return;
    }
    const scene = graph._fullLayout && graph._fullLayout.scene;
    const current = clone(scene && scene.camera) || defaultCamera();
    const eye = current.eye && ["x", "y", "z"].every(function (axis) { return Number.isFinite(current.eye[axis]); })
      ? current.eye
      : defaultCamera().eye;
    motionActive = true;
    rotateCamera(graph, { eye: eye, up: current.up || defaultCamera().up, center: { x: 0, y: 0, z: 0 } });
  }

  // The sun's traces carry their colours in meta.colors (map.py); with several groups they take turns.
  function cycleSunColors(graph) {
    const traces = [];
    (graph.data || []).forEach(function (trace, index) {
      const colors = trace && trace.meta && trace.meta.colors;
      if ((trace.name === "Sun" || trace.name === "Sun glow") && Array.isArray(colors) && colors.length > 1) {
        traces.push({ index: index, colors: colors });
      }
    });
    const key = traces.length ? JSON.stringify(traces) : null;
    if (key === sunKey) {
      return;
    }
    sunKey = key;
    if (sunTimer !== null) {
      window.clearInterval(sunTimer);
      sunTimer = null;
    }
    if (!key || !window.Plotly || typeof window.Plotly.restyle !== "function") {
      return;
    }
    let turn = 0;
    sunTimer = window.setInterval(function () {
      turn += 1;
      window.Plotly.restyle(
        graph,
        { "marker.color": traces.map(function (item) { return item.colors[turn % item.colors.length]; }) },
        traces.map(function (item) { return item.index; })
      ).catch(function () {});
    }, sunColorMs);
  }

  function onFigureUpdated(graph) {
    const view = figureView(graph);
    if (view !== lastView) {
      lastView = view;
      lastSelectedId = null;
      deckSelection = undefined;
      cancelMotion(graph);
    }
    cycleSunColors(graph);
    if (view === "deck") {
      const current = selectedId(graph) || null;
      if (current !== deckSelection) {
        deckSelection = current;
        if (current) {
          cancelMotion(graph);  // a selected card: the view holds still
        } else {
          orbitSun(graph);  // entering the deck, or the card unselected
        }
      }
      return;
    }
    const currentId = selectedId(graph);
    if (!currentId || currentId === lastSelectedId) {
      return;
    }
    lastSelectedId = currentId;
    const point = (graph.data || [])
      .find(function (item) { return item.name === "Selected"; });
    if (point && point.x && point.y && point.z && point.x.length && point.y.length && point.z.length) {
      const selection = collectSelectionSnapshot(graph, { x: point.x[0], y: point.y[0], z: point.z[0] });
      moveCamera(graph, selection);
    }
  }

  // ---------------------------------------------------------------------------
  // Constellation navigation. Everything below is
  // additive: the selection/orbit path above is not changed in meaning or lifecycle.
  // ---------------------------------------------------------------------------

  function nowMs() {
    return typeof window !== "undefined" && window.performance && typeof window.performance.now === "function"
      ? window.performance.now()
      : Date.now();
  }

  // Every camera change that is not this script's own centering/orbit write counts.
  function noteViewChange() {
    viewGeneration += 1;
  }

  function plain(value) {
    return value == null ? value : JSON.parse(JSON.stringify(value, function (key, item) {
      return ArrayBuffer.isView(item) ? Array.from(item) : item;
    }));
  }

  function numberList(value) {
    return Array.isArray(value) || ArrayBuffer.isView(value) ? Array.from(value) : null;
  }

  // Min and max of the invisible AnchorBounds trace per axis, or null when it cannot be read.
  function anchorExtents(graph) {
    const trace = (graph.data || []).find(function (item) { return item && item.name === "AnchorBounds"; });
    if (!trace) {
      return null;
    }
    const columns = [trace.x, trace.y, trace.z].map(numberList);
    if (columns.some(function (column) { return !column || !column.length || !column.every(Number.isFinite); })) {
      return null;
    }
    return {
      min: columns.map(function (column) { return Math.min.apply(null, column); }),
      max: columns.map(function (column) { return Math.max.apply(null, column); }),
    };
  }

  function readCamera(scene, internalScene) {
    // If graph._fullLayout.scene.camera lags behind a mouse rotation,
    // constellationNav.setCameraSource("scene") reads the scene's own getter instead.
    if (cameraSource === "scene" && internalScene && typeof internalScene.getCamera === "function") {
      try {
        return plain(internalScene.getCamera());
      } catch (error) {
        // fall through to the layout camera
      }
    }
    return plain(scene && scene.camera);
  }

  // Separate from collectSelectionSnapshot: no point, no rectangles, no image.
  function collectNavigationSnapshot(graph) {
    const layout = graph && graph._fullLayout;
    const scene = layout && layout.scene;
    if (!scene) {
      return null;
    }
    const internalScene = scene._scene;
    const meta = layout.meta;
    return {
      camera: readCamera(scene, internalScene),
      dataScale: plain(internalScene && internalScene.dataScale),
      axisRanges: {
        x: plain(scene.xaxis && scene.xaxis.range),
        y: plain(scene.yaxis && scene.yaxis.range),
        z: plain(scene.zaxis && scene.zaxis.range),
      },
      sceneDomain: plain(scene.domain),
      cameraMatrix: plain(internalScene && internalScene.camera && internalScene.camera.matrix),
      aspectmode: scene.aspectmode == null ? null : scene.aspectmode,
      anchor: anchorExtents(graph),
      generation: viewGeneration,
      map_token: meta && meta.map_token != null ? meta.map_token : null,
    };
  }

  function sendInvalidate() {
    invalidateTimer = null;
    if (!navSent) {
      return;
    }
    const keys = typeof window !== "undefined" ? window.constellationKeys : null;
    if (!keys || typeof keys.sendCommand !== "function") {
      return;
    }
    navSent = false;
    keys.sendCommand({ cmd: "invalidate", generation: viewGeneration });
  }

  // 200 ms debounce: the invalidate goes out once the gesture has been quiet, and only if a view was sent.
  function scheduleInvalidate() {
    if (invalidateTimer !== null) {
      window.clearTimeout(invalidateTimer);
    }
    invalidateTimer = window.setTimeout(sendInvalidate, gestureQuietMs);
  }

  function noteGesture() {
    noteViewChange();
    lastGestureAt = nowMs();
    scheduleInvalidate();
  }

  function onPointerEnd() {
    if (!pointerIsDown) {
      return;
    }
    pointerIsDown = false;
    lastGestureAt = nowMs();
    scheduleInvalidate();
  }

  // A camera relayout this script did not write: no write pending or in flight and no motion.
  function isForeignCameraRelayout(eventData) {
    if (!eventData || typeof eventData !== "object") {
      return false;
    }
    const touchesCamera = Object.keys(eventData).some(function (key) {
      return key.indexOf("scene.camera") === 0;
    });
    return touchesCamera && !cameraWriteInFlight && pendingCameraWrite === null && !motionActive;
  }

  function attachNavigation(graph) {
    ["pointerdown", "wheel", "touchstart", "dblclick"].forEach(function (eventName) {
      graph.addEventListener(eventName, function () {
        if (eventName === "pointerdown") {
          pointerIsDown = true;
        }
        noteGesture();
      }, { passive: true });
    });
    ["pointerup", "pointercancel", "blur"].forEach(function (eventName) {
      window.addEventListener(eventName, onPointerEnd, true);
    });
    graph.on("plotly_relayout", function (eventData) {
      if (isForeignCameraRelayout(eventData)) {
        noteGesture();
      }
    });
  }

  function viewIsQuiet() {
    return !motionActive
      && pendingCameraWrite === null
      && !cameraWriteInFlight
      && !pointerIsDown
      && nowMs() - lastGestureAt >= gestureQuietMs;
  }

  // Resolves true after the view has been quiet for one more animation frame, false on timeout.
  function waitForStoppedView(timeoutMs) {
    return new Promise(function (resolve) {
      let finished = false;
      let quietSeen = false;
      const timer = window.setTimeout(function () {
        finish(false);
      }, timeoutMs);

      function finish(result) {
        if (finished) {
          return;
        }
        finished = true;
        window.clearTimeout(timer);
        resolve(result);
      }

      function check() {
        if (finished) {
          return;
        }
        if (viewIsQuiet()) {
          if (quietSeen) {
            finish(true);
            return;
          }
          quietSeen = true;
        } else {
          quietSeen = false;
        }
        window.requestAnimationFrame(check);
      }

      window.requestAnimationFrame(check);
    });
  }

  // Called by Space from keyboard.js. Stop centering/orbit, wait until pending Plotly writes
  // and any manual gesture have settled, then capture the view. Arrows never call this path.
  function captureView() {
    const graph = attachedGraph;
    if (!graph) {
      return Promise.resolve({ ignored: true });
    }
    if (pointerIsDown) {
      return Promise.resolve({ ignored: true });
    }
    if (motionActive) {
      cancelMotion(graph);
    }
    const startGeneration = viewGeneration;
    return waitForStoppedView(stopTimeoutMs).then(function (stopped) {
      if (!stopped || viewGeneration !== startGeneration) {
        return { ignored: true };
      }
      const view = collectNavigationSnapshot(graph);
      if (!view) {
        return { ignored: true };
      }
      navSent = true;
      return { view: view };
    });
  }

  const constellationNav = {
    captureView: captureView,
    getGeneration: function () { return viewGeneration; },
    setCameraSource: function (source) { cameraSource = source === "scene" ? "scene" : "layout"; },
  };
  if (typeof window !== "undefined") {
    window.constellationNav = constellationNav;
  }

  function attach(graph) {
    if (!graph || graph === attachedGraph || typeof graph.on !== "function") {
      return;
    }
    attachedGraph = graph;
    graph.on("plotly_afterplot", function () {
      onFigureUpdated(graph);
    });
    graph.on("plotly_click", function () {
      lastSelectedId = null;
      cancelMotion(graph);
    });
    ["pointerdown", "wheel", "dblclick", "touchstart"].forEach(function (eventName) {
      graph.addEventListener(eventName, function () {
        cancelMotion(graph);
      }, { passive: true });
    });

    attachNavigation(graph);

    window.setInterval(function () {
      onFigureUpdated(graph);
    }, 100);
  }

  function findGraph() {
    const container = document.getElementById(graphId);
    return container && (container.querySelector(".js-plotly-plot") || container);
  }

  function watchForGraph() {
    const graph = findGraph();
    if (graph) {
      attach(graph);
      return true;
    }
    return false;
  }

  if (typeof document !== "undefined" && typeof MutationObserver !== "undefined") {
    const observer = new MutationObserver(watchForGraph);
    observer.observe(document.body, { childList: true, subtree: true });
    watchForGraph();
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      attach: attach,
      collectSelectionSnapshot: collectSelectionSnapshot,
      collectNavigationSnapshot: collectNavigationSnapshot,
      constellationNav: constellationNav,
      moveCamera: moveCamera,
      onFigureUpdated: onFigureUpdated,
    };
  }
})();
