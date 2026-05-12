#!/usr/bin/env bash
# Requires FastAPI running on port 8000 first (scripts/00_start.sh)
cd "$(dirname "$0")/../frontend" && npm run dev
