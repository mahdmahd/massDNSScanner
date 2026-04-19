import subprocess
import time
import signal
import sys
import argparse
import os
import re
from collections import Counter
from pathlib import Path

def discover_gateway_mac():
    """Run arp -a and extract the gateway MAC address"""
    print("[*] Discovering gateway MAC address...")
    
    try:
        # Run arp -a command
        result = subprocess.run(
            ["arp", "-a"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode != 0:
            print("[-] Failed to run arp -a command")
            return None
        
        # Parse the output to find the gateway
        lines = result.stdout.split('\n')
        gateway_mac = None
        gateway_ip = None
        
        # Pattern 1: Look for IPs ending with .1 (common gateway)
        for line in lines:
            # Match pattern: IP Address, Physical Address, Type
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+([0-9A-Fa-f-]{17})\s+dynamic', line)
            if match:
                ip = match.group(1)
                mac = match.group(2)
                
                # Check if it's likely a gateway (ends with .1 or .254)
                if ip.endswith('.1') or ip.endswith('.254'):
                    gateway_ip = ip
                    gateway_mac = mac
                    print(f"[+] Found gateway: {gateway_ip} -> {gateway_mac}")
                    break
        
        # If not found, just take the first dynamic entry
        if not gateway_mac:
            for line in lines:
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+([0-9A-Fa-f-]{17})\s+dynamic', line)
                if match:
                    gateway_ip = match.group(1)
                    gateway_mac = match.group(2)
                    print(f"[+] Using first dynamic entry: {gateway_ip} -> {gateway_mac}")
                    break
        
        if gateway_mac:
            # Convert MAC to format expected by masscan (colon-separated)
            if '-' in gateway_mac:
                gateway_mac = gateway_mac.replace('-', ':')
            print(f"[+] Gateway MAC address: {gateway_mac}")
            return gateway_mac
        else:
            print("[-] No gateway MAC address found in arp table")
            return None
            
    except FileNotFoundError:
        print("[-] 'arp' command not found. Make sure you're on Windows with proper PATH")
        return None
    except Exception as e:
        print(f"[-] Error discovering gateway MAC: {e}")
        return None

def get_default_gateway_alternative():
    """Alternative method to get default gateway using ipconfig or route"""
    try:
        # Try using 'route print' to find default gateway
        result = subprocess.run(
            ["route", "print", "0.0.0.0"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode == 0:
            # Parse route output to find gateway
            for line in result.stdout.split('\n'):
                # Look for lines with 0.0.0.0 and gateway
                if '0.0.0.0' in line:
                    parts = line.split()
                    for part in parts:
                        if re.match(r'\d+\.\d+\.\d+\.\d+', part):
                            gateway_ip = part
                            print(f"[+] Found default gateway IP: {gateway_ip}")
                            
                            # Now get MAC for this IP
                            arp_result = subprocess.run(
                                ["arp", "-a", gateway_ip],
                                capture_output=True,
                                text=True,
                                encoding='utf-8',
                                errors='replace'
                            )
                            
                            # Parse MAC from arp output
                            mac_match = re.search(r'([0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2})', arp_result.stdout)
                            if mac_match:
                                mac = mac_match.group(1).replace('-', ':')
                                print(f"[+] Gateway MAC: {mac}")
                                return mac
                            break
    except Exception as e:
        print(f"[-] Alternative gateway detection failed: {e}")
    
    return None

def convert_masscan_output(input_file="client_resolvers_masscan.txt", output_file="client_resolvers.txt"):
    """Convert masscan output format to simple IP list (one per line)"""
    print(f"[*] Converting masscan output from {input_file} to {output_file}...")
    
    if not os.path.exists(input_file):
        print(f"[-] {input_file} not found!")
        return False
    
    try:
        ips = []
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Skip comment lines
                if line.startswith('#'):
                    if line.startswith('#masscan'):
                        continue
                    elif line.startswith('# end'):
                        continue
                else:
                    # Extract IP address (4th field in masscan -oL format)
                    parts = line.strip().split()
                    if len(parts) >= 4 and parts[0] == 'open':
                        ip = parts[3]
                        if re.match(r'\d+\.\d+\.\d+\.\d+', ip):
                            ips.append(ip)
        
        # Write IPs to output file (one per line)
        with open(output_file, 'w', encoding='utf-8') as f:
            for ip in ips:
                f.write(f"{ip}\n")
        
        print(f"[+] Converted {len(ips)} IP addresses to {output_file}")
        return True
        
    except Exception as e:
        print(f"[-] Error converting masscan output: {e}")
        return False

def run_masscan(ip_range, router_mac=None):
    """Run masscan on the specified IP range and port 53"""
    print(f"[*] Running masscan on {ip_range}:53...")
    
    masscan_cmd = [
        ".\\masscan.exe",
        ip_range,
        "-p53",
        "--rate=10000",
        "-oL",
        "client_resolvers_masscan.txt"
    ]
    
    # Add router-mac flag if provided
    if router_mac:
        masscan_cmd.append(f"--router-mac={router_mac}")
        print(f"[*] Using router MAC: {router_mac}")
    
    try:
        subprocess.run(masscan_cmd, check=True)
        print("[+] Masscan completed successfully")
        
        # Convert the output to simple IP list format
        convert_masscan_output("client_resolvers_masscan.txt", "client_resolvers.txt")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"[-] Masscan failed with error: {e}")
        return False
    except FileNotFoundError:
        print("[-] masscan.exe not found in current directory")
        return False

def run_vpn_client(round_num, max_rounds):
    """Run the VPN client and stop when 'Session init attempt' appears"""
    print(f"\n[*] Starting round {round_num}/{max_rounds}...")
    
    vpn_cmd = [
        ".\\MasterDnsVPN_Client_Windows_AMD64_v2026.04.12.234117-978faee.exe"
    ]
    
    try:
        # Start the process with binary mode and handle encoding properly
        process = subprocess.Popen(
            vpn_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1
        )
        
        # Monitor output for the trigger phrase
        print("[*] Monitoring output for 'Session init attempt'...")
        
        # Use binary mode and handle decoding errors gracefully
        for line_bytes in process.stdout:
            try:
                # Try to decode with UTF-8 first, then fall back to latin-1 or ignore errors
                try:
                    line = line_bytes.decode('utf-8', errors='ignore')
                except UnicodeDecodeError:
                    try:
                        line = line_bytes.decode('latin-1')
                    except UnicodeDecodeError:
                        line = line_bytes.decode('cp1252', errors='replace')
                
                # Print the line (strip newlines)
                print(f"[VPN Client] {line.strip()}")
                
                # Check for trigger phrase
                if "Session init attempt" in line:
                    print("[+] Trigger phrase detected! Stopping this round...")
                    process.terminate()
                    time.sleep(1)
                    if process.poll() is None:
                        process.kill()
                    return True
                    
            except Exception as e:
                # If we can't decode, just show the raw bytes representation
                print(f"[VPN Client] [RAW BYTES: {line_bytes[:50]}...]")
                
                # Still check for trigger phrase in raw bytes
                if b"Session init attempt" in line_bytes:
                    print("[+] Trigger phrase detected in raw output! Stopping this round...")
                    process.terminate()
                    time.sleep(1)
                    if process.poll() is None:
                        process.kill()
                    return True
        
        # If we get here, the process ended without finding the phrase
        process.wait()
        print("[!] VPN client ended without encountering the trigger phrase")
        return False
        
    except FileNotFoundError:
        print("[-] VPN client executable not found in current directory")
        return False
    except Exception as e:
        print(f"[-] Error running VPN client: {e}")
        return False

def run_vpn_client_alternative(round_num, max_rounds):
    """Alternative method: Run without capturing output, just look for the phrase via regex"""
    print(f"\n[*] Starting round {round_num}/{max_rounds}...")
    
    vpn_cmd = [
        ".\\MasterDnsVPN_Client_Windows_AMD64_v2026.04.12.234117-978faee.exe"
    ]
    
    try:
        # Use CREATE_NO_WINDOW flag to avoid console issues (Windows specific)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        # Run with universal_newlines=False to handle raw bytes
        process = subprocess.Popen(
            vpn_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,  # Unbuffered
            startupinfo=startupinfo
        )
        
        print("[*] Monitoring output for 'Session init attempt'...")
        
        # Read byte by byte to find the trigger
        buffer = b""
        trigger = b"Session init attempt"
        
        while True:
            # Read one byte at a time to catch the exact moment
            byte = process.stdout.read(1)
            if not byte:
                break
                
            buffer += byte
            
            # Keep buffer manageable
            if len(buffer) > 1000:
                buffer = buffer[-1000:]
            
            # Check if trigger is in buffer
            if trigger in buffer:
                print("\n[+] Trigger phrase detected! Stopping this round...")
                # Try to print recent output
                try:
                    recent = buffer[-200:].decode('utf-8', errors='replace')
                    print(f"[Last output: {recent}]")
                except:
                    pass
                
                process.terminate()
                time.sleep(1)
                if process.poll() is None:
                    process.kill()
                return True
            
            # Print occasionally to show progress (every ~100 bytes)
            if len(buffer) % 100 == 0 and len(buffer) > 0:
                try:
                    # Try to print the last line
                    lines = buffer.split(b'\n')
                    if lines[-1]:
                        last_line = lines[-1].decode('utf-8', errors='replace')
                        if last_line.strip():
                            print(f"[VPN Client] {last_line.strip()}")
                except:
                    pass
        
        process.wait()
        print("[!] VPN client ended without encountering the trigger phrase")
        return False
        
    except FileNotFoundError:
        print("[-] VPN client executable not found in current directory")
        return False
    except Exception as e:
        print(f"[-] Error running VPN client: {e}")
        return False

def analyze_dns_results(tmp_folder="tmp", output_file="top_dnses.txt", top_n=10):
    """
    Analyze DNS query results from all round files in tmp folder
    and return the most frequent DNS server IPs
    """
    print("\n" + "="*50)
    print("[STEP 3] Analyzing DNS query results...")
    print("="*50)
    
    tmp_path = Path(tmp_folder)
    
    # Check if tmp folder exists
    if not tmp_path.exists():
        print(f"[-] Warning: {tmp_folder} folder not found!")
        return None
    
    # Find all round result files (looking for any txt files that might contain DNS results)
    # The VPN client likely creates files with specific naming patterns
    round_files = list(tmp_path.glob("*.txt")) + list(tmp_path.glob("*.log"))
    
    if not round_files:
        print(f"[-] No result files found in {tmp_folder}/")
        return None
    
    print(f"[+] Found {len(round_files)} result files")
    
    # Extract all DNS server IPs
    all_dns_servers = []
    dns_details = {}  # Store details about where each DNS was found
    
    for file_path in round_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Extract DNS server IPs from the file
                # Look for patterns like "DNS Server: X.X.X.X" or IP addresses in context
                dns_matches = re.findall(r'DNS Server[s]?:\s*(\d+\.\d+\.\d+\.\d+)', content, re.IGNORECASE)
                
                if not dns_matches:
                    # Alternative: look for any IP addresses that appear with DNS-related keywords
                    lines = content.split('\n')
                    for line in lines:
                        if any(keyword in line.lower() for keyword in ['dns', 'nameserver', 'resolver', 'query']):
                            ip_matches = re.findall(r'\b(\d+\.\d+\.\d+\.\d+)\b', line)
                            dns_matches.extend(ip_matches)
                
                # Also look for IP addresses in general (since the output format might vary)
                if not dns_matches:
                    # Extract all IP addresses and assume they might be DNS servers
                    all_ips = re.findall(r'\b(\d+\.\d+\.\d+\.\d+)\b', content)
                    # Filter out common non-DNS IPs (like localhost, private IPs might still be DNS)
                    dns_matches = [ip for ip in all_ips if not ip.startswith('127.')]
                
                if dns_matches:
                    all_dns_servers.extend(dns_matches)
                    
                    # Store details for each DNS
                    for dns in dns_matches:
                        if dns not in dns_details:
                            dns_details[dns] = []
                        dns_details[dns].append(file_path.name)
                    
                    print(f"[+] {file_path.name}: Found {len(dns_matches)} DNS server(s)")
                else:
                    print(f"[!] {file_path.name}: No DNS servers found")
                    
        except Exception as e:
            print(f"[-] Error reading {file_path}: {e}")
    
    if not all_dns_servers:
        print("[-] No DNS servers found in any result files")
        return None
    
    # Count frequencies
    dns_counter = Counter(all_dns_servers)
    
    # Get the top N DNS servers
    top_dnses = dns_counter.most_common(top_n)
    
    if not top_dnses:
        print("[-] Could not determine top DNS servers")
        return None
    
    # Calculate statistics
    total_occurrences = len(all_dns_servers)
    
    print(f"\n[+] Analysis Results:")
    print(f"    Total DNS server occurrences: {total_occurrences}")
    print(f"    Unique DNS servers found: {len(dns_counter)}")
    print(f"    Result files analyzed: {len(round_files)}")
    
    # Show top N DNS servers
    print(f"\n[+] Top {min(top_n, len(top_dnses))} DNS servers:")
    for i, (dns, count) in enumerate(top_dnses, 1):
        pct = (count / total_occurrences) * 100
        files_count = len(dns_details.get(dns, []))
        print(f"    {i}. {dns} - {count} times ({pct:.1f}%) - found in {files_count} files")
    
    # Save to output file (one IP per line, sorted by frequency)
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Top DNS Servers Analysis\n")
            f.write(f"# Analysis Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total Files Analyzed: {len(round_files)}\n")
            f.write(f"# Total DNS Occurrences: {total_occurrences}\n")
            f.write(f"# Unique DNS Servers: {len(dns_counter)}\n")
            f.write(f"#\n")
            f.write(f"# Format: IP_ADDRESS - Frequency - Percentage - Files\n")
            f.write(f"#\n\n")
            
            for dns, count in top_dnses:
                pct = (count / total_occurrences) * 100
                files_count = len(dns_details.get(dns, []))
                f.write(f"# {dns} - {count} occurrences ({pct:.1f}%) - found in {files_count} files\n")
            
            f.write(f"\n# IP Addresses (one per line, sorted by frequency):\n")
            for dns, count in top_dnses:
                f.write(f"{dns}\n")
        
        print(f"\n[+] Top DNS servers saved to {output_file}")
        
        # Also save detailed analysis to tmp folder
        analysis_file = tmp_path / "dns_analysis.txt"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            f.write(f"DNS Analysis Results\n")
            f.write(f"===================\n\n")
            f.write(f"Analysis Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Files Analyzed: {len(round_files)}\n")
            f.write(f"Total DNS Occurrences: {total_occurrences}\n")
            f.write(f"Unique DNS Servers: {len(dns_counter)}\n\n")
            f.write(f"Top {top_n} DNS Servers:\n")
            f.write("-" * 40 + "\n")
            for i, (dns, count) in enumerate(top_dnses, 1):
                pct = (count / total_occurrences) * 100
                files_count = len(dns_details.get(dns, []))
                f.write(f"{i}. {dns}: {count} occurrences ({pct:.1f}%) - in {files_count} files\n")
            
            f.write(f"\n\nComplete Ranking:\n")
            f.write("-" * 40 + "\n")
            for dns, count in dns_counter.most_common():
                pct = (count / total_occurrences) * 100
                f.write(f"{dns}: {count} ({pct:.1f}%)\n")
            
            f.write(f"\n\nDNS Details by File:\n")
            f.write("-" * 40 + "\n")
            for dns, files in sorted(dns_details.items(), key=lambda x: len(x[1]), reverse=True):
                f.write(f"\n{dns} (found in {len(files)} files):\n")
                for file in files:
                    f.write(f"  - {file}\n")
        
        print(f"[+] Detailed analysis saved to {analysis_file}")
        
    except Exception as e:
        print(f"[-] Error saving results: {e}")
    
    return [dns for dns, _ in top_dnses]

def main():
    """Main function to orchestrate the entire process"""
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='DNS Scanner with Masscan and VPN Client',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dns_scanner.py                      # Interactive mode
  python dns_scanner.py -r 5.0.0.0/8        # Specify IP range
  python dns_scanner.py -r 5.0.0.0/8 -n 20  # IP range and 20 rounds
  python dns_scanner.py --skip-masscan       # Skip masscan, use existing resolvers file
  python dns_scanner.py -s -n 5             # Skip masscan, run 5 rounds
  python dns_scanner.py --alternative        # Use alternative method for encoding issues
  python dns_scanner.py --no-mac-discovery   # Skip MAC address discovery
  python dns_scanner.py --router-mac XX:XX:XX:XX:XX:XX  # Manually specify router MAC
  python dns_scanner.py --analyze-only       # Only analyze existing tmp folder results
  python dns_scanner.py --top-n 20          # Show top 20 DNS servers instead of default 10
        """
    )
    
    parser.add_argument(
        '-r', '--range',
        type=str,
        help='IP range in CIDR notation (e.g., 5.0.0.0/8)'
    )
    
    parser.add_argument(
        '-n', '--rounds',
        type=int,
        help='Number of VPN client rounds (default: 10)'
    )
    
    parser.add_argument(
        '-s', '--skip-masscan',
        action='store_true',
        help='Skip masscan scan and use existing client_resolvers.txt'
    )
    
    parser.add_argument(
        '-f', '--resolvers-file',
        type=str,
        default='client_resolvers.txt',
        help='Resolvers file to use when skipping masscan (default: client_resolvers.txt)'
    )
    
    parser.add_argument(
        '-a', '--alternative',
        action='store_true',
        help='Use alternative method (byte-by-byte reading) to handle encoding issues'
    )
    
    parser.add_argument(
        '--no-mac-discovery',
        action='store_true',
        help='Skip automatic MAC address discovery'
    )
    
    parser.add_argument(
        '--router-mac',
        type=str,
        help='Manually specify router MAC address (e.g., 22:51:70:c1:3d:91)'
    )
    
    parser.add_argument(
        '--analyze-only',
        action='store_true',
        help='Only analyze existing tmp folder results (skip scanning)'
    )
    
    parser.add_argument(
        '--tmp-folder',
        type=str,
        default='tmp',
        help='Temporary folder for round results (default: tmp)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='top_dnses.txt',
        help='Output file for top DNS results (default: top_dnses.txt)'
    )
    
    parser.add_argument(
        '--top-n',
        type=int,
        default=10,
        help='Number of top DNS servers to output (default: 10)'
    )
    
    args = parser.parse_args()
    
    # If analyze-only mode, just run analysis and exit
    if args.analyze_only:
        print("[*] Running in analyze-only mode")
        top_dnses = analyze_dns_results(args.tmp_folder, args.output, args.top_n)
        if top_dnses:
            print(f"\n[+] Top {len(top_dnses)} DNS servers saved to {args.output}")
        else:
            print("\n[-] Analysis failed to find DNS servers")
        return
    
    # Get IP range if not skipping masscan
    ip_range = args.range
    if not args.skip_masscan and not ip_range:
        ip_range = input("Enter IP range (e.g., 5.0.0.0/8): ").strip()
        
        # Validate input
        if not ip_range:
            print("[-] No IP range provided. Exiting.")
            return
    
    # Get number of rounds
    rounds = args.rounds
    if rounds is None:
        try:
            rounds = int(input("Enter number of rounds (default: 10): ").strip() or "10")
        except ValueError:
            print("[!] Invalid input, using default of 10 rounds")
            rounds = 10
    
    # Set encoding for stdout to handle Unicode better
    if sys.platform == 'win32':
        # Try to set console to UTF-8 mode
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except:
            pass
    
    # Discover gateway MAC address (if not skipping masscan)
    router_mac = args.router_mac
    if not args.skip_masscan and not args.no_mac_discovery and not router_mac:
        print("\n" + "="*50)
        print("[STEP 0] Discovering Gateway MAC Address")
        print("="*50)
        
        # Try primary method
        router_mac = discover_gateway_mac()
        
        # If primary method fails, try alternative
        if not router_mac:
            print("[*] Trying alternative gateway detection method...")
            router_mac = get_default_gateway_alternative()
        
        if router_mac:
            print(f"[+] Successfully discovered gateway MAC: {router_mac}")
        else:
            print("[!] Could not discover gateway MAC automatically")
            print("[!] Masscan will run without --router-mac flag")
            response = input("Continue anyway? (y/n): ").lower()
            if response != 'y':
                print("[!] Exiting.")
                return
    elif router_mac:
        print(f"[+] Using manually specified router MAC: {router_mac}")
    
    # Display configuration
    print(f"\n[+] Configuration:")
    if args.skip_masscan:
        print(f"    Mode: SKIP MASSCAN (using existing resolvers file)")
        print(f"    Resolvers file: {args.resolvers_file}")
    else:
        print(f"    IP Range: {ip_range}")
        print(f"    Masscan rate: 10000 packets/sec")
        print(f"    Masscan raw output: client_resolvers_masscan.txt")
        print(f"    Final resolvers file: client_resolvers.txt")
        if router_mac:
            print(f"    Router MAC: {router_mac}")
        else:
            print(f"    Router MAC: Not specified")
    print(f"    Rounds: {rounds}")
    print(f"    Results folder: {args.tmp_folder}/ (auto-created by VPN client)")
    print(f"    Output file: {args.output}")
    print(f"    Top N DNS servers: {args.top_n}")
    if args.alternative:
        print(f"    Method: ALTERNATIVE (byte-by-byte reading)")
    print("\n" + "="*50)
    
    # Step 1: Run masscan (unless skipped)
    if not args.skip_masscan:
        print("\n[STEP 1] Running masscan...")
        if not run_masscan(ip_range, router_mac):
            print("[-] Masscan failed. Exiting.")
            return
        
        # Wait a moment for file to be written
        time.sleep(2)
    else:
        print("\n[STEP 1] Skipping masscan as requested")
        # Check if resolvers file exists
        if not os.path.exists(args.resolvers_file):
            print(f"[-] Warning: {args.resolvers_file} not found!")
            response = input("Continue anyway? (y/n): ").lower()
            if response != 'y':
                print("[!] Exiting.")
                return
        else:
            print(f"[+] Using existing resolvers file: {args.resolvers_file}")
    
    # Step 2: Run multiple rounds of VPN client
    print("\n[STEP 2] Running VPN client rounds...")
    print(f"[*] VPN client will automatically save results to {args.tmp_folder}/")
    successful_rounds = 0
    
    # Choose which method to use
    vpn_client_func = run_vpn_client_alternative if args.alternative else run_vpn_client
    
    for round_num in range(1, rounds + 1):
        success = vpn_client_func(round_num, rounds)
        if success:
            successful_rounds += 1
        else:
            print(f"[-] Round {round_num} encountered an issue. Continuing to next round...")
        
        # Small delay between rounds
        if round_num < rounds:
            print("[*] Waiting 2 seconds before next round...")
            time.sleep(2)
    
    # Step 3: Analyze results and find most frequent DNS
    print("\n" + "="*50)
    print("[STEP 3] Analyzing results...")
    print("="*50)
    
    top_dnses = analyze_dns_results(args.tmp_folder, args.output, args.top_n)
    
    print("\n" + "="*50)
    print("[+] All operations completed!")
    if not args.skip_masscan:
        print(f"[*] Masscan raw results saved to client_resolvers_masscan.txt")
        print(f"[*] Converted resolvers saved to client_resolvers.txt")
    print(f"[*] VPN client results automatically saved to {args.tmp_folder}/")
    print(f"[*] Completed {successful_rounds}/{rounds} successful rounds")
    
    if top_dnses:
        print(f"[*] Top {len(top_dnses)} DNS servers saved to {args.output}")
        if top_dnses:
            print(f"[*] Most frequent DNS server: {top_dnses[0]}")
    else:
        print(f"[!] Could not determine top DNS servers")
    
    if successful_rounds < rounds:
        print(f"[!] {rounds - successful_rounds} rounds failed or were interrupted")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n[!] Script interrupted by user. Exiting...")
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run main function
    main()