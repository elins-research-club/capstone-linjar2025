import cv2
import time
import math
from datetime import datetime
from pathlib import Path

def main():
    # Create output folder: photos/<YYYYmmdd_HHMMSS>/
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("photos") / run_ts
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(0)  # change to 1/2... if you have multiple cameras
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Optional: try to set a reasonable resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    countdown_seconds = 5
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to read frame from webcam.")
                break

            # Compute remaining countdown
            elapsed = time.time() - start_time
            remaining = max(0.0, countdown_seconds - elapsed)

            # Draw countdown text on the frame
            overlay = frame.copy()
            text = f"Starting in: {math.ceil(remaining)}"
            cv2.putText(
                overlay, text, (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 4, cv2.LINE_AA
            )

            cv2.imshow("Webcam (press ESC to cancel)", overlay)

            # Exit on ESC
            if cv2.waitKey(1) & 0xFF == 27:
                print("Canceled by user.")
                return

            # When countdown done, take 3 photos
            if remaining <= 0.0:
                # Small pause to avoid capturing the exact overlay frame
                time.sleep(0.1)
                for i in range(1, 4):
                    # Grab a fresh frame for each shot
                    ret, shot = cap.read()
                    if not ret:
                        print("Warning: Could not grab photo", i)
                        continue
                    filename = out_dir / f"photo_{i}.jpg"
                    cv2.imwrite(str(filename), shot)
                    # brief gap between shots so they differ
                    time.sleep(0.3)
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    print(f"Saved 3 photos to: {out_dir.resolve()}")

if __name__ == "__main__":
    main()
