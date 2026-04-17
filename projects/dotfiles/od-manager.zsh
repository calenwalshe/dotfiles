#!/usr/bin/env zsh
# ============================================================================
# OD Manager - Arrow-navigable TUI for OnDemand Instance Management
# ============================================================================

# Colors
typeset -g C_RESET='\033[0m'
typeset -g C_BOLD='\033[1m'
typeset -g C_DIM='\033[2m'
typeset -g C_GREEN='\033[32m'
typeset -g C_YELLOW='\033[33m'
typeset -g C_BLUE='\033[34m'
typeset -g C_MAGENTA='\033[35m'
typeset -g C_CYAN='\033[36m'
typeset -g C_RED='\033[31m'
typeset -g C_WHITE='\033[37m'
typeset -g C_BG_SELECT='\033[48;5;238m'
typeset -g C_INVERSE='\033[7m'

# State
typeset -g _OD_CACHE=""
typeset -g _OD_CACHE_TIME=0
typeset -g _OD_SELECTED=1
typeset -g _OD_MODE="instances"  # instances, actions, types

# ============================================================================
# Data Functions
# ============================================================================

_od_get_instances_json() {
  local now=$(date +%s)
  if [[ -n "$_OD_CACHE" ]] && (( now - _OD_CACHE_TIME < 30 )); then
    echo "$_OD_CACHE"
    return
  fi
  local result=$(dev list --json --quiet 2>&1 | grep -o '{.*}' | head -1)
  _OD_CACHE="$result"
  _OD_CACHE_TIME=$now
  echo "$result"
}

_od_invalidate_cache() {
  _OD_CACHE=""
  _OD_CACHE_TIME=0
}

_od_get_instances() {
  local json=$(_od_get_instances_json)
  [[ -z "$json" ]] && return 1
  if command -v jq &>/dev/null; then
    echo "$json" | jq -r '.reserved[] | "\(.name)|\(.type)|\(.status)"' 2>/dev/null
  else
    echo "$json" | grep -oE '"name":"[^"]+"|"type":"[^"]+"|"status":"[^"]+"' | \
      paste - - - | sed 's/"name":"//g; s/"type":"//g; s/"status":"//g; s/"//g; s/\t/|/g'
  fi
}

_od_get_instance_count() {
  local instances=$(_od_get_instances)
  echo "$instances" | grep -c . 2>/dev/null || echo 0
}

# ============================================================================
# Arrow Key Reading
# ============================================================================

_od_read_key() {
  local key
  read -sk1 key

  if [[ "$key" == $'\e' ]]; then
    read -sk1 -t 0.1 key2
    if [[ "$key2" == "[" ]]; then
      read -sk1 -t 0.1 key3
      case "$key3" in
        A) echo "UP" ;;
        B) echo "DOWN" ;;
        C) echo "RIGHT" ;;
        D) echo "LEFT" ;;
        *) echo "ESC" ;;
      esac
    else
      echo "ESC"
    fi
  else
    echo "$key"
  fi
}

# ============================================================================
# Dashboard with Selection
# ============================================================================

