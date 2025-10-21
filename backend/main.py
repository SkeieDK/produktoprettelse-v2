from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi import UploadFile, File, Request
import subprocess
from fastapi import UploadFile, File
import os
import json
import shutil
from PIL import Image
import unicodedata
import re
from typing import Optional
import uuid
from datetime import datetime
import sys

app = FastAPI()

# Global exception logging middleware: ensures unhandled exceptions are logged
@app.middleware("http")
async def log_exceptions(request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        # Log full traceback to a file for debugging (avoid crashing the process)
        import traceback, logging
        logging.exception("Unhandled exception during request: %s", exc)
        tb = traceback.format_exc()
        try:
            logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
            os.makedirs(logs_dir, exist_ok=True)
            with open(os.path.join(logs_dir, 'backend_exceptions.log'), 'a', encoding='utf-8') as f:
                f.write(f"--- {datetime.utcnow().isoformat()}Z {request.method} {request.url}\n")
                f.write(tb + "\n")
        except Exception:
            pass
        # Return a JSON 500 so the frontend sees an error but the server keeps running
        return JSONResponse(status_code=500, content={"error": "internal_server_error", "detail": str(exc)})

# Simple in-memory job store. In production swap for a persistent store or queue.
JOBS = {}

# Serve the cache folder (images, run_summary) under /static/cache
cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache'))
if os.path.isdir(cache_dir):
    app.mount("/static/cache", StaticFiles(directory=cache_dir), name="cache")

@app.get("/")
def read_root():
    return {"status": "Backend API is running"}

@app.post("/run-scraper")
def run_scraper(background_tasks: BackgroundTasks):
    # create a job id and enqueue background task
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        'job_id': job_id,
        'status': 'queued',
        'started_at': None,
        'finished_at': None,
        'message': None
    }

    def scraper_task(job_id_local=job_id):
        project_root = os.path.dirname(os.path.dirname(__file__))
        # update job status
        JOBS[job_id_local]['status'] = 'running'
        JOBS[job_id_local]['started_at'] = datetime.utcnow().isoformat() + 'Z'
        try:
            # Run the scraper script in a subprocess using the running Python interpreter
            python_exe = sys.executable or 'python'
            # capture output so we can surface logs on failure and persist them
            # run as a package module so imports like 'supplier_pi.utils' resolve
            proc = subprocess.run([python_exe, "-m", "supplier_pi.supplier_scraper"], cwd=project_root, capture_output=True, text=True)
            # write job log
            try:
                logs_dir = os.path.join(project_root, 'logs')
                os.makedirs(logs_dir, exist_ok=True)
                with open(os.path.join(logs_dir, f'job_{job_id_local}.log'), 'w', encoding='utf-8') as lf:
                    lf.write('=== STDOUT ===\n')
                    lf.write(proc.stdout or '')
                    lf.write('\n=== STDERR ===\n')
                    lf.write(proc.stderr or '')
            except Exception:
                pass
            # treat non-zero exit as failure
            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, proc.args, output=proc.stdout, stderr=proc.stderr)

            # after scraper completes, process images so frontend can consume thumbnails
            try:
                base = "http://127.0.0.1:8000"
                process_images(base_url=base, write_back=True, project_root=project_root)
            except Exception as e:
                # non-fatal image processing error
                JOBS[job_id_local]['message'] = f'images_error: {e}'

            JOBS[job_id_local]['status'] = 'done'
            JOBS[job_id_local]['finished_at'] = datetime.utcnow().isoformat() + 'Z'
        except subprocess.CalledProcessError as e:
            # Ensure we have a log file reference for debugging
            try:
                logs_dir = os.path.join(project_root, 'logs')
                log_path = os.path.join(logs_dir, f'job_{job_id_local}.log')
                # append error summary if not present
                with open(log_path, 'a', encoding='utf-8') as lf:
                    lf.write('\n=== CALLEDPROCESSERROR ===\n')
                    lf.write(str(e) + '\n')
                    lf.write(getattr(e, 'stderr', '') or '')
            except Exception:
                log_path = None

            JOBS[job_id_local]['status'] = 'failed'
            JOBS[job_id_local]['finished_at'] = datetime.utcnow().isoformat() + 'Z'
            JOBS[job_id_local]['message'] = f'scraper_error: exit {getattr(e, "returncode", "?")}; log={log_path}'
        except Exception as e:
            JOBS[job_id_local]['status'] = 'failed'
            JOBS[job_id_local]['finished_at'] = datetime.utcnow().isoformat() + 'Z'
            JOBS[job_id_local]['message'] = f'error: {e}'

    background_tasks.add_task(scraper_task)
    return {"job_id": job_id, "status": "queued"}


