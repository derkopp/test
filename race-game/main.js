import * as THREE from "three";

// ---------- Basic scene setup ----------

const canvas = document.getElementById("game-canvas");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x7ec8f2);
scene.fog = new THREE.Fog(0x7ec8f2, 80, 300);

const camera = new THREE.PerspectiveCamera(
  60,
  window.innerWidth / window.innerHeight,
  0.1,
  1000
);
camera.position.set(0, 6, -10);

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
renderer.setSize(window.innerWidth, window.innerHeight);

// ---------- Lighting ----------

scene.add(new THREE.HemisphereLight(0xffffff, 0x557733, 0.9));

const sun = new THREE.DirectionalLight(0xffffff, 1.2);
sun.position.set(60, 90, -40);
sun.castShadow = true;
sun.shadow.camera.left = -100;
sun.shadow.camera.right = 100;
sun.shadow.camera.top = 100;
sun.shadow.camera.bottom = -100;
sun.shadow.mapSize.set(2048, 2048);
scene.add(sun);

// ---------- Ground ----------

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(600, 600),
  new THREE.MeshStandardMaterial({ color: 0x5aa24a })
);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

// ---------- Oval race track ----------

const TRACK_OUTER_X = 45;
const TRACK_OUTER_Z = 30;
const TRACK_WIDTH = 14;

function ovalPoints(radiusX, radiusZ, segments = 128) {
  const points = [];
  for (let i = 0; i <= segments; i++) {
    const angle = (i / segments) * Math.PI * 2;
    points.push(
      new THREE.Vector2(
        Math.cos(angle) * radiusX,
        Math.sin(angle) * radiusZ
      )
    );
  }
  return points;
}

const outerPts = ovalPoints(TRACK_OUTER_X, TRACK_OUTER_Z);
const innerPts = ovalPoints(
  TRACK_OUTER_X - TRACK_WIDTH,
  TRACK_OUTER_Z - TRACK_WIDTH
);

const trackShape = new THREE.Shape(outerPts);
trackShape.holes.push(new THREE.Path(innerPts));

const trackMesh = new THREE.Mesh(
  new THREE.ShapeGeometry(trackShape, 64),
  new THREE.MeshStandardMaterial({ color: 0x3a3a3d })
);
trackMesh.rotation.x = -Math.PI / 2;
trackMesh.position.y = 0.01;
trackMesh.receiveShadow = true;
scene.add(trackMesh);

// grass infield
const infield = new THREE.Mesh(
  new THREE.ShapeGeometry(
    new THREE.Shape(
      ovalPoints(TRACK_OUTER_X - TRACK_WIDTH, TRACK_OUTER_Z - TRACK_WIDTH)
    ),
    64
  ),
  new THREE.MeshStandardMaterial({ color: 0x6fbf5c })
);
infield.rotation.x = -Math.PI / 2;
infield.position.y = 0.015;
infield.receiveShadow = true;
scene.add(infield);

// start / finish line
const finishLine = new THREE.Mesh(
  new THREE.PlaneGeometry(TRACK_WIDTH, 2),
  new THREE.MeshStandardMaterial({ color: 0xffffff })
);
finishLine.rotation.x = -Math.PI / 2;
finishLine.position.set(0, 0.02, -TRACK_OUTER_Z + TRACK_WIDTH / 2);
scene.add(finishLine);

// ---------- Car ----------

