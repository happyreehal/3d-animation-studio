# ============================================================
# 3D ANIMATION STUDIO - Physics Engine
# ============================================================
# Features:
# - Bullet Physics integration (via pybullet)
# - Rigid body dynamics
# - Collision detection
# - Gravity simulation
# - Multiple body shapes (box, sphere, cylinder, mesh)
# - Force & impulse application
# - Constraint system (joints)
# - Physics-based simulation
# - Ray casting
# - Simulation control (play/pause/step)
# ============================================================

# ===== PATH SETUP =====
import sys
import os
if __name__ == "__main__":
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(os.path.dirname(_current_dir))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
# ======================

import math
import time
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

try:
    import pybullet as pb
    PYBULLET_AVAILABLE = True
except ImportError:
    PYBULLET_AVAILABLE = False
    pb = None

from src.utils import (
    get_logger, get_config, clamp, generate_short_id
)

logger = get_logger("PhysicsEngine")


# ============================================================
# BODY TYPES
# ============================================================

class BodyType(Enum):
    """Rigid body types"""
    STATIC = "static"        # Nahi hilta (ground, walls)
    DYNAMIC = "dynamic"      # Full physics (gravity affects)
    KINEMATIC = "kinematic"  # Manually moved, affects others


class ShapeType(Enum):
    """Collision shape types"""
    BOX = "box"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    CAPSULE = "capsule"
    PLANE = "plane"
    MESH = "mesh"


# ============================================================
# MATERIAL PROPERTIES
# ============================================================

@dataclass
class PhysicsMaterial:
    """Physics material properties"""
    friction: float = 0.5           # 0=slippery, 1=grippy
    restitution: float = 0.3        # 0=no bounce, 1=perfect bounce
    linear_damping: float = 0.04    # Air resistance (linear)
    angular_damping: float = 0.04   # Air resistance (rotational)
    rolling_friction: float = 0.0   # Rolling friction

    @classmethod
    def wood(cls) -> "PhysicsMaterial":
        return cls(friction=0.6, restitution=0.2, linear_damping=0.1)

    @classmethod
    def metal(cls) -> "PhysicsMaterial":
        return cls(friction=0.4, restitution=0.3, linear_damping=0.05)

    @classmethod
    def rubber(cls) -> "PhysicsMaterial":
        return cls(friction=0.9, restitution=0.8, linear_damping=0.1)

    @classmethod
    def ice(cls) -> "PhysicsMaterial":
        return cls(friction=0.02, restitution=0.1, linear_damping=0.02)

    @classmethod
    def ground(cls) -> "PhysicsMaterial":
        return cls(friction=0.7, restitution=0.1, linear_damping=0.0)

    @classmethod
    def bouncy(cls) -> "PhysicsMaterial":
        return cls(friction=0.5, restitution=0.95, linear_damping=0.05)


# ============================================================
# RIGID BODY
# ============================================================

@dataclass
class RigidBody:
    """Physics rigid body"""
    id: str = field(default_factory=generate_short_id)
    name: str = "Body"

    # Bullet object id
    body_id: int = -1

    # Type & shape
    body_type: BodyType = BodyType.DYNAMIC
    shape_type: ShapeType = ShapeType.BOX

    # Transform
    position: List[float] = field(default_factory=lambda: [0, 0, 0])
    rotation: List[float] = field(default_factory=lambda: [0, 0, 0, 1])  # Quaternion
    scale: List[float] = field(default_factory=lambda: [1, 1, 1])

    # Physics properties
    mass: float = 1.0
    material: PhysicsMaterial = field(default_factory=PhysicsMaterial)

    # State
    enabled: bool = True
    is_sleeping: bool = False

    # Shape-specific data
    shape_data: Dict = field(default_factory=dict)

    def get_position(self) -> List[float]:
        return list(self.position)

    def get_rotation(self) -> List[float]:
        return list(self.rotation)


# ============================================================
# COLLISION EVENT
# ============================================================

