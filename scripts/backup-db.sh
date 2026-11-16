#!/data/data/com.termux/files/usr/bin/bash
# Backup rotativo do Kippe-Estoque (DB + documents)
# Uso: ./scripts/backup-db.sh
# Agendado via cron Termux 1x/dia às 03:00

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_SRC="${PROJECT_DIR}/data/estoque_producao.db"
BACKUP_ROOT="/sdcard/Download/kippe-backups"
DB_BACKUP_DIR="${BACKUP_ROOT}/db"
DOCS_BACKUP_DIR="${BACKUP_ROOT}/documents"
DB_RETENTION=14    # dias
DOCS_RETENTION=30  # dias (documentos fiscais podem ter valor legal)

[[ -d /sdcard ]] || { echo "❌ /sdcard indisponível (rode termux-setup-storage)"; exit 1; }

# ─── Backup do DB ───
if [[ -f "$DB_SRC" ]]; then
  mkdir -p "$DB_BACKUP_DIR"
  TS="$(date +%Y%m%d-%H%M%S)"
  DEST="${DB_BACKUP_DIR}/estoque_producao-${TS}.db"

  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$DB_SRC" "VACUUM INTO '${DEST}'"
  else
    cp "$DB_SRC" "$DEST"
  fi

  SIZE=$(stat -c%s "$DEST" 2>/dev/null || stat -f%z "$DEST")
  [[ "$SIZE" -gt 1000 ]] || { echo "❌ Backup DB suspeitamente pequeno ($SIZE bytes)"; exit 1; }
  echo "✅ DB:      $DEST ($SIZE bytes)"

  find "$DB_BACKUP_DIR" -name 'estoque_producao-*.db' -mtime +${DB_RETENTION} -delete 2>/dev/null || true
  echo "📦 DB backups mantidos: $(find "$DB_BACKUP_DIR" -name 'estoque_producao-*.db' | wc -l)"
else
  echo "⚠️  DB não encontrado: $DB_SRC"
fi

# ─── Backup de documentos (DANFE, PDFs, imagens) ───
DOCS_SRC="${PROJECT_DIR}/data/documents"
if [[ -d "$DOCS_SRC" ]] && [[ -n "$(ls -A "$DOCS_SRC" 2>/dev/null)" ]]; then
  mkdir -p "$DOCS_BACKUP_DIR"
  DOCS_TS="$(date +%Y%m%d-%H%M%S)"
  DOCS_ARCHIVE="${DOCS_BACKUP_DIR}/documents-${DOCS_TS}.tar.gz"

  tar czf "$DOCS_ARCHIVE" -C "${PROJECT_DIR}/data" documents
  DOCS_SIZE=$(stat -c%s "$DOCS_ARCHIVE" 2>/dev/null || stat -f%z "$DOCS_ARCHIVE")
  echo "✅ Docs:    $DOCS_ARCHIVE ($DOCS_SIZE bytes)"

  find "$DOCS_BACKUP_DIR" -name 'documents-*.tar.gz' -mtime +${DOCS_RETENTION} -delete 2>/dev/null || true
  echo "📦 Docs backups mantidos: $(find "$DOCS_BACKUP_DIR" -name 'documents-*.tar.gz' | wc -l)"
else
  echo "ℹ️  data/documents/ vazio ou ausente — pulando backup de docs"
fi

echo "🎯 Backup concluído em $(date)"
