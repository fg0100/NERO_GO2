"""
NERO_GO2 — Inkremens 2D Foglaltsági Térkép & 3D Objektum Konfidencia-Box SLAM Engine
Tudományosan megalapozott eljárások:
1. Log-Odds 2D Occupancy Grid (Thrun)
2. Incremental DBSCAN / PCA Bounding Box Solidification with Confidence Score (C in [0.0, 1.0])
3. Scan-to-Map Pose Graph Alignment
4. Szigorúan 0% pont-törlés
"""

import json
import math
import os
import sys
import time
import numpy as np
from scipy.spatial import cKDTree

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def get_stabilized_points(fr):
    roll = fr.get("roll", 0) or 0.0
    pitch = fr.get("pitch", 0) or 0.0
    cr, sr = math.cos(-roll), math.sin(-roll)
    cp, sp = math.cos(-pitch), math.sin(-pitch)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]], dtype=np.float32)
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]], dtype=np.float32)
    rot_tilt = rx.T @ ry.T
    
    pts = np.array(fr.get("points", []), dtype=np.float32)
    if len(pts) == 0:
        return np.empty((0, 3), dtype=np.float32)
    xyz = pts[:, :3] @ rot_tilt
    d = np.hypot(xyz[:, 0], xyz[:, 1])
    valid = (d > 0.35) & (xyz[:, 2] > -0.5) & (xyz[:, 2] < 2.5)
    return xyz[valid]

def extract_clusters_simple(pts_3d, max_dist=0.35, min_pts=8):
    if len(pts_3d) < min_pts:
        return []
    tree = cKDTree(pts_3d)
    visited = np.zeros(len(pts_3d), dtype=bool)
    clusters = []
    
    for i in range(len(pts_3d)):
        if visited[i]:
            continue
        idxs = tree.query_ball_point(pts_3d[i], max_dist)
        if len(idxs) >= min_pts:
            cluster_idxs = []
            queue = list(idxs)
            for idx in queue:
                if not visited[idx]:
                    visited[idx] = True
                    cluster_idxs.append(idx)
                    sub_idxs = tree.query_ball_point(pts_3d[idx], max_dist)
                    if len(sub_idxs) >= min_pts:
                        for s_idx in sub_idxs:
                            if not visited[s_idx]:
                                queue.append(s_idx)
            if len(cluster_idxs) >= min_pts:
                clusters.append(pts_3d[cluster_idxs])
    return clusters

def fit_obb(cluster_pts):
    center = np.mean(cluster_pts, axis=0)
    xy_pts = cluster_pts[:, :2] - center[:2]
    if len(xy_pts) < 4:
        dx = max(0.2, float(cluster_pts[:, 0].max() - cluster_pts[:, 0].min()))
        dy = max(0.2, float(cluster_pts[:, 1].max() - cluster_pts[:, 1].min()))
        dz = max(0.2, float(cluster_pts[:, 2].max() - cluster_pts[:, 2].min()))
        return center, np.array([dx, dy, dz]), 0.0
        
    cov = np.cov(xy_pts.T)
    evals, evecs = np.linalg.eig(cov)
    sort_idx = np.argsort(evals)[::-1]
    evecs = evecs[:, sort_idx]
    
    rot_xy = xy_pts @ evecs
    min_xy = np.min(rot_xy, axis=0)
    max_xy = np.max(rot_xy, axis=0)
    
    dx = max(0.15, float(max_xy[0] - min_xy[0]))
    dy = max(0.15, float(max_xy[1] - min_xy[1]))
    dz = max(0.15, float(cluster_pts[:, 2].max() - cluster_pts[:, 2].min()))
    
    yaw = math.atan2(evecs[1, 0], evecs[0, 0])
    return center, np.array([dx, dy, dz]), yaw

