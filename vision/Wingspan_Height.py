import os
import cv2
import time
import math
import json
import numpy as np
from PIL import Image
from datetime import datetime
from pathlib import Path
import requests

import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit  # init CUDA

# =========================
# CONFIG (edit as needed)
# =========================
CAM_INDEX = 0
FRAME_SIZE = (1280, 720)
COUNTDOWN_SECONDS = 5
NUM_PHOTOS = 3
PHOTO_GAP_SEC = 0.3

ENGINE_PATH = "deeplabv3_mobilenet.engine"
PIXEL_TO_CM = 0.345
ADDITIONAL_HEIGHT_CM = 80.0
OUTPUT_FOLDER = "output_segmentasi_deeplabv3_mobilenet"

# Supabase (be careful with secrets in code)
SUPABASE_URL = "https://ywxpzrdsxqcvnretymjr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3eHB6cmRzeHFjdm5yZXR5bWpyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA3Mzc0MjYsImV4cCI6MjA3NjMxMzQyNn0.plZizlUd6MEiafWMPWc3aikTEnCcQjW9QfmEIVYYp0Q"
SUPABASE_TABLE = "person_measurements"
SEND_TO_SUPABASE = True  # set False to skip sending


# =========================
# Utils: Supabase REST
# =========================
def send_to_supabase(row: dict):
    if not SEND_TO_SUPABASE:
        return True, "Skipped (disabled)"
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    try:
        r = requests.post(url, headers=headers, json=row, timeout=10)
        if r.status_code in (200, 201, 204):
            return True, "Success"
        return False, f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return False, str(e)


