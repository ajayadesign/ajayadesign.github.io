#!/bin/sh
# Configure git to use GH_TOKEN for HTTPS authentication.
# This runs at container start, so the token never gets baked into the image.

if [ -n "$GH_TOKEN" ]; then
  # Store credential for git push/pull/clone (repo token only)
  git config --global credential.helper store
  echo "https://x-access-token:${GH_TOKEN}@github.com" > ~/.git-credentials
  chmod 600 ~/.git-credentials

  # Also authenticate gh CLI (uses GH_TOKEN for repo ops)
  echo "$GH_TOKEN" | gh auth login --with-token 2>/dev/null || true
fi

# Log which token is used for AI
if [ -n "$AI_TOKEN" ]; then
  echo "🤖 AI calls using dedicated AI_TOKEN"
else
  echo "🤖 AI calls using GH_TOKEN (shared)"
fi

# Execute the main process (uvicorn)
exec "$@"
