# ============================================================
# 3D ANIMATION STUDIO - 3D Render Engine
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

import time
import math
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import numpy as np

try:
    import moderngl
    MODERNGL_AVAILABLE = True
except ImportError:
    MODERNGL_AVAILABLE = False
    moderngl = None

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from src.utils import (
    get_logger, get_config, ensure_dir, generate_short_id,
    clamp, degrees_to_radians, rgb_to_normalized
)

logger = get_logger("RenderEngine")


# ============================================================
# RENDER QUALITY PRESETS
# ============================================================

class RenderQuality:
    DRAFT = "draft"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"

    SETTINGS = {
        DRAFT: {
            "resolution_scale": 0.5,
            "samples": 1,
            "shadow_resolution": 512,
            "max_lights": 2,
            "wireframe_option": True,
        },
        MEDIUM: {
            "resolution_scale": 0.75,
            "samples": 2,
            "shadow_resolution": 1024,
            "max_lights": 4,
            "wireframe_option": False,
        },
        HIGH: {
            "resolution_scale": 1.0,
            "samples": 4,
            "shadow_resolution": 2048,
            "max_lights": 8,
            "wireframe_option": False,
        },
        ULTRA: {
            "resolution_scale": 1.5,
            "samples": 8,
            "shadow_resolution": 4096,
            "max_lights": 16,
            "wireframe_option": False,
        },
    }


# ============================================================
# SHADER SOURCES (GLSL)
# ============================================================

BASIC_VERTEX_SHADER = """
#version 330 core

in vec3 in_position;
in vec3 in_normal;
in vec2 in_texcoord;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

out vec3 v_position;
out vec3 v_normal;
out vec2 v_texcoord;

void main() {
    vec4 world_pos = model * vec4(in_position, 1.0);
    v_position = world_pos.xyz;
    v_normal = mat3(transpose(inverse(model))) * in_normal;
    v_texcoord = in_texcoord;

    gl_Position = projection * view * world_pos;
}
"""

BASIC_FRAGMENT_SHADER = """
#version 330 core

in vec3 v_position;
in vec3 v_normal;
in vec2 v_texcoord;

uniform vec3 light_direction;
uniform vec3 light_color;
uniform float ambient_intensity;
uniform vec3 ambient_color;
uniform vec3 object_color;
uniform vec3 camera_position;
uniform float shininess;

out vec4 frag_color;

void main() {
    vec3 normal = normalize(v_normal);

    vec3 ambient = ambient_intensity * ambient_color;

    vec3 light_dir = normalize(-light_direction);
    float diff = max(dot(normal, light_dir), 0.0);
    vec3 diffuse = diff * light_color;

    vec3 view_dir = normalize(camera_position - v_position);
    vec3 reflect_dir = reflect(-light_dir, normal);
    float spec = pow(max(dot(view_dir, reflect_dir), 0.0), shininess);
    vec3 specular = spec * light_color * 0.5;

    vec3 uv_tint = vec3(v_texcoord.x * 0.001, v_texcoord.y * 0.001, 0.0);

    vec3 result = (ambient + diffuse + specular) * object_color + uv_tint;
    frag_color = vec4(result, 1.0);
}
"""

WIREFRAME_FRAGMENT_SHADER = """
#version 330 core

in vec3 v_position;
in vec3 v_normal;
in vec2 v_texcoord;

uniform vec3 wire_color;

out vec4 frag_color;

void main() {
    vec3 uv_tint = vec3(v_texcoord.x * 0.001, v_texcoord.y * 0.001, 0.0);
    frag_color = vec4(wire_color + uv_tint, 1.0);
}
"""


# ============================================================
# CAMERA CLASS
# ============================================================

