#!/bin/bash

# DNS Scanner with Masscan and VPN Client - Linux Version
# Converted from Python script

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
IP_RANGE=""
ROUNDS=10
SKIP_MASSCAN=false
RESOLVERS_FILE="client_resolvers.txt"
USE_ALTERNATIVE=false
ANALYZE_ONLY=false
TMP_FOLDER="tmp"
OUTPUT_FILE="top_dnses.txt"
TOP_N=10
MASSCAN_BIN=""
VPN_CLIENT_BIN="./MasterDnsVPN_Client_Linux_AMD64_v2026.04.12.234117-978faee"  # Adjust name for Linux

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[-]${NC} $1"
}

print_header() {
    echo ""
    echo "=================================================="
    echo -e "${BLUE}$1${NC}"
    echo "=================================================="
}

# Signal handler for Ctrl+C
cleanup() {
    echo ""
    print_warning "Script interrupted by user. Exiting..."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

DNS Scanner with Masscan and VPN Client - Linux Version

OPTIONS:
    -r, --range RANGE          IP range in CIDR notation (e.g., 5.0.0.0/8)
    -n, --rounds NUM           Number of VPN client rounds (default: 10)
    -s, --skip-masscan         Skip masscan scan and use existing resolvers file
    -f, --resolvers-file FILE  Resolvers file when skipping masscan (default: client_resolvers.txt)
    -a, --alternative          Use alternative method for VPN client monitoring
    --analyze-only             Only analyze existing tmp folder results
    --tmp-folder DIR           Temporary folder for round results (default: tmp)
    -o, --output FILE          Output file for top DNS results (default: top_dnses.txt)
    --top-n NUM                Number of top DNS servers to output (default: 10)
    --masscan-bin PATH         Path to masscan binary (default: auto-detect)
    -h, --help                 Show this help message

EXAMPLES:
    $0                                      # Interactive mode
    $0 -r 5.0.0.0/8                        # Specify IP range
    $0 -r 5.0.0.0/8 -n 20                  # IP range and 20 rounds
    $0 --skip-masscan                       # Skip masscan, use existing resolvers file
    $0 -s -n 5                             # Skip masscan, run 5 rounds
    $0 --analyze-only                       # Only analyze existing tmp folder results
    $0 --top-n 20                          # Show top 20 DNS servers
    $0 --masscan-bin ./masscan             # Use local masscan binary
EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--range)
            IP_RANGE="$2"
            shift 2
            ;;
        -n|--rounds)
            ROUNDS="$2"
            shift 2
            ;;
        -s|--skip-masscan)
            SKIP_MASSCAN=true
            shift
            ;;
        -f|--resolvers-file)
            RESOLVERS_FILE="$2"
            shift 2
            ;;
        -a|--alternative)
            USE_ALTERNATIVE=true
            shift
            ;;
        --analyze-only)
            ANALYZE_ONLY=true
            shift
            ;;
        --tmp-folder)
            TMP_FOLDER="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --top-n)
            TOP_N="$2"
            shift 2
            ;;
        --masscan-bin)
            MASSCAN_BIN="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Function to find masscan binary
find_masscan() {
    # If user specified a path, use it
    if [[ -n "$MASSCAN_BIN" ]]; then
        if [[ -x "$MASSCAN_BIN" ]] || command -v "$MASSCAN_BIN" &> /dev/null; then
            echo "$MASSCAN_BIN"
            return 0
        else
            print_error "Specified masscan binary not found or not executable: $MASSCAN_BIN"
            return 1
        fi
    fi
    
    # Check current directory for masscan
    if [[ -x "./masscan" ]]; then
        echo "./masscan"
        return 0
    fi
    
    # Check if masscan is in PATH
    if command -v masscan &> /dev/null; then
        echo "masscan"
        return 0
    fi
    
    # Check common locations
    if [[ -x "/usr/bin/masscan" ]]; then
        echo "/usr/bin/masscan"
        return 0
    fi
    
    if [[ -x "/usr/local/bin/masscan" ]]; then
        echo "/usr/local/bin/masscan"
        return 0
    fi
    
    return 1
}

# Function to convert masscan output
convert_masscan_output() {
    local input_file="${1:-client_resolvers_masscan.txt}"
    local output_file="${2:-client_resolvers.txt}"
    
    print_info "Converting masscan output from $input_file to $output_file..."
    
    if [[ ! -f "$input_file" ]]; then
        print_error "$input_file not found!"
        return 1
    fi
    
    # Extract IPs from masscan output (4th field in -oL format)
    grep "^open" "$input_file" | awk '{print $4}' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | sort -u > "$output_file"
    
    local ip_count=$(wc -l < "$output_file")
    print_success "Converted $ip_count IP addresses to $output_file"
    return 0
}

