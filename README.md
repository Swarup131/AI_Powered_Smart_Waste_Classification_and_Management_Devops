# ♻️ AI-Based Smart Waste Segregation System

A runnable, **CPU-friendly Streamlit demo** for image-based waste segregation, with a DevOps pipeline (Docker + GitHub Actions). Built by **Swarup**.

![Smart Waste Segregation UI preview](assets/ui-preview.png)

> The image above is an illustrative render of the interface. To use a real screenshot, run the app, take a screenshot and save it as `assets/ui-preview.png`.

## Features
- **Upload or camera capture:** use a JPG, JPEG, PNG or WEBP file, or take a photo directly in the browser.
- **Instance segmentation:** a pre-trained YOLO11 segmentation model outlines each detected object.
- **Confirm categories:** the app suggests a waste category for each object and you can correct it.
- **Area analysis:** visible pixel-area share per category, with a donut chart and table.
- **Recoverable share:** the part of the detected area that has a clear route (recycle, compost or reuse).
- **Disposal guide:** bin colour, route and a short tip for every category found.
- **Exports:** CSV area report, full JSON report and the annotated segmentation image (PNG).
- **History:** save analyses during a session and see combined category shares and averages.

## Important model limitation
This demo uses `yolo11n-seg.pt`, a general pre-trained segmentation model. It is **not trained on the DWSD dataset** and does not automatically recognise the project's custom Plastic / Metal / Paper / Cloth / Glass classes. Object-to-waste category suggestions are only rough hints; the user must confirm them. Do not describe this as a custom-trained waste classifier.

The percentages are visible pixel-area estimates, not physical weight percentages. Bin colours follow a common colour-coded scheme, so check your local municipality's rules.

## Project structure
```
app.py            Streamlit UI (Analyse / History / About tabs)
waste_utils.py    Detection parsing, area calculation, overlay, reports
theme.py          CSS and HTML builders for the interface
tests/            Unit tests for the logic in waste_utils.py
.streamlit/       Theme and server settings
Dockerfile, docker-compose.yml, .github/workflows/ci-cd.yml
```

## Run on Windows (VS Code)
1. Extract this ZIP and open the folder in VS Code.
2. Open a terminal in that folder.
3. (Recommended) create and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
4. Install and launch:
   ```powershell
   pip install -r requirements.txt
   streamlit run app.py
   ```
   Or double-click `run_windows.bat`.
5. Open the local URL shown in the terminal, usually `http://localhost:8501`.

## Run with Docker
```bash
docker compose up --build
```
Then open `http://localhost:8501`.

## Run the tests
```bash
pip install pytest
python -m pytest -q tests
```

## CI/CD
The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) installs dependencies, checks Python syntax, runs the unit tests and, on a push to `main`, builds and pushes the Docker image to Docker Hub as `swarup/waste-segregation-app:latest`. Add `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` as repository secrets, and make sure the image name matches your Docker Hub username.

## First run
`yolo11n-seg.pt` is bundled in this repository. If it is missing, Ultralytics downloads it on the first run, which needs an internet connection. Inference runs on CPU, so large images may take a little longer.

## Dataset and training
The converted DWSD dataset is not included because the model has not been trained on it.