# =========================
# Webcam capture (your first script, compact)
# =========================
def capture_three_photos():
    # photos/<YYYYmmdd_HHMMSS>/
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("photos") / run_ts
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_SIZE[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_SIZE[1])

    start_time = time.time()
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                raise RuntimeError("Failed to read frame from webcam.")

            elapsed = time.time() - start_time
            remaining = max(0.0, COUNTDOWN_SECONDS - elapsed)

            overlay = frame.copy()
            text = f"Starting in: {math.ceil(remaining)}"
            cv2.putText(
                overlay, text, (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 4, cv2.LINE_AA
            )
            cv2.imshow("Webcam (press ESC to cancel)", overlay)

            if cv2.waitKey(1) & 0xFF == 27:
                raise KeyboardInterrupt("Canceled by user.")

            if remaining <= 0.0:
                time.sleep(0.1)
                for i in range(1, NUM_PHOTOS + 1):
                    ret, shot = cap.read()
                    if not ret:
                        print(f"[WARN] Could not grab photo {i}")
                        continue
                    filename = out_dir / f"photo_{i}.jpg"
                    cv2.imwrite(str(filename), shot)
                    time.sleep(PHOTO_GAP_SEC)
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return out_dir  # Path to folder with 3 photos


# =========================
# TensorRT helpers (yours)
# =========================
TRT_LOGGER = trt.Logger(trt.Logger.WARNING)

def load_engine(engine_path):
    with open(engine_path, "rb") as f, trt.Runtime(TRT_LOGGER) as runtime:
        return runtime.deserialize_cuda_engine(f.read())

def allocate_buffers(engine, context, batch_size=1):
    inputs, outputs, bindings = [], [], []
    stream = cuda.Stream()
    for binding_idx in range(engine.num_bindings):
        name = engine.get_binding_name(binding_idx)
        is_input = engine.binding_is_input(binding_idx)
        dtype = trt.nptype(engine.get_binding_dtype(binding_idx))

        shape = engine.get_binding_shape(binding_idx)
        if any(s <= 0 for s in shape):
            shape = (batch_size,) + tuple(dim if dim > 0 else 1 for dim in shape[1:])
            try:
                context.set_binding_shape(binding_idx, shape)
            except Exception:
                pass

        size = int(np.prod(shape))
        host_mem = cuda.pagelocked_empty(size, dtype)
        device_mem = cuda.mem_alloc(host_mem.nbytes)
        bindings.append(int(device_mem))
        item = {
            "name": name,
            "host_mem": host_mem,
            "device_mem": device_mem,
            "shape": shape,
            "dtype": dtype,
            "binding_idx": binding_idx,
            "is_input": is_input
        }
        if is_input:
            inputs.append(item)
        else:
            outputs.append(item)
    return inputs, outputs, bindings, stream

def do_inference(context, inputs, outputs, bindings, stream):
    for inp in inputs:
        cuda.memcpy_htod_async(inp["device_mem"], inp["host_mem"], stream)
    context.execute_async_v2(bindings=bindings, stream_handle=stream.handle)
    for out in outputs:
        cuda.memcpy_dtoh_async(out["host_mem"], out["device_mem"], stream)
    stream.synchronize()
    results = []
    for out in outputs:
        arr = np.array(out["host_mem"]).reshape(out["shape"])
        results.append((out["name"], arr))
    return results

def preprocess_image(image, size=(640, 360)):
    image = image.resize(size)
    img_np = np.array(image).astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img_np = (img_np - mean) / std
    img_np = np.transpose(img_np, (2, 0, 1))  # HWC->CHW
    return img_np


# =========================
# Segmentation + measurement for a folder (adapted)
# returns list[dict] hasil_data
# =========================
def segment_and_measure_person_folder_engine(
    input_folder,
    engine_path=ENGINE_PATH,
    output_folder=OUTPUT_FOLDER,
    pixel_to_cm_ratio=PIXEL_TO_CM,
    additional_height_cm=ADDITIONAL_HEIGHT_CM,
    batch_size=1
):
    os.makedirs(output_folder, exist_ok=True)

    engine = load_engine(engine_path)
    context = engine.create_execution_context()
    inputs, outputs, bindings, stream = allocate_buffers(engine, context, batch_size)
    input_binding = next(i for i in inputs)
    hasil_data = []

    for filename in sorted(os.listdir(input_folder)):
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        image_path = os.path.join(input_folder, filename)
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as e:
            print(f"[ERR] {filename}: gagal buka gambar ({e})")
            hasil_data.append({"filename": filename, "error": str(e)})
            continue

        img_np = preprocess_image(image)
        dtype = input_binding["dtype"]
        img_np = img_np.astype(dtype)

        try:
            input_binding["host_mem"][:] = img_np.ravel()
        except Exception as e:
            print(f"[ERR] {filename}: gagal isi input buffer ({e})")
            hasil_data.append({"filename": filename, "error": str(e)})
            continue

        try:
            results = do_inference(context, inputs, outputs, bindings, stream)
        except Exception as e:
            print(f"[ERR] {filename}: gagal inference ({e})")
            hasil_data.append({"filename": filename, "error": str(e)})
            continue

        out_name, out_arr = results[0]
        if out_arr.ndim == 4 and out_arr.shape[0] == 1:
            out_arr = out_arr[0]

        # class 15 = person (per your code/comment)
        person_class_index = 15
        person_mask = (np.argmax(out_arr, axis=0) == person_class_index).astype(np.uint8)
        person_pixels = np.where(person_mask > 0)

        if person_pixels[0].size > 0:
            left_pixel, right_pixel = np.min(person_pixels[1]), np.max(person_pixels[1])
            top_pixel, bottom_pixel = np.min(person_pixels[0]), np.max(person_pixels[0])

            width_px = right_pixel - left_pixel + 1
            height_px = bottom_pixel - top_pixel + 1

            width_cm = width_px * pixel_to_cm_ratio
            height_cm = height_px * pixel_to_cm_ratio
            adjusted_height_cm = height_cm + float(additional_height_cm)

            row = {
                "filename": filename,
                "width_pixels": int(width_px),
                "width_cm": round(float(width_cm), 2),
                "height_pixels": int(height_px),
                "height_cm": round(float(height_cm), 2),
                "adjustment_cm": float(additional_height_cm),
                "adjusted_height_cm": round(float(adjusted_height_cm), 2),
                "prediction": "Person detected",
                "source_folder": str(input_folder)
            }
            hasil_data.append(row)

            ok, msg = send_to_supabase(row)
            if ok:
                print(f"[SUPABASE] Data {filename} terkirim.")
            else:
                print(f"[WARN] gagal kirim {filename}: {msg}")

            print(f"[OK] {filename} -> W: {width_cm:.2f} cm, H(raw): {height_cm:.2f} cm, +{additional_height_cm} => H(adj): {adjusted_height_cm:.2f} cm")
        else:
            row = {"filename": filename, "prediction": "No person detected", "source_folder": str(input_folder)}
            hasil_data.append(row)
            print(f"[SKIP] {filename}: tidak ada orang terdeteksi")

    # Save raw per-photo results
    json_path = os.path.join(output_folder, "hasil_pengukuran.json")
    try:
        with open(json_path, "w") as f:
            json.dump(hasil_data, f, indent=4)
        print(f"\n>> Data pengukuran disimpan ke {json_path}")
    except Exception as e:
        print(f"[ERR] gagal menyimpan hasil ke {json_path}: {e}")

    return hasil_data


# =========================
# Consensus picker
# Rule:
# - Compute median of values.
# - Select all values within tol_cm OR tol_rel% of median.
# - If >=2 selected -> average them.
# - Else -> pick the median (single best).
# =========================
def consensus_from_values(values, abs_tol_cm=3.0, rel_tol=0.02):
    """
    values: list[float]
    Returns: dict with:
      - method: "average_close" or "median_only"
      - used_indices: list[int]
      - result: float
    """
    if not values:
        return {"method": "no_values", "used_indices": [], "result": None}

    vals = np.array(values, dtype=float)
    median_val = float(np.median(vals))
    tol = max(abs_tol_cm, abs(median_val) * rel_tol)
    close_mask = np.abs(vals - median_val) <= tol
    used_idx = np.where(close_mask)[0].tolist()

    if len(used_idx) >= 2:
        result = float(np.mean(vals[used_idx]))
        return {"method": "average_close", "used_indices": used_idx, "result": result}
    else:
        # pick the single closest to median (which is median by definition)
        # We’ll choose the actual sample closest to the median
        closest_idx = int(np.argmin(np.abs(vals - median_val)))
        return {"method": "median_only", "used_indices": [closest_idx], "result": float(vals[closest_idx])}


def build_consensus(hasil_data, abs_tol_cm=3.0, rel_tol=0.02):
    """
    Build consensus for adjusted_height_cm and width_cm among 'Person detected' rows.
    """
    valid_rows = [r for r in hasil_data if r.get("prediction") == "Person detected"]
    if not valid_rows:
        return {
            "status": "no_person_detected",
            "message": "Tidak ada foto dengan orang terdeteksi.",
        }

    heights = [r["adjusted_height_cm"] for r in valid_rows]
    widths  = [r["width_cm"] for r in valid_rows]

    h_cons = consensus_from_values(heights, abs_tol_cm, rel_tol)
    w_cons = consensus_from_values(widths,  abs_tol_cm, rel_tol)

    consensus = {
        "status": "ok",
        "rules": {"abs_tol_cm": abs_tol_cm, "rel_tol": rel_tol},
        "heights_cm": heights,
        "widths_cm": widths,
        "height_consensus": h_cons,
        "width_consensus": w_cons,
        "used_files_for_height": [valid_rows[i]["filename"] for i in h_cons.get("used_indices", [])],
        "used_files_for_width":  [valid_rows[i]["filename"] for i in w_cons.get("used_indices", [])],
    }

    # A final “row” to optionally send to Supabase
    final_row = {
        "filename": "CONSENSUS",
        "source_folder": valid_rows[0]["source_folder"],
        "prediction": "Consensus",
        "width_cm": round(w_cons["result"], 2) if w_cons["result"] is not None else None,
        "height_cm": None,  # keep raw height (without adjustment) if you like; here we emphasize adjusted
        "adjustment_cm": ADDITIONAL_HEIGHT_CM,
        "adjusted_height_cm": round(h_cons["result"], 2) if h_cons["result"] is not None else None,
        "note": f"height:{h_cons['method']} width:{w_cons['method']}"
    }

    return consensus, final_row


# =========================
# MAIN
# =========================
def main():
    # 1) Capture 3 photos -> folder
    photo_dir = capture_three_photos()
    print(f"[CAPTURE] Saved to: {photo_dir.resolve()}")

    # 2) Segment & measure that folder
    hasil_data = segment_and_measure_person_folder_engine(
        input_folder=str(photo_dir),
        engine_path=ENGINE_PATH,
        output_folder=OUTPUT_FOLDER,
        pixel_to_cm_ratio=PIXEL_TO_CM,
        additional_height_cm=ADDITIONAL_HEIGHT_CM,
        batch_size=1
    )

    # 3) Build consensus from the 3 results
    result = build_consensus(hasil_data, abs_tol_cm=3.0, rel_tol=0.02)
    if isinstance(result, dict) and result.get("status") == "no_person_detected":
        print("[CONSENSUS] No person detected in all photos.")
        # Save minimal consensus
        consensus_path = os.path.join(OUTPUT_FOLDER, "consensus.json")
        with open(consensus_path, "w") as f:
            json.dump(result, f, indent=4)
        print(f">> Consensus saved to {consensus_path}")
        return

    consensus, final_row = result

    # Save consensus JSON
    consensus_path = os.path.join(OUTPUT_FOLDER, "consensus.json")
    with open(consensus_path, "w") as f:
        json.dump(consensus, f, indent=4)
    print(f">> Consensus saved to {consensus_path}")

    # Send consensus to Supabase (optional)
    ok, msg = send_to_supabase(final_row)
    if ok:
        print("[SUPABASE] Consensus row sent.")
    else:
        print(f"[WARN] Consensus send failed: {msg}")

    # Print a friendly summary
    h = consensus["height_consensus"]["result"]
    w = consensus["width_consensus"]["result"]
    h_method = consensus["height_consensus"]["method"]
    w_method = consensus["width_consensus"]["method"]
    print("\n=== FINAL RESULT ===")
    print(f"Adjusted Height (cm) : {None if h is None else round(h, 2)} ({h_method})")
    print(f"Width (cm)           : {None if w is None else round(w, 2)} ({w_method})")
    print(f"Used files (height)  : {', '.join(consensus['used_files_for_height']) or '-'}")
    print(f"Used files (width)   : {', '.join(consensus['used_files_for_width']) or '-'}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[ABORTED] User canceled.")
    except Exception as e:
        print(f"[FATAL] {e}")