# Function to run masscan
run_masscan() {
    local ip_range="$1"
    
    print_info "Running masscan on ${ip_range}:53..."
    
    # Find masscan binary
    local masscan_path=$(find_masscan)
    if [[ -z "$masscan_path" ]]; then
        print_error "masscan not found. Please install masscan first or specify path with --masscan-bin"
        print_info "Ubuntu/Debian: sudo apt-get install masscan"
        print_info "Arch: sudo pacman -S masscan"
        print_info "Or compile from source: https://github.com/robertdavidgraham/masscan"
        print_info "Or if masscan is in current directory, use: --masscan-bin ./masscan"
        return 1
    fi
    
    print_success "Found masscan: $masscan_path"
    
    # Build masscan command (Linux doesn't need router-mac)
    local masscan_cmd="sudo $masscan_path $ip_range -p53 --rate=10000 -oL client_resolvers_masscan.txt"
    
    print_info "Running: $masscan_cmd"
    
    # Run masscan (requires sudo on Linux)
    if eval "$masscan_cmd"; then
        print_success "Masscan completed successfully"
        convert_masscan_output
        return 0
    else
        print_error "Masscan failed"
        return 1
    fi
}

# Function to run VPN client and monitor output
run_vpn_client() {
    local round_num="$1"
    local max_rounds="$2"
    
    echo ""
    print_info "Starting round $round_num/$max_rounds..."
    
    # Check if VPN client exists
    if [[ ! -f "$VPN_CLIENT_BIN" ]]; then
        # Try to find any VPN client binary
        local found_bin=$(ls -1 MasterDnsVPN_Client_Linux* 2>/dev/null | head -n1)
        if [[ -n "$found_bin" ]]; then
            VPN_CLIENT_BIN="./$found_bin"
            print_info "Found VPN client: $VPN_CLIENT_BIN"
        else
            print_error "VPN client executable not found"
            return 1
        fi
    fi
    
    # Make sure it's executable
    chmod +x "$VPN_CLIENT_BIN"
    
    print_info "Monitoring output for 'Session init attempt'..."
    
    # Create a temporary file for output
    local temp_output=$(mktemp)
    
    # Run VPN client and capture output
    "$VPN_CLIENT_BIN" 2>&1 | while IFS= read -r line; do
        echo "[VPN Client] $line"
        echo "$line" >> "$temp_output"
        
        if [[ "$line" == *"Session init attempt"* ]]; then
            print_success "Trigger phrase detected! Stopping this round..."
            # Kill the VPN client process
            pkill -f "$(basename "$VPN_CLIENT_BIN")" 2>/dev/null || true
            return 0
        fi
    done
    
    # Check if trigger was found
    if grep -q "Session init attempt" "$temp_output"; then
        rm -f "$temp_output"
        return 0
    else
        print_warning "VPN client ended without encountering the trigger phrase"
        rm -f "$temp_output"
        return 1
    fi
}

# Alternative method using timeout and background process
run_vpn_client_alternative() {
    local round_num="$1"
    local max_rounds="$2"
    
    echo ""
    print_info "Starting round $round_num/$max_rounds (alternative method)..."
    
    # Check if VPN client exists
    if [[ ! -f "$VPN_CLIENT_BIN" ]]; then
        local found_bin=$(ls -1 MasterDnsVPN_Client_Linux* 2>/dev/null | head -n1)
        if [[ -n "$found_bin" ]]; then
            VPN_CLIENT_BIN="./$found_bin"
        else
            print_error "VPN client executable not found"
            return 1
        fi
    fi
    
    chmod +x "$VPN_CLIENT_BIN"
    
    # Create named pipe for output monitoring
    local pipe_file=$(mktemp -u)
    mkfifo "$pipe_file"
    
    # Start VPN client in background, redirect output to pipe
    "$VPN_CLIENT_BIN" > "$pipe_file" 2>&1 &
    local vpn_pid=$!
    
    print_info "Monitoring output for 'Session init attempt'..."
    
    # Monitor the pipe for trigger phrase
    local found_trigger=false
    while IFS= read -r line; do
        echo "[VPN Client] $line"
        
        if [[ "$line" == *"Session init attempt"* ]]; then
            print_success "Trigger phrase detected! Stopping this round..."
            found_trigger=true
            break
        fi
    done < "$pipe_file"
    
    # Clean up
    rm -f "$pipe_file"
    
    # Kill VPN client if still running
    if kill -0 "$vpn_pid" 2>/dev/null; then
        kill -TERM "$vpn_pid" 2>/dev/null
        sleep 1
        kill -KILL "$vpn_pid" 2>/dev/null || true
    fi
    
    if [[ "$found_trigger" == "true" ]]; then
        return 0
    else
        print_warning "VPN client ended without encountering the trigger phrase"
        return 1
    fi
}