@dataclass
class Camera:
    position: List[float] = field(default_factory=lambda: [0.0, 2.0, 5.0])
    target: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    up: List[float] = field(default_factory=lambda: [0.0, 1.0, 0.0])

    fov: float = 60.0
    aspect_ratio: float = 16.0 / 9.0
    near_clip: float = 0.1
    far_clip: float = 1000.0

    is_orthographic: bool = False
    ortho_size: float = 5.0

    def get_view_matrix(self) -> np.ndarray:
        eye = np.array(self.position, dtype=np.float32)
        target = np.array(self.target, dtype=np.float32)
        up = np.array(self.up, dtype=np.float32)

        forward = target - eye
        forward_norm = np.linalg.norm(forward)
        if forward_norm > 0:
            forward = forward / forward_norm

        right = np.cross(forward, up)
        right_norm = np.linalg.norm(right)
        if right_norm > 0:
            right = right / right_norm

        up_new = np.cross(right, forward)

        view = np.eye(4, dtype=np.float32)
        view[0, :3] = right
        view[1, :3] = up_new
        view[2, :3] = -forward
        view[0, 3] = -np.dot(right, eye)
        view[1, 3] = -np.dot(up_new, eye)
        view[2, 3] = np.dot(forward, eye)

        return view

    def get_projection_matrix(self) -> np.ndarray:
        if self.is_orthographic:
            return self._get_ortho_matrix()
        return self._get_perspective_matrix()

    def _get_perspective_matrix(self) -> np.ndarray:
        f = 1.0 / math.tan(degrees_to_radians(self.fov) / 2.0)
        aspect = self.aspect_ratio
        near = self.near_clip
        far = self.far_clip

        proj = np.zeros((4, 4), dtype=np.float32)
        proj[0, 0] = f / aspect
        proj[1, 1] = f
        proj[2, 2] = (far + near) / (near - far)
        proj[2, 3] = (2.0 * far * near) / (near - far)
        proj[3, 2] = -1.0

        return proj

    def _get_ortho_matrix(self) -> np.ndarray:
        size = self.ortho_size
        aspect = self.aspect_ratio
        near = self.near_clip
        far = self.far_clip

        left = -size * aspect
        right = size * aspect
        bottom = -size
        top = size

        proj = np.zeros((4, 4), dtype=np.float32)
        proj[0, 0] = 2.0 / (right - left)
        proj[1, 1] = 2.0 / (top - bottom)
        proj[2, 2] = -2.0 / (far - near)
        proj[0, 3] = -(right + left) / (right - left)
        proj[1, 3] = -(top + bottom) / (top - bottom)
        proj[2, 3] = -(far + near) / (far - near)
        proj[3, 3] = 1.0

        return proj

    def move(self, delta: List[float]):
        for i in range(3):
            self.position[i] += delta[i]
            self.target[i] += delta[i]

    def orbit(self, angle_x: float, angle_y: float, radius: Optional[float] = None):
        eye = np.array(self.position, dtype=np.float32)
        target = np.array(self.target, dtype=np.float32)

        direction = eye - target
        r = np.linalg.norm(direction) if radius is None else radius

        theta = math.atan2(direction[0], direction[2])
        phi = math.acos(clamp(direction[1] / r, -1.0, 1.0))

        theta += degrees_to_radians(angle_x)
        phi += degrees_to_radians(angle_y)
        phi = clamp(phi, 0.1, math.pi - 0.1)

        self.position[0] = target[0] + r * math.sin(phi) * math.sin(theta)
        self.position[1] = target[1] + r * math.cos(phi)
        self.position[2] = target[2] + r * math.sin(phi) * math.cos(theta)


# ============================================================
# LIGHT CLASSES
# ============================================================

@dataclass
class DirectionalLight:
    direction: List[float] = field(default_factory=lambda: [-0.5, -1.0, -0.3])
    color: List[float] = field(default_factory=lambda: [1.0, 1.0, 0.9])
    intensity: float = 1.0

    def get_normalized_direction(self) -> np.ndarray:
        d = np.array(self.direction, dtype=np.float32)
        norm = np.linalg.norm(d)
        return d / norm if norm > 0 else d


@dataclass
class AmbientLight:
    color: List[float] = field(default_factory=lambda: [0.4, 0.4, 0.5])
    intensity: float = 0.3


