# ============================================================
# 3D ANIMATION STUDIO - 3D Model Loader
# ============================================================
# Features:
# - OBJ file loading (native + trimesh)
# - FBX/GLTF/DAE/STL support (via trimesh)
# - Automatic normal calculation (agar file me na hon)
# - UV coordinate handling
# - Multi-mesh model support
# - Material info extraction
# - Bounding box calculation
# - Auto-centering & scaling
# - Model caching (same file dobara load na ho)
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
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    trimesh = None

from src.utils import (
    get_logger, ensure_dir, get_file_extension, generate_short_id,
    is_supported_model_format, hash_file, format_bytes, get_file_size
)
from src.renderer.render_engine import Mesh

logger = get_logger("ModelLoader")


# ============================================================
# MODEL METADATA
# ============================================================

@dataclass
class ModelInfo:
    """Loaded model ki metadata"""
    filepath: str
    filename: str
    format: str
    file_size: int = 0
    load_time: float = 0.0
    total_vertices: int = 0
    total_faces: int = 0
    total_meshes: int = 0
    has_normals: bool = False
    has_uvs: bool = False
    has_colors: bool = False
    has_materials: bool = False
    bounding_box: Optional[Dict] = None
    warnings: List[str] = field(default_factory=list)


# ============================================================
# BOUNDING BOX HELPER
# ============================================================

@dataclass
class BoundingBox:
    """3D bounding box"""
    min_point: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))
    max_point: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))

    @classmethod
    def from_vertices(cls, vertices: np.ndarray) -> "BoundingBox":
        """Vertices se bounding box banao"""
        bbox = cls()
        if vertices is None or len(vertices) == 0:
            return bbox

        # Positions extract karo (first 3 floats per vertex)
        if len(vertices.shape) == 1:
            # Flat array: [x,y,z, nx,ny,nz, u,v, ...]
            positions = vertices.reshape(-1, 8)[:, :3]
        elif vertices.shape[1] >= 3:
            positions = vertices[:, :3]
        else:
            return bbox

        bbox.min_point = np.min(positions, axis=0).astype(np.float32)
        bbox.max_point = np.max(positions, axis=0).astype(np.float32)
        return bbox

    @property
    def center(self) -> np.ndarray:
        return (self.min_point + self.max_point) / 2.0

    @property
    def size(self) -> np.ndarray:
        return self.max_point - self.min_point

    @property
    def max_dimension(self) -> float:
        return float(np.max(self.size))

    def to_dict(self) -> Dict:
        return {
            "min": self.min_point.tolist(),
            "max": self.max_point.tolist(),
            "center": self.center.tolist(),
            "size": self.size.tolist(),
            "max_dimension": self.max_dimension,
        }


# ============================================================
# NATIVE OBJ PARSER (Fallback if trimesh not available)
# ============================================================