_od_draw() {
  local instances="$1"
  local instance_count="$2"
  local now=$(date '+%Y-%m-%d %H:%M')

  clear

  # Header
  echo ""
  echo -e "  ${C_BOLD}${C_CYAN}╭─────────────────────────────────────────────────────────────────────────╮${C_RESET}"
  echo -e "  ${C_BOLD}${C_CYAN}│${C_RESET}  ${C_BOLD}${C_WHITE}  OD MANAGER${C_RESET}                                          ${C_DIM}$now${C_RESET}  ${C_BOLD}${C_CYAN}│${C_RESET}"
  echo -e "  ${C_BOLD}${C_CYAN}╰─────────────────────────────────────────────────────────────────────────╯${C_RESET}"
  echo ""

  # Instances
  echo -e "  ${C_BOLD}${C_WHITE}INSTANCES${C_RESET} ${C_DIM}($instance_count active)${C_RESET}  ${C_DIM}[↑↓ navigate, Enter connect, x destroy]${C_RESET}"
  echo -e "  ${C_DIM}───────────────────────────────────────────────────────────────────────────${C_RESET}"

  if [[ "$instance_count" -eq 0 ]]; then
    echo -e "  ${C_DIM}  No active instances. Press ${C_CYAN}n${C_DIM} to create one.${C_RESET}"
    echo ""
  else
    local idx=1
    echo "$instances" | while IFS='|' read -r name od_type od_status; do
      local hostname=$(echo "$name" | grep -oE '[0-9]+\.od')
      local created=$(echo "$od_status" | grep -oE 'Created: [0-9-]+ [0-9:]+' | sed 's/Created: //')
      local vpnless=""
      [[ "$name" == *"VPNLess"* ]] && vpnless="VPNLess" || vpnless="VPN"

      local type_color="$C_BLUE"
      case "$od_type" in
        *bento*) type_color="$C_MAGENTA" ;;
        *fbcode*) type_color="$C_CYAN" ;;
        *www*) type_color="$C_YELLOW" ;;
      esac

      if [[ "$idx" -eq "$_OD_SELECTED" ]]; then
        # Selected row - highlighted
        echo -e "  ${C_INVERSE}${C_GREEN} ▶ ${hostname}   ${type_color}${od_type}${C_RESET}${C_INVERSE}   ${created}   ${vpnless} ${C_RESET}"
      else
        # Normal row
        echo -e "  ${C_DIM}   ${C_RESET}${C_GREEN}${hostname}${C_RESET}   ${type_color}${od_type}${C_RESET}   ${C_DIM}${created}   ${vpnless}${C_RESET}"
      fi
      ((idx++))
    done
    echo ""
  fi

  # Actions bar
  echo -e "  ${C_DIM}───────────────────────────────────────────────────────────────────────────${C_RESET}"
  echo ""
  echo -e "  ${C_CYAN}[n]${C_RESET} New   ${C_RED}[x]${C_RESET} Destroy selected   ${C_RED}[X]${C_RESET} Destroy ALL   ${C_BLUE}[r]${C_RESET} Refresh   ${C_DIM}[q]${C_RESET} Quit"
  echo ""

  # New instance types
  echo -e "  ${C_DIM}New instance: ${C_CYAN}[f]${C_DIM}bcode ${C_YELLOW}[w]${C_DIM}ww ${C_MAGENTA}[b]${C_DIM}ento ${C_DIM}[a]ndroid [i]os${C_RESET}"
  echo ""
}

# ============================================================================
# Actions
# ============================================================================

_od_connect_selected() {
  local instances=$(_od_get_instances)
  local line=$(echo "$instances" | sed -n "${_OD_SELECTED}p")
  [[ -z "$line" ]] && return 1

  local name=$(echo "$line" | cut -d'|' -f1)
  local hostname=$(echo "$name" | grep -oE '[0-9]+\.od')

  clear
  echo -e "  ${C_CYAN}Connecting to ${C_BOLD}${hostname}.fbinfra.net${C_RESET}..."
  echo ""

  printf '\033]11;#1e1e28\007'
  x2ssh -et "${hostname}.fbinfra.net"
  printf '\033]11;#000000\007'
}

_od_destroy_selected() {
  local instances=$(_od_get_instances)
  local line=$(echo "$instances" | sed -n "${_OD_SELECTED}p")
  [[ -z "$line" ]] && return 1

  local name=$(echo "$line" | cut -d'|' -f1)
  local hostname=$(echo "$name" | grep -oE '[0-9]+\.od')

  echo ""
  echo -n -e "  ${C_RED}Destroy ${C_BOLD}$hostname${C_RESET}${C_RED}? [y/N]: ${C_RESET}"
  read -k1 confirm
  echo ""

  if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
    echo -e "  ${C_YELLOW}Releasing...${C_RESET}"
    dev release -n "$hostname" 2>/dev/null
    _od_invalidate_cache
    _OD_SELECTED=1
    sleep 0.5
  fi
}

_od_destroy_all() {
  local count=$(_od_get_instance_count)
  [[ "$count" -eq 0 ]] && return 0

  echo ""
  echo -n -e "  ${C_RED}${C_BOLD}Destroy ALL $count instance(s)? Type 'yes': ${C_RESET}"
  read confirm

  if [[ "$confirm" == "yes" ]]; then
    echo -e "  ${C_YELLOW}Releasing all...${C_RESET}"
    dev release --all 2>/dev/null
    _od_invalidate_cache
    _OD_SELECTED=1
    sleep 0.5
  fi
}

_od_new_instance() {
  local od_type="$1"

  case "$od_type" in
    f) od_type="fbcode" ;;
    w) od_type="www" ;;
    b) od_type="bento" ;;
    a) od_type="android" ;;
    i) od_type="ios" ;;
    *)
      echo ""
      echo -e "  ${C_CYAN}Select type: [f]bcode [w]ww [b]ento [a]ndroid [i]os${C_RESET}"
      echo -n "  > "
      read -k1 od_type
      echo ""
      case "$od_type" in
        f) od_type="fbcode" ;;
        w) od_type="www" ;;
        b) od_type="bento" ;;
        a) od_type="android" ;;
        i) od_type="ios" ;;
        *) return 0 ;;
      esac
      ;;
  esac

  clear
  echo -e "  ${C_CYAN}Creating ${C_BOLD}$od_type${C_RESET}${C_CYAN} instance...${C_RESET}"
  echo ""
  _od_invalidate_cache
  dev connect -t "$od_type"
}

