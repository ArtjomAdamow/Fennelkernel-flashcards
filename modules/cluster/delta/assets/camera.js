(function () {
  "use strict";

  // Cluster module copy of assets/camera.js. Changes: the figure's meta carries the view ("decks", "topics" or
  // "cards").
  // Decks view: the camera always sits at the centre of the sphere. Nothing selected: it looks at a random deck
  // and turns the sphere like a globe around its polar axis, in a random direction or the last drag's. A deck
  // selected: it looks at the deck and the picture rolls around the line of sight (the deck stays in the middle,
  // its neighbours wheel around it). Cards view: with nothing selected the camera looks at the middle of the
  // topic's sphere from outside and turns around it at the zoom that just fits the sphere into the window; a
  // selected card is looked at from outside the sphere, the eye on the axis through the sphere's centre and the
  // card, beyond the card at the main app's close-up distance, and the picture rolls around that axis. Topics
  // view: around the center (the origin, where the deck's centroid is drawn) with nothing selected; a selected
  // topic is centred and the camera turns around it, as the main app does.
  // A mouse drag, a wheel or a double click pauses the motion; once the gesture is over, the motion goes on in
  // the direction the drag turned the camera, from where the gesture left it, and at the user's zoom (2026-10-27,
  // roadmap step 27): the zoom is the eye's distance from the point it looks at (what a wheel changes; a
  // turntable drag keeps it), and the motion resumes on the view's path at that distance. With the axis camera
  // the eye goes back onto the axis: a deck's eye at the zoomed distance from the deck (the centre of the sphere
  // at the default zoom), a card's eye at the zoomed distance beyond the card but outside the sphere; with the
  // globe the eye goes back onto the line of sight through the centre at the zoomed distance from the point it
  // looks at (the centre at the default zoom), and the globe turns on with the eye there. Selecting another dot,
  // unselecting and a view change reapply the view's default zoom. Space (by card order, keyboard.js) stops the
  // motion until the next selection or view change. Within constellation, with no dot selected or one outside
  // every constellation, Space stops the motion and the next Space lets it go on as after a drag (toggleMotion);
  // a Space that stopped the glide after a selection half-way lets the glide go on to its target first, then its
  // motion (2026-10-27).
  // A centroid with several group colours cycles through them.
  // The image window (2026-10-27, roadmap step 31): while the figure's meta carries `frozen` (the window covers
  // the map with a selected card's image), the camera stands still: a selection under the window takes the
  // card's seat at once, without the glide (nobody sees the map), and a window opened over a running motion
  // holds the camera where it is. When the window closes, the motion goes on from the held camera, as after a
  // drag (releaseHold).

  const graphId = "sphere";
  const centeringDuration = 1800;
  const rotationDuration = 90000;
  const zoomFactor = 0.5;  // a selected card: the camera's distance as a share of the default eye
  const fieldOfView = Math.PI / 4;  // plotly's gl3d camera: its vertical field of view (perspective)
  const fitMargin = 1.06;  // the sphere's radius plus room for the glow of the dots on its rim
  const axisMargin = 1.1;  // a card's eye never comes closer to the centre than this times the card's distance
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
  let deckSelection;  // topics and cards views: undefined before its first figure, then null or the selected dot
  let decksKey = "";  // decks view: the selected deck the current motion was made for
  let axisSelected = null;  // the dot the axis camera looks at (a deck or a card), or null
  let orbitCenter = null;  // the centre the camera turns (or rolls) around while a motion runs
  let orbitDirection = 1;  // +1 or -1: the way the camera turns, set by the last drag
  let dragDirection = null;  // the direction the last drag gave, if any (the globe starts with it)
  let motionKind = "turn";  // the running (or paused) motion: a turn, the inside camera's roll, or the globe
  let lastWrittenCamera = null;  // the camera as this script last wrote it
  let foreignCamera = null;  // the camera as the last relayout this script did not write (a drag) reported it
  let paused = null;  // a motion paused by a gesture: the centre and the azimuth to measure the drag against
  let resumeTimer = null;
  let spaceStopped = null;  // a motion Space stopped without a capture (like `paused`), for the next Space
  let gliding = null;  // the running glide (glideTo): its target and the motion after it, until it arrives
  let held = null;  // the camera held still under the image window (meta.frozen): its camera and the motion's kind
  let lastFrozen = false;  // whether the last figure carried `frozen`
  const centroidColorMs = 1800;
  let centroidTimer = null;
  let centroidKey = null;

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
    gliding = null;
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
  // direction. An eye inside the sphere (the inside camera) leaves on the side of what it looks at.
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

  // --- the axis camera: a selected deck in the decks view, a selected card in the cards view -----------

  // The decks' points by id, from the traces of the decks view.
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

  // An up vector at right angles to the line of sight: the given one with its part along the line removed,
  // else the z axis, else the y axis (a dot right above the centre).
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

  // The axis camera: the eye on the axis through the centre of the sphere and the selected dot (`point`, in
  // data coordinates), `distance` from the centre along that axis (0: at the centre, looking outward at a deck;
  // beyond the dot: outside the sphere, looking inward at a card), looking at the dot, the up vector at right
  // angles to the axis. The picture then rolls around the axis (rollCamera): the dot stays in the middle of the
  // window and its neighbours wheel around it.
  function axisCamera(graph, point, distance, upHint) {
    const axis = unit(point);
    if (!axis) {
      return null;
    }
    const scale = dataScaleOf(graph);
    return {
      eye: { x: axis.x * distance * scale[0], y: axis.y * distance * scale[1], z: axis.z * distance * scale[2] },
      up: perpendicularUp(axis, upHint),
      center: { x: point.x * scale[0], y: point.y * scale[1], z: point.z * scale[2] },
    };
  }

  // The eye's seat for a selected card: outside the sphere, beyond the card on its axis, the main app's close-up
  // distance (zoomFactor of the default eye distance) away from the card.
  function cardEyeDistance(graph, point) {
    const scale = Math.max.apply(null, dataScaleOf(graph));
    const defaultEye = defaultCamera().eye;
    return Math.hypot(point.x, point.y, point.z) + (zoomFactor * Math.hypot(defaultEye.x, defaultEye.y, defaultEye.z)) / scale;
  }

  // The nearest seat outside the sphere for a card: a wheel zoom never takes the eye inside.
  function outsideDistance(point, distance) {
    return Math.max(axisMargin * Math.hypot(point.x, point.y, point.z), distance);
  }

  // The user's zoom: the eye's distance from the point the camera looks at, in data coordinates. A wheel
  // changes it, a turntable drag keeps it, so the motion resumes at it (the default zoom is the view's own
  // distance: 1 for the globe and a selected deck, the close-up for a card).
  function zoomOf(graph, camera) {
    const scale = Math.max.apply(null, dataScaleOf(graph));
    return Math.hypot(camera.eye.x - camera.center.x, camera.eye.y - camera.center.y, camera.eye.z - camera.center.z) / scale;
  }

  // --- the globe: nothing selected in the decks view ---------------------------------------------

  // The direction of a random deck (the Decks traces), else a random direction in the equator's plane.
  function randomDirection(graph) {
    const points = Object.keys(deckPoints(graph)).map(function (id) { return unit(deckPoints(graph)[id]); }).filter(Boolean);
    if (points.length) {
      return points[Math.floor(Math.random() * points.length)];
    }
    const angle = Math.random() * 2 * Math.PI;
    return { x: Math.cos(angle), y: Math.sin(angle), z: 0 };
  }

  // The globe camera: the eye on the line of sight through the centre of the sphere, looking in `direction` (a
  // unit vector in data coordinates) at the point of the sphere's surface in that direction, `zoom` (data
  // units, 1 by default) away from it: at the default zoom the eye is at the centre; a user's zoom moves it
  // along the line (toward the surface, or behind the centre). The up vector upright.
  function globeCameraAt(graph, direction, zoom) {
    const scale = dataScaleOf(graph);
    const offset = 1 - (Number.isFinite(zoom) ? zoom : 1);
    return {
      eye: { x: direction.x * offset * scale[0], y: direction.y * offset * scale[1], z: direction.z * offset * scale[2] },
      up: perpendicularUp(direction, { x: 0, y: 0, z: 1 }),
      center: { x: direction.x * scale[0], y: direction.y * scale[1], z: direction.z * scale[2] },
    };
  }

  // The direction the camera looks in, in data coordinates.
  function lookDirection(graph, camera) {
    const scale = dataScaleOf(graph);
    return unit({
      x: (camera.center.x - camera.eye.x) / scale[0],
      y: (camera.center.y - camera.eye.y) / scale[1],
      z: (camera.center.z - camera.eye.z) / scale[2],
    });
  }

  // The globe's turn: the look direction turns around the polar (z) axis. The eye turns with it, so an eye at
  // the centre stays there and a zoomed eye keeps its distance along the line of sight.
  function spunGlobe(camera, elapsed, direction) {
    const angle = (direction || 1) * (elapsed / rotationDuration) * Math.PI * 2;
    const polar = { x: 0, y: 0, z: 1 };
    const center = rotateAbout(camera.center, polar, angle);
    const eye = rotateAbout(camera.eye, polar, angle);
    const axis = unit({ x: center.x - eye.x, y: center.y - eye.y, z: center.z - eye.z });
    return Object.assign({}, camera, {
      eye: eye,
      center: center,
      up: axis ? perpendicularUp(axis, { x: 0, y: 0, z: 1 }) : camera.up,
    });
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

  // The inside camera's roll: the up vector turns around the line of sight; eye and centre stay.
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
    motionKind = "turn";

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
    motionKind = "roll";

    function step(now) {
      if (!motionActive) {
        return;
      }
      writeCamera(graph, rolledCamera(centered, now - startedAt, orbitDirection));
      animationFrame = window.requestAnimationFrame(step);
    }

    animationFrame = window.requestAnimationFrame(step);
  }

  // Turn the globe: from `centered` (the eye at the centre of the sphere) the look direction turns around the
  // polar axis, in the direction of the last drag. The centre a gesture is measured against follows the look.
  function spinGlobe(graph, centered) {
    const startedAt = performance.now();
    orbitCenter = clone(centered.center);
    motionKind = "globe";

    function step(now) {
      if (!motionActive) {
        return;
      }
      const camera = spunGlobe(centered, now - startedAt, orbitDirection);
      orbitCenter = clone(camera.center);
      writeCamera(graph, camera);
      animationFrame = window.requestAnimationFrame(step);
    }

    animationFrame = window.requestAnimationFrame(step);
  }

  // Glide from the camera as it is now to `target` (the centering), then go on with the motion of
  // options.kind: a turn around the target's centre (the default), a roll around the line of sight to it, or
  // the globe's turn from it.
  function glideTo(graph, target, options) {
    noteViewChange();
    cancelMotion(graph);
    paused = null;
    spaceStopped = null;  // a new motion: its first Space stops it
    held = null;
    clearResume();
    if (!window.Plotly || typeof window.Plotly.relayout !== "function") {
      return;
    }
    const start = currentCamera(graph);
    const generation = motionGeneration;
    const kind = (options && options.kind) || "turn";
    orbitCenter = clone(target.center);
    motionKind = kind;
    motionActive = true;
    gliding = { target: clone(target), kind: kind };

    let startedAt;

    function step(now) {
      if (!motionActive) {
        return;
      }
      const progress = Math.min((now - startedAt) / centeringDuration, 1);
      writeCamera(graph, interpolateCamera(start, target, eased(progress)));
      if (progress < 1) {
        animationFrame = window.requestAnimationFrame(step);
        return;
      }
      gliding = null;
      if (kind === "roll") {
        rollCamera(graph, target);
      } else if (kind === "globe") {
        spinGlobe(graph, target);
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

  // A selected topic or card: centre on it, then turn around it, as the main app does.
  function moveCamera(graph, selection) {
    glideTo(graph, cameraTargetedAt(selection.point, selection.dataScale, zoomFactor));
  }

  // Nothing selected in the topics or cards view: look at the origin from the fitting distance, then turn
  // around it.
  function glideToOrigin(graph) {
    glideTo(graph, cameraAroundOrigin(graph, currentCamera(graph)));
  }

  // Nothing selected in the decks view: to the centre of the sphere, looking at a random deck, then the
  // globe's turn in the last drag's direction, or a random one.
  function glideToGlobe(graph) {
    orbitDirection = dragDirection || (Math.random() < 0.5 ? -1 : 1);
    glideTo(graph, globeCameraAt(graph, randomDirection(graph)), { kind: "globe" });
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
  // the direction), at the user's zoom (zoomOf: the eye's distance from the point it looks at, which a wheel
  // changes and a drag keeps). With the axis camera the eye goes back onto the axis through the centre and the
  // dot at that distance from the dot (a deck: toward the centre, which is the default; a card: beyond the card,
  // outside the sphere) and the roll goes on; with the globe the eye goes back onto the line of sight through
  // the centre at that distance from the point it looks at (the centre at the default), looking where the
  // gesture left the view, and the globe turns on; elsewhere the turn goes on from where the gesture left the
  // camera, at its distance. A glide Space stopped half-way (toggleMotion) goes on to its target first, at the
  // target's own zoom, then its motion follows; a drag in between only sets the direction.
  function resumeMotion(graph) {
    if (!paused || pointerIsDown || motionActive) {
      return;
    }
    const center = paused.center;
    const camera = currentCamera(graph);
    const turned = wrapAngle(azimuthOf(camera, center) - paused.azimuth);
    if (Math.abs(turned) > directionThreshold) {
      orbitDirection = turned > 0 ? 1 : -1;
      dragDirection = orbitDirection;
    }
    const glide = paused.glide;
    paused = null;
    if (glide) {
      glideTo(graph, glide.target, { kind: glide.kind });
      return;
    }
    const zoom = zoomOf(graph, camera);
    if (lastView === "decks" && !axisSelected) {
      const look = lookDirection(graph, camera) || unit(camera.center) || { x: 1, y: 0, z: 0 };
      glideTo(graph, globeCameraAt(graph, look, zoom), { kind: "globe" });
      return;
    }
    if ((lastView === "decks" || lastView === "cards") && axisSelected) {
      const point = selectedPoint(graph);
      const radius = point ? Math.hypot(point.x, point.y, point.z) : null;
      const distance = radius == null ? null : (lastView === "decks" ? radius - zoom : outsideDistance(point, radius + zoom));
      const target = point && distance != null ? axisCamera(graph, point, distance, camera.up) : null;
      if (target) {
        glideTo(graph, target, { kind: "roll" });
        return;
      }
    }
    motionActive = true;
    if (motionKind === "roll") {
      rollCamera(graph, camera);
    } else {
      rotateCamera(graph, { eye: camera.eye, up: camera.up || defaultCamera().up, center: center });
    }
  }

  function figureView(graph) {
    const meta = graph.layout && graph.layout.meta;
    return meta && meta.view ? meta.view : null;
  }

  // The image window covers the map: the figure's meta carries `frozen`.
  function figureFrozen(graph) {
    const meta = graph.layout && graph.layout.meta;
    return Boolean(meta && meta.frozen === true);
  }

  // The camera takes `camera` at once, without a glide, and stands still under the image window; the motion of
  // `kind` goes on from there once the window closes (releaseHold).
  function holdCamera(graph, camera, kind) {
    noteViewChange();
    cancelMotion(graph);
    paused = null;
    spaceStopped = null;
    clearResume();
    motionKind = kind;
    orbitCenter = clone(camera.center);
    held = { camera: clone(camera), kind: kind };
    writeCamera(graph, camera);
  }

  // The window opened over a running motion: hold the camera where it is.
  function holdHere(graph) {
    holdCamera(graph, currentCamera(graph), motionKind);
  }

  // The window closed: the held motion goes on from the held camera, as after a drag.
  function releaseHold(graph) {
    const hold = held;
    held = null;
    if (!hold || motionActive || pointerIsDown) {
      return;
    }
    motionActive = true;
    if (hold.kind === "roll") {
      rollCamera(graph, hold.camera);
    } else if (hold.kind === "globe") {
      spinGlobe(graph, hold.camera);
    } else {
      rotateCamera(graph, hold.camera);
    }
  }

  // The centroid's traces carry their colours in meta.colors (map.py); with several groups they take turns.
  function cycleCentroidColors(graph) {
    const traces = [];
    (graph.data || []).forEach(function (trace, index) {
      const colors = trace && trace.meta && trace.meta.colors;
      if ((trace.name === "Centroid" || trace.name === "Centroid glow") && Array.isArray(colors) && colors.length > 1) {
        traces.push({ index: index, colors: colors });
      }
    });
    const key = traces.length ? JSON.stringify(traces) : null;
    if (key === centroidKey) {
      return;
    }
    centroidKey = key;
    if (centroidTimer !== null) {
      window.clearInterval(centroidTimer);
      centroidTimer = null;
    }
    if (!key || !window.Plotly || typeof window.Plotly.restyle !== "function") {
      return;
    }
    let turn = 0;
    centroidTimer = window.setInterval(function () {
      turn += 1;
      window.Plotly.restyle(
        graph,
        { "marker.color": traces.map(function (item) { return item.colors[turn % item.colors.length]; }) },
        traces.map(function (item) { return item.index; })
      ).catch(function () {});
    }, centroidColorMs);
  }

  function onFigureUpdated(graph) {
    const view = figureView(graph);
    const frozen = figureFrozen(graph);
    if (view !== lastView) {
      lastView = view;
      deckSelection = undefined;
      viewStarted = false;
      decksKey = "";
      axisSelected = null;
      paused = null;
      held = null;
      lastFrozen = false;
      clearResume();
      cancelMotion(graph);
    }
    cycleCentroidColors(graph);
    if (view === "topics" || view === "cards") {
      const current = selectedId(graph) || null;
      if (current === deckSelection) {
        if (frozen !== lastFrozen) {
          // The same selection: the image window opened over the motion, or closed
          lastFrozen = frozen;
          if (frozen) {
            holdHere(graph);
          } else {
            releaseHold(graph);
          }
        }
        return;
      }
      deckSelection = current;
      lastFrozen = frozen;
      axisSelected = null;
      const point = current ? selectedPoint(graph) : null;
      const outside = view === "cards" && point ? axisCamera(graph, point, cardEyeDistance(graph, point), null) : null;
      if (outside) {
        axisSelected = String(current);
        if (frozen) {
          holdCamera(graph, outside, "roll");  // selected under the image window: the seat at once, standing still
        } else {
          glideTo(graph, outside, { kind: "roll" });  // the selected card: from outside on its axis, rolling
        }
      } else if (point) {
        moveCamera(graph, collectSelectionSnapshot(graph, point));  // the selected topic: centred, turned around
      } else {
        glideToOrigin(graph);  // entering the deck or topic, or the dot unselected: the center, zoomed out
      }
      return;
    }
    if (view === "decks") {
      const current = selectedId(graph) || null;
      const key = current ? String(current) : "";
      if (viewStarted && key === decksKey) {
        return;
      }
      viewStarted = true;
      decksKey = key;
      axisSelected = current ? String(current) : null;
      const point = current ? selectedPoint(graph) : null;
      const target = point ? axisCamera(graph, point, 0, null) : null;
      if (target) {
        glideTo(graph, target, { kind: "roll" });  // the selected deck: from the centre of the sphere, rolling
      } else {
        axisSelected = null;
        glideToGlobe(graph);  // nothing selected: from the centre of the sphere, the globe turning
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
    spaceStopped = null;  // stopped for good: a later Space without a capture stops first
    held = null;
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
    spaceStopped = null;
    held = null;
    clearResume();
    if (attachedGraph) {
      cancelMotion(attachedGraph);
    }
  }

  // Called by Space from keyboard.js within constellation when no view is captured (no dot selected, or one
  // outside every constellation): the first press stops the motion, remembering it like a gesture; the next one
  // lets it go on from where the camera is, as after a drag (with the inside camera: back on the line to the
  // deck, then the roll). A press during the glide after a selection stops it half-way; the next one glides on
  // to its target first (resumeMotion). A drag in between does not resume it, but sets the direction.
  function toggleMotion() {
    const graph = attachedGraph;
    if (!graph || pointerIsDown) {
      return;
    }
    if (!spaceStopped) {
      const glide = gliding;  // pauseMotion cancels it
      pauseMotion(graph);
      spaceStopped = paused || {
        center: clone(orbitCenter) || { x: 0, y: 0, z: 0 },
        azimuth: azimuthOf(currentCamera(graph), orbitCenter),
      };
      spaceStopped.glide = glide;
      paused = null;
      return;
    }
    paused = spaceStopped;
    spaceStopped = null;
    resumeMotion(graph);
  }

  const constellationNav = {
    captureView: captureView,
    getGeneration: function () { return viewGeneration; },
    setCameraSource: function (source) { cameraSource = source === "scene" ? "scene" : "layout"; },
    stopMotion: stopMotion,
    toggleMotion: toggleMotion,
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
      axisCamera: axisCamera,
      fitDistance: fitDistance,
      globeCameraAt: globeCameraAt,
      moveCamera: moveCamera,
      onFigureUpdated: onFigureUpdated,
      zoomOf: zoomOf,
    };
  }
})();