# Function to analyze DNS results
analyze_dns_results() {
    local tmp_folder="${1:-tmp}"
    local output_file="${2:-top_dnses.txt}"
    local top_n="${3:-10}"
    
    echo ""
    print_header "STEP 3: Analyzing DNS query results"
    
    if [[ ! -d "$tmp_folder" ]]; then
        print_warning "$tmp_folder folder not found!"
        return 1
    fi
    
    # Find all result files
    local round_files=$(find "$tmp_folder" -type f \( -name "*.txt" -o -name "*.log" \) 2>/dev/null)
    
    if [[ -z "$round_files" ]]; then
        print_error "No result files found in $tmp_folder/"
        return 1
    fi
    
    local file_count=$(echo "$round_files" | wc -l)
    print_success "Found $file_count result files"
    
    # Extract DNS server IPs
    local temp_dns_file=$(mktemp)
    
    while IFS= read -r file; do
        local filename=$(basename "$file")
        
        # Extract IPs that appear with DNS-related context
        local dns_ips=$(grep -iE "(DNS Server|nameserver|resolver|query).*[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" "$file" 2>/dev/null | \
                       grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | \
                       grep -v '^127\.' | \
                       sort -u)
        
        if [[ -n "$dns_ips" ]]; then
            local dns_count=$(echo "$dns_ips" | wc -l)
            print_success "$filename: Found $dns_count DNS server(s)"
            echo "$dns_ips" >> "$temp_dns_file"
        else
            print_warning "$filename: No DNS servers found"
        fi
    done <<< "$round_files"
    
    if [[ ! -s "$temp_dns_file" ]]; then
        print_error "No DNS servers found in any result files"
        rm -f "$temp_dns_file"
        return 1
    fi
    
    # Count frequencies
    local total_occurrences=$(wc -l < "$temp_dns_file")
    local unique_dnses=$(sort -u "$temp_dns_file" | wc -l)
    
    echo ""
    print_success "Analysis Results:"
    echo "    Total DNS server occurrences: $total_occurrences"
    echo "    Unique DNS servers found: $unique_dnses"
    echo "    Result files analyzed: $file_count"
    
    # Show top N DNS servers
    echo ""
    print_success "Top $top_n DNS servers:"
    
    # Create detailed analysis
    local analysis_file="$tmp_folder/dns_analysis.txt"
    
    {
        echo "DNS Analysis Results"
        echo "==================="
        echo ""
        echo "Analysis Date: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Files Analyzed: $file_count"
        echo "Total DNS Occurrences: $total_occurrences"
        echo "Unique DNS Servers: $unique_dnses"
        echo ""
        echo "Top $top_n DNS Servers:"
        echo "----------------------------------------"
    } > "$analysis_file"
    
    # Sort and count, show top N
    local rank=1
    sort "$temp_dns_file" | uniq -c | sort -rn | head -n "$top_n" | while read -r count ip; do
        local pct=$(echo "scale=1; $count * 100 / $total_occurrences" | bc 2>/dev/null || echo "0")
        echo "    $rank. $ip - $count times (${pct}%)"
        
        # Save to analysis file
        echo "$rank. $ip: $count occurrences (${pct}%)" >> "$analysis_file"
        
        # Save IP to output file
        echo "$ip"
        
        ((rank++))
    done > "$output_file.tmp"
    
    # Add header to output file
    {
        echo "# Top DNS Servers Analysis"
        echo "# Analysis Date: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "# Total Files Analyzed: $file_count"
        echo "# Total DNS Occurrences: $total_occurrences"
        echo "# Unique DNS Servers: $unique_dnses"
        echo "#"
        echo "# IP Addresses (one per line, sorted by frequency):"
        cat "$output_file.tmp"
    } > "$output_file"
    
    rm -f "$output_file.tmp"
    
    # Complete analysis file
    {
        echo ""
        echo "Complete Ranking:"
        echo "----------------------------------------"
        sort "$temp_dns_file" | uniq -c | sort -rn | while read -r count ip; do
            local pct=$(echo "scale=1; $count * 100 / $total_occurrences" | bc 2>/dev/null || echo "0")
            echo "$ip: $count (${pct}%)"
        done
    } >> "$analysis_file"
    
    rm -f "$temp_dns_file"
    
    echo ""
    print_success "Top DNS servers saved to $output_file"
    print_success "Detailed analysis saved to $analysis_file"
    
    return 0
}