@app.get('/jobs/{job_id}')
def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return {"error": "job not found"}
    return job


def slugify(value: str) -> str:
    """Simplistic slugify: normalize unicode, remove non-alphanum, replace spaces with underscores."""
    if not value:
        return ""
    value = str(value)
    value = unicodedata.normalize('NFKD', value)
    value = value.encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r"[^\w\s-]", '', value).strip().lower()
    value = re.sub(r"[-\s]+", '_', value)
    return value


def process_images(*, data=None, base_url: str = 'http://127.0.0.1:8000', write_back: bool = False, project_root: Optional[str] = None):
    """Copy image files found in supplier data into cache/public_images, generate thumbnails,
    and rewrite `images` entries to objects with 'url' and 'thumbnail'.

    If `data` is None the function will try to load `cache/supplier_info_output.json` from project_root.
    If write_back is True and data was loaded from file, the function saves the modified JSON back.
    Returns a dict summary {copied: int, processed: int} and the modified data.
    """
    # resolve project_root
    if project_root is None:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    cache_dir_local = os.path.abspath(os.path.join(project_root, 'cache'))
    output_json_path = os.path.join(cache_dir_local, 'supplier_info_output.json')

    loaded_from_file = False
    if data is None:
        if not os.path.exists(output_json_path):
            return {'error': 'no_data_file'}
        try:
            with open(output_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            loaded_from_file = True
        except Exception as e:
            return {'error': f'failed_load:{e}'}

    public_dir = os.path.join(cache_dir_local, 'public_images')
    os.makedirs(public_dir, exist_ok=True)
    thumb_dir = os.path.join(public_dir, 'thumbnails')
    os.makedirs(thumb_dir, exist_ok=True)

    copied = 0
    processed = 0

    for item in data:
        imgs = item.get('images', []) or []
        public_imgs = []
        for p in imgs:
            try:
                # if entry is already an object with url, skip
                if isinstance(p, dict) and ('url' in p or 'thumbnail' in p):
                    public_imgs.append(p)
                    continue

                # coerce to string for path operations (guards against unexpected types)
                p_str = p if isinstance(p, str) else str(p)

                # resolve absolute path
                if os.path.isabs(p_str):
                    abs_p = p_str
                else:
                    abs_p = os.path.normpath(os.path.join(project_root, p_str))

                if os.path.exists(abs_p) and os.path.isfile(abs_p):
                    base_name = os.path.basename(p_str)
                    prefix = slugify(str(item.get('product_number', '')) ) or 'img'
                    # normalize filename
                    name_no_ext, ext = os.path.splitext(base_name)
                    clean_name = slugify(name_no_ext)
                    dest_name = f"{prefix}_{clean_name}{ext.lower()}"
                    dest_path = os.path.join(public_dir, dest_name)
                    if not os.path.exists(dest_path):
                        try:
                            shutil.copy2(abs_p, dest_path)
                            copied += 1
                        except Exception:
                            pass

                    # generate thumbnail
                    thumb_dest = os.path.join(thumb_dir, dest_name)
                    try:
                        if not os.path.exists(thumb_dest):
                            with Image.open(dest_path) as im:
                                im.thumbnail((150, 150))
                                im.convert('RGB').save(thumb_dest, 'JPEG', quality=85)
                    except Exception:
                        # ignore thumb errors
                        pass

                    base = base_url.rstrip('/')
                    public_imgs.append({
                        'url': f"{base}/static/cache/public_images/{dest_name}",
                        'thumbnail': f"{base}/static/cache/public_images/thumbnails/{dest_name}" if os.path.exists(os.path.join(thumb_dir, dest_name)) else None
                    })
                    processed += 1
                    continue

                # fallback: maybe the path is already inside cache
                candidate = os.path.join(cache_dir_local, p_str)
                if os.path.exists(candidate):
                    base = base_url.rstrip('/')
                    public_imgs.append({
                        'url': f"{base}/static/cache/{p}",
                        'thumbnail': None
                    })
                    processed += 1
            except Exception:
                continue

        item['images'] = public_imgs

    if write_back and loaded_from_file:
        try:
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            return {'error': f'failed_write:{e}', 'copied': copied, 'processed': processed, 'data': data}

    return {'copied': copied, 'processed': processed, 'data': data}

@app.get("/results")
def get_results(request: Request):
    # Path to the supplier info output JSON (now project-local)
    output_json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache', 'supplier_info_output.json'))
    summary_json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache', 'run_summary.json'))
    if os.path.exists(output_json_path):
        try:
            with open(output_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # load run summary if present and merge by product_number
            summaries = {}
            if os.path.exists(summary_json_path):
                try:
                    with open(summary_json_path, 'r', encoding='utf-8') as sf:
                        run_summ = json.load(sf)
                        for item in run_summ:
                            key = item.get('product_number')
                            if key:
                                summaries[str(key)] = item
                except Exception:
                    pass

            # rewrite image paths to static URLs and attach summary info
            for item in data:
                # attach run summary if available
                pn = str(item.get('product_number', ''))
                if pn in summaries:
                    item['run_summary'] = summaries[pn]
                else:
                    item['run_summary'] = None

                # rewrite images to static URLs under /static/cache
                    imgs = item.get('images', [])
                    public_imgs = []
                    for p in imgs:
                        # p is a project-relative path (may point outside cache)
                        try:
                            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                            abs_p = os.path.normpath(os.path.join(project_root, p))
                            # destination public images folder inside cache
                            public_dir = os.path.join(cache_dir, 'public_images')
                            os.makedirs(public_dir, exist_ok=True)

                            if os.path.exists(abs_p):
                                # copy to cache/public_images with product prefix to avoid collisions
                                base = os.path.basename(p)
                                prefix = str(item.get('product_number', '')).replace('/', '_') or 'img'
                                dest_name = f"{prefix}_{base}"
                                dest_path = os.path.join(public_dir, dest_name)
                                if not os.path.exists(dest_path):
                                    try:
                                        shutil.copy2(abs_p, dest_path)
                                    except Exception:
                                        pass

                                # generate thumbnail (150x150) next to the copied file
                                try:
                                    thumb_dir = os.path.join(public_dir, 'thumbnails')
                                    os.makedirs(thumb_dir, exist_ok=True)
                                    thumb_path = os.path.join(thumb_dir, dest_name)
                                    if not os.path.exists(thumb_path):
                                        with Image.open(dest_path) as im:
                                            im.thumbnail((150, 150))
                                            im.convert('RGB').save(thumb_path, 'JPEG', quality=85)
                                except Exception:
                                    thumb_path = None

                                # Use backend base URL so the frontend (vite) requests the backend for the image
                                base = str(request.base_url).rstrip('/')
                                public_imgs.append({
                                    'url': f"{base}/static/cache/public_images/{dest_name}",
                                    'thumbnail': f"{base}/static/cache/public_images/thumbnails/{dest_name}" if os.path.exists(os.path.join(public_dir, 'thumbnails', dest_name)) else None
                                })
                                continue

                            # fallback: maybe the path is already inside cache
                            candidate = os.path.join(cache_dir, p)
                            if os.path.exists(candidate):
                                base = str(request.base_url).rstrip('/')
                                public_imgs.append({
                                    'url': f"{base}/static/cache/{p}",
                                    'thumbnail': None
                                })
                                continue

                            # last resort: ignore missing
                        except Exception:
                            continue
                    item['images'] = public_imgs

            return JSONResponse(content=data, media_type="application/json")
        except Exception as e:
            return {"error": f"Failed to read results: {e}"}
    else:
        return {"status": "No results found yet"}


@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Accept a CSV upload and save it to cache/uploads — processing is a separate step.

    This async handler uses await file.read() and logs detailed information to
    logs/upload.log so we can diagnose multipart upload issues without crashing the server.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    uploads_dir = os.path.join(project_root, 'cache', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    filename = os.path.basename(file.filename)
    save_path = os.path.join(uploads_dir, filename)
    try:
        data = await file.read()
        with open(save_path, 'wb') as out_f:
            out_f.write(data)
        # Log upload
        try:
            logs_dir = os.path.join(project_root, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            with open(os.path.join(logs_dir, 'upload.log'), 'a', encoding='utf-8') as lf:
                lf.write(f"{datetime.utcnow().isoformat()}Z UPLOAD {filename} size={len(data)}\n")
        except Exception:
            pass
    except Exception as e:
        # Log and return a helpful error without crashing
        try:
            logs_dir = os.path.join(project_root, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            with open(os.path.join(logs_dir, 'upload_errors.log'), 'a', encoding='utf-8') as lf:
                lf.write(f"{datetime.utcnow().isoformat()}Z UPLOAD_ERROR {filename} error={e}\n")
        except Exception:
            pass
        return JSONResponse(status_code=500, content={"error": f"Failed to save upload: {e}"})

    return {"status": "uploaded", "filename": filename}


@app.post('/process-csv')
def process_csv(filename: Optional[str] = None):
    """Process a previously uploaded CSV (filename relative to cache/uploads). If no filename
    is provided, process the most recently uploaded file.
    Writes cache/processed_products.json and returns row count.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    uploads_dir = os.path.join(project_root, 'cache', 'uploads')
    if filename:
        upload_path = os.path.join(uploads_dir, os.path.basename(filename))
    else:
        # pick latest file in uploads_dir
        files = [os.path.join(uploads_dir, f) for f in os.listdir(uploads_dir)] if os.path.isdir(uploads_dir) else []
        if not files:
            return JSONResponse(status_code=400, content={"error": "no uploads available"})
        upload_path = max(files, key=os.path.getmtime)

    if not os.path.exists(upload_path):
        return JSONResponse(status_code=400, content={"error": "upload file not found"})

    try:
        import pandas as pd
        from csv_data_transformation.sanitering import CSVSanitering
        df = pd.read_csv(upload_path)
        san = CSVSanitering(df)
        processed_df = san.process()
        out_path = os.path.join(project_root, 'cache', 'processed_products.json')
        san.to_json(out_path)
        return {"status": "processed", "rows": len(processed_df)}
    except Exception as e:
        # write detailed error for diagnosis
        try:
            logs_dir = os.path.join(project_root, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            with open(os.path.join(logs_dir, 'process_csv_errors.log'), 'a', encoding='utf-8') as lf:
                import traceback
                lf.write(f"{datetime.utcnow().isoformat()}Z PROCESS_CSV_ERROR file={upload_path} error={e}\n")
                lf.write(traceback.format_exc() + "\n")
        except Exception:
            pass
        return JSONResponse(status_code=500, content={"error": f"Processing failed: {e}"})


@app.get('/processed')
def get_processed():
    """Return the processed_products.json if present for UI preview."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    processed_path = os.path.join(project_root, 'cache', 'processed_products.json')
    if not os.path.exists(processed_path):
        return JSONResponse(status_code=404, content={"error": "no processed file"})
    try:
        with open(processed_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to read processed file: {e}"})


@app.post("/fix-images")
def fix_images(request: Request):
    """Scan supplier_info_output.json for image file paths, copy files into cache/public_images,
    and rewrite the images entries to absolute URLs under /static/cache/public_images/.
    Returns a summary of copied files.
    """
    # defer to process_images helper which centralizes copy + thumbnail logic
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    base = str(request.base_url).rstrip('/')
    result = process_images(base_url=base, write_back=True, project_root=project_root)
    return result
