#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Outreach Agent — Test Runner
# ═══════════════════════════════════════════════════════════
#
# Usage:
#   ./run_outreach_tests.sh              # Run all tests (mocked)
#   ./run_outreach_tests.sh unit         # Unit tests only
#   ./run_outreach_tests.sh integration  # Integration tests only
#   ./run_outreach_tests.sh e2e          # E2E pipeline test
#   ./run_outreach_tests.sh routes       # API route tests
#   ./run_outreach_tests.sh live         # Include LIVE email send to ajayadahal10@gmail.com
#
# Prerequisites:
#   cd automation && pip install -r requirements.txt
#

set -e
cd "$(dirname "$0")"

PYTEST_ARGS="-v --tb=short -x"
TEST_DIR="tests/outreach"

case "${1:-all}" in
    unit)
        echo "🧪 Running UNIT tests..."
        python -m pytest "$TEST_DIR/test_unit.py" $PYTEST_ARGS "${@:2}"
        ;;
    integration)
        echo "🔗 Running INTEGRATION tests..."
        python -m pytest "$TEST_DIR/test_integration.py" $PYTEST_ARGS "${@:2}"
        ;;
    e2e)
        echo "🚀 Running E2E PIPELINE test..."
        python -m pytest "$TEST_DIR/test_e2e.py" $PYTEST_ARGS "${@:2}"
        ;;
    routes)
        echo "🌐 Running ROUTE tests..."
        python -m pytest "$TEST_DIR/test_routes.py" $PYTEST_ARGS "${@:2}"
        ;;
    live)
        echo "📧 Running ALL tests INCLUDING LIVE email send to ajayadahal10@gmail.com..."
        echo "   (Requires SMTP_EMAIL and SMTP_APP_PASSWORD in env)"
        OUTREACH_TEST_LIVE_SEND=1 python -m pytest "$TEST_DIR" $PYTEST_ARGS "${@:2}"
        ;;
    all)
        echo "🧪 Running ALL outreach tests (mocked)..."
        python -m pytest "$TEST_DIR" $PYTEST_ARGS "${@:2}"
        ;;
    *)
        echo "Usage: $0 {unit|integration|e2e|routes|live|all}"
        exit 1
        ;;
esac

echo ""
echo "✅ Tests complete!"
