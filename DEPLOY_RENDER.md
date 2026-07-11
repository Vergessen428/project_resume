# Render Deployment

This project is a private, single-user application. The API is protected by
`APP_ACCESS_TOKEN`; set it in Render and enter the same value once in the web
login screen. It is kept only in the browser session.

## One-time setup

1. Create a private GitHub repository and push this folder to it.
2. In Render, select **New > Blueprint**, choose the GitHub repository, and let
   Render read `render.yaml`.
3. During Blueprint creation, enter values for `GEMINI_API_KEY` and
   `APP_ACCESS_TOKEN`. Do not commit them to Git.
4. Create the service. Render mounts its persistent disk at `/var/data`; your
   interviews, resumes and research library survive deploys.

## Optional model fallbacks

After the service exists, add `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`,
`OPENROUTER_API_KEY`, or the `CUSTOM_MODEL_*` variables in Render's environment
settings. See `mini_agent_python/.env.example` for model names and URLs.

## Operational notes

- The persistent disk requires a paid Render web-service plan.
- The app data is local JSON on that disk. Do not use multiple instances.
- `/healthz` is public and contains no candidate data. All `/api/*` routes need
  the access token when `APP_ACCESS_TOKEN` is configured.