# ============================================================================
# Main Loop
# ============================================================================

_od_main_loop() {
  _OD_SELECTED=1

  # Initial load with loading message
  clear
  echo ""
  echo -e "  ${C_DIM}Loading...${C_RESET}"

  local instances=$(_od_get_instances)
  local instance_count=$(echo "$instances" | grep -c . 2>/dev/null || echo 0)

  while true; do
    _od_draw "$instances" "$instance_count"

    local key=$(_od_read_key)

    case "$key" in
      UP|k)
        (( _OD_SELECTED > 1 )) && (( _OD_SELECTED-- ))
        ;;
      DOWN|j)
        (( _OD_SELECTED < instance_count )) && (( _OD_SELECTED++ ))
        ;;
      ""|$'\n')  # Enter
        if [[ "$instance_count" -gt 0 ]]; then
          _od_connect_selected
          # Refresh after returning
          instances=$(_od_get_instances)
          instance_count=$(echo "$instances" | grep -c . 2>/dev/null || echo 0)
        fi
        ;;
      x)
        if [[ "$instance_count" -gt 0 ]]; then
          _od_destroy_selected
          instances=$(_od_get_instances)
          instance_count=$(echo "$instances" | grep -c . 2>/dev/null || echo 0)
          (( _OD_SELECTED > instance_count )) && _OD_SELECTED=$instance_count
          (( _OD_SELECTED < 1 )) && _OD_SELECTED=1
        fi
        ;;
      X)
        _od_destroy_all
        instances=$(_od_get_instances)
        instance_count=$(echo "$instances" | grep -c . 2>/dev/null || echo 0)
        _OD_SELECTED=1
        ;;
      n)
        _od_new_instance ""
        _od_invalidate_cache
        instances=$(_od_get_instances)
        instance_count=$(echo "$instances" | grep -c . 2>/dev/null || echo 0)
        ;;
      f|w|b|a|i)
        _od_new_instance "$key"
        _od_invalidate_cache
        instances=$(_od_get_instances)
        instance_count=$(echo "$instances" | grep -c . 2>/dev/null || echo 0)
        ;;
      r|R)
        _od_invalidate_cache
        clear
        echo ""
        echo -e "  ${C_DIM}Refreshing...${C_RESET}"
        instances=$(_od_get_instances)
        instance_count=$(echo "$instances" | grep -c . 2>/dev/null || echo 0)
        ;;
      q|Q|ESC)
        clear
        return 0
        ;;
    esac
  done
}

# ============================================================================
# Entry Point
# ============================================================================

od() {
  local action="${1:-}"

  case "$action" in
    "")
      _od_main_loop
      ;;
    help|h|--help|-h)
      cat << 'EOF'
OD Manager - Arrow-navigable TUI

USAGE:
  od              Open TUI (arrow keys to navigate)
  od <number>     Quick connect to that OD
  od list         List instances

NAVIGATION:
  ↑/↓ or j/k   Move selection
  Enter        Connect to selected
  x            Destroy selected
  X            Destroy ALL
  n            New instance (then pick type)
  f/w/b/a/i    New fbcode/www/bento/android/ios
  r            Refresh
  q/Esc        Quit

EOF
      ;;
    list|ls|l)
      local instances=$(_od_get_instances)
      [[ -z "$instances" ]] && echo "No instances" && return 0
      echo ""
      printf "%-14s  %-22s  %-20s\n" "HOSTNAME" "TYPE" "CREATED"
      echo "─────────────────────────────────────────────────────────"
      echo "$instances" | while IFS='|' read -r name od_type od_status; do
        local hostname=$(echo "$name" | grep -oE '[0-9]+\.od')
        local created=$(echo "$od_status" | grep -oE 'Created: [0-9-]+ [0-9:]+' | sed 's/Created: //')
        printf "%-14s  %-22s  %-20s\n" "$hostname" "$od_type" "$created"
      done
      echo ""
      ;;
    *)
      if [[ "$action" =~ ^[0-9]+$ ]]; then
        echo -e "Connecting to ${action}.od.fbinfra.net..."
        printf '\033]11;#1e1e28\007'
        x2ssh -et "${action}.od.fbinfra.net"
        printf '\033]11;#000000\007'
      else
        echo "Unknown: $action (try: od --help)"
      fi
      ;;
  esac
}