function buildCar() {
  const car = new THREE.Group();

  const bodyMat = new THREE.MeshStandardMaterial({ color: 0xd7263d });
  const body = new THREE.Mesh(new THREE.BoxGeometry(2, 0.6, 4), bodyMat);
  body.position.y = 0.6;
  body.castShadow = true;
  car.add(body);

  const cabin = new THREE.Mesh(
    new THREE.BoxGeometry(1.4, 0.5, 1.8),
    new THREE.MeshStandardMaterial({ color: 0xdfe8f0 })
  );
  cabin.position.set(0, 1.05, -0.2);
  cabin.castShadow = true;
  car.add(cabin);

  const wheelGeo = new THREE.CylinderGeometry(0.45, 0.45, 0.4, 16);
  const wheelMat = new THREE.MeshStandardMaterial({ color: 0x111111 });
  const wheelOffsets = [
    [-1.05, 0.45, 1.3],
    [1.05, 0.45, 1.3],
    [-1.05, 0.45, -1.3],
    [1.05, 0.45, -1.3],
  ];
  for (const [x, y, z] of wheelOffsets) {
    const wheel = new THREE.Mesh(wheelGeo, wheelMat);
    wheel.rotation.z = Math.PI / 2;
    wheel.position.set(x, y, z);
    wheel.castShadow = true;
    car.add(wheel);
  }

  return car;
}

const car = buildCar();
car.position.set(0, 0, -TRACK_OUTER_Z + TRACK_WIDTH / 2);
scene.add(car);

// ---------- Controls ----------

const keys = { forward: false, backward: false, left: false, right: false };

function setKey(code, value) {
  switch (code) {
    case "ArrowUp":
    case "KeyW":
      keys.forward = value;
      break;
    case "ArrowDown":
    case "KeyS":
      keys.backward = value;
      break;
    case "ArrowLeft":
    case "KeyA":
      keys.left = value;
      break;
    case "ArrowRight":
    case "KeyD":
      keys.right = value;
      break;
  }
}

window.addEventListener("keydown", (e) => setKey(e.code, true));
window.addEventListener("keyup", (e) => setKey(e.code, false));

const startOverlay = document.getElementById("start-overlay");
let started = false;
function start() {
  if (started) return;
  started = true;
  startOverlay.classList.add("hidden");
}
startOverlay.addEventListener("click", start);
window.addEventListener("keydown", start);

// ---------- Simple arcade car physics ----------

const physics = {
  speed: 0,
  maxSpeed: 26,
  maxReverseSpeed: -10,
  acceleration: 18,
  brakeForce: 30,
  friction: 10,
  steerSpeed: 2.2,
};

const speedEl = document.getElementById("speed");

function updateCar(delta) {
  if (keys.forward) {
    physics.speed += physics.acceleration * delta;
  } else if (keys.backward) {
    physics.speed -= physics.brakeForce * delta;
  } else {
    const decel = physics.friction * delta;
    if (physics.speed > 0) physics.speed = Math.max(0, physics.speed - decel);
    else if (physics.speed < 0) physics.speed = Math.min(0, physics.speed + decel);
  }

  physics.speed = THREE.MathUtils.clamp(
    physics.speed,
    physics.maxReverseSpeed,
    physics.maxSpeed
  );

  const steerInput = (keys.left ? 1 : 0) - (keys.right ? 1 : 0);
  if (steerInput !== 0 && Math.abs(physics.speed) > 0.05) {
    const speedFactor = physics.speed / physics.maxSpeed;
    car.rotation.y += steerInput * physics.steerSpeed * speedFactor * delta;
  }

  const forward = new THREE.Vector3(
    Math.sin(car.rotation.y),
    0,
    Math.cos(car.rotation.y)
  );
  car.position.addScaledVector(forward, physics.speed * delta);

  speedEl.textContent = `${Math.round(Math.abs(physics.speed) * 6.2)} km/h`;
}

// ---------- Follow camera ----------

const camOffset = new THREE.Vector3(0, 4.5, -8);
const camTarget = new THREE.Vector3();

function updateCamera(delta) {
  const desired = car.position
    .clone()
    .add(camOffset.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), car.rotation.y));
  camera.position.lerp(desired, 1 - Math.pow(0.001, delta));

  camTarget.copy(car.position).add(new THREE.Vector3(0, 1, 0));
  camera.lookAt(camTarget);
}

// ---------- Main loop ----------

const clock = new THREE.Clock();

function animate() {
  requestAnimationFrame(animate);
  const delta = Math.min(clock.getDelta(), 0.1);

  if (started) {
    updateCar(delta);
  }
  updateCamera(delta);

  renderer.render(scene, camera);
}

animate();
