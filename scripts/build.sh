#!/usr/bin/env bash
# Regenerate everything. Pass a photo to rebuild the portrait too.
#   ./scripts/build.sh                  -> card + heatmap
#   ./scripts/build.sh photo.jpg        -> portrait + card + heatmap
set -euo pipefail
cd "$(dirname "$0")/.."

if [ $# -ge 1 ]; then
  python scripts/prep_photo.py "$1"
  python scripts/make_ascii_svg.py
fi

python scripts/make_info_card.py
python scripts/fetch_contributions.py
python scripts/render_heatmap_svg.py

echo "done"