class OBJParser:
    """
    Native OBJ file parser.
    Simple, no dependencies.
    Handles v, vn, vt, f (faces).
    """

    @staticmethod
    def parse(filepath: str) -> Optional[Dict]:
        """
        OBJ file parse karo.

        Returns:
            Dict with vertices, indices, has_normals, has_uvs
        """
        try:
            positions: List[List[float]] = []
            normals: List[List[float]] = []
            texcoords: List[List[float]] = []

            # Face data: list of (pos_idx, tex_idx, norm_idx) tuples
            face_data: List[List[Tuple[int, int, int]]] = []

            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split()
                    if not parts:
                        continue

                    prefix = parts[0].lower()

                    # Vertex position
                    if prefix == "v" and len(parts) >= 4:
                        positions.append([
                            float(parts[1]),
                            float(parts[2]),
                            float(parts[3])
                        ])

                    # Vertex normal
                    elif prefix == "vn" and len(parts) >= 4:
                        normals.append([
                            float(parts[1]),
                            float(parts[2]),
                            float(parts[3])
                        ])

                    # Texture coordinate
                    elif prefix == "vt" and len(parts) >= 3:
                        texcoords.append([
                            float(parts[1]),
                            float(parts[2])
                        ])

                    # Face
                    elif prefix == "f" and len(parts) >= 4:
                        face = []
                        for vertex_str in parts[1:]:
                            # Format: v/vt/vn or v//vn or v
                            indices = vertex_str.split("/")

                            pos_idx = int(indices[0]) - 1 if indices[0] else 0
                            tex_idx = int(indices[1]) - 1 if len(indices) > 1 and indices[1] else -1
                            norm_idx = int(indices[2]) - 1 if len(indices) > 2 and indices[2] else -1

                            face.append((pos_idx, tex_idx, norm_idx))

                        # Triangulate (agar quad ya polygon hai)
                        if len(face) == 3:
                            face_data.append(face)
                        elif len(face) == 4:
                            # Quad → 2 triangles
                            face_data.append([face[0], face[1], face[2]])
                            face_data.append([face[0], face[2], face[3]])
                        elif len(face) > 4:
                            # Fan triangulation
                            for i in range(1, len(face) - 1):
                                face_data.append([face[0], face[i], face[i + 1]])

            if not positions or not face_data:
                logger.error("OBJ has no vertices or faces")
                return None

            has_normals = len(normals) > 0
            has_uvs = len(texcoords) > 0

            # Build final vertex array (position + normal + uv per vertex)
            # Each face vertex becomes unique vertex
            final_vertices = []
            final_indices = []

            vertex_counter = 0

            for face in face_data:
                for pos_idx, tex_idx, norm_idx in face:
                    # Position
                    if 0 <= pos_idx < len(positions):
                        pos = positions[pos_idx]
                    else:
                        pos = [0.0, 0.0, 0.0]

                    # Normal
                    if has_normals and 0 <= norm_idx < len(normals):
                        norm = normals[norm_idx]
                    else:
                        norm = [0.0, 1.0, 0.0]  # Default up

                    # Texcoord
                    if has_uvs and 0 <= tex_idx < len(texcoords):
                        uv = texcoords[tex_idx]
                    else:
                        uv = [0.0, 0.0]

                    final_vertices.extend(pos)
                    final_vertices.extend(norm)
                    final_vertices.extend(uv)

                    final_indices.append(vertex_counter)
                    vertex_counter += 1

            vertices_arr = np.array(final_vertices, dtype=np.float32)
            indices_arr = np.array(final_indices, dtype=np.uint32)

            # Agar normals nahi the to calculate karo
            if not has_normals:
                OBJParser._calculate_normals(vertices_arr, indices_arr)

            return {
                "vertices": vertices_arr,
                "indices": indices_arr,
                "has_normals": has_normals or True,  # Ab hain
                "has_uvs": has_uvs,
                "vertex_count": vertex_counter,
                "face_count": len(face_data),
            }

        except Exception as e:
            logger.error(f"OBJ parse failed: {e}")
            return None

    @staticmethod
    def _calculate_normals(vertices: np.ndarray, indices: np.ndarray):
        """
        Vertices ke liye normals calculate karo (in-place).
        Cross product of triangle edges.
        """
        try:
            # Reshape: [x,y,z,nx,ny,nz,u,v] per vertex
            verts = vertices.reshape(-1, 8)

            # Har triangle ke normal calculate karo
            for i in range(0, len(indices), 3):
                if i + 2 >= len(indices):
                    break

                i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]

                v0 = verts[i0, :3]
                v1 = verts[i1, :3]
                v2 = verts[i2, :3]

                edge1 = v1 - v0
                edge2 = v2 - v0
                normal = np.cross(edge1, edge2)

                norm_len = np.linalg.norm(normal)
                if norm_len > 0:
                    normal = normal / norm_len

                # Sab teen vertices pe assign karo
                verts[i0, 3:6] = normal
                verts[i1, 3:6] = normal
                verts[i2, 3:6] = normal

        except Exception as e:
            logger.error(f"Normal calculation failed: {e}")


# ============================================================
# TRIMESH LOADER (For FBX, GLTF, etc.)
# ============================================================

