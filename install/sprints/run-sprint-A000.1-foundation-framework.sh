#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM A
# SPRINT A000.1
# FOUNDATION FRAMEWORK INSTALLER
# ============================================================

set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"

source install/lib/bootstrap.sh

kippe::init
kippe::init_environment

trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=14

kippe::banner_program \
    "A" \
    "A000.1" \
    "Foundation Framework"

kippe::step 1 ${TOTAL_STEPS} "Validating environment..."
kippe::validate_environment

kippe::step 2 ${TOTAL_STEPS} "Creating installation directories..."
kippe::mkdirs \
    install \
    install/lib \
    install/templates \
    install/sprints

kippe::step 3 ${TOTAL_STEPS} "Creating documentation directories..."
kippe::mkdirs \
    docs \
    docs/architecture \
    docs/checkpoints \
    docs/standards \
    docs/diagrams

kippe::step 4 ${TOTAL_STEPS} "Creating report directories..."
kippe::mkdirs \
    reports

kippe::step 5 ${TOTAL_STEPS} "Preparing export structure..."
kippe::export_init

kippe::step 6 ${TOTAL_STEPS} "Validating framework..."
kippe::validate_framework

kippe::step 7 ${TOTAL_STEPS} "Displaying framework information..."
kippe::framework_info

kippe::step 8 ${TOTAL_STEPS} "Generating initial manifest..."
kippe::manifest_create \
    "A000.1" \
    "A" \
    "1.0.0" \
    "SUCCESS" \
    "A000.2"

kippe::step 9 ${TOTAL_STEPS} "Generating initial checkpoint..."
kippe::checkpoint_create \
    "000" \
    "1.0.0" \
    "A000.1" \
    "SUCCESS"

kippe::step 10 ${TOTAL_STEPS} "Exporting manifest..."
kippe::export_manifest "A000.1"

kippe::step 11 ${TOTAL_STEPS} "Exporting checkpoint..."
kippe::export_checkpoint "000"

kippe::step 12 ${TOTAL_STEPS} "Exporting logs..."
kippe::export_logs

kippe::step 13 ${TOTAL_STEPS} "Git status..."
kippe::git_status || true

kippe::step 14 ${TOTAL_STEPS} "Framework installation completed."

kippe::banner_finish

kippe::success \
"Foundation Framework successfully installed."

echo

echo "Next Sprint: A000.2"

echo
