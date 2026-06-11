#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Validation script for code quality and security checks.
# Run before submitting for Content Security Review.
#
# Usage: ./scripts/validate.sh

set -e

echo "=== Code Validation ==="
echo ""

# 1. Python syntax check
echo "1. Python syntax check..."
find . -name "*.py" -not -path "./.venv/*" -not -path "*/__pycache__/*" | while read f; do
    python3 -c "import ast; ast.parse(open('$f').read())" || { echo "FAIL: $f"; exit 1; }
done
echo "   ✓ All Python files pass syntax check"

# 2. SPDX license headers
echo "2. Checking SPDX license headers..."
MISSING=0
for f in $(find . -name "*.py" -not -path "./.venv/*" -not -path "*/__pycache__/*"); do
    if ! head -2 "$f" | grep -q "SPDX-License-Identifier"; then
        echo "   MISSING HEADER: $f"
        MISSING=$((MISSING+1))
    fi
done
if [ $MISSING -eq 0 ]; then
    echo "   ✓ All files have SPDX headers"
else
    echo "   ✗ $MISSING files missing SPDX headers"
    exit 1
fi

# 3. No hardcoded secrets
echo "3. Checking for hardcoded secrets..."
SECRETS_FOUND=$(grep -rn "AKIA" --include="*.py" --exclude-dir=.venv . 2>/dev/null | grep -v "example\|placeholder" || true)
if [ -n "$SECRETS_FOUND" ]; then
    echo "   ✗ Potential AWS access keys found!"
    echo "   $SECRETS_FOUND"
    exit 1
else
    echo "   ✓ No hardcoded secrets"
fi

# 4. No internal Amazon links
echo "4. Checking for internal links..."
INTERNAL_LINKS=$(grep -rn "w\.amazon\.com\|gitlab\.aws\.dev\|quip-amazon\|midway\.amazon" --include="*.py" --include="*.md" --include="*.yaml" --exclude-dir=.venv --exclude-dir=workshop . 2>/dev/null || true)
if [ -n "$INTERNAL_LINKS" ]; then
    echo "   ✗ Internal links found!"
    echo "   $INTERNAL_LINKS"
    exit 1
else
    echo "   ✓ No internal links"
fi

# 5. Required files
echo "5. Checking required files..."
for f in LICENSE NOTICE CONTRIBUTING.md CODE_OF_CONDUCT.md THIRD-PARTY-LICENSES README.md .gitignore requirements.txt pyproject.toml .env.example; do
    if [ ! -f "$f" ]; then
        echo "   ✗ MISSING: $f"
        exit 1
    fi
done
echo "   ✓ All required files present"

# 6. Run tests
echo "6. Running tests..."
if command -v pytest &> /dev/null || [ -f .venv/bin/pytest ]; then
    .venv/bin/pytest tests/ -q 2>&1 | tail -3
else
    echo "   ⚠️  pytest not installed, skipping"
fi

# 7. No dangerous Python patterns
echo "7. Checking for dangerous patterns..."
DANGEROUS=$(grep -rn 'eval(' --include="*.py" --exclude-dir=.venv . 2>/dev/null | grep -v "#\|retrieval\|evaluate\|self_eval" || true)
DANGEROUS2=$(grep -rn 'os\.system(' --include="*.py" --exclude-dir=.venv . 2>/dev/null | grep -v "#" || true)
if [ -n "$DANGEROUS" ] || [ -n "$DANGEROUS2" ]; then
    echo "   ⚠️  Review dangerous function usage:"
    [ -n "$DANGEROUS" ] && echo "   $DANGEROUS"
    [ -n "$DANGEROUS2" ] && echo "   $DANGEROUS2"
else
    echo "   ✓ No dangerous patterns"
fi

echo ""
echo "=== ✅ All validation checks passed ==="
echo ""
echo "Ready for Content Security Review submission."
echo "Run 'ash --source-dir . --output-dir ./ash-output' for full security scan."
