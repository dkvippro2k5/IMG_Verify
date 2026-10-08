"""Trích đặc trưng mặt cho ảnh golden: SCRFD (detect + 5 điểm mốc) và ArcFace (embedding).

Dùng model ONNX trong bộ buffalo_l của InsightFace (giấy phép phi thương mại, dự án nghiên cứu),
chạy bằng onnxruntime trên CPU, không cần cài gói insightface.

Đầu ra (golden/features/):
  faces.json      mỗi ảnh: kích thước, danh sách mặt (bbox, điểm tin cậy, landmarks, diện tích %, độ nét, yaw)
  embeddings.npy  ma trận (số mặt, 512) đã chuẩn hóa L2; faces.json trỏ tới bằng chỉ số "emb"

Chạy: .venv/Scripts/python tools/extract_faces.py [golden|scope]
(scope: đọc scope/manifest.json, ghi scope/features/, chạy tiếp được khi bị dừng)
"""
import glob
import json
import os
import sys
import time

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "golden")
OUT = os.path.join(GOLDEN, "features")
MODEL_DIR = os.path.join(ROOT, "models", "buffalo_l")

DET_SIZE = 640
DET_THRESH = 0.5
NMS_THRESH = 0.4
ARCFACE_DST = np.array([[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
                        [41.5493, 92.3655], [70.7299, 92.2041]], dtype=np.float32)


def find_model(name):
    hits = glob.glob(os.path.join(MODEL_DIR, "**", name), recursive=True)
    if not hits:
        raise FileNotFoundError(f"Không thấy {name} trong {MODEL_DIR}")
    return hits[0]


def session(path):
    opts = ort.SessionOptions()
    # Dùng hết luồng (22) trên Core Ultra chậm hơn ~10 lần do tranh chấp; 6 luồng nhanh nhất khi đo.
    opts.intra_op_num_threads = 6
    return ort.InferenceSession(path, opts, providers=["CPUExecutionProvider"])


class SCRFD:
    strides = (8, 16, 32)
    num_anchors = 2

    def __init__(self, path):
        self.sess = session(path)
        self.input_name = self.sess.get_inputs()[0].name
        self._centers = {}

    def _anchor_centers(self, h, w, stride):
        key = (h, w, stride)
        if key not in self._centers:
            c = np.stack(np.mgrid[:h, :w][::-1], axis=-1).astype(np.float32)
            c = (c * stride).reshape(-1, 2)
            self._centers[key] = np.stack([c] * self.num_anchors, axis=1).reshape(-1, 2)
        return self._centers[key]

    def detect(self, img):
        h, w = img.shape[:2]
        if h / w > 1:
            nh, nw = DET_SIZE, int(DET_SIZE * w / h)
        else:
            nw, nh = DET_SIZE, int(DET_SIZE * h / w)
        scale = nh / h
        canvas = np.zeros((DET_SIZE, DET_SIZE, 3), dtype=np.uint8)
        canvas[:nh, :nw] = cv2.resize(img, (nw, nh))
        blob = cv2.dnn.blobFromImage(canvas, 1.0 / 128, (DET_SIZE, DET_SIZE), (127.5, 127.5, 127.5), swapRB=True)
        outs = self.sess.run(None, {self.input_name: blob})

        scores_all, boxes_all, kps_all = [], [], []
        fmc = len(self.strides)
        for i, stride in enumerate(self.strides):
            scores = outs[i].reshape(-1)
            boxes = outs[i + fmc].reshape(-1, 4) * stride
            kps = outs[i + 2 * fmc].reshape(-1, 10) * stride
            centers = self._anchor_centers(DET_SIZE // stride, DET_SIZE // stride, stride)
            keep = np.where(scores >= DET_THRESH)[0]
            if not len(keep):
                continue
            c = centers[keep]
            b = boxes[keep]
            scores_all.append(scores[keep])
            boxes_all.append(np.stack([c[:, 0] - b[:, 0], c[:, 1] - b[:, 1], c[:, 0] + b[:, 2], c[:, 1] + b[:, 3]], axis=1))
            k = kps[keep].reshape(-1, 5, 2) + c[:, None, :]
            kps_all.append(k)
        if not scores_all:
            return np.zeros((0, 5)), np.zeros((0, 5, 2))
        scores = np.concatenate(scores_all)
        boxes = np.concatenate(boxes_all) / scale
        kps = np.concatenate(kps_all) / scale
        order = self._nms(boxes, scores)
        return np.hstack([boxes[order], scores[order, None]]), kps[order]

    @staticmethod
    def _nms(boxes, scores):
        x1, y1, x2, y2 = boxes.T
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]
        keep = []
        while order.size:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            inter = np.maximum(0, xx2 - xx1 + 1) * np.maximum(0, yy2 - yy1 + 1)
            iou = inter / (areas[i] + areas[order[1:]] - inter)
            order = order[np.where(iou <= NMS_THRESH)[0] + 1]
        return np.array(keep, dtype=int)


class ArcFace:
    def __init__(self, path):
        self.sess = session(path)
        self.input_name = self.sess.get_inputs()[0].name

    @staticmethod
    def align(img, kps):
        m, _ = cv2.estimateAffinePartial2D(kps.astype(np.float32), ARCFACE_DST, method=cv2.LMEDS)
        return cv2.warpAffine(img, m, (112, 112), borderValue=0)

    def embed(self, crops):
        blob = cv2.dnn.blobFromImages(crops, 1.0 / 127.5, (112, 112), (127.5, 127.5, 127.5), swapRB=True)
        feats = self.sess.run(None, {self.input_name: blob})[0]
        return feats / np.linalg.norm(feats, axis=1, keepdims=True)


def read_image(path):
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)