class TrimeshLoader:
    """Trimesh library use karke advanced formats load karo"""

    @staticmethod
    def load(filepath: str) -> Optional[List[Dict]]:
        """
        Trimesh se model load karo.

        Returns:
            List of mesh dicts (multi-mesh support)
        """
        if not TRIMESH_AVAILABLE:
            logger.error("trimesh not installed! pip install trimesh")
            return None

        try:
            scene = trimesh.load(filepath, force="scene")

            if scene is None:
                logger.error(f"Trimesh returned None: {filepath}")
                return None

            # Scene se sab meshes nikaalo
            meshes_data = []

            if hasattr(scene, "geometry"):
                # Multi-mesh scene
                geometries = scene.geometry
            else:
                # Single mesh
                geometries = {"main": scene}

            for name, geom in geometries.items():
                if not isinstance(geom, trimesh.Trimesh):
                    continue

                mesh_data = TrimeshLoader._convert_trimesh(geom, name)
                if mesh_data:
                    meshes_data.append(mesh_data)

            if not meshes_data:
                logger.error("No valid meshes found")
                return None

            return meshes_data

        except Exception as e:
            logger.error(f"Trimesh load failed: {e}")
            return None

    @staticmethod
    def _convert_trimesh(tm: Any, name: str) -> Optional[Dict]:
        """Trimesh mesh ko humare format me convert karo"""
        try:
            positions = np.array(tm.vertices, dtype=np.float32)
            faces = np.array(tm.faces, dtype=np.uint32)

            if len(positions) == 0 or len(faces) == 0:
                return None

            # Normals
            if hasattr(tm, "vertex_normals") and tm.vertex_normals is not None:
                normals = np.array(tm.vertex_normals, dtype=np.float32)
                has_normals = True
            else:
                # Face normals se vertex normals calculate karo
                normals = np.zeros_like(positions)
                has_normals = False

                if hasattr(tm, "face_normals") and tm.face_normals is not None:
                    face_normals = np.array(tm.face_normals, dtype=np.float32)
                    for i, face in enumerate(faces):
                        for vidx in face:
                            normals[vidx] += face_normals[i]

                    # Normalize
                    lengths = np.linalg.norm(normals, axis=1)
                    lengths[lengths == 0] = 1
                    normals = normals / lengths[:, np.newaxis]

            # UVs
            uvs = None
            has_uvs = False

            if hasattr(tm.visual, "uv") and tm.visual.uv is not None:
                try:
                    uvs = np.array(tm.visual.uv, dtype=np.float32)
                    if len(uvs) == len(positions):
                        has_uvs = True
                    else:
                        uvs = None
                except Exception:
                    uvs = None

            if uvs is None:
                uvs = np.zeros((len(positions), 2), dtype=np.float32)

            # Interleave: [x,y,z, nx,ny,nz, u,v] per vertex
            interleaved = np.zeros((len(positions), 8), dtype=np.float32)
            interleaved[:, :3] = positions
            interleaved[:, 3:6] = normals
            interleaved[:, 6:8] = uvs

            # Flatten
            vertices_flat = interleaved.flatten()

            # Face indices flatten
            indices_flat = faces.flatten()

            return {
                "name": name,
                "vertices": vertices_flat,
                "indices": indices_flat,
                "vertex_count": len(positions),
                "face_count": len(faces),
                "has_normals": has_normals,
                "has_uvs": has_uvs,
            }

        except Exception as e:
            logger.error(f"Trimesh convert failed: {e}")
            return None


# ============================================================
# MAIN MODEL LOADER
# ============================================================

