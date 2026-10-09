#!/usr/bin/env bash
# ==============================================================================
#  AUTORESEARCHING — VPS DEPLOYMENT SCRIPT
#  Mục tiêu: Kiểm tra toàn bộ môi trường, cài đặt phụ thuộc và khởi động
#            hệ thống hoàn chỉnh (hạ tầng + 4 AI service) trên Linux VPS.
#
#  Cách dùng:
#    chmod +x deploy.sh
#    ./deploy.sh [--skip-build] [--infra-only] [--app-only]
#
#  Flags:
#    --skip-build    Bỏ qua bước docker build (dùng image đã có sẵn)
#    --infra-only    Chỉ khởi động hạ tầng (Kafka, Redis, Mongo, Qdrant, MinIO, LiteLLM)
#    --app-only      Chỉ khởi động 4 AI service (hạ tầng phải đã chạy)
#    --help          Hiển thị trợ giúp
# ==============================================================================

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC}  $*" >&2; }
fatal()   { error "$*"; exit 1; }
section() {
  echo -e "\n${BOLD}${CYAN}══════════════════════════════════════════${NC}"
  echo -e "${BOLD}${CYAN}  $*${NC}"
  echo -e "${BOLD}${CYAN}══════════════════════════════════════════${NC}"
}

# ── Defaults ──────────────────────────────────────────────────────────────────
SKIP_BUILD=false
INFRA_ONLY=false
APP_ONLY=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Parse flags ───────────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=true ;;
    --infra-only) INFRA_ONLY=true ;;
    --app-only)   APP_ONLY=true ;;
    --help|-h)
      echo "Usage: ./deploy.sh [--skip-build] [--infra-only] [--app-only]"
      exit 0 ;;
    *) warn "Unknown flag: $arg" ;;
  esac
done

# ==============================================================================
# SECTION 1 — KIỂM TRA MÔI TRƯỜNG HỆ THỐNG
# ==============================================================================
section "BƯỚC 1/6 — Kiểm tra môi trường hệ thống"

# --- OS ---
OS=$(uname -s)
[[ "$OS" != "Linux" ]] && fatal "Script này chỉ hỗ trợ Linux (hiện tại: $OS)"
success "OS: Linux"

# --- CPU & RAM tối thiểu ---
CPU_CORES=$(nproc)
MEM_GB=$(awk '/MemTotal/ {printf "%.0f", $2/1024/1024}' /proc/meminfo)
info "CPU: ${CPU_CORES} cores | RAM: ${MEM_GB} GB"
[[ "$CPU_CORES" -lt 2 ]] && warn "Khuyến nghị >= 2 CPU cores (hiện tại: ${CPU_CORES})"
[[ "$MEM_GB" -lt 4 ]]    && warn "Khuyến nghị >= 4 GB RAM (hiện tại: ${MEM_GB} GB)"

# --- Disk space: cần ít nhất 10 GB trống ---
DISK_FREE_GB=$(df -BG "$SCRIPT_DIR" | awk 'NR==2 {gsub("G",""); print $4}')
info "Disk trống: ${DISK_FREE_GB} GB"
[[ "$DISK_FREE_GB" -lt 10 ]] && fatal "Cần ít nhất 10 GB dung lượng trống (hiện tại: ${DISK_FREE_GB} GB)"
success "Disk: OK (${DISK_FREE_GB} GB trống)"

# --- Docker ---
if ! command -v docker &>/dev/null; then
  warn "Docker chưa được cài đặt. Bắt đầu cài đặt tự động..."
  curl -fsSL https://get.docker.com | bash
  sudo usermod -aG docker "$USER"
  warn "Đã thêm user '$USER' vào nhóm docker. Bạn có thể cần đăng xuất/đăng nhập lại."
fi
DOCKER_VER=$(docker --version 2>/dev/null | grep -oP '[\d.]+' | head -1)
success "Docker: v${DOCKER_VER}"

# --- Docker daemon đang chạy? ---
if ! docker info &>/dev/null; then
  info "Docker daemon chưa chạy, thử khởi động..."
  sudo systemctl start docker || fatal "Không thể khởi động Docker daemon"