# Main execution
main() {
    # If analyze-only mode, just run analysis and exit
    if [[ "$ANALYZE_ONLY" == "true" ]]; then
        print_info "Running in analyze-only mode"
        analyze_dns_results "$TMP_FOLDER" "$OUTPUT_FILE" "$TOP_N"
        exit $?
    fi
    
    # Get IP range if not skipping masscan
    if [[ "$SKIP_MASSCAN" == "false" ]] && [[ -z "$IP_RANGE" ]]; then
        read -p "Enter IP range (e.g., 5.0.0.0/8): " IP_RANGE
        
        if [[ -z "$IP_RANGE" ]]; then
            print_error "No IP range provided. Exiting."
            exit 1
        fi
    fi
    
    # Get number of rounds if not provided
    if [[ -z "$ROUNDS" ]]; then
        read -p "Enter number of rounds (default: 10): " input_rounds
        ROUNDS="${input_rounds:-10}"
    fi
    
    # Display configuration
    echo ""
    print_success "Configuration:"
    if [[ "$SKIP_MASSCAN" == "true" ]]; then
        echo "    Mode: SKIP MASSCAN (using existing resolvers file)"
        echo "    Resolvers file: $RESOLVERS_FILE"
    else
        echo "    IP Range: $IP_RANGE"
        echo "    Masscan rate: 10000 packets/sec"
        echo "    Masscan raw output: client_resolvers_masscan.txt"
        echo "    Final resolvers file: client_resolvers.txt"
        # Show masscan binary location
        local masscan_path=$(find_masscan)
        if [[ -n "$masscan_path" ]]; then
            echo "    Masscan binary: $masscan_path"
        fi
    fi
    echo "    Rounds: $ROUNDS"
    echo "    Results folder: $TMP_FOLDER/ (auto-created by VPN client)"
    echo "    Output file: $OUTPUT_FILE"
    echo "    Top N DNS servers: $TOP_N"
    if [[ "$USE_ALTERNATIVE" == "true" ]]; then
        echo "    Method: ALTERNATIVE"
    fi
    echo ""
    echo "=================================================="
    
    # Step 1: Run masscan
    if [[ "$SKIP_MASSCAN" == "false" ]]; then
        echo ""
        print_header "STEP 1: Running masscan"
        if ! run_masscan "$IP_RANGE"; then
            print_error "Masscan failed. Exiting."
            exit 1
        fi
        sleep 2
    else
        echo ""
        print_header "STEP 1: Skipping masscan as requested"
        if [[ ! -f "$RESOLVERS_FILE" ]]; then
            print_warning "$RESOLVERS_FILE not found!"
            read -p "Continue anyway? (y/n): " response
            if [[ "$response" != "y" ]]; then
                print_warning "Exiting."
                exit 0
            fi
        else
            print_success "Using existing resolvers file: $RESOLVERS_FILE"
        fi
    fi
    
    # Step 2: Run VPN client rounds
    echo ""
    print_header "STEP 2: Running VPN client rounds"
    print_info "VPN client will automatically save results to $TMP_FOLDER/"
    
    local successful_rounds=0
    
    # Choose which method to use
    local vpn_func="run_vpn_client"
    if [[ "$USE_ALTERNATIVE" == "true" ]]; then
        vpn_func="run_vpn_client_alternative"
    fi
    
    for ((round_num=1; round_num<=ROUNDS; round_num++)); do
        if $vpn_func "$round_num" "$ROUNDS"; then
            ((successful_rounds++))
        else
            print_error "Round $round_num encountered an issue. Continuing to next round..."
        fi
        
        if [[ $round_num -lt $ROUNDS ]]; then
            print_info "Waiting 2 seconds before next round..."
            sleep 2
        fi
    done
    
    # Step 3: Analyze results
    analyze_dns_results "$TMP_FOLDER" "$OUTPUT_FILE" "$TOP_N"
    
    # Summary
    echo ""
    print_header "All operations completed!"
    if [[ "$SKIP_MASSCAN" == "false" ]]; then
        echo "[*] Masscan raw results saved to client_resolvers_masscan.txt"
        echo "[*] Converted resolvers saved to client_resolvers.txt"
    fi
    echo "[*] VPN client results automatically saved to $TMP_FOLDER/"
    echo "[*] Completed $successful_rounds/$ROUNDS successful rounds"
    
    if [[ -f "$OUTPUT_FILE" ]]; then
        echo "[*] Top DNS servers saved to $OUTPUT_FILE"
        local top_dns=$(head -n 6 "$OUTPUT_FILE" | tail -n 1)
        if [[ -n "$top_dns" ]]; then
            echo "[*] Most frequent DNS server: $top_dns"
        fi
    else
        print_warning "Could not determine top DNS servers"
    fi
    
    if [[ $successful_rounds -lt $ROUNDS ]]; then
        print_warning "$((ROUNDS - successful_rounds)) rounds failed or were interrupted"
    fi
}

# Check if running as root for masscan
if [[ "$SKIP_MASSCAN" == "false" ]] && [[ "$EUID" -ne 0 ]]; then
    print_warning "Masscan typically requires root privileges on Linux"
    print_info "You may be prompted for sudo password during masscan execution"
    echo ""
fi

# Run main function
main