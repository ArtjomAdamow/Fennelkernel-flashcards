(function () {
  "use strict";

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
    const scenePoint = {
      x: point.x * scale[0],
      y: point.y * scale[1],
      z: point.z * scale[2],
    };
    return Object.assign({}, camera, {
      eye: {
        x: eye.x * distanceFactor,
        y: eye.y * distanceFactor,
        z: eye.z * distanceFactor,
      },
      center: scenePoint,
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

  function onFigureUpdated(graph) {
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

  function mapHasFocus(graph, event) {
    return event.target === graph || graph.contains(event.target) || document.activeElement === graph;
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

    graph.addEventListener("keydown", function (event) {
      if (mapHasFocus(graph, event)) {
        cancelMotion(graph);
      }
    });

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

  const observer = new MutationObserver(watchForGraph);
  observer.observe(document.body, { childList: true, subtree: true });
  watchForGraph();
})();
