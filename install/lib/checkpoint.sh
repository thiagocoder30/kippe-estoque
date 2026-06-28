#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# Institutional Installation Framework
# ------------------------------------------------------------
# Module  : checkpoint.sh
# Version : 1.0.0
# Status  : Stable
# ============================================================

[[ -n "${KIPPE_CHECKPOINT_LOADED:-}" ]] && return 0 2>/dev/null || true
readonly KIPPE_CHECKPOINT_LOADED=1

kippe::checkpoint_directory() {

    echo "${KIPPE_ROOT}/docs/checkpoints"

}

kippe::checkpoint_file() {

    local checkpoint="$1"

    printf "%s/CHECKPOINT-%s.md" \
        "$(kippe::checkpoint_directory)" \
        "${checkpoint}"

}

kippe::checkpoint_create() {

    local checkpoint="$1"
    local version="$2"
    local sprint="$3"
    local status="$4"

    local file

    file="$(kippe::checkpoint_file "${checkpoint}")"

    mkdir -p "$(dirname "${file}")"

    cat > "${file}" <<EOF
# CHECKPOINT ${checkpoint}

## Metadata

- Version: ${version}
- Sprint: ${sprint}
- Status: ${status}
- Date: $(date '+%Y-%m-%d %H:%M:%S')

---

## Summary

TODO

---

## Architecture

TODO

---

## Modules

TODO

---

## Tests

TODO

---

## Risks

TODO

---

## Technical Debt

TODO

---

## Next Sprint

TODO

EOF

    kippe::success "Checkpoint ${checkpoint} created."

}

kippe::checkpoint_exists() {

    [[ -f "$(kippe::checkpoint_file "$1")" ]]

}

kippe::checkpoint_latest() {

    local dir

    dir="$(kippe::checkpoint_directory)"

    [[ -d "${dir}" ]] || return 0

    ls -1 "${dir}"/CHECKPOINT-*.md 2>/dev/null \
        | sort \
        | tail -n 1

}

kippe::checkpoint_count() {

    local dir

    dir="$(kippe::checkpoint_directory)"

    [[ -d "${dir}" ]] || {
        echo 0
        return
    }

    find "${dir}" \
        -name "CHECKPOINT-*.md" \
        | wc -l

}

kippe::checkpoint_info() {

    cat <<EOF
Checkpoint Directory : $(kippe::checkpoint_directory)
Latest Checkpoint    : $(kippe::checkpoint_latest)
Total Checkpoints    : $(kippe::checkpoint_count)
EOF

}