fi
success "Docker daemon: running"

# --- Docker Compose (plugin hoặc standalone) ---
if docker compose version &>/dev/null; then
  DC="docker compose"
elif command -v docker-compose &>/dev/null; then
  DC="docker-compose"
else
  warn "Docker Compose chưa cài. Cài Docker Compose plugin..."
  sudo apt-get update -qq
  sudo apt-get install -y docker-compose-plugin
  DC="docker compose"
fi
DC_VER=$($DC version 2>/dev/null | grep -oP '[\d.]+' | head -1)
success "Docker Compose: v${DC_VER} (cmd: '$DC')"

# --- Git ---
if command -v git &>/dev/null; then
  success "Git: $(git --version | grep -oP '[\d.]+')"
else
  warn "Git chưa cài (không bắt buộc nhưng khuyến nghị)"
fi

# --- curl ---
command -v curl &>/dev/null && success "curl: OK" || fatal "curl chưa cài. Chạy: sudo apt install curl"

# --- Python 3 ---
if command -v python3 &>/dev/null; then
  PY_VER=$(python3 --version 2>&1 | grep -oP '[\d.]+')
  success "Python 3: v${PY_VER}"
else
  warn "Python 3 không tìm thấy. Bước seed infrastructure sẽ bị bỏ qua."
fi

# ==============================================================================
# SECTION 2 — KIỂM TRA FILE PROJECT
# ==============================================================================
section "BƯỚC 2/6 — Kiểm tra cấu trúc project"

cd "$SCRIPT_DIR"
info "Project root: $SCRIPT_DIR"

REQUIRED_FILES=(
  "docker-compose-infra.yaml"
  "docker-compose-app.yaml"
  "litellm_config.yaml"
  "Dockerfile"
  "requirements.txt"
  "main_doc_local.py"
  "main_write_local.py"
  "main_chat_local.py"
  "main_enhance_local.py"
)

for f in "${REQUIRED_FILES[@]}"; do
  [[ -f "$f" ]] && success "  OK: $f" || fatal "File bắt buộc không tồn tại: $f"
done

# --- .env file ---
if [[ ! -f ".env" ]]; then
  if [[ -f ".env.example" ]]; then
    warn ".env chưa có. Tạo từ .env.example..."
    cp .env.example .env
    warn ">>> VUI LÒNG CHỈNH SỬA FILE .env VÀ ĐIỀN CÁC GIÁ TRỊ BẮT BUỘC <<<"
    warn "    Ít nhất cần: GROQ_API_KEY"
    warn "    File: ${SCRIPT_DIR}/.env"
    echo ""
    read -rp "Nhấn ENTER sau khi đã điền xong .env (hoặc Ctrl+C để dừng)..."
  else
    fatal ".env không tồn tại và không có .env.example để sao chép."
  fi
fi
success ".env: OK"

# ==============================================================================
# SECTION 3 — KIỂM TRA BIẾN MÔI TRƯỜNG QUAN TRỌNG
# ==============================================================================
section "BƯỚC 3/6 — Xác thực biến môi trường"

# Load .env
set -a
source .env 2>/dev/null || true
set +a

MISSING_KEYS=()

# Yêu cầu ít nhất 1 API key LLM (OPEN_AI_KEY, GEMINI_KEY, hoặc GROQ_API_KEY)
if [[ -z "${OPEN_AI_KEY:-}" ]] && [[ -z "${GEMINI_KEY:-}" ]] && [[ -z "${GROQ_API_KEY:-}" ]]; then
  MISSING_KEYS+=("Cần ít nhất 1 trong 3 key: OPEN_AI_KEY, GEMINI_KEY hoặc GROQ_API_KEY")
fi