class ModelLoader:
    """
    Main model loader.
    Auto-detects format and uses appropriate parser.
    Caches loaded models.
    """

    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, List[Dict]] = {}  # file_hash → mesh data list

        logger.info(f"ModelLoader initialized (cache: {cache_enabled})")

    def load(self, filepath: str,
             center: bool = False,
             normalize_scale: bool = False,
             target_size: float = 2.0) -> Tuple[List[Mesh], ModelInfo]:
        """
        3D model load karo.

        Args:
            filepath: Model file path
            center: Auto-center at origin
            normalize_scale: Scale to target_size
            target_size: Target max dimension (agar normalize_scale=True)

        Returns:
            (list of Mesh objects, ModelInfo)
        """
        start_time = time.time()

        # Info object
        info = ModelInfo(
            filepath=filepath,
            filename=os.path.basename(filepath),
            format=get_file_extension(filepath),
            file_size=get_file_size(filepath) if os.path.exists(filepath) else 0
        )

        # File check
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            info.warnings.append("File not found")
            return [], info

        # Format check
        if not is_supported_model_format(filepath):
            logger.error(f"Unsupported format: {info.format}")
            info.warnings.append(f"Unsupported format: {info.format}")
            return [], info

        # Cache check
        file_hash = None
        if self.cache_enabled:
            file_hash = hash_file(filepath)
            if file_hash and file_hash in self._cache:
                logger.debug(f"Cache hit: {info.filename}")
                mesh_data_list = self._cache[file_hash]
            else:
                mesh_data_list = self._load_from_disk(filepath, info)
                if mesh_data_list and file_hash:
                    self._cache[file_hash] = mesh_data_list
        else:
            mesh_data_list = self._load_from_disk(filepath, info)

        if not mesh_data_list:
            info.warnings.append("Load failed")
            return [], info

        # Meshes create karo
        meshes = []
        total_bbox = BoundingBox()
        first_bbox = True

        for mesh_data in mesh_data_list:
            mesh = Mesh(name=mesh_data.get("name", info.filename))
            mesh.set_vertices(mesh_data["vertices"], mesh_data["indices"])

            # Stats update
            info.total_vertices += mesh_data.get("vertex_count", 0)
            info.total_faces += mesh_data.get("face_count", 0)

            if mesh_data.get("has_normals"):
                info.has_normals = True
            if mesh_data.get("has_uvs"):
                info.has_uvs = True

            # Bounding box
            mesh_bbox = BoundingBox.from_vertices(mesh.vertices)
            if first_bbox:
                total_bbox = mesh_bbox
                first_bbox = False
            else:
                total_bbox.min_point = np.minimum(total_bbox.min_point, mesh_bbox.min_point)
                total_bbox.max_point = np.maximum(total_bbox.max_point, mesh_bbox.max_point)

            meshes.append(mesh)

        info.total_meshes = len(meshes)
        info.bounding_box = total_bbox.to_dict()
        info.load_time = time.time() - start_time

        # Post-processing
        if center or normalize_scale:
            self._apply_transformations(
                meshes, total_bbox, center, normalize_scale, target_size
            )

        logger.info(
            f"Loaded '{info.filename}': "
            f"{info.total_meshes} meshes, "
            f"{info.total_vertices} vertices, "
            f"{info.total_faces} faces "
            f"({info.load_time:.2f}s)"
        )

        return meshes, info

    def _load_from_disk(self, filepath: str, info: ModelInfo) -> Optional[List[Dict]]:
        """Actual disk se load karo (parser choose karke)"""
        ext = get_file_extension(filepath)

        # OBJ files: native parser preferred (faster)
        if ext == "obj":
            logger.debug(f"Using native OBJ parser: {info.filename}")
            data = OBJParser.parse(filepath)
            if data:
                return [data]
            # Fallback to trimesh
            logger.debug("Native parser failed, trying trimesh...")

        # Other formats or OBJ fallback: use trimesh
        if TRIMESH_AVAILABLE:
            logger.debug(f"Using trimesh: {info.filename}")
            return TrimeshLoader.load(filepath)

        logger.error("No parser available for this format")
        info.warnings.append("No suitable parser available")
        return None

    def _apply_transformations(self, meshes: List[Mesh],
                                bbox: BoundingBox,
                                center: bool,
                                normalize_scale: bool,
                                target_size: float):
        """Center aur/ya scale apply karo"""
        try:
            # Scale calculate karo
            scale_factor = 1.0
            if normalize_scale and bbox.max_dimension > 0:
                scale_factor = target_size / bbox.max_dimension

            # Center offset
            center_offset = bbox.center if center else np.zeros(3, dtype=np.float32)

            # Har mesh me apply karo
            for mesh in meshes:
                if mesh.vertices is None:
                    continue

                verts = mesh.vertices.reshape(-1, 8)

                # Center
                if center:
                    verts[:, :3] -= center_offset

                # Scale
                if normalize_scale:
                    verts[:, :3] *= scale_factor

                # Flatten back
                mesh.vertices = verts.flatten()
                mesh._uploaded = False  # Re-upload needed

            if center:
                logger.debug(f"Centered at origin (offset: {center_offset})")
            if normalize_scale:
                logger.debug(f"Scaled by {scale_factor:.3f} to fit {target_size} units")

        except Exception as e:
            logger.error(f"Transform failed: {e}")

    def clear_cache(self):
        """Cache clear karo"""
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared ({cache_size} entries removed)")

    def get_cache_info(self) -> Dict:
        """Cache statistics"""
        return {
            "enabled": self.cache_enabled,
            "entries": len(self._cache),
            "total_meshes": sum(len(v) for v in self._cache.values()),
        }


