# Public speed-test deployment

This is a Flask application, so GitHub Pages alone cannot run it. The included `render.yaml` deploys the app as a public Render web service using Gunicorn.

## Publish the source on GitHub

Create a **public** repository, for example `veloce-internet-speed-test`, then upload only these files from this workspace:

- `.gitignore`
- `.python-version`
- `internetspedd.py`
- `render.yaml`
- `requirements.txt`
- `SPEEDTEST_DEPLOYMENT.md`

Do not upload `.venv`, `__pycache__`, other scripts, or local secrets.

## Deploy the public website

1. Sign in to Render and choose **New → Blueprint**.
2. Connect the GitHub repository containing the files above.
3. Render reads `render.yaml` and creates the web service. Confirm the free plan and deploy.
4. Share the `onrender.com` URL shown by Render. The free service can sleep after inactivity, so the first visit after a quiet period may take longer while it starts.

The speed-test page calls Cloudflare's public speed-test endpoints from each visitor's browser. Each visitor's result therefore uses that visitor's own internet connection; the Render server only serves the page and API fallback routes.