# ============================================================
# MESH CLASS
# ============================================================

class Mesh:
    def __init__(self, name: str = "Mesh"):
        self.id = generate_short_id()
        self.name = name

        self.vertices: Optional[np.ndarray] = None
        self.indices: Optional[np.ndarray] = None

        self.position = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.rotation = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.scale = np.array([1.0, 1.0, 1.0], dtype=np.float32)

        self.color = [0.8, 0.8, 0.8]
        self.shininess = 32.0

        self._vao = None
        self._vbo = None
        self._ibo = None
        self._uploaded = False

        self.visible = True

    def set_vertices(self, vertices: np.ndarray, indices: Optional[np.ndarray] = None):
        self.vertices = vertices.astype(np.float32)
        if indices is not None:
            self.indices = indices.astype(np.uint32)
        self._uploaded = False

    def get_model_matrix(self) -> np.ndarray:
        translation = np.eye(4, dtype=np.float32)
        translation[0, 3] = self.position[0]
        translation[1, 3] = self.position[1]
        translation[2, 3] = self.position[2]

        rx = degrees_to_radians(self.rotation[0])
        ry = degrees_to_radians(self.rotation[1])
        rz = degrees_to_radians(self.rotation[2])

        rot_x = np.array([
            [1, 0, 0, 0],
            [0, math.cos(rx), -math.sin(rx), 0],
            [0, math.sin(rx), math.cos(rx), 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        rot_y = np.array([
            [math.cos(ry), 0, math.sin(ry), 0],
            [0, 1, 0, 0],
            [-math.sin(ry), 0, math.cos(ry), 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        rot_z = np.array([
            [math.cos(rz), -math.sin(rz), 0, 0],
            [math.sin(rz), math.cos(rz), 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        rotation = rot_z @ rot_y @ rot_x

        scale = np.eye(4, dtype=np.float32)
        scale[0, 0] = self.scale[0]
        scale[1, 1] = self.scale[1]
        scale[2, 2] = self.scale[2]

        return translation @ rotation @ scale


# ============================================================
# PRIMITIVE FACTORY
# ============================================================

class PrimitiveFactory:

    @staticmethod
    def create_cube(size: float = 1.0) -> Mesh:
        s = size / 2.0

        vertices = np.array([
            -s, -s,  s, 0, 0, 1, 0, 0,
             s, -s,  s, 0, 0, 1, 1, 0,
             s,  s,  s, 0, 0, 1, 1, 1,
            -s,  s,  s, 0, 0, 1, 0, 1,
             s, -s, -s, 0, 0, -1, 0, 0,
            -s, -s, -s, 0, 0, -1, 1, 0,
            -s,  s, -s, 0, 0, -1, 1, 1,
             s,  s, -s, 0, 0, -1, 0, 1,
            -s,  s,  s, 0, 1, 0, 0, 0,
             s,  s,  s, 0, 1, 0, 1, 0,
             s,  s, -s, 0, 1, 0, 1, 1,
            -s,  s, -s, 0, 1, 0, 0, 1,
            -s, -s, -s, 0, -1, 0, 0, 0,
             s, -s, -s, 0, -1, 0, 1, 0,
             s, -s,  s, 0, -1, 0, 1, 1,
            -s, -s,  s, 0, -1, 0, 0, 1,
             s, -s,  s, 1, 0, 0, 0, 0,
             s, -s, -s, 1, 0, 0, 1, 0,
             s,  s, -s, 1, 0, 0, 1, 1,
             s,  s,  s, 1, 0, 0, 0, 1,
            -s, -s, -s, -1, 0, 0, 0, 0,
            -s, -s,  s, -1, 0, 0, 1, 0,
            -s,  s,  s, -1, 0, 0, 1, 1,
            -s,  s, -s, -1, 0, 0, 0, 1,
        ], dtype=np.float32)

        indices = np.array([
            0, 1, 2,   2, 3, 0,
            4, 5, 6,   6, 7, 4,
            8, 9, 10,  10, 11, 8,
            12, 13, 14, 14, 15, 12,
            16, 17, 18, 18, 19, 16,
            20, 21, 22, 22, 23, 20,
        ], dtype=np.uint32)

        mesh = Mesh(name="Cube")
        mesh.set_vertices(vertices, indices)
        return mesh

    @staticmethod
    def create_plane(size: float = 5.0) -> Mesh:
        s = size / 2.0

        vertices = np.array([
            -s, 0, -s, 0, 1, 0, 0, 0,
             s, 0, -s, 0, 1, 0, 1, 0,
             s, 0,  s, 0, 1, 0, 1, 1,
            -s, 0,  s, 0, 1, 0, 0, 1,
        ], dtype=np.float32)

        indices = np.array([
            0, 2, 1, 0, 3, 2
        ], dtype=np.uint32)

        mesh = Mesh(name="Plane")
        mesh.set_vertices(vertices, indices)
        return mesh

    @staticmethod
    def create_sphere(radius: float = 1.0,
                     segments: int = 32,
                     rings: int = 16) -> Mesh:
        vertices = []
        indices = []

        for ring in range(rings + 1):
            theta = ring * math.pi / rings
            sin_theta = math.sin(theta)
            cos_theta = math.cos(theta)

            for seg in range(segments + 1):
                phi = seg * 2.0 * math.pi / segments
                sin_phi = math.sin(phi)
                cos_phi = math.cos(phi)

                x = cos_phi * sin_theta
                y = cos_theta
                z = sin_phi * sin_theta

                u = seg / segments
                v = ring / rings

                vertices.extend([
                    radius * x, radius * y, radius * z,
                    x, y, z,
                    u, v
                ])

        for ring in range(rings):
            for seg in range(segments):
                first = ring * (segments + 1) + seg
                second = first + segments + 1

                indices.extend([first, second, first + 1])
                indices.extend([second, second + 1, first + 1])

        vertices_arr = np.array(vertices, dtype=np.float32)
        indices_arr = np.array(indices, dtype=np.uint32)

        mesh = Mesh(name="Sphere")
        mesh.set_vertices(vertices_arr, indices_arr)
        return mesh


# ============================================================
# RENDER STATISTICS
# ============================================================

@dataclass
class RenderStats:
    fps: float = 0.0
    frame_time_ms: float = 0.0
    draw_calls: int = 0
    triangles_rendered: int = 0
    meshes_rendered: int = 0
    last_frame_time: float = 0.0
    frames_rendered: int = 0

    def reset_frame(self):
        self.draw_calls = 0
        self.triangles_rendered = 0
        self.meshes_rendered = 0


# ============================================================
# MAIN RENDER ENGINE
# ============================================================

class RenderEngine:

    def __init__(self, config: Optional[Dict] = None,
                 width: int = 1280, height: int = 720,
                 headless: bool = True):
        if config is None:
            try:
                self.config = get_config().get_all()
            except Exception:
                self.config = {}
        else:
            self.config = config

        self.width = width
        self.height = height
        self.headless = headless

        render_config = self.config.get("rendering", {})
        self.quality = render_config.get("default_quality", RenderQuality.DRAFT)
        self.quality_settings = RenderQuality.SETTINGS.get(
            self.quality, RenderQuality.SETTINGS[RenderQuality.DRAFT]
        )

        self.ctx: Optional[Any] = None
        self.initialized = False

        self._framebuffer = None
        self._color_texture = None
        self._depth_texture = None

        self._programs: Dict[str, Any] = {}
        self._active_program = None

        self.meshes: List[Mesh] = []
        self.camera = Camera(aspect_ratio=width / height)
        self.directional_light = DirectionalLight()
        self.ambient_light = AmbientLight()

        self.background_color = [0.12, 0.12, 0.16]

        self.stats = RenderStats()
        self._last_frame_time = time.time()

        logger.info(f"RenderEngine created: {width}x{height} @ {self.quality}")

        self._initialize()

    def _initialize(self) -> bool:
        if not MODERNGL_AVAILABLE:
            logger.error("moderngl not installed!")
            return False

        try:
            if self.headless:
                self.ctx = moderngl.create_standalone_context()
                logger.info("OpenGL standalone context created")
            else:
                self.ctx = moderngl.create_context()
                logger.info("OpenGL context attached")

            info = self.ctx.info
            logger.info(f"GPU: {info.get('GL_RENDERER', 'Unknown')}")
            logger.info(f"OpenGL: {info.get('GL_VERSION', 'Unknown')}")

            self.ctx.enable(moderngl.DEPTH_TEST)
            self.ctx.enable(moderngl.CULL_FACE)

            self._create_framebuffer()
            self._compile_shaders()

            self.initialized = True
            logger.info("RenderEngine initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Render engine init failed: {e}")
            return False

    def _create_framebuffer(self):
        try:
            scale = self.quality_settings["resolution_scale"]
            fb_width = int(self.width * scale)
            fb_height = int(self.height * scale)

            self._color_texture = self.ctx.texture(
                (fb_width, fb_height), 4
            )
            self._color_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)

            self._depth_texture = self.ctx.depth_texture(
                (fb_width, fb_height)
            )

            self._framebuffer = self.ctx.framebuffer(
                color_attachments=[self._color_texture],
                depth_attachment=self._depth_texture
            )

            logger.debug(f"Framebuffer created: {fb_width}x{fb_height}")

        except Exception as e:
            logger.error(f"Framebuffer creation failed: {e}")

    def _compile_shaders(self):
        try:
            self._programs["basic"] = self.ctx.program(
                vertex_shader=BASIC_VERTEX_SHADER,
                fragment_shader=BASIC_FRAGMENT_SHADER
            )
            logger.debug("Basic shader compiled")

            self._programs["wireframe"] = self.ctx.program(
                vertex_shader=BASIC_VERTEX_SHADER,
                fragment_shader=WIREFRAME_FRAGMENT_SHADER
            )
            logger.debug("Wireframe shader compiled")

        except Exception as e:
            logger.error(f"Shader compilation failed: {e}")

    def add_mesh(self, mesh: Mesh) -> bool:
        if not self.initialized:
            return False

        try:
            self._upload_mesh(mesh)
            self.meshes.append(mesh)
            logger.debug(f"Mesh added: {mesh.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add mesh: {e}")
            return False

    def _upload_mesh(self, mesh: Mesh):
        if mesh.vertices is None:
            return

        mesh._vbo = self.ctx.buffer(mesh.vertices.tobytes())

        if mesh.indices is not None:
            mesh._ibo = self.ctx.buffer(mesh.indices.tobytes())

        program = self._programs["basic"]

        # Check which attributes are actually available in program
        available_attrs = []
        for attr in ["in_position", "in_normal", "in_texcoord"]:
            if attr in program:
                available_attrs.append(attr)

        vertex_content = [
            (mesh._vbo, "3f 3f 2f", *available_attrs)
        ]

        if mesh._ibo:
            mesh._vao = self.ctx.vertex_array(
                program, vertex_content, mesh._ibo
            )
        else:
            mesh._vao = self.ctx.vertex_array(program, vertex_content)

        mesh._uploaded = True

    def remove_mesh(self, mesh_id: str) -> bool:
        for i, mesh in enumerate(self.meshes):
            if mesh.id == mesh_id:
                if mesh._vao:
                    mesh._vao.release()
                if mesh._vbo:
                    mesh._vbo.release()
                if mesh._ibo:
                    mesh._ibo.release()
                self.meshes.pop(i)
                logger.debug(f"Mesh removed: {mesh.name}")
                return True
        return False

    def clear_meshes(self):
        for mesh in self.meshes:
            if mesh._vao:
                mesh._vao.release()
            if mesh._vbo:
                mesh._vbo.release()
            if mesh._ibo:
                mesh._ibo.release()
        self.meshes.clear()

    def render_frame(self) -> bool:
        if not self.initialized:
            return False

        frame_start = time.time()
        self.stats.reset_frame()

        try:
            self._framebuffer.use()

            r, g, b = self.background_color
            self._framebuffer.clear(r, g, b, 1.0, depth=1.0)

            view_matrix = self.camera.get_view_matrix()
            proj_matrix = self.camera.get_projection_matrix()

            program = self._programs["basic"]

            program["view"].write(view_matrix.T.tobytes())
            program["projection"].write(proj_matrix.T.tobytes())
            program["camera_position"].value = tuple(self.camera.position)

            light_dir = self.directional_light.get_normalized_direction()
            program["light_direction"].value = tuple(light_dir)
            program["light_color"].value = tuple([
                c * self.directional_light.intensity
                for c in self.directional_light.color
            ])
            program["ambient_intensity"].value = self.ambient_light.intensity
            program["ambient_color"].value = tuple(self.ambient_light.color)

            for mesh in self.meshes:
                if not mesh.visible or mesh._vao is None:
                    continue

                model_matrix = mesh.get_model_matrix()
                program["model"].write(model_matrix.T.tobytes())
                program["object_color"].value = tuple(mesh.color)
                program["shininess"].value = mesh.shininess

                mesh._vao.render()

                self.stats.draw_calls += 1
                self.stats.meshes_rendered += 1
                if mesh.indices is not None:
                    self.stats.triangles_rendered += len(mesh.indices) // 3

            frame_end = time.time()
            self.stats.frame_time_ms = (frame_end - frame_start) * 1000
            self.stats.fps = 1.0 / max(frame_end - self._last_frame_time, 0.001)
            self._last_frame_time = frame_end
            self.stats.frames_rendered += 1
            self.stats.last_frame_time = frame_end

            return True

        except Exception as e:
            logger.error(f"Render error: {e}")
            return False

    def render_to_image(self, output_path: str) -> bool:
        if not self.initialized:
            return False

        if not PIL_AVAILABLE:
            logger.error("PIL not installed!")
            return False

        try:
            if not self.render_frame():
                return False

            data = self._framebuffer.read(components=3)

            fb_size = self._color_texture.size
            img = Image.frombytes("RGB", fb_size, data)

            img = img.transpose(Image.FLIP_TOP_BOTTOM)

            ensure_dir(os.path.dirname(output_path))
            img.save(output_path)

            logger.info(f"Frame saved: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Render to image failed: {e}")
            return False

    def set_quality(self, quality: str):
        if quality not in RenderQuality.SETTINGS:
            logger.warning(f"Unknown quality: {quality}")
            return

        self.quality = quality
        self.quality_settings = RenderQuality.SETTINGS[quality]

        if self.initialized:
            if self._framebuffer:
                self._framebuffer.release()
            if self._color_texture:
                self._color_texture.release()
            if self._depth_texture:
                self._depth_texture.release()
            self._create_framebuffer()

        logger.info(f"Quality changed to: {quality}")

    def resize(self, width: int, height: int):
        self.width = width
        self.height = height
        self.camera.aspect_ratio = width / height

        if self.initialized:
            if self._framebuffer:
                self._framebuffer.release()
            if self._color_texture:
                self._color_texture.release()
            if self._depth_texture:
                self._depth_texture.release()
            self._create_framebuffer()

        logger.info(f"Resized to: {width}x{height}")

    def shutdown(self):
        try:
            self.clear_meshes()

            for program in self._programs.values():
                program.release()
            self._programs.clear()

            if self._framebuffer:
                self._framebuffer.release()
            if self._color_texture:
                self._color_texture.release()
            if self._depth_texture:
                self._depth_texture.release()

            if self.ctx:
                self.ctx.release()

            self.initialized = False
            logger.info("RenderEngine shut down")

        except Exception as e:
            logger.error(f"Shutdown error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "fps": round(self.stats.fps, 2),
            "frame_time_ms": round(self.stats.frame_time_ms, 2),
            "draw_calls": self.stats.draw_calls,
            "triangles": self.stats.triangles_rendered,
            "meshes": self.stats.meshes_rendered,
            "frames_rendered": self.stats.frames_rendered,
            "resolution": f"{self.width}x{self.height}",
            "quality": self.quality,
        }


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Render Engine Test", "3D Graphics with OpenGL")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    print_section("Test 1: Initialize Render Engine")

    engine = RenderEngine(width=1280, height=720, headless=True)

    if not engine.initialized:
        print("❌ Render engine failed to initialize!")
        sys.exit(1)

    print(f"✅ Engine initialized")
    print(f"Resolution: {engine.width}x{engine.height}")
    print(f"Quality: {engine.quality}")

    print_section("Test 2: Create 3D Objects")

    plane = PrimitiveFactory.create_plane(size=10.0)
    plane.color = [0.3, 0.4, 0.3]
    plane.position = np.array([0, -1, 0], dtype=np.float32)
    engine.add_mesh(plane)
    print(f"✓ Plane created (green ground)")

    cube = PrimitiveFactory.create_cube(size=1.5)
    cube.color = [0.8, 0.2, 0.2]
    cube.position = np.array([-2, 0, 0], dtype=np.float32)
    cube.rotation = np.array([0, 30, 0], dtype=np.float32)
    engine.add_mesh(cube)
    print(f"✓ Cube created (red)")

    sphere = PrimitiveFactory.create_sphere(radius=1.0, segments=32, rings=16)
    sphere.color = [0.2, 0.4, 0.9]
    sphere.position = np.array([2, 0, 0], dtype=np.float32)
    sphere.shininess = 128.0
    engine.add_mesh(sphere)
    print(f"✓ Sphere created (blue, shiny)")

    print(f"Total meshes: {len(engine.meshes)}")

    print_section("Test 3: Camera Setup")

    engine.camera.position = [4, 3, 6]
    engine.camera.target = [0, 0, 0]
    engine.camera.fov = 55.0

    print(f"Camera position: {engine.camera.position}")
    print(f"Camera target: {engine.camera.target}")
    print(f"FOV: {engine.camera.fov}°")

    print_section("Test 4: Render Frame")

    success = engine.render_frame()
    print(f"Render success: {success}")

    stats = engine.get_stats()
    print(f"FPS: {stats['fps']}")
    print(f"Frame time: {stats['frame_time_ms']} ms")
    print(f"Draw calls: {stats['draw_calls']}")
    print(f"Triangles: {stats['triangles']}")

    print_section("Test 5: Save Render to PNG")

    output_dir = os.path.join(base_dir, "temp")
    ensure_dir(output_dir)

    output_path = os.path.join(output_dir, "test_render.png")
    success = engine.render_to_image(output_path)

    if success and os.path.exists(output_path):
        from src.utils import get_file_size_readable
        size = get_file_size_readable(output_path)
        print(f"✅ Image saved: {output_path}")
        print(f"File size: {size}")
        print(f"\n👉 Open this file to see your first 3D render:")
        print(f"   {output_path}")

    print_section("Test 6: Multiple Frames (FPS Test)")

    print("Rendering 30 frames...")

    start_time = time.time()
    for i in range(30):
        engine.camera.orbit(angle_x=5, angle_y=0)
        cube.rotation[1] += 5.0
        engine.render_frame()

    elapsed = time.time() - start_time
    avg_fps = 30 / elapsed

    print(f"30 frames in {elapsed:.2f}s")
    print(f"Average FPS: {avg_fps:.1f}")

    print_section("Test 7: Change Quality Setting")

    print(f"Current: {engine.quality}")

    engine.set_quality(RenderQuality.HIGH)
    print(f"Changed to: {engine.quality}")

    hq_path = os.path.join(output_dir, "test_render_high.png")
    engine.render_to_image(hq_path)
    print(f"✅ High-quality render saved: {hq_path}")

    print_section("Test 8: Final Statistics")

    stats = engine.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print_section("Cleanup")

    engine.shutdown()
    print("Engine shut down")

    print_banner(
        "✅ All Tests Passed",
        f"Check rendered images in: {output_dir}"
    )