def yaw_proxy(k):
    """Lệch của mũi so với giữa hai mắt, chia cho khoảng cách hai mắt (0 = nhìn thẳng)."""
    eye_mid = (k[0] + k[1]) / 2
    eye_dist = np.linalg.norm(k[1] - k[0]) + 1e-6
    return float((k[2][0] - eye_mid[0]) / eye_dist)


def process(img, det, rec, timing):
    """Detect + embedding một ảnh. Trả về (danh sách mặt chưa gán chỉ số emb, ma trận embedding)."""
    h, w = img.shape[:2]
    t = time.time()
    boxes, kpss = det.detect(img)
    timing["det"] += time.time() - t
    crops = [ArcFace.align(img, k) for k in kpss]
    t = time.time()
    feats = rec.embed(crops) if crops else np.zeros((0, 512), dtype=np.float32)
    timing["rec"] += time.time() - t
    faces = []
    for (x1, y1, x2, y2, score), k, crop in zip(boxes, kpss, crops):
        fw, fh = max(0.0, x2 - x1), max(0.0, y2 - y1)
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        faces.append({
            "bbox": [round(float(v), 1) for v in (x1, y1, x2, y2)],
            "score": round(float(score), 4),
            "kps": [[round(float(a), 1), round(float(b), 1)] for a, b in k],
            "area_pct": round(float(100 * fw * fh / (w * h)), 3),
            "size_px": round(float(min(fw, fh)), 1),
            "blur": round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 1),
            "yaw": round(yaw_proxy(k), 3),
        })
    return faces, feats.astype(np.float32)


