#!/bin/bash
# Perf Audit Skill v6.1 — One-command setup
# Run: curl -sL https://raw.githubusercontent.com/aaradhyaraiHO/perf-audit-skill/main/setup.sh | bash

set -e

echo "🔧 Setting up Perf Audit Skill v6.1..."

# 1. Clone skill into Claude's skills directory
if [ -d "$HOME/.claude/skills/perf-audit-v6" ]; then
    echo "  Updating existing installation..."
    cd "$HOME/.claude/skills/perf-audit-v6" && git pull
else
    echo "  Cloning skill..."
    git clone https://github.com/aaradhyaraiHO/perf-audit-skill.git "$HOME/.claude/skills/perf-audit-v6"
fi

# 2. Install Python dependency
echo "  Installing google-cloud-bigquery..."
pip install -q google-cloud-bigquery 2>/dev/null || pip3 install -q google-cloud-bigquery

# 3. Check BQ auth
if gcloud auth application-default print-access-token &>/dev/null; then
    echo "  BQ auth: ✓ already authenticated"
else
    echo "  BQ auth: needs login — opening browser..."
    gcloud auth application-default login
fi

echo ""
echo "✅ Done! To use:"
echo "   cd ~/analytics && claude"
echo "   /perf-audit-v6 \"CE Name\""
echo ""
echo "To update later: cd ~/.claude/skills/perf-audit-v6 && git pull"