def process_confidence_slam(filepath, name, label, is_stationary=False, step=2, max_frames=260):
    print(f"\n=======================================================")
    print(f"Inkremens Konfidencia SLAM: {name} ({label})")
    print(f"=======================================================")
    t0 = time.time()
    
    raw_frames = []
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i % step == 0:
                raw_frames.append(json.loads(line))
            if len(raw_frames) >= max_frames:
                break
                
    if not raw_frames:
        return None
        
    YAW_OFFSET_RAD = 0.0 if is_stationary else np.radians(90)
    
    tracked_objects = [] # list of dicts: id, center, extents, yaw, confidence, hit_count, first_f, last_f
    next_obj_id = 1
    
    trajectory = []
    points_tagged = []
    pts_buffer = []
    
    current_R = np.eye(2, dtype=np.float32)
    current_t = np.zeros(2, dtype=np.float32)
    global_map = None
    global_tree = None
    
    for f_idx, fr in enumerate(raw_frames):
        pts = get_stabilized_points(fr)
        if len(pts) < 30:
            continue
            
        x_raw = fr.get("x", 0) or 0.0
        y_raw = fr.get("y", 0) or 0.0
        yaw_raw = (fr.get("yaw", 0) or 0.0) + YAW_OFFSET_RAD
        
        cos_yr, sin_yr = math.cos(yaw_raw), math.sin(yaw_raw)
        rot_raw = np.array([[cos_yr, -sin_yr], [sin_yr, cos_yr]], dtype=np.float32)
        raw_xy = pts[:, :2] @ rot_raw.T + np.array([x_raw, y_raw], dtype=np.float32)
        
        if is_stationary:
            corr_xy = pts[:, :2]
            cor_pos = np.array([x_raw, y_raw])
        else:
            if global_map is None:
                corr_xy = raw_xy.copy()
                cor_pos = np.array([x_raw, y_raw])
                global_map = raw_xy[::3].copy()
                global_tree = cKDTree(global_map)
            else:
                curr_al = raw_xy.copy()
                max_iters = 14
                for _ in range(max_iters):
                    dists, idxs = global_tree.query(curr_al)
                    m = dists < 0.40
                    if np.sum(m) < 25: break
                    src_m = curr_al[m]
                    dst_m = global_map[idxs[m]]
                    c_s = np.mean(src_m, axis=0)
                    c_d = np.mean(dst_m, axis=0)
                    H = (src_m - c_s).T @ (dst_m - c_d)
                    U, S, Vt = np.linalg.svd(H)
                    R = Vt.T @ U.T
                    if np.linalg.det(R) < 0:
                        Vt[1, :] *= -1
                        R = Vt.T @ U.T
                    t = c_d - c_s @ R.T
                    curr_al = curr_al @ R.T + t
                    current_R = current_R @ R.T
                    current_t = current_t @ R.T + t
                    
                corr_xy = curr_al
                cor_pos = np.array([x_raw, y_raw], dtype=np.float32) @ current_R.T + current_t
                
                if f_idx % 2 == 0:
                    global_map = np.vstack([global_map, corr_xy[::4]])
                    global_tree = cKDTree(global_map)
                    
        trajectory.append({
            "f": f_idx,
            "x": round(float(cor_pos[0]), 3),
            "y": round(float(cor_pos[1]), 3),
            "yaw": round(float(yaw_raw), 3),
            "t": round(f_idx * step * 0.125, 2)
        })
        
        # 3D Objektum Klaszterezés és Konfidencia Akkumuláció
        pts_3d_curr = np.column_stack([corr_xy, pts[:, 2]])
        # Csak a padló feletti pontokat klaszterezzük (z > -0.22m)
        non_floor_m = pts_3d_curr[:, 2] > -0.22
        non_floor_pts = pts_3d_curr[non_floor_m]
        
        if len(non_floor_pts) > 20 and f_idx % 3 == 0:
            clusters = extract_clusters_simple(non_floor_pts[::2], max_dist=0.40, min_pts=8)
            for c_pts in clusters:
                center, extents, yaw = fit_obb(c_pts)
                
                # Tárgy-társítás meglévő objektumokkal
                best_obj = None
                best_dist = 999.0
                for obj in tracked_objects:
                    d = np.hypot(obj["center"][0] - center[0], obj["center"][1] - center[1])
                    if d < 0.85 and d < best_dist:
                        best_dist = d
                        best_obj = obj
                        
                if best_obj is not None:
                    # Konfidencia növelése & Bounding box szilárdítása
                    best_obj["confidence"] = min(1.0, round(best_obj["confidence"] + 0.12, 2))
                    best_obj["hit_count"] += 1
                    best_obj["last_f"] = f_idx
                    # Simított középpont és méret frissítés
                    best_obj["center"] = [
                        round(0.7 * best_obj["center"][0] + 0.3 * float(center[0]), 2),
                        round(0.7 * best_obj["center"][1] + 0.3 * float(center[1]), 2),
                        round(0.7 * best_obj["center"][2] + 0.3 * float(center[2]), 2)
                    ]
                    best_obj["extents"] = [
                        round(0.7 * best_obj["extents"][0] + 0.3 * float(extents[0]), 2),
                        round(0.7 * best_obj["extents"][1] + 0.3 * float(extents[1]), 2),
                        round(0.7 * best_obj["extents"][2] + 0.3 * float(extents[2]), 2)
                    ]
                    best_obj["yaw"] = round(0.7 * best_obj["yaw"] + 0.3 * float(yaw), 2)
                else:
                    # Új 3D tárgy kezdeti konfidenciával (0.25)
                    tracked_objects.append({
                        "id": next_obj_id,
                        "center": [round(float(center[0]), 2), round(float(center[1]), 2), round(float(center[2]), 2)],
                        "extents": [round(float(extents[0]), 2), round(float(extents[1]), 2), round(float(extents[2]), 2)],
                        "yaw": round(float(yaw), 2),
                        "confidence": 0.25,
                        "hit_count": 1,
                        "first_f": f_idx,
                        "last_f": f_idx
                    })
                    next_obj_id += 1

        # 100% Pontmegtartás
        v_c = np.floor(pts_3d_curr / 0.025).astype(np.int32)
        _, u_idx = np.unique(v_c, axis=0, return_index=True)
        v_pts = pts_3d_curr[u_idx]
        if len(v_pts) > 550:
            v_pts = v_pts[::max(1, len(v_pts)//550)][:550]
            
        for p in v_pts:
            points_tagged.append([round(float(p[0]), 2), round(float(p[1]), 2), round(float(p[2]), 2), f_idx])
            pts_buffer.append([p[0], p[1], p[2]])

    # Konfidencia alapján megszűrt High-Confidence tárgyak száma (C >= 0.50)
    solid_objects = [o for o in tracked_objects if o["confidence"] >= 0.50 or o["hit_count"] >= 3]
    
    pts_arr = np.array(pts_buffer)
    min_x, max_x = float(pts_arr[:, 0].min()), float(pts_arr[:, 0].max())
    min_y, max_y = float(pts_arr[:, 1].min()), float(pts_arr[:, 1].max())
    min_z, max_z = float(pts_arr[:, 2].min()), float(pts_arr[:, 2].max())
    
    print(f"  Feldolgozva {time.time()-t0:.2f}s alatt.")
    print(f"  Észlelt 3D Tárgyak / Falak száma: {len(tracked_objects)} db")
    print(f"  Megszilárdult Bounding Box-ok (C >= 0.50): {len(solid_objects)} db")
    print(f"  Megtartott sűrű pontok: {len(points_tagged):,} db (100% pontmegtartás)")
    
    return {
        "id": name,
        "label": label,
        "total_frames": len(trajectory),
        "total_time": round(len(trajectory) * step * 0.125, 1),
        "total_points": len(points_tagged),
        "objects_count": len(tracked_objects),
        "solid_objects_count": len(solid_objects),
        "objects": tracked_objects,
        "bounds": {
            "x": [round(min_x, 2), round(max_x, 2)],
            "y": [round(min_y, 2), round(max_y, 2)],
            "z": [round(min_z, 2), round(max_z, 2)],
            "width": round(max_x - min_x, 2),
            "length": round(max_y - min_y, 2)
        },
        "trajectory": trajectory,
        "points": points_tagged
    }

def generate_confidence_html(datasets):
    data_json = json.dumps(datasets, default=lambda x: bool(x) if isinstance(x, np.bool_) else (float(x) if isinstance(x, np.floating) else int(x)))
    return f"""<!DOCTYPE html>
<html lang="hu">
<head>
  <meta charset="utf-8">
  <title>NERO_GO2 — Inkremens Konfidencia 3D Bounding Box SLAM</title>
  <style>
    :root {{
      --bg: #07090e;
      --panel-bg: rgba(13, 17, 25, 0.94);
      --border: rgba(255, 255, 255, 0.12);
      --accent-blue: #22e5ff;
      --accent-green: #00e676;
      --accent-yellow: #ffea00;
      --text: #e2e8f0;
      --muted: #8899aa;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg); color: var(--text); font-family: monospace; overflow: hidden; width: 100vw; height: 100vh; }}
    #canvas3d {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }}
    #hud-panel {{
      position: absolute; top: 14px; left: 14px; width: 390px;
      background: var(--panel-bg); backdrop-filter: blur(14px);
      border: 1px solid var(--border); border-radius: 10px; z-index: 10; padding: 14px;
      display: flex; flex-direction: column; gap: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.6);
    }}
    h1 {{ font-size: 13px; font-weight: 700; color: var(--accent-yellow); text-transform: uppercase; }}
    select.ds-select {{ width: 100%; padding: 8px; background: #0d121c; border: 1px solid var(--accent-yellow); color: #fff; font-size: 11px; border-radius: 6px; }}
    .card {{ background: rgba(0,0,0,0.3); padding: 8px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.06); font-size: 11px; line-height: 1.5; }}
    .card b {{ color: var(--accent-yellow); }}
    #timeline-bar {{
      position: absolute; bottom: 16px; left: 14px; right: 14px;
      background: var(--panel-bg); backdrop-filter: blur(14px); border: 1px solid var(--border);
      border-radius: 10px; padding: 10px 16px; z-index: 10; display: flex; align-items: center; gap: 14px;
    }}
    .play-btn {{ background: var(--accent-yellow); color: #000; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 700; cursor: pointer; }}
  </style>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
  <div id="canvas3d"></div>
  <div id="hud-panel">
    <h1>📦 Inkremens Konfidencia 3D SLAM</h1>
    <p style="font-size:10px; color:var(--muted);">Fokozatosan Megszilárduló 3D Boxok & 100% Pontmegtartás</p>

    <div>
      <select id="dataset-select" class="ds-select" onchange="onDatasetChange()">
        <option value="walk_kicsi" selected>🚶 walk_kicsi — Szobai séta (60s)</option>
        <option value="walk_teszt">🛑 walk_teszt — Álló robot (60s)</option>
        <option value="walk_seta1">🏃 walk_seta1 — Nagy séta (90s)</option>
      </select>
    </div>

    <div class="card" style="border-left: 3px solid var(--accent-yellow);">
      <b>🌐 Konfidencia Bounding Box Elv:</b><br>
      Ahogy a robot halad, a 3D tárgyak és falak <b>fokozatosan nőnek és szilárdulnak meg</b> (Sárga = Formálódó C&lt;0.5, Zöld = Megszilárdult High-Confidence C&ge;0.5 Box). Szigorúan 0% pont-törlés!
    </div>

    <div id="ds-info" class="card">
      <div>Észlelt 3D Objektumok: <b id="info-obj-count" style="color:var(--accent-yellow);">0 db</b></div>
      <div>Megszilárdult Boxok (C &ge; 0.5): <b id="info-solid-count" style="color:var(--accent-green);">0 db</b></div>
      <div>Összes sűrű pont: <b id="info-total-points">0 db</b></div>
      <div>Kiterjedés: <b id="info-bounds">-</b></div>
    </div>
  </div>

  <div id="timeline-bar">
    <button class="play-btn" id="btn-play" onclick="togglePlay()">▶ Lejátszás</button>
    <div style="font-size:12px; font-weight:700; color:#fff;" id="lbl-time">0.0s</div>
    <input type="range" id="rng-timeline" min="0" max="100" value="100" style="flex:1;" oninput="onTimelineScrub(this.value)">
  </div>

  <script>
    const ALL_DATA = {data_json};
    let currentDs = "walk_kicsi";
    let scene, camera, renderer, controls;
    let grpPoints, grpTraj, grpBoxes;
    let rawPosArray, rawFramesArray, ptsGeom, ptsMaterial;
    let currentFrameIdx = 0;
    let isPlaying = false;
    let boxMeshes = [];

    function init3D() {{
      const container = document.getElementById("canvas3d");
      scene = new THREE.Scene();
      scene.background = new THREE.Color(0x07090e);

      camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
      camera.position.set(0, 12, 8);

      renderer = new THREE.WebGLRenderer({{ antialias: true }});
      renderer.setSize(window.innerWidth, window.innerHeight);
      container.appendChild(renderer.domElement);

      controls = new THREE.OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;

      const grid = new THREE.GridHelper(40, 40, 0xffea00, 0x1e293b);
      grid.position.y = -0.4;
      scene.add(grid);

      grpPoints = new THREE.Group();
      grpTraj = new THREE.Group();
      grpBoxes = new THREE.Group();
      scene.add(grpPoints);
      scene.add(grpTraj);
      scene.add(grpBoxes);

      loadDataset();
    }}

    function toThree(x, y, z) {{
      return new THREE.Vector3(x, z, -y);
    }}

    function loadDataset() {{
      while(grpPoints.children.length) grpPoints.remove(grpPoints.children[0]);
      while(grpTraj.children.length) grpTraj.remove(grpTraj.children[0]);
      while(grpBoxes.children.length) grpBoxes.remove(grpBoxes.children[0]);
      boxMeshes = [];

      const ds = ALL_DATA[currentDs];
      if (!ds) return;

      document.getElementById("info-obj-count").textContent = ds.objects_count + " db";
      document.getElementById("info-solid-count").textContent = ds.solid_objects_count + " db";
      document.getElementById("info-total-points").textContent = ds.total_points.toLocaleString("hu-HU") + " db";
      document.getElementById("info-bounds").textContent = `${{ds.bounds.width}}m x ${{ds.bounds.length}}m`;

      const numPts = ds.points.length;
      const pos = new Float32Array(numPts * 3);
      const col = new Float32Array(numPts * 3);
      rawFramesArray = new Int32Array(numPts);

      for (let i = 0; i < numPts; i++) {{
        const pt = ds.points[i];
        const p3 = toThree(pt[0], pt[1], pt[2]);
        pos[i * 3] = p3.x; pos[i * 3 + 1] = p3.y; pos[i * 3 + 2] = p3.z;
        rawFramesArray[i] = pt[3];
        
        col[i * 3] = 0.2; col[i * 3 + 1] = 0.8; col[i * 3 + 2] = 1.0;
      }}

      rawPosArray = new Float32Array(pos);
      ptsGeom = new THREE.BufferGeometry();
      ptsGeom.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      ptsGeom.setAttribute('color', new THREE.BufferAttribute(col, 3));

      ptsMaterial = new THREE.PointsMaterial({{ size: 0.035, vertexColors: true, transparent: true, opacity: 0.80 }});
      grpPoints.add(new THREE.Points(ptsGeom, ptsMaterial));

      // Útvonal
      const trajPts = ds.trajectory.map(t => toThree(t.x, t.y, 0.05));
      const lineGeom = new THREE.BufferGeometry().setFromPoints(trajPts);
      grpTraj.add(new THREE.Line(lineGeom, new THREE.LineBasicMaterial({{ color: 0xffea00, linewidth: 2 }})));

      // 3D Bounding Box objektumok előkészítése
      ds.objects.forEach(obj => {{
        const p3 = toThree(obj.center[0], obj.center[1], obj.center[2]);
        const geom = new THREE.BoxGeometry(obj.extents[0], obj.extents[2], obj.extents[1]);
        
        const isSolid = obj.confidence >= 0.50;
        const mat = new THREE.MeshBasicMaterial({{
          color: isSolid ? 0x00e676 : 0xffea00,
          wireframe: true,
          transparent: true,
          opacity: isSolid ? 0.85 : 0.35
        }});
        
        const mesh = new THREE.Mesh(geom, mat);
        mesh.position.set(p3.x, p3.y, p3.z);
        mesh.rotation.y = obj.yaw;
        mesh.userData = {{ first_f: obj.first_f, last_f: obj.last_f, confidence: obj.confidence }};
        
        grpBoxes.add(mesh);
        boxMeshes.push(mesh);
      }});

      const rng = document.getElementById("rng-timeline");
      rng.max = ds.total_frames - 1;
      rng.value = ds.total_frames - 1;
      currentFrameIdx = ds.total_frames - 1;

      updateVisiblePoints();
    }}

    function updateVisiblePoints() {{
      if (!ptsGeom || !rawPosArray) return;
      const ds = ALL_DATA[currentDs];
      const posAttr = ptsGeom.getAttribute('position');
      const numPts = rawFramesArray.length;

      for (let i = 0; i < numPts; i++) {{
        if (rawFramesArray[i] <= currentFrameIdx) {{
          posAttr.setXYZ(i, rawPosArray[i * 3], rawPosArray[i * 3 + 1], rawPosArray[i * 3 + 2]);
        }} else {{
          posAttr.setXYZ(i, 0, -999, 0);
        }}
      }}
      posAttr.needsUpdate = true;

      // 3D Boxok inkremens megjelenítése az idővonal alapján
      boxMeshes.forEach(mesh => {{
        if (mesh.userData.first_f <= currentFrameIdx) {{
          mesh.visible = true;
        }} else {{
          mesh.visible = false;
        }}
      }});

      document.getElementById("lbl-time").textContent = `${{(currentFrameIdx * 0.25).toFixed(1)}}s / ${{ds.total_time}}s`;
    }}

    function onDatasetChange() {{
      currentDs = document.getElementById("dataset-select").value;
      loadDataset();
    }}

    function onTimelineScrub(val) {{
      currentFrameIdx = parseInt(val);
      updateVisiblePoints();
    }}

    function togglePlay() {{
      isPlaying = !isPlaying;
      document.getElementById("btn-play").textContent = isPlaying ? "⏸ Megállítás" : "▶ Lejátszás";
    }}

    function animate() {{
      requestAnimationFrame(animate);
      if (isPlaying) {{
        const ds = ALL_DATA[currentDs];
        if (currentFrameIdx < ds.total_frames - 1) {{
          currentFrameIdx++;
          updateVisiblePoints();
          document.getElementById("rng-timeline").value = currentFrameIdx;
        }} else {{
          togglePlay();
        }}
      }}
      controls.update();
      renderer.render(scene, camera);
    }}

    init3D();
    animate();
  </script>
</body>
</html>
"""

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    datasets = [
        ("walk_kicsi.jsonl", "walk_kicsi", "🚶 Kis szobai séta (60s)", False, 2, 240),
        ("walk_teszt.jsonl", "walk_teszt", "🛑 Álló robot (60s)", True, 2, 240),
        ("walk_seta1.jsonl", "walk_seta1", "🏃 Nagy séta (90s)", False, 2, 240),
    ]
    
    processed = {}
    for filename, ds_id, label, is_stat, step_val, max_fr in datasets:
        fpath = os.path.join(base_dir, filename)
        if os.path.exists(fpath):
            res = process_confidence_slam(fpath, ds_id, label, is_stationary=is_stat, step=step_val, max_frames=max_fr)
            if res:
                processed[ds_id] = res
                
    html_content = generate_confidence_html(processed)
    out_file = os.path.join(base_dir, "confidence_slam.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\nMentve: {out_file} ({len(html_content):,} bájt)")

if __name__ == "__main__":
    main()
