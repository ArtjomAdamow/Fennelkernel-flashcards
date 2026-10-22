(function () {
  "use strict";

  // Cluster module copy of assets/camera.js. Changes: the figure's meta carries the view ("space" or "deck")
  // and, in the space view, the constellation of the selected deck.
  // Space view, nothing selected: the camera looks at the centre of the sphere from outside and turns around
  // it, at the zoom that just fits the decks' sphere into the window. Space view, a deck selected: the
  // planetarium. The eye sits on the line from the centre of the sphere to the deck and looks at the deck, so
  // only that part of the sphere is in view; its distance along the line is the one at which the deck's
  // constellation just fits the window (a deck on its own is looked at from the very centre); the picture rolls
  // around the selected deck. Deck view: with no card selected the camera turns around the sun (the origin) at
  // the zoomed-out distance; a selected card is centred and the camera turns around it, as the main app does.
  // A mouse drag, a wheel or a double click pauses the motion; once the gesture is over, the motion goes on in
  // the direction the drag turned the camera, from where the gesture left it (in the planetarium: back on the
  // line to the deck, at the zoom the gesture left). Space (by card order, keyboard.js) stops the motion until
  // the next selection or view change. A sun with several group colours cycles through them.

  const graphId = "sphere";
  const centeringDuration = 1800;
  const rotationDuration = 90000;
  const zoomFactor = 0.5;  // a selected card: the camera's distance as a share of the default eye
  const fieldOfView = Math.PI / 4;  // plotly's gl3d camera: its vertical field of view (perspective)
  const fitMargin = 1.06;  // the sphere's radius plus room for the glow of the dots on its rim
  const zoomCap = 0.95;  // the planetarium's eye never goes closer to the deck than this share of the way
  const zoomFloor = -4;  // nor farther behind the centre of the sphere than this share of the deck's distance
  const resumeDelayMs = 300;  // after a gesture ends, the motion goes on this much later
  const directionThreshold = 0.02;  // radians of azimuth a drag must turn the camera to set the direction
  let attachedGraph = null;
  let motionActive = false;
  let animationFrame = null;
  let cameraWriteInFlight = false;
  let pendingCameraWrite = null;
  let cameraWritePromise = Promise.resolve();
  let motionGeneration = 0;
  let lastView = null;
  let viewStarted = false;  // the view's first motion has been started
  let deckSelection;  // deck view: undefined before its first figure, then null or the selected card
  let spaceKey = "";  // space view: the selected deck and its constellation the current motion was made for
  let spaceSelected = null;  // space view: the selected deck, or null
  let orbitCenter = null;  // the centre the camera turns (or rolls) around while a motion runs
  let orbitDirection = 1;  // +1 or -1: the way the camera turns, set by the last drag
  let motionRolls = false;  // the running (or paused) motion is the planetarium's roll, not a turn
  let lastWrittenCamera = null;  // the camera as this script last wrote it
  let foreignCamera = null;  // the camera as the last relayout this script did not write (a drag) reported it
  let paused = null;  // a motion paused by a gesture: the centre and the azimuth to measure the drag against
  let resumeTimer = null;
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

  function selectedTrace(graph) {
    return (graph.data || []).find(function (item) {
      return item.name === "Selected";
    });
  }

  function selectedId(graph) {
    const trace = selectedTrace(graph);
    return trace && trace.customdata && trace.customdata[0];
  }

  function selectedPoint(graph) {
    const trace = selectedTrace(graph);
    if (trace && trace.x && trace.y && trace.z && trace.x.length && trace.y.length && trace.z.length) {
      return { x: trace.x[0], y: trace.y[0], z: trace.z[0] };
    }
    return null;
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
    lastWrittenCamera = clone(camera);
    foreignCamera = null;
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

  function unit(vector) {
    if (!vector || !["x", "y", "z"].every(function (axis) { return Number.isFinite(vector[axis]); })) {
      return null;
    }
    const length = Math.hypot(vector.x, vector.y, vector.z);
    return length > 1e-12 ? { x: vector.x / length, y: vector.y / length, z: vector.z / length } : null;
  }

  function interpolateCamera(start, target, progress) {
    const eye = start.eye || {};
    const targetEye = target.eye || {};
    const center = start.center || { x: 0, y: 0, z: 0 };
    const targetCenter = target.center || center;
    const up = start.up;
    const targetUp = target.up;
    const between = up && targetUp
      ? unit({
        x: up.x + (targetUp.x - up.x) * progress,
        y: up.y + (targetUp.y - up.y) * progress,
        z: up.z + (targetUp.z - up.z) * progress,
      })
      : null;
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
      up: between || targetUp || up,
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

  // --- the camera as it is now, and where things fit ---------------------------------------

  function validCamera(camera) {
    return Boolean(camera && camera.eye && camera.center && ["x", "y", "z"].every(function (axis) {
      return Number.isFinite(camera.eye[axis]) && Number.isFinite(camera.center[axis]);
    }));
  }

  function sceneCamera(graph) {
    const scene = graph._fullLayout && graph._fullLayout.scene;
    const internalScene = scene && scene._scene;
    if (internalScene && typeof internalScene.getCamera === "function") {
      try {
        return plain(internalScene.getCamera());
      } catch (error) {
        // fall through to the layout camera
      }
    }
    return clone(scene && scene.camera);
  }

  // A drag's own report first, then the scene's camera, then this script's last write, then the default.
  function currentCamera(graph) {
    const candidates = [foreignCamera, sceneCamera(graph), lastWrittenCamera];
    for (let index = 0; index < candidates.length; index += 1) {
      if (validCamera(candidates[index])) {
        return clone(candidates[index]);
      }
    }
    return defaultCamera();
  }

  function azimuthOf(camera, center) {
    const around = center || camera.center || { x: 0, y: 0, z: 0 };
    return Math.atan2(camera.eye.y - around.y, camera.eye.x - around.x);
  }

  function wrapAngle(angle) {
    return Math.atan2(Math.sin(angle), Math.cos(angle));
  }

  function dataScaleOf(graph) {
    const scene = graph._fullLayout && graph._fullLayout.scene;
    const scale = scene && scene._scene && numberList(scene._scene.dataScale);
    return scale && scale.length === 3 && scale.every(Number.isFinite) ? scale : [1, 1, 1];
  }

  function sceneSize(graph) {
    const scene = graph._fullLayout && graph._fullLayout.scene;
    const container = scene && scene._scene && scene._scene.container;
    const rect = rectangleOf(container) || rectangleOf(graph);
    return rect && rect.width > 0 && rect.height > 0 ? rect : { width: 1, height: 1 };
  }

  // The half angle of view that limits what fits: the narrower side of the window, less the margin.
  function halfViewAngle(graph) {
    const size = sceneSize(graph);
    const halfVertical = fieldOfView / 2;
    const halfHorizontal = Math.atan((size.width / size.height) * Math.tan(halfVertical));
    return Math.atan(Math.tan(Math.min(halfVertical, halfHorizontal)) / fitMargin);
  }

  // The eye's distance from the centre at which the unit sphere (the decks, the farthest cards) just fits into
  // the window. The unit sphere's radius in the camera's space is the data scale (the axis ranges are the
  // same, the anchor trace keeps them so).
  function fitDistance(graph) {
    const radius = Math.max.apply(null, dataScaleOf(graph));
    return radius / Math.sin(halfViewAngle(graph));
  }

  // The camera that looks at the origin from outside, at the fitting distance, in the current viewing
  // direction. An eye inside the sphere (the planetarium) leaves on the side of what it looks at.
  function cameraAroundOrigin(graph, current) {
    const fallback = defaultCamera();
    const base = validCamera(current) ? current : fallback;
    const inside = Math.hypot(base.eye.x, base.eye.y, base.eye.z) < 0.98 * Math.max.apply(null, dataScaleOf(graph));
    let direction = inside
      ? unit(base.center)
      : unit({ x: base.eye.x - base.center.x, y: base.eye.y - base.center.y, z: base.eye.z - base.center.z });
    if (!direction) {
      direction = unit(fallback.eye);
    }
    const distance = fitDistance(graph);
    return {
      eye: { x: direction.x * distance, y: direction.y * distance, z: direction.z * distance },
      up: fallback.up,
      center: { x: 0, y: 0, z: 0 },
    };
  }

  // --- the planetarium: a selected deck in the space view ---------------------------------------

  // The decks' points by id, from the traces of the space view.
  function deckPoints(graph) {
    const points = {};
    (graph.data || []).forEach(function (trace) {
      if (!trace || !trace.customdata || !trace.x || !trace.y || !trace.z) {
        return;
      }
      if (trace.name !== "Decks" && trace.name !== "Decks (dimmed)" && trace.name !== "Selected") {
        return;
      }
      for (let index = 0; index < trace.customdata.length; index += 1) {
        points[String(trace.customdata[index])] = { x: trace.x[index], y: trace.y[index], z: trace.z[index] };
      }
    });
    return points;
  }

  // The members of the selected deck's constellation (the figure's meta, from the callback), else the deck alone.
  function constellationOf(graph, selected) {
    const meta = graph.layout && graph.layout.meta;
    const members = meta && Array.isArray(meta.constellation) ? meta.constellation.map(String) : [];
    return members.indexOf(String(selected)) >= 0 ? members : [String(selected)];
  }

  // Where along the line from the centre of the sphere to the deck the eye goes: 0 is the centre, 1 the deck,
  // below 0 behind the centre. The largest share at which every member of the constellation stays inside the
  // window whatever the roll: a member at the angle phi from the deck (seen from the centre) allows
  // cos(phi) - sin(phi) / tan(half angle of view). A deck on its own is looked at from the centre.
  function planetariumZoom(graph, axis, memberPoints) {
    const cotangent = 1 / Math.tan(halfViewAngle(graph));
    let zoom = zoomCap;
    let others = 0;
    memberPoints.forEach(function (point) {
      const direction = unit(point);
      if (!direction) {
        return;
      }
      const cosine = Math.max(-1, Math.min(1, axis.x * direction.x + axis.y * direction.y + axis.z * direction.z));
      if (cosine > 1 - 1e-9) {
        return;  // the selected deck itself
      }
      others += 1;
      zoom = Math.min(zoom, cosine - Math.sqrt(1 - cosine * cosine) * cotangent);
    });
    return others ? Math.max(zoomFloor, zoom) : 0;
  }

  // An up vector at right angles to the line of sight: the given one with its part along the line removed,
  // else the z axis, else the y axis (a deck right above the centre).
  function perpendicularUp(axis, hint) {
    const candidates = [hint, { x: 0, y: 0, z: 1 }, { x: 0, y: 1, z: 0 }];
    for (let index = 0; index < candidates.length; index += 1) {
      const candidate = candidates[index];
      if (!candidate || !Number.isFinite(candidate.x) || !Number.isFinite(candidate.y) || !Number.isFinite(candidate.z)) {
        continue;
      }
      const along = axis.x * candidate.x + axis.y * candidate.y + axis.z * candidate.z;
      const flat = unit({ x: candidate.x - axis.x * along, y: candidate.y - axis.y * along, z: candidate.z - axis.z * along });
      if (flat) {
        return flat;
      }
    }
    return { x: 0, y: 0, z: 1 };
  }

  // The planetarium camera of the selected deck: the eye on the line from the centre to the deck (`zoomAlong`
  // of the way, or the fitting share), looking at the deck, the up vector at right angles to the line.
  function planetariumCamera(graph, selected, zoomAlong, upHint) {
    const points = deckPoints(graph);
    const point = points[String(selected)] || selectedPoint(graph);
    const axis = unit(point);
    if (!axis) {
      return null;
    }
    const members = constellationOf(graph, selected).map(function (id) { return points[id]; }).filter(Boolean);
    const zoom = zoomAlong == null
      ? planetariumZoom(graph, axis, members)
      : Math.max(zoomFloor, Math.min(zoomCap, zoomAlong));
    const scale = dataScaleOf(graph);
    const radius = Math.hypot(point.x, point.y, point.z);
    return {
      eye: { x: axis.x * zoom * radius * scale[0], y: axis.y * zoom * radius * scale[1], z: axis.z * zoom * radius * scale[2] },
      up: perpendicularUp(axis, upHint),
      center: { x: point.x * scale[0], y: point.y * scale[1], z: point.z * scale[2] },
    };
  }

  // Where the eye sits along the line to the deck, as a share of the deck's distance from the centre.
  function zoomAlongAxis(graph, camera, selected) {
    const point = deckPoints(graph)[String(selected)] || selectedPoint(graph);
    const axis = unit(point);
    if (!axis) {
      return null;
    }
    const scale = dataScaleOf(graph);
    const radius = Math.hypot(point.x, point.y, point.z) || 1;
    return ((camera.eye.x / scale[0]) * axis.x + (camera.eye.y / scale[1]) * axis.y + (camera.eye.z / scale[2]) * axis.z) / radius;
  }

  // --- turning, rolling, gliding, pausing ------------------------------------------------------

  function orbitCamera(camera, point, elapsed, direction) {
    const eye = camera.eye || { x: 1.25, y: 1.25, z: 1.25 };
    const center = camera.center || point;
    const relative = {
      x: eye.x - center.x,
      y: eye.y - center.y,
      z: eye.z - center.z,
    };
    const angle = (direction || 1) * (elapsed / rotationDuration) * Math.PI * 2;
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

  function rotateAbout(vector, axis, angle) {
    const cosine = Math.cos(angle);
    const sine = Math.sin(angle);
    const dot = axis.x * vector.x + axis.y * vector.y + axis.z * vector.z;
    const cross = {
      x: axis.y * vector.z - axis.z * vector.y,
      y: axis.z * vector.x - axis.x * vector.z,
      z: axis.x * vector.y - axis.y * vector.x,
    };
    return {
      x: vector.x * cosine + cross.x * sine + axis.x * dot * (1 - cosine),
      y: vector.y * cosine + cross.y * sine + axis.y * dot * (1 - cosine),
      z: vector.z * cosine + cross.z * sine + axis.z * dot * (1 - cosine),
    };
  }

  // The planetarium's roll: the up vector turns around the line of sight; eye and centre stay.
  function rolledCamera(camera, elapsed, direction) {
    const axis = unit({ x: camera.center.x - camera.eye.x, y: camera.center.y - camera.eye.y, z: camera.center.z - camera.eye.z });
    if (!axis) {
      return camera;
    }
    const angle = (direction || 1) * (elapsed / rotationDuration) * Math.PI * 2;
    return Object.assign({}, camera, { up: rotateAbout(camera.up || { x: 0, y: 0, z: 1 }, axis, angle) });
  }

  // Turn around `centered.center`, starting from `centered.eye`, in the direction of the last drag.
  function rotateCamera(graph, centered) {
    const startedAt = performance.now();
    orbitCenter = clone(centered.center);
    motionRolls = false;

    function step(now) {
      if (!motionActive) {
        return;
      }
      writeCamera(graph, orbitCamera(centered, centered.center, now - startedAt, orbitDirection));
      animationFrame = window.requestAnimationFrame(step);
    }

    animationFrame = window.requestAnimationFrame(step);
  }

  // Roll around the line of sight to `centered.center`, in the direction of the last drag.
  function rollCamera(graph, centered) {
    const startedAt = performance.now();
    orbitCenter = clone(centered.center);
    motionRolls = true;

    function step(now) {
      if (!motionActive) {
        return;
      }
      writeCamera(graph, rolledCamera(centered, now - startedAt, orbitDirection));
      animationFrame = window.requestAnimationFrame(step);
    }

    animationFrame = window.requestAnimationFrame(step);
  }

  // Glide from the camera as it is now to `target` (the centering), then turn around the target's centre, or
  // roll around the line of sight to it (options.roll).
  function glideTo(graph, target, options) {
    noteViewChange();
    cancelMotion(graph);
    paused = null;
    clearResume();
    if (!window.Plotly || typeof window.Plotly.relayout !== "function") {
      return;
    }
    const start = currentCamera(graph);
    const generation = motionGeneration;
    orbitCenter = clone(target.center);
    motionRolls = Boolean(options && options.roll);
    motionActive = true;

    let startedAt;

    function step(now) {
      if (!motionActive) {
        return;
      }
      const progress = Math.min((now - startedAt) / centeringDuration, 1);
      writeCamera(graph, interpolateCamera(start, target, eased(progress)));
      if (progress < 1) {
        animationFrame = window.requestAnimationFrame(step);
      } else if (options && options.roll) {
        rollCamera(graph, target);
      } else {
        rotateCamera(graph, target);
      }
    }

    writeCamera(graph, start).then(function () {
      if (!motionActive || generation !== motionGeneration) {
        return;
      }
      startedAt = performance.now();
      animationFrame = window.requestAnimationFrame(step);
    });
  }

  // A selected card (deck view): centre on it, then turn around it, as the main app does.
  function moveCamera(graph, selection) {
    glideTo(graph, cameraTargetedAt(selection.point, selection.dataScale, zoomFactor));
  }

  // No card selected, or nothing selected in the space view: look at the origin from the fitting distance,
  // then turn around it.
  function glideToOrigin(graph) {
    glideTo(graph, cameraAroundOrigin(graph, currentCamera(graph)));
  }

  function clearResume() {
    if (resumeTimer !== null) {
      window.clearTimeout(resumeTimer);
      resumeTimer = null;
    }
  }

  // A gesture: the user takes the camera. Remember the centre and the azimuth the motion had, to go on from
  // there afterwards in the direction the gesture turned the camera.
  function pauseMotion(graph) {
    clearResume();
    if (motionActive) {
      paused = {
        center: clone(orbitCenter) || { x: 0, y: 0, z: 0 },
        azimuth: azimuthOf(lastWrittenCamera || currentCamera(graph), orbitCenter),
      };
      cancelMotion(graph);
    } else if (paused) {
      paused.azimuth = azimuthOf(currentCamera(graph), paused.center);
    }
  }

  function scheduleResume(graph) {
    clearResume();
    if (!paused || !graph) {
      return;
    }
    resumeTimer = window.setTimeout(function () {
      resumeTimer = null;
      resumeMotion(graph);
    }, resumeDelayMs);
  }

  // The gesture is over: go on in the direction the drag turned the camera (a drag that did not turn it keeps
  // the direction). In the planetarium the eye goes back onto the line to the deck, at the zoom the gesture
  // left, and the roll goes on; elsewhere the turn goes on from where the gesture left the camera.
  function resumeMotion(graph) {
    if (!paused || pointerIsDown || motionActive) {
      return;
    }
    const center = paused.center;
    const camera = currentCamera(graph);
    const turned = wrapAngle(azimuthOf(camera, center) - paused.azimuth);
    if (Math.abs(turned) > directionThreshold) {
      orbitDirection = turned > 0 ? 1 : -1;
    }
    paused = null;
    if (lastView === "space" && spaceSelected) {
      const along = zoomAlongAxis(graph, camera, spaceSelected);
      const target = along == null ? null : planetariumCamera(graph, spaceSelected, along, camera.up);
      if (target) {
        glideTo(graph, target, { roll: true });
        return;
      }
    }
    motionActive = true;
    if (motionRolls) {
      rollCamera(graph, camera);
    } else {
      rotateCamera(graph, { eye: camera.eye, up: camera.up || defaultCamera().up, center: center });
    }
  }

  function figureView(graph) {
    const meta = graph.layout && graph.layout.meta;
    return meta && meta.view ? meta.view : null;
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
      deckSelection = undefined;
      viewStarted = false;
      spaceKey = "";
      spaceSelected = null;
      paused = null;
      clearResume();
      cancelMotion(graph);
    }
    cycleSunColors(graph);
    if (view === "deck") {
      const current = selectedId(graph) || null;
      if (current === deckSelection) {
        return;
      }
      deckSelection = current;
      const point = current ? selectedPoint(graph) : null;
      if (point) {
        moveCamera(graph, collectSelectionSnapshot(graph, point));  // the selected card: centred, turned around
      } else {
        glideToOrigin(graph);  // entering the deck, or the card unselected: the sun, zoomed out
      }
      return;
    }
    if (view === "space") {
      const current = selectedId(graph) || null;
      const key = current ? String(current) + "|" + constellationOf(graph, current).join(",") : "";
      if (viewStarted && key === spaceKey) {
        return;
      }
      viewStarted = true;
      spaceKey = key;
      spaceSelected = current ? String(current) : null;
      const target = current ? planetariumCamera(graph, current, null, null) : null;
      if (target) {
        glideTo(graph, target, { roll: true });  // the planetarium: from inside, at the deck, its constellation fitted
      } else {
        glideToOrigin(graph);  // nothing selected: the whole sphere from outside, turning
      }
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
    scheduleResume(attachedGraph);  // the drag is over: the motion goes on in its direction
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
        if (validCamera(eventData["scene.camera"])) {
          foreignCamera = clone(eventData["scene.camera"]);  // where the user's gesture left the camera
        }
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

  // Called by Space from keyboard.js. Stop centering/orbit (for good: no motion resumes behind a captured
  // view), wait until pending Plotly writes and any manual gesture have settled, then capture the view.
  // Arrows never call this path.
  function captureView() {
    const graph = attachedGraph;
    if (!graph) {
      return Promise.resolve({ ignored: true });
    }
    if (pointerIsDown) {
      return Promise.resolve({ ignored: true });
    }
    paused = null;
    clearResume();
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

  // Called by Space from keyboard.js in the by-card-order mode: stop the motion for good. It starts again with
  // the next selection, constellation or view change, never by itself; a drag no longer resumes it.
  function stopMotion() {
    paused = null;
    clearResume();
    if (attachedGraph) {
      cancelMotion(attachedGraph);
    }
  }

  const constellationNav = {
    captureView: captureView,
    getGeneration: function () { return viewGeneration; },
    setCameraSource: function (source) { cameraSource = source === "scene" ? "scene" : "layout"; },
    stopMotion: stopMotion,
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
    // A drag or a touch pauses the motion until the pointer is up (onPointerEnd); a wheel or a double click
    // has no end of its own, so the motion goes on after a short quiet time
    ["pointerdown", "touchstart"].forEach(function (eventName) {
      graph.addEventListener(eventName, function () {
        pauseMotion(graph);
      }, { passive: true });
    });
    ["wheel", "dblclick"].forEach(function (eventName) {
      graph.addEventListener(eventName, function () {
        pauseMotion(graph);
        scheduleResume(graph);
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
      fitDistance: fitDistance,
      moveCamera: moveCamera,
      onFigureUpdated: onFigureUpdated,
      planetariumCamera: planetariumCamera,
    };
  }
})();