[[ -z "${KAFKA:-}" ]]      && warn "KAFKA chưa set. Dùng mặc định: localhost:9092"
[[ -z "${REDIS:-}" ]]      && warn "REDIS chưa set. Dùng mặc định redis://..."
[[ -z "${QDRANT_URL:-}" ]] && warn "QDRANT_URL chưa set."
[[ -n "${OPEN_AI_KEY:-}" ]] && success "OPEN_AI_KEY: set OK (Dùng GPT & text-embedding-3-small)"
[[ -n "${GEMINI_KEY:-}" ]]  && success "GEMINI_KEY: set OK (Dùng Google Gemini)"
[[ -n "${GROQ_API_KEY:-}" ]] && success "GROQ_API_KEY: set OK (Dùng LiteLLM / Groq)"
[[ -z "${SERP_KEY:-}" ]]    && warn "SERP_KEY: không set => chức năng tìm kiếm web sẽ không hoạt động"

if [[ "${#MISSING_KEYS[@]}" -gt 0 ]]; then
  error "Lỗi biến môi trường trong .env:"
  for k in "${MISSING_KEYS[@]}"; do
    error "  THIẾU: $k"
  done
  fatal "Hãy điền ít nhất OPEN_AI_KEY (hoặc GROQ_API_KEY) vào .env rồi chạy lại script."
fi

success "Biến môi trường: OK"

# ==============================================================================
# SECTION 4 — KHỞI ĐỘNG HẠ TẦNG
# ==============================================================================
if [[ "$APP_ONLY" == "false" ]]; then
  section "BƯỚC 4/6 — Khởi động hạ tầng (Infrastructure)"

  info "Pull images mới nhất..."
  $DC -f docker-compose-infra.yaml pull || warn "Pull một số image thất bại, thử dùng image cũ..."

  info "Khởi động các container hạ tầng..."
  $DC -f docker-compose-infra.yaml up -d

  # --- Chờ các service healthy ---
  info "Đợi các service sẵn sàng (tối đa 120s)..."

  wait_healthy() {
    local container="$1"
    local max_wait="${2:-120}"
    local elapsed=0
    while [[ "$elapsed" -lt "$max_wait" ]]; do
      STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "not_found")
      case "$STATUS" in
        healthy)   success "  $container: healthy"; return 0 ;;
        not_found) warn    "  $container: container không tìm thấy"; return 1 ;;
      esac
      sleep 5
      elapsed=$((elapsed + 5))
      info "  Đợi $container... (${elapsed}s / ${max_wait}s) [status: $STATUS]"
    done
    warn "  $container: timeout sau ${max_wait}s (status: $STATUS)"
    return 1
  }

  wait_healthy "autoresearching-kafka"   120
  wait_healthy "autoresearching-redis"   60
  wait_healthy "autoresearching-mongodb" 60
  wait_healthy "autoresearching-qdrant"  60
  wait_healthy "autoresearching-minio"   60
  wait_healthy "autoresearching-litellm" 90

  # --- Seed hạ tầng ---
  if command -v python3 &>/dev/null && [[ -f "scripts/seed_infra.py" ]]; then
    info "Chạy seed_infra.py (tạo Kafka topics, MinIO bucket)..."
    python3 -m pip install --quiet aiokafka minio pymongo 2>/dev/null || true
    python3 scripts/seed_infra.py && success "Seed infrastructure: OK" \
      || warn "seed_infra.py thất bại — chạy thủ công: python3 scripts/seed_infra.py"
  else
    warn "Bỏ qua seed_infra.py (python3 hoặc file không tồn tại)"
  fi
else
  section "BƯỚC 4/6 — Bỏ qua hạ tầng (--app-only mode)"
  info "Đảm bảo hạ tầng đã chạy trước khi tiếp tục."
fi

