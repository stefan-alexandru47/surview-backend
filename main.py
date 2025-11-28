from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import cv2, os
from ultralytics import YOLO
import tempfile
import shutil

app = FastAPI()

# Add CORS middleware - CRITICAL for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Load model
model = YOLO("models/best.pt")

# Health check endpoint - REQUIRED for Railway
@app.get("/")
async def root():
    return {"message": "Crack Detection API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/upload")
async def upload_video(video: UploadFile = File(...)):
    # Use temporary files since Railway has ephemeral storage
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_input:
        try:
            # Save uploaded video to temp file
            content = await video.read()
            temp_input.write(content)
            temp_input_path = temp_input.name

            # Process video
            cap = cv2.VideoCapture(temp_input_path)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

            # ----------------------------
            # Stats variables
            # ----------------------------
            total_crack_area = 0.0
            total_frame_area = width * height
            total_crack_count = 0
            num_frames = 0
            crack_density_per_frame = []

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                num_frames += 1

                # Downscale frame for faster inference
                small_frame = cv2.resize(frame, (640, 360))
                results = model(small_frame)

                # Scale boxes back to original resolution for stats
                scale_x = width / 640
                scale_y = height / 360

                frame_crack_area = 0.0
                crack_count = len(results[0].boxes) if results[0].boxes is not None else 0

                if results[0].boxes is not None:
                    for box in results[0].boxes.xyxy:
                        x1, y1, x2, y2 = box
                        w = max((x2 - x1) * scale_x, 0)
                        h = max((y2 - y1) * scale_y, 0)
                        frame_crack_area += w * h

                total_crack_area += frame_crack_area
                total_crack_count += crack_count
                
                # Calculate and store crack density for this frame
                frame_crack_density = (frame_crack_area / total_frame_area) * 100 if total_frame_area > 0 else 0
                crack_density_per_frame.append(float(frame_crack_density))

            cap.release()

            # ----------------------------
            # Final Stats
            # ----------------------------
            avg_crack_density = total_crack_count / num_frames if num_frames > 0 else 0
            
            if num_frames > 0 and total_frame_area > 0:
                crack_coverage = total_crack_area / (total_frame_area * num_frames)
            else:
                crack_coverage = 0.0
            
            coverage_percentage = float(crack_coverage * 100)

            return {
                "status": "success",
                "stats": {
                    "coverage_percentage": round(coverage_percentage, 2),
                    "avg_cracks_per_frame": round(avg_crack_density, 2),
                    "crack_density_per_frame": [round(x, 2) for x in crack_density_per_frame],
                    "total_frames_processed": num_frames,
                    "total_cracks_detected": total_crack_count
                }
            }

        except Exception as e:
            return {"error": f"Processing failed: {str(e)}"}
        finally:
            # Clean up temp file
            if os.path.exists(temp_input_path):
                os.unlink(temp_input_path)

# Note: We removed video writing and static file serving because 
# Railway has ephemeral storage and can't serve static files easily