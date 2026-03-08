#!/bin/sh
# Run once after cloning: sh scripts/setup-hooks.sh
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
echo "Git hooks installed."