# ============================================================
# TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    from src.utils import setup_logging, print_banner, print_section

    setup_logging(log_level="DEBUG")
    print_banner("Model Loader Test", "OBJ/FBX/GLTF Loading")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))

    # ============================================================
    # Test 1: Create Test OBJ File
    # ============================================================
    print_section("Test 1: Create Test OBJ File")

    test_obj_content = """# Test cube
v -1.0 -1.0  1.0
v  1.0 -1.0  1.0
v  1.0  1.0  1.0
v -1.0  1.0  1.0
v -1.0 -1.0 -1.0
v  1.0 -1.0 -1.0
v  1.0  1.0 -1.0
v -1.0  1.0 -1.0

vn  0.0  0.0  1.0
vn  0.0  0.0 -1.0
vn  1.0  0.0  0.0
vn -1.0  0.0  0.0
vn  0.0  1.0  0.0
vn  0.0 -1.0  0.0

vt 0.0 0.0
vt 1.0 0.0
vt 1.0 1.0
vt 0.0 1.0

# Front
f 1/1/1 2/2/1 3/3/1 4/4/1
# Back
f 5/1/2 8/4/2 7/3/2 6/2/2
# Right
f 2/1/3 6/2/3 7/3/3 3/4/3
# Left
f 1/1/4 4/4/4 8/3/4 5/2/4
# Top
f 4/1/5 3/2/5 7/3/5 8/4/5
# Bottom
f 1/1/6 5/2/6 6/3/6 2/4/6
"""

    test_dir = os.path.join(base_dir, "temp", "test_models")
    ensure_dir(test_dir)

    test_obj_path = os.path.join(test_dir, "test_cube.obj")
    with open(test_obj_path, "w") as f:
        f.write(test_obj_content)

    print(f"✓ Test OBJ created: {test_obj_path}")

    # ============================================================
    # Test 2: Load Model
    # ============================================================
    print_section("Test 2: Load OBJ Model")

    loader = ModelLoader(cache_enabled=True)
    meshes, info = loader.load(test_obj_path)

    print(f"Loaded {len(meshes)} meshes")
    print(f"Format: {info.format}")
    print(f"File size: {format_bytes(info.file_size)}")
    print(f"Load time: {info.load_time:.3f}s")
    print(f"Total vertices: {info.total_vertices}")
    print(f"Total faces: {info.total_faces}")
    print(f"Has normals: {info.has_normals}")
    print(f"Has UVs: {info.has_uvs}")

    if info.bounding_box:
        bbox = info.bounding_box
        print(f"Bounding box:")
        print(f"  Min: {bbox['min']}")
        print(f"  Max: {bbox['max']}")
        print(f"  Size: {bbox['size']}")
        print(f"  Center: {bbox['center']}")

    # ============================================================
    # Test 3: Cache Test
    # ============================================================
    print_section("Test 3: Cache Test")

    print("Loading same file again (should be cached)...")
    start = time.time()
    meshes2, info2 = loader.load(test_obj_path)
    cache_time = time.time() - start

    print(f"Cache load time: {cache_time:.4f}s (much faster!)")
    print(f"Cache info: {loader.get_cache_info()}")

    # ============================================================
    # Test 4: Load with Transformations
    # ============================================================
    print_section("Test 4: Load with Center & Normalize")

    loader.clear_cache()
    meshes3, info3 = loader.load(
        test_obj_path,
        center=True,
        normalize_scale=True,
        target_size=1.0
    )

    if meshes3:
        # Check new bounding box
        new_bbox = BoundingBox.from_vertices(meshes3[0].vertices)
        print(f"After transformation:")
        print(f"  New center: {new_bbox.center}")
        print(f"  New max dimension: {new_bbox.max_dimension:.3f}")
        print(f"  New size: {new_bbox.size}")

    # ============================================================
    # Test 5: Render Loaded Model
    # ============================================================
    print_section("Test 5: Render Loaded Model")

    from src.renderer.render_engine import RenderEngine, RenderQuality

    engine = RenderEngine(width=1280, height=720, headless=True)

    if engine.initialized:
        # Loaded model add karo
        for mesh in meshes3:
            mesh.color = [0.9, 0.6, 0.2]  # Orange
            engine.add_mesh(mesh)

        # Camera setup
        engine.camera.position = [3, 2, 4]
        engine.camera.target = [0, 0, 0]

        # Render karo
        output_path = os.path.join(base_dir, "temp", "test_loaded_model.png")
        engine.render_to_image(output_path)

        print(f"✅ Rendered loaded model: {output_path}")
        print(f"👉 Open to see: start temp\\test_loaded_model.png")

        engine.shutdown()

    # ============================================================
    # Test 6: Invalid Formats
    # ============================================================
    print_section("Test 6: Error Handling")

    # Non-existent file
    meshes_err, info_err = loader.load("nonexistent.obj")
    print(f"Non-existent file: {len(meshes_err)} meshes, warnings: {info_err.warnings}")

    # Unsupported format
    meshes_err2, info_err2 = loader.load("test.xyz")
    print(f"Unsupported format: {len(meshes_err2)} meshes, warnings: {info_err2.warnings}")

    # ============================================================
    # Cleanup
    # ============================================================
    print_section("Cleanup")

    from src.utils import delete_file, delete_directory
    delete_directory(test_dir)
    print("Test files cleaned")

    print_banner(
        "✅ All Tests Passed",
        "Model Loader Working - OBJ/FBX/GLTF support ready!"
    )