# ==============================================================================
# SECTION 5 — BUILD & KHỞI ĐỘNG 4 AI SERVICE
# ==============================================================================
if [[ "$INFRA_ONLY" == "false" ]]; then
  section "BƯỚC 5/6 — Build & khởi động 4 AI Service"

  if [[ "$SKIP_BUILD" == "false" ]]; then
    info "Build Docker image autoresearching-ai:latest..."
    docker build \
      --progress=plain \
      --tag autoresearching-ai:latest \
      --file Dockerfile \
      . \
      && success "Docker build: OK" \
      || fatal "Docker build thất bại. Xem log phía trên để debug."
  else
    info "Bỏ qua build (--skip-build). Dùng image hiện có."
    docker image inspect autoresearching-ai:latest &>/dev/null \
      || fatal "Image autoresearching-ai:latest chưa tồn tại. Chạy lại không có --skip-build."
  fi

  info "Dừng 4 AI service cũ nếu có..."
  $DC -f docker-compose-app.yaml down --remove-orphans 2>/dev/null || true

  info "Khởi động 4 AI service..."
  $DC -f docker-compose-app.yaml up -d

  success "4 AI Service đã được khởi động"
else
  section "BƯỚC 5/6 — Bỏ qua AI Services (--infra-only mode)"
fi

# ==============================================================================
# SECTION 6 — HEALTH CHECK TỔNG THỂ
# ==============================================================================
section "BƯỚC 6/6 — Tổng kiểm tra trạng thái hệ thống"

echo ""
echo -e "${BOLD}  Container Status:${NC}"
docker ps --format "  {{.Names}}\t{{.Status}}\t{{.Ports}}" \
  | grep "autoresearching" | sort || true

echo ""
echo -e "${BOLD}  Port Accessibility (từ localhost):${NC}"

check_port() {
  local name="$1" host="$2" port="$3"
  if timeout 3 bash -c "exec 3<>/dev/tcp/${host}/${port}" 2>/dev/null; then
    success "  ${name}: ${host}:${port}"
  else
    warn    "  ${name}: ${host}:${port} — KHÔNG PHẢN HỒI"
  fi
}

check_port "Kafka"         "localhost" "9092"
check_port "Kafka UI"      "localhost" "8080"
check_port "Redis"         "localhost" "6379"
check_port "MongoDB"       "localhost" "27017"
check_port "Qdrant"        "localhost" "6333"
check_port "MinIO API"     "localhost" "9000"
check_port "MinIO Console" "localhost" "9001"
check_port "LiteLLM Proxy" "localhost" "8000"

# LiteLLM liveliness
echo ""
info "Kiểm tra LiteLLM /health/liveliness..."
if curl -sf "http://localhost:8000/health/liveliness" &>/dev/null; then
  success "LiteLLM API: ALIVE"
else
  warn "LiteLLM API: chưa phản hồi (đang khởi động — thử lại sau 30s)"
fi

# ==============================================================================
# HOÀN THÀNH
# ==============================================================================
echo ""
echo -e "${GREEN}${BOLD}+----------------------------------------------------------+${NC}"
echo -e "${GREEN}${BOLD}|      AUTORESEARCHING — DEPLOY THANH CONG  ^^             |${NC}"
echo -e "${GREEN}${BOLD}+----------------------------------------------------------+${NC}"
echo ""
echo -e "  ${BOLD}Ha tang:${NC}"
echo -e "    - Kafka UI:       http://localhost:8080"
echo -e "    - MinIO Console:  http://localhost:9001  (minio_admin / minio_password_local)"
echo -e "    - Qdrant UI:      http://localhost:6333/dashboard"
echo -e "    - LiteLLM Proxy:  http://localhost:8000"
echo ""
echo -e "  ${BOLD}4 AI Services dang chay:${NC}"
echo -e "    - autoresearching-doc      (Document Setup)"
echo -e "    - autoresearching-write    (Write Reports)"
echo -e "    - autoresearching-chat     (AI Chatbot)"
echo -e "    - autoresearching-enhance  (Enhancement)"
echo ""
echo -e "  ${BOLD}Lenh huu ich:${NC}"
echo -e "    Xem log:       docker logs -f autoresearching-doc"
echo -e "    Dung tat ca:   docker compose -f docker-compose-infra.yaml -f docker-compose-app.yaml down"
echo -e "    Restart app:   docker compose -f docker-compose-app.yaml restart"
echo -e "    Seed lai:      python3 scripts/seed_infra.py"
echo ""