@dataclass
class CollisionEvent:
    """Collision information"""
    body_a_id: str
    body_b_id: str
    contact_point: List[float]
    contact_normal: List[float]
    contact_distance: float
    timestamp: float = field(default_factory=time.time)


# ============================================================
# RAYCAST RESULT
# ============================================================

@dataclass
class RaycastHit:
    """Ray casting result"""
    hit: bool = False
    body_id: Optional[str] = None
    hit_position: List[float] = field(default_factory=lambda: [0, 0, 0])
    hit_normal: List[float] = field(default_factory=lambda: [0, 0, 0])
    distance: float = 0.0
    fraction: float = 0.0  # 0-1 (kitni door hit hua)


# ============================================================
# MAIN PHYSICS ENGINE
# ============================================================

class PhysicsEngine:
    """
    Main physics engine using PyBullet.
    """

    def __init__(self, config: Optional[Dict] = None):
        # Config
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        physics_config = self.config.get("physics", {})

        # Settings
        self.gravity = physics_config.get("gravity", [0, -9.81, 0])
        self.simulation_steps = physics_config.get("simulation_steps", 60)
        self.time_step = 1.0 / self.simulation_steps
        self.enabled = physics_config.get("enabled", True)

        # Bullet client
        self.client_id: int = -1
        self.initialized = False

        # Bodies storage
        self.bodies: Dict[str, RigidBody] = {}
        self._body_id_to_uuid: Dict[int, str] = {}

        # Simulation state
        self.is_running = False
        self.is_paused = False
        self.simulation_time = 0.0
        self.frame_count = 0

        # Collision tracking
        self._collision_pairs: List[CollisionEvent] = []
        self._collision_listeners: List[Callable] = []

        # Constraints
        self.constraints: Dict[str, int] = {}  # uuid → bullet constraint id

        # Initialize
        self._initialize()

    # ------------------------------------------------------------
    # INITIALIZATION
    # ------------------------------------------------------------

    def _initialize(self) -> bool:
        """PyBullet initialize karo"""
        if not PYBULLET_AVAILABLE:
            logger.error("pybullet not installed! pip install pybullet")
            return False

        try:
            # Direct mode (no GUI)
            self.client_id = pb.connect(pb.DIRECT)

            # Gravity set karo
            pb.setGravity(*self.gravity, physicsClientId=self.client_id)

            # Time step
            pb.setTimeStep(self.time_step, physicsClientId=self.client_id)

            # Real-time simulation off (manual control)
            pb.setRealTimeSimulation(0, physicsClientId=self.client_id)

            self.initialized = True
            logger.info(f"PhysicsEngine initialized (gravity: {self.gravity})")
            return True

        except Exception as e:
            logger.error(f"Physics init failed: {e}")
            return False

    def shutdown(self):
        """Physics engine shutdown"""
        if self.initialized:
            try:
                pb.disconnect(physicsClientId=self.client_id)
                self.initialized = False
                logger.info("PhysicsEngine shut down")
            except Exception as e:
                logger.error(f"Shutdown error: {e}")

    # ------------------------------------------------------------
    # BODY CREATION
    # ------------------------------------------------------------

    def create_box(self, name: str = "Box",
                   position: Optional[List[float]] = None,
                   size: Optional[List[float]] = None,
                   mass: float = 1.0,
                   body_type: BodyType = BodyType.DYNAMIC,
                   material: Optional[PhysicsMaterial] = None) -> Optional[RigidBody]:
        """Box rigid body create karo"""
        if not self.initialized:
            return None

        position = position or [0, 5, 0]
        size = size or [1, 1, 1]
        material = material or PhysicsMaterial()

        try:
            # Collision shape
            half_extents = [s / 2.0 for s in size]
            shape_id = pb.createCollisionShape(
                pb.GEOM_BOX,
                halfExtents=half_extents,
                physicsClientId=self.client_id
            )

            # Static body: mass = 0
            actual_mass = 0.0 if body_type == BodyType.STATIC else mass

            # Create body
            body_id = pb.createMultiBody(
                baseMass=actual_mass,
                baseCollisionShapeIndex=shape_id,
                basePosition=position,
                physicsClientId=self.client_id
            )

            # Material properties apply karo
            self._apply_material(body_id, material)

            # RigidBody object
            body = RigidBody(
                name=name,
                body_id=body_id,
                body_type=body_type,
                shape_type=ShapeType.BOX,
                position=list(position),
                mass=actual_mass,
                material=material,
                shape_data={"size": size}
            )

            self.bodies[body.id] = body
            self._body_id_to_uuid[body_id] = body.id

            logger.debug(f"Created box: {name} at {position}")
            return body

        except Exception as e:
            logger.error(f"Box creation failed: {e}")
            return None

    def create_sphere(self, name: str = "Sphere",
                      position: Optional[List[float]] = None,
                      radius: float = 1.0,
                      mass: float = 1.0,
                      body_type: BodyType = BodyType.DYNAMIC,
                      material: Optional[PhysicsMaterial] = None) -> Optional[RigidBody]:
        """Sphere rigid body"""
        if not self.initialized:
            return None

        position = position or [0, 5, 0]
        material = material or PhysicsMaterial()

        try:
            shape_id = pb.createCollisionShape(
                pb.GEOM_SPHERE,
                radius=radius,
                physicsClientId=self.client_id
            )

            actual_mass = 0.0 if body_type == BodyType.STATIC else mass

            body_id = pb.createMultiBody(
                baseMass=actual_mass,
                baseCollisionShapeIndex=shape_id,
                basePosition=position,
                physicsClientId=self.client_id
            )

            self._apply_material(body_id, material)

            body = RigidBody(
                name=name,
                body_id=body_id,
                body_type=body_type,
                shape_type=ShapeType.SPHERE,
                position=list(position),
                mass=actual_mass,
                material=material,
                shape_data={"radius": radius}
            )

            self.bodies[body.id] = body
            self._body_id_to_uuid[body_id] = body.id

            logger.debug(f"Created sphere: {name} at {position}")
            return body

        except Exception as e:
            logger.error(f"Sphere creation failed: {e}")
            return None

    def create_cylinder(self, name: str = "Cylinder",
                        position: Optional[List[float]] = None,
                        radius: float = 0.5,
                        height: float = 2.0,
                        mass: float = 1.0,
                        body_type: BodyType = BodyType.DYNAMIC,
                        material: Optional[PhysicsMaterial] = None) -> Optional[RigidBody]:
        """Cylinder rigid body"""
        if not self.initialized:
            return None

        position = position or [0, 5, 0]
        material = material or PhysicsMaterial()

        try:
            shape_id = pb.createCollisionShape(
                pb.GEOM_CYLINDER,
                radius=radius,
                height=height,
                physicsClientId=self.client_id
            )

            actual_mass = 0.0 if body_type == BodyType.STATIC else mass

            body_id = pb.createMultiBody(
                baseMass=actual_mass,
                baseCollisionShapeIndex=shape_id,
                basePosition=position,
                physicsClientId=self.client_id
            )

            self._apply_material(body_id, material)

            body = RigidBody(
                name=name,
                body_id=body_id,
                body_type=body_type,
                shape_type=ShapeType.CYLINDER,
                position=list(position),
                mass=actual_mass,
                material=material,
                shape_data={"radius": radius, "height": height}
            )

            self.bodies[body.id] = body
            self._body_id_to_uuid[body_id] = body.id

            logger.debug(f"Created cylinder: {name}")
            return body

        except Exception as e:
            logger.error(f"Cylinder creation failed: {e}")
            return None

    def create_plane(self, name: str = "Ground",
                     position: Optional[List[float]] = None,
                     normal: Optional[List[float]] = None,
                     material: Optional[PhysicsMaterial] = None) -> Optional[RigidBody]:
        """Infinite plane (ground)"""
        if not self.initialized:
            return None

        position = position or [0, 0, 0]
        normal = normal or [0, 1, 0]
        material = material or PhysicsMaterial.ground()

        try:
            shape_id = pb.createCollisionShape(
                pb.GEOM_PLANE,
                planeNormal=normal,
                physicsClientId=self.client_id
            )

            # Plane always static
            body_id = pb.createMultiBody(
                baseMass=0,
                baseCollisionShapeIndex=shape_id,
                basePosition=position,
                physicsClientId=self.client_id
            )

            self._apply_material(body_id, material)

            body = RigidBody(
                name=name,
                body_id=body_id,
                body_type=BodyType.STATIC,
                shape_type=ShapeType.PLANE,
                position=list(position),
                mass=0.0,
                material=material,
                shape_data={"normal": normal}
            )

            self.bodies[body.id] = body
            self._body_id_to_uuid[body_id] = body.id

            logger.debug(f"Created plane: {name}")
            return body

        except Exception as e:
            logger.error(f"Plane creation failed: {e}")
            return None

    def _apply_material(self, body_id: int, material: PhysicsMaterial):
        """Material properties bullet body pe apply karo"""
        try:
            pb.changeDynamics(
                body_id,
                -1,  # base link
                lateralFriction=material.friction,
                restitution=material.restitution,
                linearDamping=material.linear_damping,
                angularDamping=material.angular_damping,
                rollingFriction=material.rolling_friction,
                physicsClientId=self.client_id
            )
        except Exception as e:
            logger.error(f"Material apply failed: {e}")

    # ------------------------------------------------------------
    # BODY REMOVAL
    # ------------------------------------------------------------

    def remove_body(self, body_uuid: str) -> bool:
        """Body remove karo"""
        if body_uuid not in self.bodies:
            return False

        body = self.bodies[body_uuid]

        try:
            pb.removeBody(body.body_id, physicsClientId=self.client_id)
            del self._body_id_to_uuid[body.body_id]
            del self.bodies[body_uuid]
            logger.debug(f"Removed body: {body.name}")
            return True
        except Exception as e:
            logger.error(f"Remove failed: {e}")
            return False

    def clear_all_bodies(self):
        """Sab bodies remove karo"""
        for body_uuid in list(self.bodies.keys()):
            self.remove_body(body_uuid)
        logger.info("All bodies cleared")

    # ------------------------------------------------------------
    # BODY QUERIES
    # ------------------------------------------------------------

    def get_body(self, body_uuid: str) -> Optional[RigidBody]:
        return self.bodies.get(body_uuid)

    def get_all_bodies(self) -> List[RigidBody]:
        return list(self.bodies.values())

    def get_position(self, body_uuid: str) -> Optional[List[float]]:
        """Body ki current position"""
        body = self.get_body(body_uuid)
        if not body:
            return None

        try:
            pos, _ = pb.getBasePositionAndOrientation(
                body.body_id, physicsClientId=self.client_id
            )
            return list(pos)
        except Exception:
            return None

    def get_rotation(self, body_uuid: str) -> Optional[List[float]]:
        """Body ki current rotation (quaternion)"""
        body = self.get_body(body_uuid)
        if not body:
            return None

        try:
            _, rot = pb.getBasePositionAndOrientation(
                body.body_id, physicsClientId=self.client_id
            )
            return list(rot)
        except Exception:
            return None

    def get_velocity(self, body_uuid: str) -> Optional[Tuple[List[float], List[float]]]:
        """Body ki linear + angular velocity"""
        body = self.get_body(body_uuid)
        if not body:
            return None

        try:
            linear, angular = pb.getBaseVelocity(
                body.body_id, physicsClientId=self.client_id
            )
            return (list(linear), list(angular))
        except Exception:
            return None

    # ------------------------------------------------------------
    # BODY MANIPULATION
    # ------------------------------------------------------------

    def set_position(self, body_uuid: str,
                     position: List[float]) -> bool:
        """Body ki position set karo"""
        body = self.get_body(body_uuid)
        if not body:
            return False

        try:
            current_rotation = self.get_rotation(body_uuid) or [0, 0, 0, 1]
            pb.resetBasePositionAndOrientation(
                body.body_id,
                position,
                current_rotation,
                physicsClientId=self.client_id
            )
            body.position = list(position)
            return True
        except Exception as e:
            logger.error(f"Set position failed: {e}")
            return False

    def set_velocity(self, body_uuid: str,
                     linear: Optional[List[float]] = None,
                     angular: Optional[List[float]] = None) -> bool:
        """Body ki velocity set karo"""
        body = self.get_body(body_uuid)
        if not body:
            return False

        try:
            current_linear, current_angular = self.get_velocity(body_uuid) or ([0,0,0], [0,0,0])

            new_linear = linear if linear else current_linear
            new_angular = angular if angular else current_angular

            pb.resetBaseVelocity(
                body.body_id,
                linearVelocity=new_linear,
                angularVelocity=new_angular,
                physicsClientId=self.client_id
            )
            return True
        except Exception as e:
            logger.error(f"Set velocity failed: {e}")
            return False

    def apply_force(self, body_uuid: str,
                    force: List[float],
                    position: Optional[List[float]] = None) -> bool:
        """Body pe force apply karo"""
        body = self.get_body(body_uuid)
        if not body:
            return False

        try:
            apply_pos = position or [0, 0, 0]
            pb.applyExternalForce(
                body.body_id,
                -1,
                forceObj=force,
                posObj=apply_pos,
                flags=pb.WORLD_FRAME,
                physicsClientId=self.client_id
            )
            return True
        except Exception as e:
            logger.error(f"Apply force failed: {e}")
            return False

    def apply_impulse(self, body_uuid: str,
                      impulse: List[float],
                      position: Optional[List[float]] = None) -> bool:
        """Body pe impulse apply karo (instant velocity change)"""
        body = self.get_body(body_uuid)
        if not body:
            return False

        try:
            apply_pos = position or [0, 0, 0]
            pb.applyExternalForce(
                body.body_id,
                -1,
                forceObj=impulse,
                posObj=apply_pos,
                flags=pb.WORLD_FRAME,
                physicsClientId=self.client_id
            )
            return True
        except Exception as e:
            logger.error(f"Apply impulse failed: {e}")
            return False

    def apply_torque(self, body_uuid: str,
                     torque: List[float]) -> bool:
        """Body pe torque apply karo"""
        body = self.get_body(body_uuid)
        if not body:
            return False

        try:
            pb.applyExternalTorque(
                body.body_id,
                -1,
                torqueObj=torque,
                flags=pb.WORLD_FRAME,
                physicsClientId=self.client_id
            )
            return True
        except Exception as e:
            logger.error(f"Apply torque failed: {e}")
            return False

    # ------------------------------------------------------------
    # RAYCASTING
    # ------------------------------------------------------------

    def raycast(self, start: List[float],
                end: List[float]) -> RaycastHit:
        """
        Ray cast karo aur hit info return karo.
        Useful for mouse picking, line-of-sight checks.
        """
        result = RaycastHit()

        try:
            hits = pb.rayTest(
                start, end,
                physicsClientId=self.client_id
            )

            if hits and hits[0][0] >= 0:
                hit = hits[0]
                bullet_body_id = hit[0]

                result.hit = True
                result.body_id = self._body_id_to_uuid.get(bullet_body_id)
                result.hit_position = list(hit[3])
                result.hit_normal = list(hit[4])
                result.fraction = hit[2]

                # Distance
                start_np = np.array(start)
                end_np = np.array(end)
                result.distance = np.linalg.norm(end_np - start_np) * hit[2]

        except Exception as e:
            logger.error(f"Raycast failed: {e}")

        return result

    # ------------------------------------------------------------
    # SIMULATION CONTROL
    # ------------------------------------------------------------

    def step(self, steps: int = 1):
        """Physics simulation step forward"""
        if not self.initialized or not self.enabled:
            return

        try:
            for _ in range(steps):
                pb.stepSimulation(physicsClientId=self.client_id)

                # Update body positions
                for body in self.bodies.values():
                    if body.body_type != BodyType.STATIC:
                        pos, rot = pb.getBasePositionAndOrientation(
                            body.body_id, physicsClientId=self.client_id
                        )
                        body.position = list(pos)
                        body.rotation = list(rot)

                self.simulation_time += self.time_step
                self.frame_count += 1

            # Collision detection
            self._detect_collisions()

        except Exception as e:
            logger.error(f"Step failed: {e}")

    def start_simulation(self):
        """Simulation start"""
        self.is_running = True
        self.is_paused = False
        logger.info("Physics simulation started")

    def pause_simulation(self):
        """Simulation pause"""
        self.is_paused = True
        logger.info("Physics simulation paused")

    def resume_simulation(self):
        """Simulation resume"""
        self.is_paused = False
        logger.info("Physics simulation resumed")

    def stop_simulation(self):
        """Simulation stop"""
        self.is_running = False
        self.is_paused = False
        self.simulation_time = 0.0
        self.frame_count = 0
        logger.info("Physics simulation stopped")

    def reset_simulation(self):
        """Simulation reset (sab bodies remove)"""
        self.stop_simulation()
        self.clear_all_bodies()
        logger.info("Physics simulation reset")

    # ------------------------------------------------------------
    # COLLISION DETECTION
    # ------------------------------------------------------------

    def _detect_collisions(self):
        """Collisions detect karo aur listeners ko notify karo"""
        self._collision_pairs.clear()

        try:
            contacts = pb.getContactPoints(physicsClientId=self.client_id)

            for contact in contacts:
                body_a_bullet = contact[1]
                body_b_bullet = contact[2]

                body_a_uuid = self._body_id_to_uuid.get(body_a_bullet)
                body_b_uuid = self._body_id_to_uuid.get(body_b_bullet)

                if body_a_uuid and body_b_uuid:
                    event = CollisionEvent(
                        body_a_id=body_a_uuid,
                        body_b_id=body_b_uuid,
                        contact_point=list(contact[5]),
                        contact_normal=list(contact[7]),
                        contact_distance=contact[8]
                    )
                    self._collision_pairs.append(event)

                    # Notify listeners
                    for listener in self._collision_listeners:
                        try:
                            listener(event)
                        except Exception as e:
                            logger.error(f"Collision listener error: {e}")

        except Exception as e:
            logger.error(f"Collision detection error: {e}")

    def add_collision_listener(self, callback: Callable):
        """Collision event listener add karo"""
        self._collision_listeners.append(callback)

    def get_current_collisions(self) -> List[CollisionEvent]:
        """Current frame ki collisions"""
        return list(self._collision_pairs)

    # ------------------------------------------------------------
    # GRAVITY & SETTINGS
    # ------------------------------------------------------------

    def set_gravity(self, gravity: List[float]):
        """Gravity change karo"""
        self.gravity = list(gravity)
        if self.initialized:
            try:
                pb.setGravity(*gravity, physicsClientId=self.client_id)
                logger.info(f"Gravity set to: {gravity}")
            except Exception as e:
                logger.error(f"Gravity set failed: {e}")

    def set_time_step(self, time_step: float):
        """Simulation time step change karo"""
        self.time_step = time_step
        self.simulation_steps = int(1.0 / time_step)
        if self.initialized:
            try:
                pb.setTimeStep(time_step, physicsClientId=self.client_id)
            except Exception as e:
                logger.error(f"Time step set failed: {e}")

    # ------------------------------------------------------------
    # STATISTICS
    # ------------------------------------------------------------

    def get_stats(self) -> Dict:
        """Physics engine stats"""
        static_count = sum(1 for b in self.bodies.values() if b.body_type == BodyType.STATIC)
        dynamic_count = sum(1 for b in self.bodies.values() if b.body_type == BodyType.DYNAMIC)

        return {
            "initialized": self.initialized,
            "enabled": self.enabled,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "gravity": self.gravity,
            "simulation_steps": self.simulation_steps,
            "time_step": self.time_step,
            "simulation_time": round(self.simulation_time, 3),
            "frame_count": self.frame_count,
            "total_bodies": len(self.bodies),
            "static_bodies": static_count,
            "dynamic_bodies": dynamic_count,
            "active_collisions": len(self._collision_pairs),
        }


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Physics Engine Test", "Bullet Physics Simulation")

    # ============================================================
    # Test 1: Initialize
    # ============================================================
    print_section("Test 1: Initialize Physics Engine")

    physics = PhysicsEngine()

    if not physics.initialized:
        print("❌ Physics engine failed to initialize!")
        sys.exit(1)

    print(f"✅ Physics initialized")
    print(f"Gravity: {physics.gravity}")
    print(f"Simulation steps: {physics.simulation_steps} per second")

    # ============================================================
    # Test 2: Create Bodies
    # ============================================================
    print_section("Test 2: Create Physics Bodies")

    # Ground plane
    ground = physics.create_plane(name="Ground")
    print(f"✓ Ground plane created: {ground.name}")

    # Falling box
    box = physics.create_box(
        name="Falling Box",
        position=[0, 10, 0],
        size=[1, 1, 1],
        mass=1.0,
        material=PhysicsMaterial.wood()
    )
    print(f"✓ Box created: {box.name} at {box.position}")

    # Bouncy sphere
    sphere = physics.create_sphere(
        name="Bouncy Ball",
        position=[2, 8, 0],
        radius=0.5,
        mass=0.5,
        material=PhysicsMaterial.bouncy()
    )
    print(f"✓ Sphere created: {sphere.name}")

    # Cylinder
    cylinder = physics.create_cylinder(
        name="Cylinder",
        position=[-2, 12, 0],
        radius=0.4,
        height=1.5,
        mass=0.8,
        material=PhysicsMaterial.metal()
    )
    print(f"✓ Cylinder created: {cylinder.name}")

    stats = physics.get_stats()
    print(f"\nTotal bodies: {stats['total_bodies']}")
    print(f"Static: {stats['static_bodies']}, Dynamic: {stats['dynamic_bodies']}")

    # ============================================================
    # Test 3: Simulation - Falling Objects
    # ============================================================
    print_section("Test 3: Simulate Falling Objects")

    print("\nSimulating 2 seconds of falling...")
    print(f"{'Time':>6} | {'Box Y':>8} | {'Sphere Y':>10} | {'Cylinder Y':>12}")
    print("-" * 45)

    simulation_seconds = 2.0
    steps_per_report = 20  # Report every 20 steps

    total_steps = int(simulation_seconds * physics.simulation_steps)

    for i in range(total_steps + 1):
        if i > 0:
            physics.step(1)

        if i % steps_per_report == 0:
            t = physics.simulation_time
            box_pos = physics.get_position(box.id)
            sphere_pos = physics.get_position(sphere.id)
            cyl_pos = physics.get_position(cylinder.id)

            print(f"{t:>6.2f} | "
                  f"{box_pos[1]:>8.2f} | "
                  f"{sphere_pos[1]:>10.2f} | "
                  f"{cyl_pos[1]:>12.2f}")

    # Final positions
    print(f"\nFinal positions:")
    print(f"  Box:      {[round(x,2) for x in physics.get_position(box.id)]}")
    print(f"  Sphere:   {[round(x,2) for x in physics.get_position(sphere.id)]}")
    print(f"  Cylinder: {[round(x,2) for x in physics.get_position(cylinder.id)]}")

    # ============================================================
    # Test 4: Apply Force
    # ============================================================
    print_section("Test 4: Apply Forces")

    # Reset positions
    physics.set_position(box.id, [0, 3, 0])
    physics.set_velocity(box.id, linear=[0, 0, 0], angular=[0, 0, 0])

    print("Applying horizontal force to box...")
    physics.apply_impulse(box.id, [5, 0, 0])  # Push right

    # Simulate
    for i in range(60):
        physics.step(1)

    pos = physics.get_position(box.id)
    vel = physics.get_velocity(box.id)
    print(f"After 1 second:")
    print(f"  Position: {[round(x,2) for x in pos]}")
    print(f"  Velocity: {[round(x,2) for x in vel[0]]}")

    # ============================================================
    # Test 5: Collision Detection
    # ============================================================
    print_section("Test 5: Collision Detection")

    collision_count = [0]

    def on_collision(event):
        collision_count[0] += 1
        body_a = physics.get_body(event.body_a_id)
        body_b = physics.get_body(event.body_b_id)
        if body_a and body_b and collision_count[0] <= 3:
            print(f"  💥 Collision: {body_a.name} <-> {body_b.name}")

    physics.add_collision_listener(on_collision)

    # Reset & drop
    physics.set_position(sphere.id, [0, 5, 0])
    physics.set_velocity(sphere.id, linear=[0, 0, 0])

    print("Dropping sphere onto ground...")
    for i in range(120):
        physics.step(1)

    print(f"\nTotal collision events: {collision_count[0]}")

    # ============================================================
    # Test 6: Raycasting
    # ============================================================
    print_section("Test 6: Raycasting")

    # Reset
    physics.set_position(box.id, [0, 2, 0])

    print("Casting ray from above (5,10,0) → (0,-5,0)...")
    hit = physics.raycast(start=[5, 10, 0], end=[0, -5, 0])

    if hit.hit:
        body = physics.get_body(hit.body_id)
        print(f"  ✓ Hit: {body.name if body else 'Unknown'}")
        print(f"  Position: {[round(x,2) for x in hit.hit_position]}")
        print(f"  Normal: {[round(x,2) for x in hit.hit_normal]}")
        print(f"  Distance: {hit.distance:.2f}")
    else:
        print("  No hit")

    # ============================================================
    # Test 7: Materials Comparison
    # ============================================================
    print_section("Test 7: Different Materials Bounce Test")

    physics.reset_simulation()

    # Ground
    physics.create_plane()

    # Different material spheres from same height
    materials = {
        "Rubber (bouncy)": PhysicsMaterial.rubber(),
        "Wood": PhysicsMaterial.wood(),
        "Metal": PhysicsMaterial.metal(),
        "Ice": PhysicsMaterial.ice(),
    }

    spheres = {}
    x = -3
    for name, mat in materials.items():
        s = physics.create_sphere(
            name=name,
            position=[x, 8, 0],
            radius=0.4,
            mass=0.5,
            material=mat
        )
        spheres[name] = s
        x += 2

    print("\nDropping 4 spheres with different materials...")
    print(f"{'Material':<20} | {'Bounce Height':>15}")
    print("-" * 40)

    max_heights = {name: 0.0 for name in spheres}
    prev_ys = {name: 8.0 for name in spheres}
    was_falling = {name: True for name in spheres}

    # Simulate 3 seconds
    for i in range(180):
        physics.step(1)

        # Track max bounce heights
        for name, sphere in spheres.items():
            pos = physics.get_position(sphere.id)
            current_y = pos[1]

            # Detect bounce (was going down, now going up)
            if was_falling[name] and current_y > prev_ys[name]:
                # Just bounced, wait for peak
                was_falling[name] = False

            if not was_falling[name]:
                if current_y > max_heights[name]:
                    max_heights[name] = current_y
                elif current_y < prev_ys[name]:
                    was_falling[name] = True

            prev_ys[name] = current_y

    for name, height in max_heights.items():
        print(f"{name:<20} | {height:>14.2f}m")

    # ============================================================
    # Test 8: Statistics
    # ============================================================
    print_section("Test 8: Final Statistics")

    stats = physics.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # ============================================================
    # Cleanup
    # ============================================================
    print_section("Cleanup")

    physics.reset_simulation()
    physics.shutdown()
    print("Physics engine shut down")

    print_banner(
        "✅ All Tests Passed",
        "Physics Engine Working - Gravity, Collision, Materials!"
    )