def run_golden(det, rec):
    """Golden: ghi faces.json + embeddings.npy (định dạng cũ, eval_identity.py đang dùng)."""
    os.makedirs(OUT, exist_ok=True)
    text = open(os.path.join(GOLDEN, "data.js"), encoding="utf-8").read()
    data = json.loads(text[text.index("["):text.rindex("]") + 1])
    records, embs = [], []
    timing = {"det": 0.0, "rec": 0.0}
    for r in data:
        out = {"line_no": r["line_no"], "slug": r["slug"], "faces": [], "error": ""}
        try:
            img = read_image(os.path.join(GOLDEN, r["local_image"])) if r.get("local_image") else None
        except Exception as e:
            img, out["error"] = None, f"read_error: {e}"
        if img is None:
            out["error"] = out["error"] or "no_image"
        else:
            out.update(width=img.shape[1], height=img.shape[0])
            faces, feats = process(img, det, rec, timing)
            for f, e in zip(faces, feats):
                f["emb"] = len(embs)
                embs.append(e)
            out["faces"] = faces
        records.append(out)
    np.save(os.path.join(OUT, "embeddings.npy"), np.array(embs, dtype=np.float32).reshape(-1, 512))
    with open(os.path.join(OUT, "faces.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)
    print(f"Golden: {len(records)} ảnh, {len(embs)} mặt")


def run_scope(det, rec, items=None):
    """Phạm vi làm việc (hoặc một phần: items), chạy tiếp được khi bị dừng.
    scope/features/faces.jsonl (mỗi dòng 1 ảnh) + embeddings.f32 (float32 nối liên tiếp, 512 chiều/mặt)."""
    scope = os.path.join(ROOT, "scope")
    out_dir = os.path.join(scope, "features")
    os.makedirs(out_dir, exist_ok=True)
    if items is None:
        items = json.load(open(os.path.join(scope, "manifest.json"), encoding="utf-8"))
    jsonl = os.path.join(out_dir, "faces.jsonl")
    embf = os.path.join(out_dir, "embeddings.f32")

    done, n_emb = set(), 0
    if os.path.exists(jsonl):
        with open(jsonl, encoding="utf-8") as f:
            for line in f:
                try:
                    rec_ = json.loads(line)
                except json.JSONDecodeError:
                    break  # dòng cuối ghi dở khi bị dừng
                if rec_.get("error") != "no_image":  # ảnh chưa tải được lần trước: thử lại
                    done.add((rec_["entity_id"], rec_["sha256"]))
                n_emb = max([n_emb] + [fc["emb"] + 1 for fc in rec_["faces"]])
    # Cắt phần embedding thừa (ghi xong embedding nhưng chưa kịp ghi dòng jsonl).
    if os.path.exists(embf):
        with open(embf, "r+b") as f:
            f.truncate(n_emb * 512 * 4)
    # Viết lại jsonl chỉ gồm các dòng hợp lệ.
    if done:
        good = []
        with open(jsonl, encoding="utf-8") as f:
            for line in f:
                try:
                    json.loads(line)
                    good.append(line if line.endswith("\n") else line + "\n")
                except json.JSONDecodeError:
                    break
        with open(jsonl, "w", encoding="utf-8") as f:
            f.writelines(good)

    todo = [it for it in items if (it["entity_id"], it["sha256"]) not in done]
    print(f"Đã có {len(done)} ảnh, còn {len(todo)} ảnh", flush=True)
    timing = {"det": 0.0, "rec": 0.0}
    t0 = time.time()
    with open(jsonl, "a", encoding="utf-8") as fj, open(embf, "ab") as fe:
        for n, it in enumerate(todo, 1):
            out = {"entity_id": it["entity_id"], "sha256": it["sha256"], "line_no": it["line_no"],
                   "slug": it["slug"], "faces": [], "error": ""}
            path = os.path.join(scope, "images", it["image_file"])
            img = None
            if it.get("download_error") or not os.path.exists(path):
                out["error"] = "no_image"
            else:
                try:
                    img = read_image(path)
                except Exception as e:
                    out["error"] = f"read_error: {e}"
            if img is not None:
                out.update(width=img.shape[1], height=img.shape[0])
                faces, feats = process(img, det, rec, timing)
                for f, e in zip(faces, feats):
                    f["emb"] = n_emb
                    n_emb += 1
                fe.write(feats.tobytes())
                fe.flush()
                out["faces"] = faces
            fj.write(json.dumps(out, ensure_ascii=False) + "\n")
            fj.flush()
            if n % 100 == 0:
                el = time.time() - t0
                print(f"{n}/{len(todo)} ảnh, {el:.0f}s, còn ~{el / n * (len(todo) - n) / 60:.0f} phút", flush=True)
    print(f"Xong. {n_emb} mặt. detect {1000 * timing['det'] / max(len(todo), 1):.0f} ms/ảnh, "
          f"tổng {time.time() - t0:.0f}s", flush=True)


def main():
    det = SCRFD(find_model("det_10g.onnx"))
    rec = ArcFace(find_model("w600k_r50.onnx"))
    target = sys.argv[1] if len(sys.argv) > 1 else "golden"
    if target == "scope":
        run_scope(det, rec)
    else:
        run_golden(det, rec)


if __name__ == "__main__":
    main()
